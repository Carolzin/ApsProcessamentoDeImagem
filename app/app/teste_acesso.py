import mysql.connector


# =========================
# CONEXÃO COM O BANCO
# =========================

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="aps_biometria"
)

cursor = conexao.cursor(dictionary=True)


# =========================
# BUSCAR USUÁRIO
# =========================

matricula = input("Digite a matrícula do usuário: ")

cursor.execute(
    """
    SELECT *
    FROM usuarios
    WHERE matricula = %s
    """,
    (matricula,)
)

usuario = cursor.fetchone()


if usuario is None:
    print("Usuário não encontrado.")

else:

    print()
    print("Usuário:", usuario["nome"])
    print("Nível de acesso:", usuario["nivel_acesso"])

    # =========================
    # ESCOLHER ÁREA
    # =========================

    print()
    print("Áreas disponíveis:")

    cursor.execute(
        """
        SELECT *
        FROM areas
        ORDER BY id
        """
    )

    areas = cursor.fetchall()

    for area in areas:
        print(
            f'{area["id"]} - {area["nome"]} '
            f'(nível mínimo: {area["nivel_minimo"]})'
        )

    escolha = int(input("\nDigite o ID da área: "))

    # =========================
    # BUSCAR ÁREA ESCOLHIDA
    # =========================

    cursor.execute(
        """
        SELECT *
        FROM areas
        WHERE id = %s
        """,
        (escolha,)
    )

    area = cursor.fetchone()


    if area is None:

        print("Área não encontrada.")

    else:

        print()
        print("Área escolhida:", area["nome"])
        print("Nível necessário:", area["nivel_minimo"])

        # =========================
        # VERIFICAR AUTORIZAÇÃO
        # =========================

        if usuario["nivel_acesso"] >= area["nivel_minimo"]:

            print()
            print("🔓 ACESSO PERMITIDO")

        else:

            print()
            print("🔒 ACESSO NEGADO")


cursor.close()
conexao.close()