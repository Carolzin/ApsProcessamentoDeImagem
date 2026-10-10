import cv2
import json
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
    exit()

cadastros = []

for usuario in usuarios:

    embedding = np.array(
        json.loads(usuario["embedding"]),
        dtype=np.float32
    )

    embedding = embedding / np.linalg.norm(embedding)

    cadastros.append({
        "id": usuario["id"],
        "nome": usuario["nome"],
        "matricula": usuario["matricula"],
        "cargo": usuario["cargo"],
        "nivel_acesso": usuario["nivel_acesso"],
        "embedding": embedding
    })


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

for area in areas:
    print(
        f'{area["id"]} - {area["nome"]} '
        f'(nível mínimo: {area["nivel_minimo"]})'
    )

escolha = int(input("\nDigite o ID da área que deseja acessar: "))

area_escolhida = None

for area in areas:

    if area["id"] == escolha:
        area_escolhida = area
        break


if area_escolhida is None:

    print("Área não encontrada.")

    cursor.close()
    conexao.close()
    exit()


print()
print("Área escolhida:", area_escolhida["nome"])
print("Nível necessário:", area_escolhida["nivel_minimo"])


# ==================================================
# INSIGHTFACE
# ==================================================

app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))


# ==================================================
# CÂMERA
# ==================================================

camera = cv2.VideoCapture(0)

print("\nCâmera iniciada.")
print("Pressione Q para sair.")


while True:

    sucesso, frame = camera.read()

    if not sucesso:
        print("Erro ao acessar a câmera.")
        break

    faces = app.get(frame)

    for face in faces:

        # ------------------------------------------
        # EMBEDDING DO ROSTO DA CÂMERA
        # ------------------------------------------

        embedding_camera = face.embedding.astype(np.float32)

        embedding_camera = (
            embedding_camera /
            np.linalg.norm(embedding_camera)
        )


        # ------------------------------------------
        # PROCURAR A PESSOA MAIS PARECIDA
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
        # VERIFICAR IDENTIDADE
        # ------------------------------------------

        if menor_distancia < 1.0:

            nome = melhor_usuario["nome"]
            nivel = melhor_usuario["nivel_acesso"]

            # --------------------------------------
            # VERIFICAR AUTORIZAÇÃO
            # --------------------------------------

            if nivel >= area_escolhida["nivel_minimo"]:

                resultado = "ACESSO PERMITIDO"
                texto_cor = (0, 255, 0)

            else:

                resultado = "ACESSO NEGADO"
                texto_cor = (0, 0, 255)


            texto1 = nome

            texto2 = resultado

            texto3 = (
                f"Nivel: {nivel} | "
                f"Distancia: {menor_distancia:.2f}"
            )

        else:

            texto1 = "PESSOA NAO RECONHECIDA"
            texto2 = "ACESSO NEGADO"
            texto3 = (
                f"Distancia: {menor_distancia:.2f}"
            )

            texto_cor = (0, 0, 255)


        # ------------------------------------------
        # DESENHAR NA CÂMERA
        # ------------------------------------------

        x1, y1, x2, y2 = face.bbox.astype(int)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            texto_cor,
            2
        )

        cv2.putText(
            frame,
            texto1,
            (x1, y1 - 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            texto_cor,
            2
        )

        cv2.putText(
            frame,
            texto2,
            (x1, y1 - 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            texto_cor,
            2
        )

        cv2.putText(
            frame,
            texto3,
            (x1, y2 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )


    cv2.imshow(
        "Sistema de Autenticacao Biometrica",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==================================================
# ENCERRAR
# ==================================================

camera.release()
cv2.destroyAllWindows()

cursor.close()
conexao.close()