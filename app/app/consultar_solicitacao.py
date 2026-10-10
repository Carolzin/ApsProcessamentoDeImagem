
import mysql.connector


def consultar_solicitacao():
    conexao = None
    cursor = None

    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="aps_biometria"
        )

        cursor = conexao.cursor()

        print("\n===== CONSULTA DE SOLICITAÇÃO =====\n")

        nome = input("Digite seu nome completo: ").strip()

        if not nome:
            print("\nErro: informe seu nome.")
            return

        cursor.execute(
            """
            SELECT
                id,
                nome,
                status,
                cargo_aprovado,
                nivel_aprovado,
                matricula_gerada
            FROM solicitacoes_cadastro
            WHERE LOWER(TRIM(nome)) = LOWER(TRIM(%s))
            ORDER BY data_solicitacao DESC
            """,
            (nome,)
        )

        solicitacoes = cursor.fetchall()

        if not solicitacoes:
            print("\nNenhuma solicitação encontrada com esse nome.")
            return

        if len(solicitacoes) > 1:
            print("\nEncontramos mais de uma solicitação com esse nome.")

            for solicitacao in solicitacoes:
                print(
                    f"ID: {solicitacao[0]} | "
                    f"Data/status: {solicitacao[2]}"
                )

            print(
                "\nPara evitar mostrar dados da pessoa errada, "
                "procure o administrador para identificar "
                "a solicitação correta."
            )
            return

        solicitacao = solicitacoes[0]

        _, nome_cadastrado, status, cargo, nivel, matricula = solicitacao

        print("\n===== RESULTADO DA CONSULTA =====")
        print(f"Nome: {nome_cadastrado}")
        print(f"Status: {status}")

        if status == "PENDENTE":
            print("\nSua solicitação ainda está em análise.")

        elif status == "RECUSADO":
            print("\nSua solicitação não foi aprovada.")

        elif status == "APROVADO":
            print(f"\nCargo aprovado: {cargo}")
            print(f"Nível de acesso: {nivel}")
            print(f"Matrícula gerada: {matricula}")

            print(
                "\nVocê pode prosseguir para o cadastro biométrico "
                "usando essa matrícula."
            )

        else:
            print("\nStatus desconhecido. Procure o administrador.")

    except mysql.connector.Error as erro:
        print(f"\nErro ao consultar o banco de dados: {erro}")

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()


if __name__ == "__main__":
    consultar_solicitacao()
