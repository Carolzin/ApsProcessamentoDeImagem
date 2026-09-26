import cv2
from insightface.app import FaceAnalysis


# 1. Carrega o modelo
print("Carregando modelo...")

modelo = FaceAnalysis(
    name="buffalo_l"
)

modelo.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("Modelo carregado!")


# 2. Carrega a foto
imagem = cv2.imread(
    "app/imagens/carol.jpg"
)

if imagem is None:
    print("ERRO: não foi possível carregar a imagem.")
    exit()

print("Imagem carregada!")


# 3. Detecta o rosto
rostos = modelo.get(imagem)

print("Quantidade de rostos encontrados:", len(rostos))


# 4. Verifica se encontrou alguém
if len(rostos) == 0:
    print("Nenhum rosto foi encontrado.")
    exit()


# 5. Pega o primeiro rosto encontrado
rosto = rostos[0]


# 6. Obtém o embedding facial
embedding = rosto.embedding


# 7. Mostra algumas informações
print("Embedding extraído com sucesso!")
print("Quantidade de números no embedding:", len(embedding))

print("Primeiros 10 valores:")
print(embedding[:10])