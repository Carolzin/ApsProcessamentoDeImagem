
import os
import mysql.connector


def conectar_banco():
    """
    Abre uma conexão com o banco de dados do BioSegura.
    A senha é obtida por variável de ambiente.
    """

    senha = os.getenv("BIOSEGURA_DB_PASSWORD")

    if not senha:
        raise RuntimeError(
            "A variável BIOSEGURA_DB_PASSWORD não foi configurada."
        )

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=senha,
        database="aps_biometria"
    )
