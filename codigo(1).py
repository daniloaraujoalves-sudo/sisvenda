from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import hashlib

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = "mercado_2026_super_key"

# Configuração de Caminhos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'venda.db')

class MercadoAppWeb:
    def __init__(self):
        self.inicializar_db()
        self.criar_admin_padrao()

    def hash_senha(self, senha):
        salt = "mercado_app_2026"
        return hashlib.sha256((senha + salt).encode()).hexdigest()

    def inicializar_db(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    usuario TEXT UNIQUE, 
                    senha TEXT, 
                    cargo TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    nome TEXT, 
                    email TEXT UNIQUE, 
                    senha TEXT, 
                    pontos_fidelidade INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    nome TEXT, 
                    preco REAL, 
                    estoque INTEGER
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    produto_id INTEGER, 
                    quantidade INTEGER, 
                    total REAL, 
                    cliente_id INTEGER, 
                    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def criar_admin_padrao(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE usuario = 'admin'")
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha, cargo) VALUES (?, ?, 'admin')", 
                    ('admin', self.hash_senha('admin123'))
                )
            conn.commit()

mercado = MercadoAppWeb()

@app.route('/')
def index():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        produtos = conn.execute("SELECT * FROM produtos").fetchall()
        faturamento = 0
        if session.get('cargo') == 'admin':
            res = conn.execute("SELECT SUM(total) FROM vendas").fetchone()
            faturamento = res[0] if res[0] else 0
    return render_template('index.html', produtos=produtos, faturamento=faturamento)

@app.route('/login', methods=['POST'])
def login():
    id_input = request.form.get('u')      # corrigido para 'u' do form
    senha = mercado.hash_senha(request.form.get('s'))  # corrigido para 's' do form

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        # Tenta Admin
        adm = conn.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?", 
            (id_input, senha)
        ).fetchone()
        if adm:
            session.update({'user_id': adm['id'], 'nome': 'Administrador', 'cargo': 'admin'})
            return redirect(url_for('index'))

        # Tenta Cliente
        cli = conn.execute(
            "SELECT * FROM clientes WHERE email=? AND senha=?", 
            (id_input, senha)
        ).fetchone()
        if cli:
            session.update({
                'user_id': cli['id'], 
                'nome': cli['nome'], 
                'cargo': 'cliente', 
                'pontos': cli['pontos_fidelidade']
            })
            flash(f"Bem-vindo, {cli['nome']}!", "success")
            return redirect(url_for('index'))

    flash("Credenciais inválidas!", "danger")
    return redirect(url_for('index'))

@app.route('/comprar/<int:id>')
def comprar(id):
    if session.get('cargo') != 'cliente':
        flash("Apenas clientes podem comprar!", "warning")
        return redirect(url_for('index'))

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        p = cursor.execute(
            "SELECT nome, preco, estoque FROM produtos WHERE id=?", 
            (id,)
        ).fetchone()
        if p and p[2] > 0:
            cursor.execute("UPDATE produtos SET estoque = estoque - 1 WHERE id=?", (id,))
            cursor.execute(
                "INSERT INTO vendas (produto_id, quantidade, total, cliente_id) VALUES (?,1,?,?)", 
                (id, p[1], session['user_id'])
            )
            cursor.execute(
                "UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id=?", 
                (int(p[1]//10), session['user_id'])
            )
            conn.commit()
            flash(f"Compra de {p[0]} realizada!", "success")

    return redirect(url_for('index'))

@app.route('/admin/add', methods=['POST'])
def add_produto():
    if session.get('cargo') == 'admin':
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", 
                (request.form['nome'], request.form['preco'], request.form['estoque'])
            )
        flash("Produto cadastrado!", "success")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
