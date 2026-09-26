import cv2


# Caminho do classificador facial
caminho_classificador = r"C:\Users\carol\haarcascade_frontalface_default.xml"


# Carrega o classificador
classificador_rosto = cv2.CascadeClassifier(
    caminho_classificador
)


# Verifica se o classificador foi carregado
if classificador_rosto.empty():
    print("ERRO: não foi possível carregar o classificador facial.")
    exit()


print("Classificador facial carregado com sucesso!")


# Abre a câmera
camera = cv2.VideoCapture(0)


# Verifica se a câmera abriu
if not camera.isOpened():
    print("ERRO: não foi possível acessar a câmera.")
    exit()


print("Câmera iniciada!")
print("Pressione Q para sair.")


while True:

    # Captura uma imagem da câmera
    sucesso, frame = camera.read()


    # Verifica se conseguiu capturar
    if not sucesso:
        print("ERRO: não foi possível capturar a imagem.")
        break


    # Converte a imagem para tons de cinza
    imagem_cinza = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    # Detecta os rostos
    rostos = classificador_rosto.detectMultiScale(
        imagem_cinza,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )


    # Percorre cada rosto encontrado
    for (x, y, largura, altura) in rostos:

        # Recorta somente o rosto
        rosto = frame[
            y:y + altura,
            x:x + largura
        ]


        # Desenha o quadrado ao redor do rosto
        cv2.rectangle(
            frame,
            (x, y),
            (x + largura, y + altura),
            (0, 255, 0),
            2
        )


        # Escreve o texto
        cv2.putText(
            frame,
            "Rosto detectado",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


        # Mostra somente o rosto recortado
        cv2.imshow(
            "Rosto segmentado",
            rosto
        )


    # Mostra a imagem completa
    cv2.imshow(
        "Sistema de Identificacao Biometrica",
        frame
    )


    # Verifica se a tecla Q foi pressionada
    tecla = cv2.waitKey(1) & 0xFF


    if tecla == ord("q"):
        break


# Encerra a câmera
camera.release()

cv2.destroyAllWindows()

print("Sistema encerrado.")