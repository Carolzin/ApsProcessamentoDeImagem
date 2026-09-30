import cv2
import numpy as np
from insightface.app import FaceAnalysis

print("Carregando modelo...")

modelo = FaceAnalysis(name="buffalo_l")
modelo.prepare(ctx_id=0, det_size=(640, 640))

print("Modelo carregado!")


def obter_embedding(caminho_imagem):

    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        print("ERRO: não foi possível carregar:", caminho_imagem)
        return None

    rostos = modelo.get(imagem)

    if len(rostos) == 0:
        print("ERRO: nenhum rosto encontrado em:", caminho_imagem)
        return None

    return rostos[0].embedding


print("Analisando carol.jpg...")

embedding_cadastrado = obter_embedding(
    "app/imagens/sofia.jpg"
)


print("Analisando carol_teste.jpg...")

embedding_teste = obter_embedding(
    "app/imagens/sofia2.jpg"
)


if embedding_cadastrado is None or embedding_teste is None:
    print("Não foi possível realizar a comparação.")
    exit()


# Normalizando os embeddings
embedding_cadastrado = embedding_cadastrado / np.linalg.norm(
    embedding_cadastrado
)

embedding_teste = embedding_teste / np.linalg.norm(
    embedding_teste
)


# Calculando a distância
distancia = np.linalg.norm(
    embedding_cadastrado - embedding_teste
)


print()
print("Comparação concluída!")
print("Distância entre os rostos:", distancia)