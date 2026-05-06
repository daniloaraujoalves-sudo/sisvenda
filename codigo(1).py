from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mercado_2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'venda.db')

# ================= BANCO =================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            senha TEXT,
            cargo TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            preco REAL,
            estoque INTEGER,
            imagem TEXT
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS carrinho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            quantidade INTEGER,
            total REAL,
            cliente_id INTEGER
        )''')

        # ADMIN PADRÃO
        adm = c.execute("SELECT * FROM usuarios WHERE usuario='admin'").fetchone()
        if not adm:
            c.execute("INSERT INTO usuarios VALUES (NULL,?,?,?)",
                      ('admin', generate_password_hash('admin123'), 'admin'))

        conn.commit()

init_db()

# ================= HOME =================
@app.route('/')
def index():
    q = request.args.get('q')

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        if q:
            produtos = conn.execute(
                "SELECT * FROM produtos WHERE nome LIKE ?",
                ('%' + q + '%',)
            ).fetchall()
        else:
            produtos = conn.execute("SELECT * FROM produtos").fetchall()

        # carrinho
        carrinho_qtd = 0
        if session.get('cargo') == 'cliente':
            res = conn.execute(
                "SELECT SUM(quantidade) FROM carrinho WHERE cliente_id=?",
                (session['user_id'],)
            ).fetchone()[0]
            carrinho_qtd = res if res else 0

        # faturamento admin
        faturamento = 0
        if session.get('cargo') == 'admin':
            res = conn.execute("SELECT SUM(total) FROM vendas").fetchone()[0]
            faturamento = res if res else 0

    return render_template("index.html",
                           produtos=produtos,
                           carrinho_qtd=carrinho_qtd,
                           faturamento=faturamento)

# ================= LOGIN =================
@app.route('/login', methods=['POST'])
def login():
    user = request.form['u']
    senha = request.form['s']

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row

        # ADMIN
        adm = conn.execute("SELECT * FROM usuarios WHERE usuario=?", (user,)).fetchone()
        if adm and check_password_hash(adm['senha'], senha):
            session.clear()
            session['user_id'] = adm['id']
            session['nome'] = 'Administrador'
            session['cargo'] = 'admin'
            flash("Login admin OK", "success")
            return redirect('/')

        # CLIENTE
        cli = conn.execute("SELECT * FROM clientes WHERE email=?", (user,)).fetchone()
        if cli and check_password_hash(cli['senha'], senha):
            session.clear()
            session['user_id'] = cli['id']
            session['nome'] = cli['nome']
            session['cargo'] = 'cliente'
            flash("Login cliente OK", "success")
            return redirect('/')

    flash("Login inválido", "danger")
    return redirect('/')

# ================= REGISTRO =================
@app.route('/register', methods=['POST'])
def register():
    nome = request.form['nome']
    email = request.form['email']
    senha = generate_password_hash(request.form['senha'])

    with sqlite3.connect(DB_NAME) as conn:
        try:
            conn.execute(
                "INSERT INTO clientes (nome,email,senha) VALUES (?,?,?)",
                (nome, email, senha)
            )
            flash("Conta criada!", "success")
        except:
            flash("Email já existe!", "danger")

    return redirect('/')

# ================= CARRINHO =================
@app.route('/add_carrinho/<int:id>', methods=['POST'])
def add_carrinho(id):
    if session.get('cargo') != 'cliente':
        flash("Entre como cliente!", "warning")
        return redirect('/')

    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO carrinho (cliente_id,produto_id,quantidade) VALUES (?,?,1)",
            (session['user_id'], id)
        )

    flash("Adicionado ao carrinho!", "success")
    return redirect('/')

# ================= FINALIZAR =================
@app.route('/finalizar')
def finalizar():
    if session.get('cargo') != 'cliente':
        flash("Faça login como cliente!", "warning")
        return redirect('/')

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        itens = c.execute(
            "SELECT produto_id, quantidade FROM carrinho WHERE cliente_id=?",
            (session['user_id'],)
        ).fetchall()

        if not itens:
            flash("Carrinho vazio!", "warning")
            return redirect('/')

        for produto_id, qtd in itens:
            p = c.execute("SELECT preco, estoque FROM produtos WHERE id=?", (produto_id,)).fetchone()

            if not p or p[1] < qtd:
                flash("Estoque insuficiente!", "danger")
                return redirect('/')

            total = p[0] * qtd

            c.execute("UPDATE produtos SET estoque = estoque - ? WHERE id=?",
                      (qtd, produto_id))

            c.execute("INSERT INTO vendas VALUES (NULL,?,?,?,?)",
                      (produto_id, qtd, total, session['user_id']))

        c.execute("DELETE FROM carrinho WHERE cliente_id=?", (session['user_id'],))
        conn.commit()

    flash("Compra realizada!", "success")
    return redirect('/')

# ================= ADMIN =================
@app.route('/admin/add', methods=['POST'])
def add_produto():
    if session.get('cargo') == 'admin':
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT INTO produtos (nome,preco,estoque,imagem) VALUES (?,?,?,?)",
                (request.form['nome'], request.form['preco'],
                 request.form['estoque'], request.form['imagem'])
            )
            flash("Produto adicionado!", "success")
    return redirect('/')

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
