
import json
import cv2
import numpy as np
import mysql.connector
from insightface.app import FaceAnalysis
import threading
from app.integracao.banco import conectar_banco as conectar_banco_web


def conectar_banco():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="aps_biometria"
    )


def cadastrar_usuario():
    conexao = None
    cursor = None
    camera = None

    try:
        # 1. Conexão com o banco
        conexao = conectar_banco()
        cursor = conexao.cursor()

        print("\n===== CADASTRO BIOMÉTRICO =====\n")

        # 2. Consulta da matrícula autorizada
        matricula = input(
            "Digite sua matrícula autorizada: "
        ).strip().upper()

        if not matricula:
            print("\nErro: informe a matrícula.")
            return

        cursor.execute(
            """
            SELECT nome_autorizado, cargo, nivel_acesso
            FROM matriculas_autorizadas
            WHERE matricula = %s AND utilizada = FALSE
            """,
            (matricula,)
        )

        autorizacao = cursor.fetchone()

        if autorizacao is None:
            print("\nCadastro não autorizado.")
            print(
                "Matrícula inexistente ou autorização "
                "já utilizada."
            )
            return

        nome, cargo, nivel_acesso = autorizacao

        # 3. Confere se já existe cadastro biométrico
        cursor.execute(
            "SELECT id FROM usuarios WHERE matricula = %s",
            (matricula,)
        )

        if cursor.fetchone() is not None:
            print("\nErro: essa matrícula já possui biometria.")
            return

        print("\n===== DADOS DA AUTORIZAÇÃO =====")
        print(f"Nome: {nome}")
        print(f"Matrícula: {matricula}")
        print(f"Cargo: {cargo}")
        print(f"Nível de acesso: {nivel_acesso}")

        confirmacao = input(
            "\nEsses dados correspondem à pessoa autorizada? "
            "(S/N): "
        ).strip().upper()

        if confirmacao != "S":
            print("\nCadastro cancelado.")
            return

        # 4. Carrega o modelo de reconhecimento facial
        print("\nCarregando modelo facial...")

        modelo = FaceAnalysis(name="buffalo_l")
        modelo.prepare(ctx_id=0, det_size=(640, 640))

        # 5. Captura do rosto
        print("\nA câmera será aberta.")
        print("Posicione o rosto em frente à câmera.")
        print("Pressione ESPAÇO para capturar ou Q para cancelar.")

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            print("\nErro: não foi possível abrir a câmera.")
            return

        embedding = None

        while True:
            sucesso, frame = camera.read()

            if not sucesso:
                print("Erro ao capturar imagem da câmera.")
                break

            faces = modelo.get(frame)

            for face in faces:
                x1, y1, x2, y2 = face.bbox.astype(int)

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

            cv2.putText(
                frame,
                "ESPACO: capturar | Q: cancelar",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.imshow("Cadastro Biometrico", frame)
            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("q"):
                break

            if tecla == 32:
                if len(faces) == 0:
                    print("Nenhum rosto encontrado. Tente novamente.")
                    continue

                if len(faces) > 1:
                    print(
                        "Mais de um rosto encontrado. "
                        "Deixe apenas uma pessoa na imagem."
                    )
                    continue

                vetor = faces[0].embedding.astype(np.float32)
                norma = np.linalg.norm(vetor)

                if norma == 0:
                    print("Erro ao gerar a biometria. Tente novamente.")
                    continue

                embedding = vetor / norma
                break

        if embedding is None:
            print("\nCadastro cancelado ou imagem não capturada.")
            return

        # Fecha a câmera antes de salvar
        camera.release()
        camera = None
        cv2.destroyAllWindows()

        # 6. Confirma a autorização e salva tudo em uma transação
        cursor.execute(
            """
            SELECT nome_autorizado, cargo, nivel_acesso
            FROM matriculas_autorizadas
            WHERE matricula = %s AND utilizada = FALSE
            FOR UPDATE
            """,
            (matricula,)
        )

        autorizacao_atual = cursor.fetchone()

        if autorizacao_atual is None:
            print(
                "\nErro: a autorização foi utilizada ou "
                "deixou de estar disponível."
            )
            conexao.rollback()
            return

        # Usa novamente os dados atuais do banco
        nome, cargo, nivel_acesso = autorizacao_atual

        cursor.execute(
            """
            INSERT INTO usuarios
                (nome, matricula, cargo, nivel_acesso, embedding)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                nome,
                matricula,
                cargo,
                nivel_acesso,
                json.dumps(embedding.tolist())
            )
        )

        cursor.execute(
            """
            UPDATE matriculas_autorizadas
            SET utilizada = TRUE
            WHERE matricula = %s AND utilizada = FALSE
            """,
            (matricula,)
        )

        if cursor.rowcount != 1:
            raise mysql.connector.Error(
                "Não foi possível confirmar o uso da autorização."
            )

        conexao.commit()

        print("\n===== CADASTRO CONCLUÍDO =====")
        print(f"Nome: {nome}")
        print(f"Matrícula: {matricula}")
        print(f"Cargo: {cargo}")
        print(f"Nível de acesso: {nivel_acesso}")
        print("Biometria salva no banco de dados.")

    except mysql.connector.IntegrityError:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()

        print(
            "\nErro: matrícula duplicada ou restrição "
            "do banco de dados."
        )

    except mysql.connector.Error as erro:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()

        print(f"\nErro no banco de dados: {erro}")

    except Exception as erro:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()

        print(f"\nErro durante o cadastro: {erro}")

    finally:
        if camera is not None:
            camera.release()

        cv2.destroyAllWindows()

        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()

# ==========================================================
# INTEGRAÇÃO DO CADASTRO COM A INTERFACE WEB
# ==========================================================

_modelo_web = None
_lock_modelo_web = threading.Lock()


def carregar_modelo_web():
    """Reutiliza o modelo buffalo_l durante a execução web."""

    global _modelo_web

    with _lock_modelo_web:
        if _modelo_web is None:
            _modelo_web = FaceAnalysis(name="buffalo_l")
            _modelo_web.prepare(ctx_id=0, det_size=(640, 640))

    return _modelo_web


def listar_matriculas_disponiveis():
    """Lista as autorizações ainda não utilizadas."""

    conexao = conectar_banco_web()
    cursor = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT matricula, nome_autorizado, cargo, nivel_acesso
            FROM matriculas_autorizadas
            WHERE utilizada = FALSE
            ORDER BY nome_autorizado
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conexao.close()


def consultar_matricula_disponivel(matricula):
    """Consulta os dados de uma matrícula autorizada."""

    matricula = matricula.strip().upper()

    conexao = conectar_banco_web()
    cursor = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT matricula, nome_autorizado, cargo, nivel_acesso
            FROM matriculas_autorizadas
            WHERE matricula = %s AND utilizada = FALSE
        """, (matricula,))

        return cursor.fetchone()

    finally:
        cursor.close()
        conexao.close()


def gerar_embedding_web(frame):
    """Gera a biometria a partir de um frame enviado pelo navegador."""

    if frame is None or frame.size == 0:
        raise ValueError("Imagem inválida.")

    modelo = carregar_modelo_web()
    faces = modelo.get(frame)

    if len(faces) == 0:
        raise ValueError("Nenhum rosto encontrado. Tente novamente.")

    if len(faces) > 1:
        raise ValueError(
            "Mais de um rosto encontrado. "
            "Deixe apenas uma pessoa na imagem."
        )

    vetor = faces[0].embedding.astype(np.float32)
    norma = np.linalg.norm(vetor)

    if norma == 0:
        raise ValueError("Erro ao gerar a biometria.")

    return vetor / norma


def cadastrar_usuario_web(matricula, frame, confirmar_dados=False):
    """Realiza o cadastro biométrico solicitado pela interface web."""

    matricula = matricula.strip().upper()

    if not matricula:
        raise ValueError("Informe a matrícula.")

    if confirmar_dados is not True:
        raise ValueError("Confirme os dados da autorização.")

    autorizacao = consultar_matricula_disponivel(matricula)

    if autorizacao is None:
        raise ValueError(
            "Matrícula inexistente ou autorização já utilizada."
        )

    embedding = gerar_embedding_web(frame)

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco_web()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT nome_autorizado, cargo, nivel_acesso
            FROM matriculas_autorizadas
            WHERE matricula = %s AND utilizada = FALSE
            FOR UPDATE
        """, (matricula,))

        autorizacao_atual = cursor.fetchone()

        if autorizacao_atual is None:
            raise ValueError(
                "A autorização foi utilizada ou deixou de estar disponível."
            )

        nome, cargo, nivel_acesso = autorizacao_atual

        cursor.execute("""
            SELECT id
            FROM usuarios
            WHERE matricula = %s
        """, (matricula,))

        if cursor.fetchone() is not None:
            raise ValueError(
                "Essa matrícula já possui biometria cadastrada."
            )

        cursor.execute("""
            INSERT INTO usuarios
                (nome, matricula, cargo, nivel_acesso, embedding)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            nome,
            matricula,
            cargo,
            nivel_acesso,
            json.dumps(embedding.tolist())
        ))

        cursor.execute("""
            UPDATE matriculas_autorizadas
            SET utilizada = TRUE
            WHERE matricula = %s AND utilizada = FALSE
        """, (matricula,))

        if cursor.rowcount != 1:
            raise mysql.connector.Error(
                "Não foi possível confirmar o uso da autorização."
            )

        conexao.commit()

        return {
            "nome": nome,
            "matricula": matricula,
            "cargo": cargo,
            "nivel_acesso": nivel_acesso
        }

    except Exception:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()

        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()

def criar_autorizacao_web(nome, matricula, cargo, nivel_acesso):
    """Registra uma nova autorização para cadastro biométrico."""

    nome = nome.strip()
    matricula = matricula.strip().upper()
    cargo = cargo.strip()

    if not nome or not matricula or not cargo:
        raise ValueError(
            "Nome, matrícula e cargo são obrigatórios."
        )

    try:
        nivel_acesso = int(nivel_acesso)
    except (ValueError, TypeError):
        raise ValueError("Nível de acesso inválido.")

    if nivel_acesso not in (1, 2, 3):
        raise ValueError(
            "O nível de acesso deve ser 1, 2 ou 3."
        )

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco_web()
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT matricula
            FROM matriculas_autorizadas
            WHERE matricula = %s
        """, (matricula,))

        if cursor.fetchone() is not None:
            raise ValueError(
                "Essa matrícula já possui uma autorização cadastrada."
            )

        cursor.execute("""
            SELECT matricula
            FROM usuarios
            WHERE matricula = %s
        """, (matricula,))

        if cursor.fetchone() is not None:
            raise ValueError(
                "Essa matrícula já possui usuário cadastrado."
            )

        cursor.execute("""
            INSERT INTO matriculas_autorizadas
                (matricula, nome_autorizado, cargo, nivel_acesso, utilizada)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (
            matricula,
            nome,
            cargo,
            nivel_acesso
        ))

        conexao.commit()

        return {
            "nome_autorizado": nome,
            "matricula": matricula,
            "cargo": cargo,
            "nivel_acesso": nivel_acesso
        }

    except Exception:
        if conexao is not None and conexao.is_connected():
            conexao.rollback()

        raise

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()

if __name__ == "__main__":
    cadastrar_usuario()