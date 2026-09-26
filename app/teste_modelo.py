from insightface.app import FaceAnalysis

print("Carregando modelo...")

app = FaceAnalysis(
    name="buffalo_l"
)

app.prepare(
    ctx_id=0,
    det_size=(640, 640)
)

print("Modelo carregado com sucesso!")