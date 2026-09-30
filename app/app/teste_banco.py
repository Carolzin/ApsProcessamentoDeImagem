import mysql.connector

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

print("Conexão com o MySQL realizada com sucesso!")

conexao.close()