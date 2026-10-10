import json
import cv2
import numpy as np
import mysql.connector
from insightface.app import FaceAnalysis


# ==========================================
# 1. CONEXÃO COM O BANCO DE DADOS
# ==========================================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

cursor = conexao.cursor()

try:

    # ==========================================
    # 2. IDENTIFICAÇÃO E AUTORIZAÇÃO
    # ==========================================

    print("\n===== CADASTRO DE USUÁRIO =====\n")

    nome = input("Nome completo: ").strip()
    matricula = input("Matrícula institucional: ").strip().upper()

    if not nome or not matricula:
        print("\nErro: preencha o nome e a matrícula.")
        raise SystemExit

    # Consulta uma matrícula previamente autorizada
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
        print("Matrícula inexistente ou autorização já utilizada.")
        raise SystemExit

    nome_autorizado, cargo, nivel_acesso = autorizacao

    # Confere se o nome informado corresponde à autorização
    if nome.casefold() != nome_autorizado.casefold():
        print("\nErro: o nome não corresponde à matrícula autorizada.")
        raise SystemExit

    # Confere se a matrícula já possui cadastro biométrico
    cursor.execute(
        "SELECT id FROM usuarios WHERE matricula = %s",
        (matricula,)
    )

    if cursor.fetchone() is not None:
        print("\nErro: essa matrícula já possui cadastro biométrico.")
        raise SystemExit

    print("\nMatrícula autorizada!")
    print(f"Nome: {nome_autorizado}")
    print(f"Matrícula: {matricula}")
    print(f"Cargo: {cargo}")
    print(f"Nível de acesso: {nivel_acesso}")

    # ==========================================
    # 3. CARREGAMENTO DO MODELO FACIAL
    # ==========================================

    print("\nCarregando modelo de reconhecimento facial...")

    modelo = FaceAnalysis(name="buffalo_l")
    modelo.prepare(ctx_id=0, det_size=(640, 640))

    # ==========================================
    # 4. CAPTURA DA BIOMETRIA
    # ==========================================

    print("\nA câmera será aberta.")
    print("Posicione o rosto em frente à câmera.")
    print("Pressione ESPAÇO para capturar ou Q para cancelar.")

    camera = cv2.VideoCapture(0)
    embedding = None

    if not camera.isOpened():
        print("Erro: não foi possível abrir a câmera.")
        raise SystemExit

    try:
        while True:
            sucesso, frame = camera.read()

            if not sucesso:
                print("Erro ao capturar imagem da câmera.")
                break

            faces = modelo.get(frame)

            for face in faces:
                x1, y1, x2, y2 = face.bbox.astype(int)
                cv2.rectangle(
                    frame, (x1, y1), (x2, y2), (0, 255, 0), 2
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
                faces = modelo.get(frame)

                if len(faces) == 0:
                    print("Nenhum rosto encontrado. Tente novamente.")
                    continue

                if len(faces) > 1:
                    print(
                        "Mais de um rosto encontrado. "
                        "Deixe apenas um rosto na imagem."
                    )
                    continue

                embedding = faces[0].embedding.astype(np.float32)
                norma = np.linalg.norm(embedding)

                if norma == 0:
                    print("Erro ao gerar a biometria. Tente novamente.")
                    embedding = None
                    continue

                embedding = embedding / norma
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    if embedding is None:
        print("\nCadastro cancelado ou imagem não capturada.")
        raise SystemExit

    # ==========================================
    # 5. SALVAMENTO DO USUÁRIO
    # ==========================================

    # A transação garante que o usuário e a autorização
    # sejam atualizados juntos, se tudo funcionar.

    cursor.execute(
        """
        SELECT nome_autorizado, cargo, nivel_acesso
        FROM matriculas_autorizadas
        WHERE matricula = %s AND utilizada = FALSE
        FOR UPDATE
        """,
        (matricula,)
    )

    autorizacao = cursor.fetchone()

    if autorizacao is None:
        print("\nErro: a autorização não está mais disponível.")
        raise SystemExit

    sql = """
        INSERT INTO usuarios
        (nome, matricula, cargo, nivel_acesso, embedding)
        VALUES (%s, %s, %s, %s, %s)
    """

    valores = (
        nome_autorizado,
        matricula,
        cargo,
        nivel_acesso,
        json.dumps(embedding.tolist())
    )

    cursor.execute(sql, valores)

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
    print(f"Nome: {nome_autorizado}")
    print(f"Matrícula: {matricula}")
    print(f"Cargo: {cargo}")
    print(f"Nível de acesso: {nivel_acesso}")
    print("Biometria salva no banco de dados.")

except mysql.connector.IntegrityError:
    conexao.rollback()
    print("\nErro: matrícula duplicada ou restrição do banco de dados.")

except mysql.connector.Error as erro:
    conexao.rollback()
    print(f"\nErro no banco de dados: {erro}")

finally:
    cv2.destroyAllWindows()
    cursor.close()
    conexao.close()
