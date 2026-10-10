
import mysql.connector
from datetime import datetime


def conectar_banco():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="aps_biometria"
    )


def listar_solicitacoes(cursor, apenas_pendentes=False):
    if apenas_pendentes:
        cursor.execute("""
            SELECT id, nome, email, cargo_pretendido,
                   justificativa, status
            FROM solicitacoes_cadastro
            WHERE status = 'PENDENTE'
            ORDER BY data_solicitacao ASC
        """)
    else:
        cursor.execute("""
            SELECT id, nome, email, cargo_pretendido,
                   justificativa, status
            FROM solicitacoes_cadastro
            ORDER BY data_solicitacao DESC
        """)

    solicitacoes = cursor.fetchall()

    if not solicitacoes:
        print("\nNenhuma solicitação encontrada.")
        return

    titulo = (
        "SOLICITAÇÕES PENDENTES"
        if apenas_pendentes
        else "TODAS AS SOLICITAÇÕES"
    )

    print(f"\n=== {titulo} ===")

    for s in solicitacoes:
        print(f"\nID: {s[0]}")
        print(f"Nome: {s[1]}")
        print(f"E-mail: {s[2]}")
        print(f"Cargo pretendido: {s[3]}")
        print(f"Justificativa: {s[4] or 'Não informada'}")
        print(f"Status: {s[5]}")


def gerar_matricula(cursor, nivel):
    prefixos = {
        1: "G",
        2: "D",
        3: "M"
    }

    prefixo = prefixos[nivel]

    # Busca as matrículas desse prefixo já cadastradas
    cursor.execute("""
        SELECT matricula
        FROM matriculas_autorizadas
        WHERE matricula LIKE %s

        UNION

        SELECT matricula_gerada
        FROM solicitacoes_cadastro
        WHERE matricula_gerada LIKE %s
    """, (prefixo + "%", prefixo + "%"))

    existentes = cursor.fetchall()
    numeros = []

    for registro in existentes:
        matricula = registro[0]

        if matricula and matricula.startswith(prefixo):
            numero = matricula[1:]

            if numero.isdigit():
                numeros.append(int(numero))

    proximo = max(numeros, default=0) + 1

    return f"{prefixo}{proximo:04d}"


def aprovar_solicitacao(cursor, conexao):
    listar_solicitacoes(cursor, apenas_pendentes=True)

    try:
        id_solicitacao = int(
            input("\nID da solicitação que deseja aprovar: ")
        )
    except ValueError:
        print("ID inválido.")
        return

    try:
        cursor.execute("""
            SELECT id, nome, status
            FROM solicitacoes_cadastro
            WHERE id = %s
            FOR UPDATE
        """, (id_solicitacao,))

        solicitacao = cursor.fetchone()

        if not solicitacao:
            print("Solicitação não encontrada.")
            conexao.rollback()
            return

        if solicitacao[2] != "PENDENTE":
            print("Essa solicitação já foi analisada.")
            conexao.rollback()
            return

        print("\nNíveis de acesso:")
        print("1 - Área Geral")
        print("2 - Área Geral e Área dos Diretores")
        print("3 - Todas as áreas, incluindo o cofre")

        try:
            nivel = int(
                input("Nível aprovado pelo administrador: ")
            )
        except ValueError:
            print("Nível inválido.")
            conexao.rollback()
            return

        if nivel not in (1, 2, 3):
            print("Escolha um nível entre 1 e 3.")
            conexao.rollback()
            return

        confirmacao = input(
            f"Confirma a aprovação de {solicitacao[1]} "
            f"para o nível {nivel}? (S/N): "
        ).strip().upper()

        if confirmacao != "S":
            conexao.rollback()
            print("Aprovação cancelada.")
            return

        cargos = {
            1: "Funcionário - Acesso Geral",
            2: "Diretor de Divisão",
            3: "Ministro do Meio Ambiente"
        }

        cargo_aprovado = cargos[nivel]
        matricula = gerar_matricula(cursor, nivel)

        # Insere a matrícula autorizada
        cursor.execute("""
            INSERT INTO matriculas_autorizadas
                (matricula, nome_autorizado, cargo, nivel_acesso)
            VALUES (%s, %s, %s, %s)
        """, (
            matricula,
            solicitacao[1],
            cargo_aprovado,
            nivel
        ))

        # Marca a solicitação como aprovada
        cursor.execute("""
            UPDATE solicitacoes_cadastro
            SET status = 'APROVADO',
                cargo_aprovado = %s,
                nivel_aprovado = %s,
                matricula_gerada = %s,
                data_decisao = %s
            WHERE id = %s AND status = 'PENDENTE'
        """, (
            cargo_aprovado,
            nivel,
            matricula,
            datetime.now(),
            id_solicitacao
        ))

        if cursor.rowcount != 1:
            conexao.rollback()
            print("Não foi possível aprovar a solicitação.")
            return

        # Confirma as duas operações juntas
        conexao.commit()

        print("\nSolicitação aprovada com sucesso!")
        print(f"Nome: {solicitacao[1]}")
        print(f"Cargo aprovado: {cargo_aprovado}")
        print(f"Nível de acesso: {nivel}")
        print(f"Matrícula gerada: {matricula}")
        print("\nA pessoa já está autorizada a iniciar")
        print("o cadastro biométrico com essa matrícula.")

    except mysql.connector.Error as erro:
        conexao.rollback()
        print(f"Erro ao aprovar solicitação: {erro}")
        print("As alterações foram canceladas.")


def recusar_solicitacao(cursor, conexao):
    listar_solicitacoes(cursor, apenas_pendentes=True)

    try:
        id_solicitacao = int(
            input("\nID da solicitação que deseja recusar: ")
        )
    except ValueError:
        print("ID inválido.")
        return

    try:
        cursor.execute("""
            UPDATE solicitacoes_cadastro
            SET status = 'RECUSADO',
                data_decisao = %s
            WHERE id = %s AND status = 'PENDENTE'
        """, (datetime.now(), id_solicitacao))

        if cursor.rowcount == 1:
            conexao.commit()
            print("Solicitação recusada com sucesso.")
        else:
            conexao.rollback()
            print("Solicitação não encontrada ou já analisada.")

    except mysql.connector.Error as erro:
        conexao.rollback()
        print(f"Erro ao recusar solicitação: {erro}")


def administrar():
    conexao = None
    cursor = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor()

        while True:
            print("\n=== ADMINISTRAÇÃO DE CADASTROS ===")
            print("1 - Listar todas as solicitações")
            print("2 - Aprovar solicitação")
            print("3 - Recusar solicitação")
            print("0 - Sair")

            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                listar_solicitacoes(cursor)

            elif opcao == "2":
                aprovar_solicitacao(cursor, conexao)

            elif opcao == "3":
                recusar_solicitacao(cursor, conexao)

            elif opcao == "0":
                print("Saindo da administração...")
                break

            else:
                print("Opção inválida.")

    except mysql.connector.Error as erro:
        print(f"Erro ao conectar ao banco: {erro}")

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None and conexao.is_connected():
            conexao.close()


if __name__ == "__main__":
    administrar()
