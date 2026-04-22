import sqlite3
import os
import hashlib
import re
from datetime import datetime
from typing import Optional, Tuple, List

DB_NAME = 'mercado_app.db'
BACKUP_DIR = 'backups'

class MercadoApp:
    def __init__(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        self.inicializar_db_completo()
        self.criar_usuario_padrao()
    
    def hash_senha(self, senha: str) -> str:
        salt = "mercado_app_2026"
        return hashlib.sha256((senha + salt).encode()).hexdigest()
    
    def validar_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def inicializar_db_completo(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                cargo TEXT NOT NULL CHECK (cargo IN ('admin', 'vendedor')),
                ativo INTEGER DEFAULT 1
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                pontos_fidelidade INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                estoque INTEGER NOT NULL DEFAULT 0
            )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL,
                total REAL NOT NULL,
                cliente_id INTEGER,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produto_id) REFERENCES produtos (id),
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )''')
            conn.commit()

    def criar_usuario_padrao(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE usuario = 'admin'")
            if not cursor.fetchone():
                senha_hash = self.hash_senha('admin123')
                cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (?, ?, ?)",
                             ('admin', senha_hash, 'admin'))
                conn.commit()

    # --- 1. LÓGICA DE CARRINHO E COMPRA ---
    def menu_loja(self, cliente_id: int):
        carrinho = []
        while True:
            self.listar_produtos()
            print("\n🛒 CARRINHO ATUAL:", [f"{item['nome']} (x{item['qtd']})" for item in carrinho] if carrinho else "Vazio")
            print("1. Adicionar ao Carrinho | 2. Finalizar Compra | 3. Cancelar")
            op = input("👉 ")

            if op == '1':
                try:
                    p_id = int(input("🆔 ID do Produto: "))
                    qtd = int(input("🔢 Quantidade: "))
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT nome, preco, estoque FROM produtos WHERE id = ?", (p_id,))
                        res = cursor.fetchone()
                        if res and res[2] >= qtd:
                            carrinho.append({'id': p_id, 'nome': res[0], 'preco': res[1], 'qtd': qtd})
                            print("✅ Adicionado!")
                        else:
                            print("❌ Produto inexistente ou estoque insuficiente.")
                except ValueError: print("❌ Use números.")
            
            elif op == '2':
                if not carrinho:
                    print("❌ Carrinho vazio!")
                    continue
                self.processar_venda_completa(cliente_id, carrinho)
                break
            elif op == '3': break

    def processar_venda_completa(self, cliente_id: int, carrinho: List[dict]):
        total_venda = 0
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                for item in carrinho:
                    subtotal = item['preco'] * item['qtd']
                    total_venda += subtotal
                    # Atualiza Estoque
                    cursor.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (item['qtd'], item['id']))
                    # Registra Venda
                    cursor.execute("INSERT INTO vendas (produto_id, quantidade, total, cliente_id) VALUES (?,?,?,?)",
                                 (item['id'], item['qtd'], subtotal, cliente_id))
                
                # 2. SISTEMA DE PONTOS (1 ponto por cada 10 unidades monetárias)
                pontos = int(total_venda // 10)
                cursor.execute("UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id = ?", (pontos, cliente_id))
                
                conn.commit()
                print(f"\n🎉 Compra finalizada! Total: R$ {total_venda:.2f}")
                print(f"⭐ Ganhou {pontos} pontos de fidelidade!")
            except Exception as e:
                conn.rollback()
                print(f"❌ Erro ao processar: {e}")

    # --- 3. HISTÓRICO DE PEDIDOS ---
    def ver_historico_cliente(self, cliente_id: int):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT v.data, p.nome, v.quantidade, v.total 
                FROM vendas v JOIN produtos p ON v.produto_id = p.id 
                WHERE v.cliente_id = ? ORDER BY v.data DESC
            ''', (cliente_id,))
            vendas = cursor.fetchall()
            print("\n📜 SEU HISTÓRICO:")
            for v in vendas: print(f"📅 {v[0][:16]} | {v[1]} (x{v[2]}) | R$ {v[3]:.2f}")

    # --- 4. RELATÓRIOS PARA ADMIN ---
    def relatorio_financeiro(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(total), COUNT(id) FROM vendas")
            res = cursor.fetchone()
            print(f"\n📊 RELATÓRIO GERAL")
            print(f"💰 Faturamento Total: R$ {res[0] if res[0] else 0:.2f}")
            print(f"📦 Total de Vendas Realizadas: {res[1]}")
            
            print("\n🔝 PRODUTOS MAIS VENDIDOS:")
            cursor.execute('''
                SELECT p.nome, SUM(v.quantidade) as total_qtd
                FROM vendas v JOIN produtos p ON v.produto_id = p.id
                GROUP BY p.id ORDER BY total_qtd DESC LIMIT 5
            ''')
            for row in cursor.fetchall(): print(f"- {row[0]}: {row[1]} unidades")

    # --- MÉTODOS DE SUPORTE E MENUS ---
    def login_cliente(self):
        email = input("📧 Email: ").strip().lower()
        senha = input("🔒 Senha: ")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome FROM clientes WHERE email = ? AND senha = ?', (email, self.hash_senha(senha)))
            return cursor.fetchone()

    def cadastrar_cliente(self):
        nome = input("👤 Nome: "); email = input("📧 Email: ")
        if not self.validar_email(email): return print("❌ Email inválido")
        senha = input("🔒 Senha: ")
        try:
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute('INSERT INTO clientes (nome, email, senha) VALUES (?,?,?)', (nome, email.lower(), self.hash_senha(senha)))
                print("✅ Cliente Cadastrado!")
        except: print("❌ Email já existe.")

    def listar_produtos(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome, preco, estoque FROM produtos')
            print(f"\n{'ID':<4} | {'PRODUTO':<20} | {'PREÇO':<10} | {'ESTOQUE'}")
            for p in cursor.fetchall():
                aviso = "⚠️" if p[3] < 5 else ""
                print(f"{p[0]:<4} | {p[1]:<20} | R$ {p[2]:<8.2f} | {p[3]} {aviso}")

    def menu_principal(self):
        while True:
            print(f"\n{'='*30}\n🏪 SISTEMA MERCADO V3\n{'='*30}")
            print("1. Cliente | 2. Admin | 3. Sair")
            op = input("👉 ")
            if op == '1': self.submenu_cliente()
            elif op == '2':
                if self.fazer_login_admin(): self.menu_admin()
            elif op == '3': break

    def fazer_login_admin(self):
        u = input("👤 User: "); s = input("🔒 Senha: ")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM usuarios WHERE usuario=? AND senha=? AND cargo="admin"', (u, self.hash_senha(s)))
            return cursor.fetchone()

    def submenu_cliente(self):
        print("\n1. Login | 2. Cadastro")
        op = input("👉 ")
        if op == '1':
            res = self.login_cliente()
            if res: self.menu_cliente(res[0], res[1])
        elif op == '2': self.cadastrar_cliente()

    def menu_cliente(self, cid, nome):
        while True:
            print(f"\n👋 Olá {nome}!")
            print("1. 🛒 Abrir Loja/Carrinho | 2. 📜 Histórico | 3. Sair")
            op = input("👉 ")
            if op == '1': self.menu_loja(cid)
            elif op == '2': self.ver_historico_cliente(cid)
            elif op == '3': break

    def menu_admin(self):
        while True:
            print("\n🛠️ PAINEL ADMIN")
            print("1. Estoque | 2. Novo Produto | 3. Relatórios | 4. Sair")
            op = input("👉 ")
            if op == '1': self.listar_produtos()
            elif op == '2': 
                n = input("Nome: "); p = float(input("Preço: ")); e = int(input("Estoque: "))
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)", (n,p,e))
            elif op == '3': self.relatorio_financeiro()
            elif op == '4': break

if __name__ == "__main__":
    MercadoApp().menu_principal()
