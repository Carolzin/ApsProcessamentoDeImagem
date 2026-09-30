import json
import mysql.connector
from insightface.app import FaceAnalysis


# =========================
# CONFIGURAÇÃO DO BANCO
# =========================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

cursor = conexao.cursor()


# =========================
# CONFIGURAÇÃO DO INSIGHTFACE
# =========================

app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=0, det_size=(640, 640))


# =========================
# DADOS DO USUÁRIO
# =========================

nome = "Sofia"
matricula = "002"
cargo = "Funcionária"
nivel_acesso = 1
caminho_imagem = "app/imagens/sofia.jpg"


# =========================
# GERAR EMBEDDING
# =========================

import cv2

imagem = cv2.imread(caminho_imagem)

faces = app.get(imagem)

if len(faces) == 0:
    print("Nenhum rosto encontrado na imagem.")
    exit()

if len(faces) > 1:
    print("Mais de um rosto encontrado na imagem.")
    exit()

embedding = faces[0].embedding.tolist()


# =========================
# SALVAR NO BANCO
# =========================

sql = """
INSERT INTO usuarios
(nome, matricula, cargo, nivel_acesso, embedding)
VALUES (%s, %s, %s, %s, %s)
"""

valores = (
    nome,
    matricula,
    cargo,
    nivel_acesso,
    json.dumps(embedding)
)

cursor.execute(sql, valores)
conexao.commit()

print("Usuário cadastrado com sucesso!")
print("Nome:", nome)
print("Matrícula:", matricula)
print("Nível de acesso:", nivel_acesso)


cursor.close()
conexao.close()