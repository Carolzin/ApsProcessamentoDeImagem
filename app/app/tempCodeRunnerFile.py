
import json
import cv2
import numpy as np
import mysql.connector
from insightface.app import FaceAnalysis


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


if __name__ == "__main__":
    cadastrar_usuario()
