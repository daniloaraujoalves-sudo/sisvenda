import sqlite3
import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple

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
    
    def inicializar_db_completo(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT NOT NULL,
                    cargo TEXT NOT NULL CHECK (cargo IN ('admin', 'vendedor')),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    preco REAL NOT NULL CHECK (preco > 0),
                    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER NOT NULL,
                    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                    total REAL NOT NULL CHECK (total > 0),
                    usuario TEXT NOT NULL,
                    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (produto_id) REFERENCES produtos (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    produto_id INTEGER NOT NULL,
                    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                    custo_unitario REAL NOT NULL CHECK (custo_unitario > 0),
                    custo_total REAL NOT NULL CHECK (custo_total > 0),
                    usuario TEXT NOT NULL,
                    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (produto_id) REFERENCES produtos (id)
                )
            ''')
            
            conn.commit()
            print("✅ Banco inicializado!")
    
    def criar_usuario_padrao(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE usuario = 'admin'")
            if not cursor.fetchone():
                senha_hash = self.hash_senha('admin123')
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha, cargo) VALUES (?, ?, ?)",
                    ('admin', senha_hash, 'admin')
                )
                conn.commit()
                print("✅ Usuario padrão: admin / admin123")
    
    def fazer_login(self) -> Optional[Tuple[str, str]]:
        print("\n" + "="*50)
        print("                SISTEMA DE LOGIN v4.2")
        print("="*50)
        print("💡 Dica: admin / admin123")
        print()
        
        usuario = input("👤 Usuario: ").strip()
        senha = input("🔒 Senha: ").strip()  # ✅ SIMPLES E FUNCIONA SEMPRE!
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT usuario, cargo FROM usuarios WHERE usuario = ? AND senha = ?',
                (usuario, self.hash_senha(senha))
            )
            return cursor.fetchone()
    
    def cadastrar_usuario(self):
        print("\n" + "="*50)
        print("                NOVO USUARIO")
        print("="*50)
        
        usuario = input("👤 Nome de usuario: ").strip()
        senha1 = input("🔒 Senha (min 4 chars): ").strip()
        senha2 = input("🔒 Confirme senha: ").strip()
        
        if senha1 != senha2:
            print("❌ Senhas não conferem!")
            return
        
        if len(senha1) < 4:
            print("❌ Senha muito curta!")
            return
        
        print("Cargo: [1] Admin  [2] Vendedor")
        cargo_op = input("Opção (1/2): ").strip()
        cargo = 'admin' if cargo_op == '1' else 'vendedor'
        
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO usuarios (usuario, senha, cargo) VALUES (?, ?, ?)',
                    (usuario, self.hash_senha(senha1), cargo)
                )
                conn.commit()
            print(f"✅ '{usuario}' criado como {cargo.upper()}!")
        except sqlite3.IntegrityError:
            print("❌ Usuario já existe!")
    
    def listar_produtos(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM produtos ORDER BY nome')
            produtos = cursor.fetchall()
            
            if not produtos:
                print("\n❌ Nenhum produto!")
                return
            
            print("\n" + "="*70)
            print(f"{'ID':<5} {'PRODUTO':<25} {'PREÇO':<12} {'ESTOQUE':<10} {'STATUS'}")
            print("-"*70)
            for p in produtos:
                status = "🚨 CRÍTICO" if p[3] < 10 else "✅ OK"
                print(f"{p[0]:<5} {p[1]:<25} R${p[2]:<10.2f} {p[3]:<10} {status}")
            print("="*70)
    
    def estoque_critico(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nome, estoque FROM produtos WHERE estoque < 10')
            criticos = cursor.fetchall()
            if criticos:
                print("\n🚨 ESTOQUE CRÍTICO:")
                for p in criticos:
                    print(f"   {p[0]}: {p[1]} und")
    
    def cadastrar_produto(self):
        print("\n🆕 CADASTRO PRODUTO")
        print("-"*30)
        
        nome = input("Nome: ").strip()
        try:
            preco = float(input("Preço R$: "))
            estoque = int(input("Estoque: "))
            
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)',
                    (nome, preco, estoque)
                )
                conn.commit()
            print(f"✅ '{nome}' cadastrado!")
        except ValueError:
            print("❌ Números inválidos!")
    
    def realizar_venda(self, produto_id: int, quantidade: int, usuario: str):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nome, preco, estoque FROM produtos WHERE id = ?', (produto_id,))
            produto = cursor.fetchone()
            
            if not produto:
                print("❌ Produto não existe!")
                return
            
            if produto[2] < quantidade:
                print(f"❌ Estoque: {produto[2]}")
                return
            
            total = produto[1] * quantidade
            cursor.execute('UPDATE produtos SET estoque = estoque - ? WHERE id = ?', (quantidade, produto_id))
            cursor.execute(
                'INSERT INTO vendas (produto_id, quantidade, total, usuario) VALUES (?, ?, ?, ?)',
                (produto_id, quantidade, total, usuario)
            )
            conn.commit()
            
            print("\n✅ VENDA OK!")
            print(f"{produto[0]} x{quantidade} = R${total:.2f}")
    
    def registrar_compra(self, produto_id: int, quantidade: int, custo_total: float, usuario: str):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM produtos WHERE id = ?', (produto_id,))
            produto = cursor.fetchone()
            
            if not produto:
                print("❌ Produto não existe!")
                return
            
            custo_unit = custo_total / quantidade
            cursor.execute('UPDATE produtos SET estoque = estoque + ? WHERE id = ?', (quantidade, produto_id))
            cursor.execute(
                'INSERT INTO compras (produto_id, quantidade, custo_unitario, custo_total, usuario) VALUES (?, ?, ?, ?, ?)',
                (produto_id, quantidade, custo_unit, custo_total, usuario)
            )
            conn.commit()
            
            print("\n✅ COMPRA OK!")
            print(f"{produto[0]} x{quantidade} = R${custo_total:.2f}")
    
    def relatorio_vendas(self):
        hoje = datetime.now().strftime('%Y-%m-%d')
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.nome, v.quantidade, v.total, v.data, v.usuario
                FROM vendas v JOIN produtos p ON v.produto_id = p.id 
                WHERE DATE(v.data) = ? ORDER BY v.data DESC
            ''', (hoje,))
            vendas = cursor.fetchall()
            
            if not vendas:
                print("\n📊 Sem vendas hoje!")
                return
            
            print("\n📊 VENDAS HOJE")
            print("-"*60)
            total_dia = 0
            for v in vendas:
                print(f"{v[0]:<25} x{v[1]:<3} R${v[2]:<8.2f} {v[4]} {v[3][:16]}")
                total_dia += v[2]
            print("-"*60)
            print(f"TOTAL: R$ {total_dia:.2f}")
    
    def menu_vendedor(self, usuario: str):
        while True:
            print(f"\n👨‍💼 VENDEDOR - {usuario}")
            print("1. 📋 Estoque")
            print("2. 💰 Venda")
            print("3. 📊 Relatório")
            print("4. 🚪 Sair")
            
            op = input("Opção: ").strip()
            
            if op == '1':
                self.listar_produtos()
                self.estoque_critico()
            elif op == '2':
                self.listar_produtos()
                try:
                    pid = int(input("ID: "))
                    qtd = int(input("Qtd: "))
                    self.realizar_venda(pid, qtd, usuario)
                except:
                    print("❌ Erro!")
            elif op == '3':
                self.relatorio_vendas()
            elif op == '4':
                break
            input("⏎ Enter...")
    
    def menu_admin(self, usuario: str):
        while True:
            print(f"\n👑 ADMIN - {usuario}")
            print("1. 🆕 Produto")
            print("2. 📋 Estoque")
            print("3. 💰 Venda")
            print("4. 🛒 Compra")
            print("5. 📊 Relatório")
            print("6. 👤 Usuario")
            print("7. 🚪 Sair")
            
            op = input("Opção: ").strip()
            
            if op == '1':
                self.cadastrar_produto()
            elif op == '2':
                self.listar_produtos()
                self.estoque_critico()
            elif op == '3':
                self.listar_produtos()
                try:
                    pid = int(input("ID: "))
                    qtd = int(input("Qtd: "))
                    self.realizar_venda(pid, qtd, usuario)
                except:
                    print("❌ Erro!")
            elif op == '4':
                self.listar_produtos()
                try:
                    pid = int(input("ID: "))
                    qtd = int(input("Qtd: "))
                    custo = float(input("Custo R$: "))
                    self.registrar_compra(pid, qtd, custo, usuario)
                except:
                    print("❌ Erro!")
            elif op == '5':
                self.relatorio_vendas()
            elif op == '6':
                self.cadastrar_usuario()
            elif op == '7':
                break
            input("⏎ Enter...")
    
    def main(self):
        print("🎯 SISTEMA COMERCIAL v4.2")
        print("👤 admin / admin123")
        print("-"*40)
        
        while True:
            print("\n🔐 MENU PRINCIPAL")
            print("1. Login")
            print("2. Novo Usuario")
            print("3. Sair")
            
            op = input("Opção: ").strip()
            
            if op == '1':
                credenciais = self.fazer_login()
                if credenciais:
                    usuario, cargo = credenciais
                    print(f"\n🎉 {usuario} ({cargo.upper()})")
                    if cargo == 'admin':
                        self.menu_admin(usuario)
                    else:
                        self.menu_vendedor(usuario)
                else:
                    print("❌ Login inválido!")
                input("⏎ Enter...")
            elif op == '2':
                self.cadastrar_usuario()
                input("⏎ Enter...")
            elif op == '3':
                print("👋 Até logo!")
                break

if __name__ == "__main__":
    app = SistemaComercial()
    app.main()