from flask import Flask, render_template, request, redirect, url_for, flash
from database import conectar, inicializar_banco

app = Flask(__name__)
app.config["SECRET_KEY"] = "chave-secreta-fila-atendimento"


# Inicializa o banco ao iniciar a aplicação
inicializar_banco()


@app.route("/")
def index():
    conexao = conectar()

    clientes = conexao.execute("""
        SELECT *
        FROM clientes
        ORDER BY
            CASE status
                WHEN 'em atendimento' THEN 1
                WHEN 'aguardando' THEN 2
                WHEN 'concluído' THEN 3
                WHEN 'cancelado' THEN 4
            END,
            id ASC
    """).fetchall()

    aguardando = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM clientes
        WHERE status = 'aguardando'
    """).fetchone()["total"]

    em_atendimento = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM clientes
        WHERE status = 'em atendimento'
    """).fetchone()["total"]

    concluidos = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM clientes
        WHERE status = 'concluído'
    """).fetchone()["total"]

    cancelados = conexao.execute("""
        SELECT COUNT(*) AS total
        FROM clientes
        WHERE status = 'cancelado'
    """).fetchone()["total"]

    conexao.close()

    return render_template(
        "index.html",
        clientes=clientes,
        aguardando=aguardando,
        em_atendimento=em_atendimento,
        concluidos=concluidos,
        cancelados=cancelados
    )


@app.route("/clientes/cadastrar", methods=["POST"])
def cadastrar_cliente():
    nome = request.form.get("nome", "").strip()
    telefone = request.form.get("telefone", "").strip()

    if not nome:
        flash("Informe o nome do cliente.", "erro")
        return redirect(url_for("index"))

    conexao = conectar()

    conexao.execute("""
        INSERT INTO clientes (nome, telefone, status)
        VALUES (?, ?, 'aguardando')
    """, (nome, telefone))

    conexao.commit()
    conexao.close()

    flash(f"Cliente {nome} adicionado à fila.", "sucesso")

    return redirect(url_for("index"))


@app.route("/chamar-proximo", methods=["POST"])
def chamar_proximo():
    conexao = conectar()

    # Verifica se existe alguém em atendimento
    atendimento_atual = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status = 'em atendimento'
        LIMIT 1
    """).fetchone()

    if atendimento_atual:
        conexao.close()

        flash(
            f"Finalize ou cancele o atendimento de "
            f"{atendimento_atual['nome']} antes de chamar o próximo.",
            "erro"
        )

        return redirect(url_for("index"))

    # FIFO:
    # seleciona o cliente aguardando mais antigo
    proximo = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE status = 'aguardando'
        ORDER BY id ASC
        LIMIT 1
    """).fetchone()

    if not proximo:
        conexao.close()

        flash("Não existem clientes aguardando atendimento.", "aviso")

        return redirect(url_for("index"))

    conexao.execute("""
        UPDATE clientes
        SET
            status = 'em atendimento',
            iniciado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (proximo["id"],))

    conexao.commit()
    conexao.close()

    flash(
        f"Próximo cliente chamado: {proximo['nome']}.",
        "sucesso"
    )

    return redirect(url_for("index"))


@app.route("/cliente/<int:cliente_id>/status", methods=["POST"])
def alterar_status(cliente_id):
    novo_status = request.form.get("status")

    status_validos = [
        "aguardando",
        "em atendimento",
        "concluído",
        "cancelado"
    ]

    if novo_status not in status_validos:
        flash("Status inválido.", "erro")
        return redirect(url_for("index"))

    conexao = conectar()

    cliente = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE id = ?
    """, (cliente_id,)).fetchone()

    if not cliente:
        conexao.close()

        flash("Cliente não encontrado.", "erro")

        return redirect(url_for("index"))

    # Não permite colocar outro cliente em atendimento
    if novo_status == "em atendimento":
        atendimento_atual = conexao.execute("""
            SELECT id
            FROM clientes
            WHERE status = 'em atendimento'
              AND id != ?
            LIMIT 1
        """, (cliente_id,)).fetchone()

        if atendimento_atual:
            conexao.close()

            flash(
                "Já existe outro cliente em atendimento.",
                "erro"
            )

            return redirect(url_for("index"))

    if novo_status == "concluído":
        conexao.execute("""
            UPDATE clientes
            SET
                status = ?,
                concluido_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (novo_status, cliente_id))
    else:
        conexao.execute("""
            UPDATE clientes
            SET status = ?
            WHERE id = ?
        """, (novo_status, cliente_id))

    conexao.commit()
    conexao.close()

    flash("Status atualizado com sucesso.", "sucesso")

    return redirect(url_for("index"))


@app.route("/cliente/<int:cliente_id>/cancelar", methods=["POST"])
def cancelar_atendimento(cliente_id):
    conexao = conectar()

    cliente = conexao.execute("""
        SELECT *
        FROM clientes
        WHERE id = ?
    """, (cliente_id,)).fetchone()

    if not cliente:
        conexao.close()

        flash("Cliente não encontrado.", "erro")

        return redirect(url_for("index"))

    conexao.execute("""
        UPDATE clientes
        SET status = 'cancelado'
        WHERE id = ?
    """, (cliente_id,))

    conexao.commit()
    conexao.close()

    flash(
        f"Atendimento de {cliente['nome']} cancelado.",
        "aviso"
    )

    return redirect(url_for("index"))


@app.route("/cliente/<int:cliente_id>/excluir", methods=["POST"])
def excluir_cliente(cliente_id):
    conexao = conectar()

    conexao.execute("""
        DELETE FROM clientes
        WHERE id = ?
    """, (cliente_id,))

    conexao.commit()
    conexao.close()

    flash("Registro excluído.", "sucesso")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
