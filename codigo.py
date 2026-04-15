import sqlite3
import os
import hashlib
import re
from datetime import datetime
from typing import Optional, Tuple
import getpass

DB_NAME = 'comercial_v.db'
BACKUP_DIR = 'backups'

class SistemaComercial:
    def __init__(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        self.inicializar_db_completo()
        self.criar_usuario_padrao()
    
    def hash_senha(self, senha: str) -> str:
        salt = "sistema_comercial_v4_2024"
        return hashlib.sha256((senha + salt).encode()).hexdigest()
    
    def validar_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def inicializar_db_completo(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Tabela Usuários (Funcionários)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    cargo TEXT NOT NULL CHECK (cargo IN ('admin', 'vendedor')),
                    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela Clientes - COM SENHA PARA LOGIN
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    telefone TEXT,
                    senha TEXT NOT NULL,
                    data_nascimento TEXT,
                    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
                    pontos_fidelidade INTEGER DEFAULT 0 CHECK (pontos_fidelidade >= 0),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela Produtos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    preco REAL NOT NULL CHECK (preco > 0),
                    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela Vendas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER NOT NULL,
                    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                    total REAL NOT NULL CHECK (total > 0),
                    usuario TEXT NOT NULL,
                    cliente_id INTEGER,
                    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (produto_id) REFERENCES produtos (id),
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id)
                )
            ''')
            
            conn.commit()
            print("✅ Banco inicializado completamente!")
    
    def criar_usuario_padrao(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE usuario = 'danilo'")
            if not cursor.fetchone():
                senha_hash = self.hash_senha('19062010danilo2')
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha, cargo, ativo) VALUES (?, ?, ?, ?)",
                    ('danilo', senha_hash, 'admin', 1)
                )
                conn.commit()
                print("✅ Admin padrão: danilo / 19062010danilo2")
    
    # === SISTEMA DE CLIENTES ===
    def cadastrar_cliente(self):
        print("\n" + "="*70)
        print("                🆕 CADASTRO DE CLIENTE")
        print("="*70)
        
        nome = input("👤 Nome completo: ").strip()
        if len(nome) < 2:
            print("❌ Nome muito curto (mínimo 2 caracteres)!")
            return
        
        email = input("📧 Email: ").strip().lower()
        if not self.validar_email(email):
            print("❌ Email inválido!")
            return
        
        telefone = input("📱 Telefone (opcional): ").strip()
        data_nasc = input("🎂 Data nascimento (DD/MM/AAAA, opcional): ").strip()
        
        senha1 = getpass.getpass("🔒 Senha (mín 6 caracteres): ")
        senha2 = getpass.getpass("🔒 Confirme a senha: ")
        
        if senha1 != senha2:
            print("❌ As senhas não conferem!")
            return
        
        if len(senha1) < 6:
            print("❌ Senha muito curta! Mínimo 6 caracteres.")
            return
        
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO clientes (nome, email, telefone, senha, data_nascimento, ativo, pontos_fidelidade) 
                       VALUES (?, ?, ?, ?, ?, 1, 0)''',
                    (nome, email, telefone or None, self.hash_senha(senha1), data_nasc or None)
                )
                conn.commit()
            print(f"\n🎉 CLIENTE '{nome}' CADASTRADO COM SUCESSO!")
            print(f"📧 Email para login: {email}")
            print("💡 Guarde bem sua senha!")
        except sqlite3.IntegrityError:
            print("❌ Este email já está cadastrado!")
    
    def login_cliente(self) -> Optional[Tuple[int, str]]:
        print("\n" + "="*60)
        print("                👤 LOGIN DO CLIENTE")
        print("="*60)
        print("💡 Cadastre-se primeiro se não tiver conta!")
        print()
        
        email = input("📧 Email: ").strip().lower()
        senha = getpass.getpass("🔒 Senha: ")
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, nome FROM clientes WHERE email = ? AND senha = ? AND ativo = 1',
                (email, self.hash_senha(senha))
            )
            return cursor.fetchone()
    
    def menu_cliente(self, cliente_id: int, cliente_nome: str):
        while True:
            print(f"\n👩‍🦰 CLIENTE: {cliente_nome}")
            print("="*50)
            self.mostrar_pontos_cliente(cliente_id)
            print("1. 📦 Ver Produtos")
            print("2. 🛒 Fazer Compra")
            print("3. 📊 Minhas Compras")
            print("4. 👋 Sair")
            print("="*50)
            
            op = input("Escolha: ").strip()
            
            if op == '1':
                self.listar_produtos_cliente()
            elif op == '2':
                self.compra_cliente(cliente_id)
            elif op == '3':
                self.minhas_compras_cliente(cliente_id)
            elif op == '4':
                print("👋 Obrigado por usar nosso sistema!")
                break
            else:
                print("❌ Opção inválida!")
    
    def mostrar_pontos_cliente(self, cliente_id: int):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT pontos_fidelidade FROM clientes WHERE id = ?', (cliente_id,))
            pontos = cursor.fetchone()
            if pontos:
                print(f"⭐ SEUS PONTOS: {pontos[0]}")
    
    def listar_produtos_cliente(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome, preco FROM produtos WHERE estoque > 0 ORDER BY nome')
            produtos = cursor.fetchall()
            
            if not produtos:
                print("\n❌ Nenhum produto disponível!")
                return
            
            print("\n🛍️  PRODUTOS DISPONÍVEIS")
            print("-"*50)
            print(f"{'ID':<4} {'PRODUTO':<25} {'PREÇO'}")
            print("-"*50)
            for p in produtos:
                print(f"{p[0]:<4} {p[1]:<25} R$ {p[2]:.2f}")
            print("-"*50)
    
    def compra_cliente(self, cliente_id: int):
        self.listar_produtos_cliente()
        print("\n🛒 REALIZAR COMPRA")
        
        try:
            pid = int(input("ID do produto: "))
            qtd = int(input("Quantidade: "))
            
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, nome, preco, estoque FROM produtos WHERE id = ? AND estoque >= ?', (pid, qtd))
                produto = cursor.fetchone()
                
                if not produto:
                    print("❌ Produto não disponível ou estoque insuficiente!")
                    return
                
                total = produto[2] * qtd
                
                # Simula venda para cliente (sem reduzir estoque real)
                cursor.execute(
                    'INSERT INTO vendas (produto_id, quantidade, total, usuario, cliente_id) VALUES (?, ?, ?, ?, ?)',
                    (pid, qtd, total, f'cliente_{cliente_id}', cliente_id)
                )
                
                # Adiciona pontos (1 ponto por item)
                pontos = qtd
                cursor.execute('UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id = ?', (pontos, cliente_id))
                
                conn.commit()
                
                print("\n✅ COMPRA REALIZADA!")
                print(f"📦 {produto[1]} x{qtd}")
                print(f"💰 Total: R$ {total:.2f}")
                print(f"⭐ +{pontos} pontos ganhos!")
                
        except ValueError:
            print("❌ Digite números válidos!")
    
    def minhas_compras_cliente(self, cliente_id: int):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.nome, v.quantidade, v.total, v.data 
                FROM vendas v 
                JOIN produtos p ON v.produto_id = p.id 
                WHERE v.cliente_id = ? 
                ORDER BY v.data DESC LIMIT 10
            ''', (cliente_id,))
            compras = cursor.fetchall()
            
            if not compras:
                print("\n📋 Você ainda não fez compras!")
                return
            
            print("\n📋 SUAS ÚLTIMAS COMPRAS")
            print("-"*60)
            total_gasto = 0
            for c in compras:
                print(f"{c[0]:<25} x{c[1]:<3} R${c[2]:<8.2f} {c[3][:16]}")
                total_gasto += c[2]
            print("-"*60)
            print(f"💎 Total gasto: R$ {total_gasto:.2f}")
    
    # === SISTEMA FUNCIONÁRIOS ===
    def fazer_login_funcionario(self) -> Optional[Tuple[str, str]]:
        print("\n" + "="*60)
        print("                👨‍💼 LOGIN FUNCIONÁRIO")
        print("="*60)
        print("💡 danilo/19062010danilo2")
        print()
        
        usuario = input("👤 Usuário: ").strip()
        senha = getpass.getpass("🔒 Senha: ")
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT usuario, cargo FROM usuarios WHERE usuario = ? AND senha = ? AND ativo = 1',
                (usuario, self.hash_senha(senha))
            )
            return cursor.fetchone()
    
    def listar_produtos(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM produtos ORDER BY nome')
            produtos = cursor.fetchall()
            
            if not produtos:
                print("\n❌ Nenhum produto!")
                return
            
            print("\n📦 PRODUTOS")
            print("-"*70)
            print(f"{'ID':<5} {'NOME':<25} {'PREÇO':<10} {'ESTOQUE':<8} {'STATUS'}")
            print("-"*70)
            for p in produtos:
                status = "🚨 CRÍTICO" if p[3] < 10 else "✅ OK"
                print(f"{p[0]:<5} {p[1]:<25} R${p[2]:<10.2f} {p[3]:<8} {status}")
            print("-"*70)
    
    def menu_principal(self):
        while True:
            print("\n" + "="*70)
            print("                SISTEMA COMERCIAL v5.0")
            print("="*70)
            print("1. 👤 Login Cliente")
            print("2. 🆕 Cadastrar Cliente")
            print("3. 👨‍💼 Login Funcionário")
            print("4. 🚪 Sair")
            print("="*70)
            
            op = input("Escolha uma opção: ").strip()
            
            if op == '1':
                credenciais = self.login_cliente()
                if credenciais:
                    cid, nome = credenciais
                    self.menu_cliente(cid, nome)
                else:
                    print("❌ Email ou senha incorretos!")
            elif op == '2':
                self.cadastrar_cliente()
            elif op == '3':
                credenciais = self.fazer_login_funcionario()
                if credenciais:
                    usuario, cargo = credenciais
                    print(f"\n🎉 Bem-vindo, {usuario}! ({cargo.upper()})")
                    self.menu_vendedor(usuario)
                else:
                    print("❌ Credenciais inválidas!")
            elif op == '4':
                print("👋 Obrigado por usar o sistema!")
                break
            else:
                print("❌ Opção inválida!")
    
    def menu_vendedor(self, usuario: str):
        while True:
            print(f"\n👨‍💼 VENDEDOR: {usuario}")
            print("="*50)
            print("1. 📦 Listar Produtos")
            print("2. ➕ Cadastrar Produto")
            print("3. 📊 Vendas Hoje")
            print("4. 🚪 Logout")
            print("="*50)
            
            op = input("Opção: ").strip()
            
            if op == '1':
                self.listar_produtos()
            elif op == '2':
                self.cadastrar_produto()
            elif op == '3':
                self.relatorio_vendas()
            elif op == '4':
                break
            else:
                print("❌ Opção inválida!")
    
    def cadastrar_produto(self):
        print("\n➕ NOVO PRODUTO")
        print("-"*30)
        nome = input("Nome: ").strip()
        try:
            preco = float(input("Preço R$: "))
            estoque = int(input("Estoque: "))
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)', (nome, preco, estoque))
                conn.commit()
            print(f"✅ '{nome}' cadastrado!")
        except ValueError:
            print("❌ Dados inválidos!")
    
    def relatorio_vendas(self):
        hoje = datetime.now().strftime('%Y-%m-%d')
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT SUM(total) FROM vendas WHERE DATE(data) = ?', (hoje,))
            total = cursor.fetchone()[0] or 0
            print(f"\n💰 VENDAS HOJE: R$ {total:.2f}")

def main():
    sistema = SistemaComercial()
    sistema.menu_principal()

if __name__ == "__main__":
    main()
