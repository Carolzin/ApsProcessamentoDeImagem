
import mysql.connector


def conectar_banco():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="aps_biometria"
    )


def solicitar_cadastro():
    print("\n=== SOLICITAÇÃO DE CADASTRO ===")

    nome = input("Nome completo: ").strip()
    email = input("E-mail: ").strip()
    cargo = input("Cargo pretendido: ").strip()
    justificativa = input("Justificativa (opcional): ").strip()

    if not nome or not email or not cargo:
        print("Erro: preencha nome, e-mail e cargo.")
        return

    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        comando = """
            INSERT INTO solicitacoes_cadastro
                (nome, email, cargo_pretendido, justificativa)
            VALUES (%s, %s, %s, %s)
        """

        valores = (
            nome,
            email,
            cargo,
            justificativa or None
        )

        cursor.execute(comando, valores)
        conexao.commit()

        print("\nSolicitação registrada com sucesso!")
        print("Status: PENDENTE")
        print("Aguarde a análise do administrador.")

    except mysql.connector.Error as erro:
        print(f"Erro ao registrar solicitação: {erro}")

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()


if __name__ == "__main__":
    solicitar_cadastro()
