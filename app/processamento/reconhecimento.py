
import json
import time
import threading

import numpy as np
from insightface.app import FaceAnalysis

from app.integracao.banco import conectar_banco


# ==================================================
# CONFIGURAÇÕES ORIGINAIS DO RECONHECIMENTO
# ==================================================

LIMIAR_RECONHECIMENTO = 1.0
LIMIAR_REARME = 0.8
TEMPO_REARME = 3.0

# Modelo carregado uma única vez por processo.
_modelo = None
_lock_modelo = threading.Lock()

# Controle de rostos ativos, conforme o sistema original.
rostos_ativos = []
_lock_reconhecimento = threading.Lock()


# ==================================================
# CARREGAMENTO DO INSIGHTFACE
# ==================================================

def obter_modelo():
    global _modelo

    if _modelo is None:
        with _lock_modelo:
            if _modelo is None:
                modelo = FaceAnalysis(name="buffalo_l")
                modelo.prepare(
                    ctx_id=0,
                    det_size=(640, 640)
                )
                _modelo = modelo

    return _modelo


# ==================================================
# CARREGAR USUÁRIOS CADASTRADOS
# ==================================================

def carregar_usuarios(cursor):
    cursor.execute("""
        SELECT
            id,
            nome,
            matricula,
            cargo,
            nivel_acesso,
            embedding
        FROM usuarios
    """)

    usuarios = cursor.fetchall()
    cadastros = []

    for usuario in usuarios:
        embedding = np.array(
            json.loads(usuario["embedding"]),
            dtype=np.float32
        )

        norma = np.linalg.norm(embedding)

        if norma == 0:
            continue

        embedding = embedding / norma

        cadastros.append({
            "id": usuario["id"],
            "nome": usuario["nome"],
            "matricula": usuario["matricula"],
            "cargo": usuario["cargo"],
            "nivel_acesso": usuario["nivel_acesso"],
            "embedding": embedding
        })

    return cadastros


# ==================================================
# REGISTRAR TENTATIVA DE ACESSO
# ==================================================

def registrar_tentativa(
    cursor,
    usuario_id,
    area_id,
    nome_identificado,
    matricula,
    resultado,
    distancia
):
    cursor.execute("""
        INSERT INTO tentativas_acesso (
            usuario_id,
            area_id,
            nome_identificado,
            matricula,
            resultado,
            distancia
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        usuario_id,
        area_id,
        nome_identificado,
        matricula,
        resultado,
        distancia
    ))


# ==================================================
# PROCESSAR UM FRAME RECEBIDO DO NAVEGADOR
# ==================================================

def processar_frame(frame, area_id):

    global rostos_ativos

    if frame is None or not isinstance(frame, np.ndarray):
        raise ValueError("Imagem recebida inválida.")

    if frame.size == 0:
        raise ValueError("Imagem recebida vazia.")

    with _lock_reconhecimento:

        modelo = obter_modelo()

        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        try:
            # ------------------------------------------
            # CONSULTAR ÁREA
            # ------------------------------------------

            cursor.execute("""
                SELECT id, nome, nivel_minimo
                FROM areas
                WHERE id = %s
            """, (area_id,))

            area = cursor.fetchone()

            if area is None:
                raise ValueError("Área não encontrada.")

            # ------------------------------------------
            # CARREGAR USUÁRIOS E EMBEDDINGS
            # ------------------------------------------

            cadastros = carregar_usuarios(cursor)

            if not cadastros:
                raise ValueError(
                    "Nenhum usuário com embedding válido cadastrado."
                )

            # ------------------------------------------
            # DETECTAR ROSTOS
            # ------------------------------------------

            agora = time.time()
            faces = modelo.get(frame)

            resultados = []

            for face in faces:

                embedding_camera = face.embedding.astype(np.float32)
                norma = np.linalg.norm(embedding_camera)

                if norma == 0:
                    continue

                embedding_camera /= norma

                # --------------------------------------
                # PROCURAR USUÁRIO MAIS PARECIDO
                # --------------------------------------

                melhor_usuario = None
                menor_distancia = float("inf")

                for usuario in cadastros:

                    distancia = np.linalg.norm(
                        embedding_camera - usuario["embedding"]
                    )

                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        melhor_usuario = usuario

                # --------------------------------------
                # IDENTIFICAR E VERIFICAR AUTORIZAÇÃO
                # --------------------------------------

                if (
                    menor_distancia < LIMIAR_RECONHECIMENTO
                    and melhor_usuario is not None
                ):

                    usuario_id = melhor_usuario["id"]
                    nome = melhor_usuario["nome"]
                    matricula = melhor_usuario["matricula"]
                    nivel = melhor_usuario["nivel_acesso"]

                    if nivel >= area["nivel_minimo"]:
                        resultado = "ACESSO PERMITIDO"
                    else:
                        resultado = "ACESSO NEGADO"

                else:
                    usuario_id = None
                    nome = "PESSOA NAO RECONHECIDA"
                    matricula = None
                    nivel = None
                    resultado = "ACESSO NEGADO"

                # --------------------------------------
                # CONTROLE DE REPETIÇÃO
                # --------------------------------------

                rosto_existente = None

                for indice, registro in enumerate(rostos_ativos):

                    distancia_rosto = np.linalg.norm(
                        embedding_camera - registro["embedding"]
                    )

                    if distancia_rosto < LIMIAR_REARME:
                        rosto_existente = indice
                        break

                registrada = False

                if rosto_existente is None:

                    registrar_tentativa(
                        cursor=cursor,
                        usuario_id=usuario_id,
                        area_id=area["id"],
                        nome_identificado=nome,
                        matricula=matricula,
                        resultado=resultado,
                        distancia=float(menor_distancia)
                    )

                    rostos_ativos.append({
                        "embedding": embedding_camera.copy(),
                        "ultimo_visto": agora
                    })

                    rosto_existente = len(rostos_ativos) - 1
                    registrada = True

                else:

                    rostos_ativos[rosto_existente]["ultimo_visto"] = agora

                    rostos_ativos[rosto_existente]["embedding"] = (
                        embedding_camera.copy()
                    )

                # --------------------------------------
                # RESULTADO PARA A INTERFACE WEB
                # --------------------------------------

                resultados.append({
                    "nome": nome,
                    "matricula": matricula,
                    "nivel": nivel,
                    "resultado": resultado,
                    "distancia": float(menor_distancia),
                    "registrada": registrada,
                    "bbox": face.bbox.astype(int).tolist()
                })

            # ------------------------------------------
            # REMOVER ROSTOS AUSENTES HÁ MAIS DE 3 SEG.
            # ------------------------------------------

            rostos_ativos = [
                registro
                for registro in rostos_ativos
                if agora - registro["ultimo_visto"] < TEMPO_REARME
            ]

            conexao.commit()

            return {
                "area": area["nome"],
                "resultados": resultados
            }

        except Exception:
            conexao.rollback()
            raise

        finally:
            cursor.close()
            conexao.close()
