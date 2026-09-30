import cv2
import numpy as np
from insightface.app import FaceAnalysis


# ==========================================
# 1. CARREGAR O MODELO
# ==========================================

print("Carregando modelo...")

modelo = FaceAnalysis(name="buffalo_l")
modelo.prepare(ctx_id=0, det_size=(640, 640))

print("Modelo carregado!")


# ==========================================
# 2. FUNÇÃO PARA OBTER EMBEDDING
# ==========================================

def obter_embedding(caminho_imagem):

    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        print("ERRO: não foi possível carregar:", caminho_imagem)
        return None

    rostos = modelo.get(imagem)

    if len(rostos) == 0:
        print("ERRO: nenhum rosto encontrado em:", caminho_imagem)
        return None

    embedding = rostos[0].embedding

    embedding = embedding / np.linalg.norm(embedding)

    return embedding


# ==========================================
# 3. CADASTROS
# ==========================================

cadastros = {

    "Carol": {
        "imagem": "app/imagens/carol.jpg"
    },

    "Sofia": {
        "imagem": "app/imagens/sofia.jpg"
    }

}


# ==========================================
# 4. GERAR EMBEDDINGS DOS CADASTRADOS
# ==========================================

print()
print("Carregando usuários cadastrados...")

for nome, dados in cadastros.items():

    print("Cadastrando:", nome)

    embedding = obter_embedding(
        dados["imagem"]
    )

    if embedding is None:
        print("Não foi possível cadastrar:", nome)
        exit()

    dados["embedding"] = embedding

print("Usuários carregados com sucesso!")


# ==========================================
# 5. INICIAR CÂMERA
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERRO: não foi possível acessar a câmera.")
    exit()

print()
print("Câmera iniciada!")
print("Pressione Q para sair.")


# ==========================================
# 6. RECONHECIMENTO
# ==========================================

while True:

    sucesso, frame = camera.read()

    if not sucesso:
        print("ERRO: não foi possível capturar a imagem.")
        break


    rostos = modelo.get(frame)


    for rosto in rostos:

        # Coordenadas do rosto

        x1, y1, x2, y2 = rosto.bbox.astype(int)


        # Embedding do rosto da câmera

        embedding_atual = rosto.embedding

        embedding_atual = embedding_atual / np.linalg.norm(
            embedding_atual
        )


        # ==========================================
        # COMPARAR COM TODOS OS CADASTRADOS
        # ==========================================

        melhor_nome = "Pessoa não reconhecida"
        menor_distancia = float("inf")


        for nome, dados in cadastros.items():

            distancia = np.linalg.norm(
                dados["embedding"] - embedding_atual
            )

            if distancia < menor_distancia:

                menor_distancia = distancia
                melhor_nome = nome


        # ==========================================
        # VERIFICAR LIMIAR
        # ==========================================

        if menor_distancia < 1.0:

            texto = f"{melhor_nome} - RECONHECIDA"

        else:

            texto = "PESSOA NAO RECONHECIDA"


        # ==========================================
        # MOSTRAR NA TELA
        # ==========================================

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )


        cv2.putText(
            frame,
            texto,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


        cv2.putText(
            frame,
            f"Distancia: {menor_distancia:.2f}",
            (x1, y2 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )


    cv2.imshow(
        "Sistema de Identificacao Biometrica",
        frame
    )


    tecla = cv2.waitKey(1) & 0xFF

    if tecla == ord("q"):
        break


# ==========================================
# 7. ENCERRAR
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("Sistema encerrado.")