
from app.integracao.banco import conectar_banco


def consultar_historico():
    """
    Retorna as tentativas de acesso registradas no banco.
    Pode ser utilizada pelo Flask ou pelo terminal.
    """

    conexao = conectar_banco()
    cursor = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                t.id,
                t.usuario_id,
                t.nome_identificado,
                t.matricula,
                t.resultado,
                t.distancia,
                t.data_hora,
                t.area_id,
                a.nome AS area
            FROM tentativas_acesso t
            LEFT JOIN areas a ON a.id = t.area_id
            ORDER BY t.data_hora DESC
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conexao.close()


if __name__ == "__main__":
    print("\n========== HISTÓRICO DE ACESSOS ==========\n")

    try:
        tentativas = consultar_historico()

        if not tentativas:
            print("Nenhuma tentativa de acesso registrada.")

        else:
            for tentativa in tentativas:
                print(f'ID: {tentativa["id"]}')
                print(f'Nome: {tentativa["nome_identificado"]}')
                print(
                    f'Matrícula: '
                    f'{tentativa["matricula"] or "Não identificada"}'
                )
                print(f'Área: {tentativa["area"] or "Não informada"}')
                print(f'Resultado: {tentativa["resultado"]}')

                distancia = tentativa["distancia"]

                if distancia is not None:
                    print(f'Distância facial: {distancia:.4f}')

                print(f'Data e hora: {tentativa["data_hora"]}')
                print("-" * 40)

    except Exception as erro:
        print(f"Erro ao consultar histórico: {erro}")
