
import base64
import binascii

import cv2
import numpy as np

from flask import Flask, render_template, request, jsonify

from app.integracao.banco import conectar_banco
from app.processamento.reconhecimento import processar_frame

from app.app.cadastrar_usuario import (
    listar_matriculas_disponiveis,
    consultar_matricula_disponivel,
    cadastrar_usuario_web,
    criar_autorizacao_web
)


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


@app.route("/")
def dashboard():
    conexao = None
    cursor = None

    metricas = {
        "usuarios": 0,
        "matriculas_total": 0,
        "matriculas_disponiveis": 0,
        "matriculas_utilizadas": 0,
        "tentativas": 0,
        "permitidos": 0,
        "negados": 0
    }

    recentes = []
    erro = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        metricas["usuarios"] = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(utilizada = FALSE), 0) AS disponiveis,
                COALESCE(SUM(utilizada = TRUE), 0) AS utilizadas
            FROM matriculas_autorizadas
        """)

        matriculas = cursor.fetchone()
        metricas["matriculas_total"] = matriculas["total"]
        metricas["matriculas_disponiveis"] = matriculas["disponiveis"]
        metricas["matriculas_utilizadas"] = matriculas["utilizadas"]

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(resultado = 'ACESSO PERMITIDO'), 0) AS permitidos,
                COALESCE(SUM(resultado = 'ACESSO NEGADO'), 0) AS negados
            FROM tentativas_acesso
        """)

        acessos = cursor.fetchone()
        metricas["tentativas"] = acessos["total"]
        metricas["permitidos"] = acessos["permitidos"]
        metricas["negados"] = acessos["negados"]

        cursor.execute("""
            SELECT
                t.id,
                t.nome_identificado,
                t.matricula,
                t.resultado,
                t.data_hora,
                a.nome AS area
            FROM tentativas_acesso t
            LEFT JOIN areas a ON a.id = t.area_id
            ORDER BY t.data_hora DESC
            LIMIT 8
        """)

        recentes = cursor.fetchall()

    except Exception as e:
        erro = str(e)

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

    return render_template(
        "dashboard.html",
        metricas=metricas,
        recentes=recentes,
        erro=erro
    )


# ==================================================
# PÁGINA DE RECONHECIMENTO FACIAL
# ==================================================

@app.route("/reconhecimento")
def reconhecimento():
    conexao = None
    cursor = None
    areas = []
    erro = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, nome, nivel_minimo
            FROM areas
            ORDER BY id
        """)

        areas = cursor.fetchall()

    except Exception:
        app.logger.exception("Erro ao consultar áreas.")
        erro = "Não foi possível carregar as áreas cadastradas."

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

    return render_template(
        "reconhecimento.html",
        areas=areas,
        erro=erro
    )


# ==================================================
# API DE RECONHECIMENTO FACIAL
# ==================================================
@app.route("/api/matriculas", methods=["POST"])
def criar_matricula_autorizada():
    dados = request.get_json(silent=True) or {}

    nome = dados.get("nome", "")
    matricula = dados.get("matricula", "")
    cargo = dados.get("cargo", "")
    nivel_acesso = dados.get("nivel_acesso")

    try:
        autorizacao = criar_autorizacao_web(
            nome,
            matricula,
            cargo,
            nivel_acesso
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Autorização cadastrada com sucesso.",
            "autorizacao": autorizacao
        }), 201

    except ValueError as erro:
        return jsonify({
            "sucesso": False,
            "erro": str(erro)
        }), 400

    except Exception:
        app.logger.exception("Erro ao criar autorização.")
        return jsonify({
            "sucesso": False,
            "erro": "Não foi possível cadastrar a autorização."
        }), 500

@app.route("/api/reconhecimento", methods=["POST"])
def api_reconhecimento():

    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({
            "erro": "Dados da imagem não foram enviados."
        }), 400

    imagem_base64 = dados.get("imagem")
    area_id = dados.get("area_id")

    if not imagem_base64 or area_id is None:
        return jsonify({
            "erro": "Imagem e área são obrigatórias."
        }), 400

    try:
        area_id = int(area_id)

        if area_id <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "erro": "ID da área inválido."
        }), 400

    try:
        if "," in imagem_base64:
            imagem_base64 = imagem_base64.split(",", 1)[1]

        conteudo = base64.b64decode(
            imagem_base64,
            validate=True
        )

        if not conteudo:
            return jsonify({
                "erro": "Imagem vazia."
            }), 400

        array_imagem = np.frombuffer(
            conteudo,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            array_imagem,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return jsonify({
                "erro": "Não foi possível interpretar a imagem."
            }), 400

    except (ValueError, binascii.Error):
        return jsonify({
            "erro": "Formato de imagem inválido."
        }), 400

    try:
        resultado = processar_frame(
            frame=frame,
            area_id=area_id
        )

        return jsonify({
            "sucesso": True,
            **resultado
        })

    except ValueError as erro:
        return jsonify({
            "sucesso": False,
            "erro": str(erro)
        }), 400

    except Exception:
        app.logger.exception(
            "Erro durante o reconhecimento facial."
        )

        return jsonify({
            "sucesso": False,
            "erro": "Não foi possível processar o reconhecimento."
        }), 500

# ==================================================
# PÁGINA DE USUÁRIOS
# ==================================================

@app.route("/usuarios")
def usuarios():
    conexao = None
    cursor = None

    lista_usuarios = []
    matriculas = []
    erro = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                nome,
                matricula,
                cargo,
                nivel_acesso,
                data_cadastro
            FROM usuarios
            ORDER BY nome
        """)

        lista_usuarios = cursor.fetchall()

        matriculas = listar_matriculas_disponiveis()

    except Exception:
        app.logger.exception("Erro ao carregar usuários.")
        erro = "Não foi possível carregar os dados dos usuários."

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()

    return render_template(
        "usuarios.html",
        usuarios=lista_usuarios,
        matriculas=matriculas,
        erro=erro
    )

    return render_template(
        "usuarios.html",
        usuarios=lista_usuarios,
        matriculas=matriculas,
        erro=erro
    )


# ==================================================
# API - CONSULTAR MATRÍCULA AUTORIZADA
# ==================================================

@app.route("/api/matriculas/<matricula>", methods=["GET"])
def api_consultar_matricula(matricula):

    try:
        autorizacao = consultar_matricula_disponivel(matricula)

        if autorizacao is None:
            return jsonify({
                "sucesso": False,
                "erro": "Matrícula inexistente ou autorização já utilizada."
            }), 404

        return jsonify({
            "sucesso": True,
            "autorizacao": autorizacao
        })

    except Exception:
        app.logger.exception("Erro ao consultar matrícula.")

        return jsonify({
            "sucesso": False,
            "erro": "Não foi possível consultar a matrícula."
        }), 500

# ==================================================
# PÁGINA DE CONTROLE DE ACESSO
# ==================================================

@app.route("/controle-acesso")
def controle_acesso():
    conexao = None
    cursor = None

    areas = []
    lista_usuarios = []
    erro = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                nome,
                nivel_minimo
            FROM areas
            ORDER BY id
        """)

        areas = cursor.fetchall()

        cursor.execute("""
            SELECT
                id,
                nome,
                matricula,
                cargo,
                nivel_acesso
            FROM usuarios
            ORDER BY nome
        """)

        lista_usuarios = cursor.fetchall()

        for area in areas:
            area["total_aptos"] = sum(
                usuario["nivel_acesso"] >= area["nivel_minimo"]
                for usuario in lista_usuarios
            )

    except Exception:
        app.logger.exception("Erro ao carregar controle de acesso.")
        erro = "Não foi possível carregar os dados de controle de acesso."

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()

    return render_template(
        "controle_acesso.html",
        areas=areas,
        usuarios=lista_usuarios,
        erro=erro
    )


# ==================================================
# PÁGINA DE HISTÓRICO
# ==================================================

@app.route("/historico")
def historico():
    conexao = None
    cursor = None
    tentativas = []
    erro = None

    try:
        conexao = conectar_banco()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                ta.id,
                COALESCE(ta.nome_identificado, u.nome, 'Não identificado') AS nome,
                COALESCE(ta.matricula, u.matricula, '—') AS matricula,
                a.nome AS area,
                ta.resultado,
                ta.data_hora
            FROM tentativas_acesso ta
            LEFT JOIN usuarios u
                ON ta.usuario_id = u.id
            LEFT JOIN areas a
                ON ta.area_id = a.id
            ORDER BY ta.data_hora DESC, ta.id DESC
        """)

        tentativas = cursor.fetchall()

    except Exception:
        app.logger.exception("Erro ao carregar histórico de acessos.")
        erro = "Não foi possível carregar o histórico de acessos."

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()

    return render_template(
        "historico.html",
        tentativas=tentativas,
        erro=erro
    )

# ==================================================
# API - CADASTRAR USUÁRIO
# ==================================================

@app.route("/api/usuarios", methods=["POST"])
def api_cadastrar_usuario():

    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({
            "sucesso": False,
            "erro": "Dados do cadastro não foram enviados."
        }), 400

    matricula = dados.get("matricula")
    imagem_base64 = dados.get("imagem")
    confirmar_dados = dados.get("confirmar_dados")

    if not matricula or not imagem_base64:
        return jsonify({
            "sucesso": False,
            "erro": "Matrícula e imagem são obrigatórias."
        }), 400

    if confirmar_dados is not True:
        return jsonify({
            "sucesso": False,
            "erro": "Confirme os dados da autorização."
        }), 400

    try:
        if "," in imagem_base64:
            imagem_base64 = imagem_base64.split(",", 1)[1]

        conteudo = base64.b64decode(
            imagem_base64,
            validate=True
        )

        if not conteudo:
            return jsonify({
                "sucesso": False,
                "erro": "Imagem vazia."
            }), 400

        array_imagem = np.frombuffer(
            conteudo,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            array_imagem,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return jsonify({
                "sucesso": False,
                "erro": "Não foi possível interpretar a imagem."
            }), 400

    except (ValueError, binascii.Error):
        return jsonify({
            "sucesso": False,
            "erro": "Formato de imagem inválido."
        }), 400

    try:
        usuario = cadastrar_usuario_web(
            matricula=matricula,
            frame=frame,
            confirmar_dados=confirmar_dados
        )

        return jsonify({
            "sucesso": True,
            "mensagem": "Cadastro biométrico realizado com sucesso.",
            "usuario": usuario
        })

    except ValueError as erro:
        return jsonify({
            "sucesso": False,
            "erro": str(erro)
        }), 400

    except Exception:
        app.logger.exception("Erro durante o cadastro biométrico.")

        return jsonify({
            "sucesso": False,
            "erro": "Não foi possível concluir o cadastro biométrico."
        }), 500

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
