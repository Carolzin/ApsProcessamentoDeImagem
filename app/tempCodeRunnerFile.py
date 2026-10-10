
import cv2
import json
import time
import numpy as np
import mysql.connector
from insightface.app import FaceAnalysis


# ==================================================
# CONEXÃO COM O BANCO
# ==================================================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

cursor = conexao.cursor(dictionary=True)


# ==================================================
# FUNÇÃO PARA REGISTRAR TENTATIVAS DE ACESSO
# ==================================================

def registrar_tentativa(
    usuario_id,
    area_id,
    nome_identificado,
    matricula,
    resultado,
    distancia
):
    cursor_log = conexao.cursor()

    try:
        cursor_log.execute("""
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

        conexao.commit()
        print(
            f"Histórico registrado: {nome_identificado} - "
            f"{resultado}"
        )

    except mysql.connector.Error as erro:
        conexao.rollback()
        print("Erro ao registrar tentativa:", erro)

    finally:
        cursor_log.close()


# ==================================================
# CARREGAR USUÁRIOS
# ==================================================

cursor.execute("""
    SELECT id, nome, matricula, cargo, nivel_acesso, embedding
    FROM usuarios
""")

usuarios = cursor.fetchall()

if not usuarios:
    print("Nenhum usuário cadastrado.")
    cursor.close()
    conexao.close()
    raise SystemExit


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


if not cadastros:
    print("Nenhum embedding válido encontrado.")
    cursor.close()
    conexao.close()
    raise SystemExit


print(f"{len(cadastros)} usuário(s) carregado(s).")


# ==================================================
# ESCOLHER A ÁREA
# ==================================================

print("\nÁreas disponíveis:")

cursor.execute("""
    SELECT id, nome, nivel_minimo
    FROM areas
    ORDER BY id
""")

areas = cursor.fetchall()

if not areas:
    print("Nenhuma área cadastrada.")

    cursor.close()
    conexao.close()
    raise SystemExit


for area in areas:
    print(
        f'{area["id"]} - {area["nome"]} '
        f'(nível mínimo: {area["nivel_minimo"]})'
    )


try:
    escolha = int(
        input("\nDigite o ID da área que deseja acessar: ")
    )
except ValueError:
    print("Digite um ID numérico válido.")
    cursor.close()
    conexao.close()
    raise SystemExit


area_escolhida = next(
    (area for area in areas if area["id"] == escolha),
    None
)

if area_escolhida is None:
    print("Área não encontrada.")
    cursor.close()
    conexao.close()
    raise SystemExit


print("\nÁrea escolhida:", area_escolhida["nome"])
print("Nível necessário:", area_escolhida["nivel_minimo"])


# ==================================================
# INSIGHTFACE
# ==================================================

app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))


# ==================================================
# CÂMERA E CONTROLE DE REGISTROS REPETIDOS
# ==================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Não foi possível abrir a câmera.")
    cursor.close()
    conexao.close()
    raise SystemExit


print("\nCâmera iniciada.")
print("Pressione Q para sair.")

# Guarda os rostos que já tiveram tentativa registrada
rostos_ativos = []

# Tempo sem detectar o rosto para considerar uma nova tentativa
TEMPO_REARME = 3.0

# Distância usada para comparar rostos entre quadros
# É apenas um critério de controle de repetição, não de identidade.
LIMIAR_REARME = 0.8


try:
    while True:

        sucesso, frame = camera.read()

        if not sucesso:
            print("Erro ao acessar a câmera.")
            break

        agora = time.time()
        faces = app.get(frame)

        # Marca os rostos ativos que foram vistos neste quadro
        rostos_vistos = set()

        for face in faces:

            embedding_camera = face.embedding.astype(np.float32)
            norma = np.linalg.norm(embedding_camera)

            if norma == 0:
                continue

            embedding_camera /= norma

            # ------------------------------------------
            # PROCURAR O USUÁRIO MAIS PARECIDO
            # ------------------------------------------

            melhor_usuario = None
            menor_distancia = float("inf")

            for usuario in cadastros:

                distancia = np.linalg.norm(
                    embedding_camera - usuario["embedding"]
                )

                if distancia < menor_distancia:
                    menor_distancia = distancia
                    melhor_usuario = usuario

            # ------------------------------------------
            # IDENTIFICAR E VERIFICAR AUTORIZAÇÃO
            # ------------------------------------------

            if menor_distancia < 1.0 and melhor_usuario is not None:

                usuario_id = melhor_usuario["id"]
                nome = melhor_usuario["nome"]
                matricula = melhor_usuario["matricula"]
                nivel = melhor_usuario["nivel_acesso"]

                if nivel >= area_escolhida["nivel_minimo"]:
                    resultado = "ACESSO PERMITIDO"
                    texto_cor = (0, 255, 0)
                else:
                    resultado = "ACESSO NEGADO"
                    texto_cor = (0, 0, 255)

            else:
                usuario_id = None
                nome = "PESSOA NAO RECONHECIDA"
                matricula = None
                nivel = None
                resultado = "ACESSO NEGADO"
                texto_cor = (0, 0, 255)

            # ------------------------------------------
            # REGISTRAR UMA TENTATIVA POR APARIÇÃO
            # ------------------------------------------

            # Compara o rosto atual com os rostos que já
            # foram registrados e ainda estão ativos.
            rosto_existente = None

            for indice, registro in enumerate(rostos_ativos):
                distancia_rosto = np.linalg.norm(
                    embedding_camera - registro["embedding"]
                )

                if distancia_rosto < LIMIAR_REARME:
                    rosto_existente = indice
                    break

            if rosto_existente is None:
                # Novo rosto: registra uma tentativa
                registrar_tentativa(
                    usuario_id=usuario_id,
                    area_id=area_escolhida["id"],
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

            else:
                # Atualiza a última vez em que esse rosto apareceu
                rostos_ativos[rosto_existente]["ultimo_visto"] = agora
                rostos_ativos[rosto_existente]["embedding"] = (
                    embedding_camera.copy()
                )

            rostos_vistos.add(rosto_existente)

            # ------------------------------------------
            # TEXTO EXIBIDO NA CÂMERA
            # ------------------------------------------

            texto1 = nome
            texto2 = resultado

            if nivel is not None:
                texto3 = (
                    f"Nivel: {nivel} | "
                    f"Distancia: {menor_distancia:.2f}"
                )
            else:
                texto3 = f"Distancia: {menor_distancia:.2f}"

            x1, y1, x2, y2 = face.bbox.astype(int)

            cv2.rectangle(
                frame, (x1, y1), (x2, y2), texto_cor, 2
            )

            cv2.putText(
                frame, texto1, (x1, max(y1 - 55, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, texto_cor, 2
            )

            cv2.putText(
                frame, texto2, (x1, max(y1 - 25, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, texto_cor, 2
            )

            cv2.putText(
                frame, texto3, (x1, y2 + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )

        # Remove rostos que ficaram ausentes por alguns segundos.
        # Se voltarem depois, poderão gerar uma nova tentativa.
        rostos_ativos = [
            registro
            for registro in rostos_ativos
            if agora - registro["ultimo_visto"] < TEMPO_REARME
        ]

        cv2.imshow("Sistema de Autenticacao Biometrica", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    camera.release()
    cv2.destroyAllWindows()
    cursor.close()
    conexao.close()
    print("Sistema encerrado.")
