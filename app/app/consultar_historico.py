
import mysql.connector


# ==========================================
# CONEXÃO COM O BANCO
# ==========================================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

cursor = conexao.cursor(dictionary=True)


# ==========================================
# CONSULTAR HISTÓRICO
# ==========================================

cursor.execute("""
    SELECT
        id,
        nome_identificado,
        matricula,
        resultado,
        distancia,
        data_hora
    FROM tentativas_acesso
    ORDER BY data_hora DESC
""")

tentativas = cursor.fetchall()


# ==========================================
# EXIBIR RESULTADOS
# ==========================================

print("\n========== HISTÓRICO DE ACESSOS ==========\n")

if not tentativas:
    print("Nenhuma tentativa de acesso registrada.")

else:
    for tentativa in tentativas:
        print(f'ID: {tentativa["id"]}')
        print(f'Nome: {tentativa["nome_identificado"]}')
        print(f'Matrícula: {tentativa["matricula"] or "Não identificada"}')
        print(f'Resultado: {tentativa["resultado"]}')

        distancia = tentativa["distancia"]

        if distancia is not None:
            print(f'Distância facial: {distancia:.4f}')

        print(f'Data e hora: {tentativa["data_hora"]}')
        print("-" * 40)


# ==========================================
# ENCERRAR
# ==========================================

cursor.close()
conexao.close()
