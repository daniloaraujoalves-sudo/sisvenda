import sqlite3
import os
import hashlib
import re
from datetime import datetime
from typing import Optional, Tuple
import getpass

DB_NAME = 'comercial_new.db'
BACKUP_DIR = 'backups'

class SistemaComercial:
    def __init__(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        self.inicializar_db_completo()
        self.criar_usuario_padrao()
    
    def hash_senha(self, senha: str) -> str:
        salt = "sistema_comercial_v5_2026"  # Salt atualizado
        return hashlib.sha256((senha + salt).encode()).hexdigest()
    
    def validar_email(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def inicializar_db_completo(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Tabelas principais
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
                telefone TEXT,
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
                vendedor_id TEXT,
                cliente_id INTEGER,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'CONCLUIDA',
                FOREIGN KEY (produto_id) REFERENCES produtos (id),
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )''')
            conn.commit()

    def criar_usuario_padrao(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE usuario = 'danilo'")
            if not cursor.fetchone():
                cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (?, ?, ?)",
                             ('danilo', self.hash_senha('123456'), 'admin'))
                conn.commit()

    # --- LÓGICA DE NEGÓCIO ---

    def compra_cliente(self, cliente_id: int):
        self.listar_produtos_cliente()
        print("\n🛒 [NOVA COMPRA]")
        
        try:
            pid = int(input("🆔 ID do Produto: "))
            qtd = int(input("🔢 Quantidade: "))
            
            if qtd <= 0: return print("❌ Quantidade inválida.")

            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT nome, preco, estoque FROM produtos WHERE id = ?', (pid,))
                prod = cursor.fetchone()

                if not prod:
                    return print("❌ Produto não encontrado!")
                if prod[2] < qtd:
                    return print(f"❌ Estoque insuficiente! (Disponível: {prod[2]})")

                total = prod[1] * qtd
                
                # Transação Atômica: Deduz estoque e registra venda
                cursor.execute('UPDATE produtos SET estoque = estoque - ? WHERE id = ?', (qtd, pid))
                cursor.execute('''INSERT INTO vendas (produto_id, quantidade, total, vendedor_id, cliente_id) 
                                  VALUES (?, ?, ?, ?, ?)''', (pid, qtd, total, 'AUTO_CLIENTE', cliente_id))
                cursor.execute('UPDATE clientes SET pontos_fidelidade = pontos_fidelidade + ? WHERE id = ?', (qtd, cliente_id))
                
                conn.commit()
                print(f"\n✅ Compra de {prod[0]} realizada! Total: R$ {total:.2f}")

        except ValueError:
            print("❌ Erro: Digite apenas números!")

    def relatorio_vendas(self):
        print("\n" + "─"*40)
        print("📊 RELATÓRIO DE VENDAS (HOJE)")
        print("─"*40)
        hoje = datetime.now().strftime('%Y-%m-%d')
        
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT v.id, p.nome, v.quantidade, v.total, v.status 
                              FROM vendas v JOIN produtos p ON v.produto_id = p.id 
                              WHERE DATE(v.data) = ?''', (hoje,))
            vendas = cursor.fetchall()
            
            if not vendas:
                print("Nenhuma venda realizada hoje.")
                return

            soma = 0
            for v in vendas:
                status_icon = "✅" if v[4] == 'CONCLUIDA' else "❌"
                print(f"{status_icon} ID:{v[0]} | {v[1]} (x{v[2]}) | R$ {v[3]:.2f}")
                if v[4] == 'CONCLUIDA': soma += v[3]
            
            print("─"*40)
            print(f"💰 FATURAMENTO LÍQUIDO: R$ {soma:.2f}")

    # --- MENUS ---

    def menu_principal(self):
        while True:
            print(f"\n{'—'*30}\n 🏪 MERCADO DIGITAL\n{'—'*30}")
            print("1. 👤 Área do Cliente")
            print("2. 👨‍💼 Área da Equipe")
            print("3. 🚪 Sair")
            
            op = input("\nSelecione: ").strip()
            
            if op == '1': self.submenu_cliente()
            elif op == '2': self.submenu_funcionario()
            elif op == '3': break
            else: print("❌ Opção inválida.")

    def submenu_cliente(self):
        print("\n1. Login | 2. Cadastro")
        escolha = input(">> ")
        if escolha == '1':
            res = self.login_cliente()
            if res: self.menu_cliente(res[0], res[1])
            else: print("❌ Falha no login.")
        elif escolha == '2':
            self.cadastrar_cliente()

    def submenu_funcionario(self):
        res = self.fazer_login_funcionario()
        if res: self.menu_vendedor(res[0])
        else: print("❌ Acesso negado.")

    def menu_cliente(self, cid, nome):
        while True:
            print(f"\n👋 Olá, {nome}!")
            print("1. 🛍️ Ver Loja | 2. 🛒 Comprar | 3. 📜 Histórico | 4. 🔙 Voltar")
            op = input(">> ")
            if op == '1': self.listar_produtos_cliente()
            elif op == '2': self.compra_cliente(cid)
            elif op == '3': self.minhas_compras_cliente(cid)
            elif op == '4': break

    def listar_produtos_cliente(self):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome, preco, estoque FROM produtos WHERE estoque > 0')
            prods = cursor.fetchall()
            print(f"\n{'ID':<4} | {'PRODUTO':<20} | {'PREÇO':<10} | {'DISP.'}")
            print("-" * 50)
            for p in prods:
                print(f"{p[0]:<4} | {p[1]:<20} | R$ {p[2]:<8.2f} | {p[3]} un")

    # Reutilizando e adaptando as outras funções que você enviou...
    # (Cadastrar_cliente, Login_cliente, etc., mantêm a mesma lógica do seu original)

    def login_cliente(self) -> Optional[Tuple[int, str]]:
        email = input("📧 Email: ").strip().lower()
        senha = getpass.getpass("🔒 Senha: ")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, nome FROM clientes WHERE email = ? AND senha = ? AND ativo = 1',
                         (email, self.hash_senha(senha)))
            return cursor.fetchone()

    def fazer_login_funcionario(self) -> Optional[Tuple[str, str]]:
        usuario = input("👤 Usuário: ").strip()
        senha = getpass.getpass("🔒 Senha: ")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT usuario, cargo FROM usuarios WHERE usuario = ? AND senha = ?',
                         (usuario, self.hash_senha(senha)))
            return cursor.fetchone()

    def menu_vendedor(self, usuario):
        while True:
            print(f"\n🛠️ PAINEL ADMIN: {usuario}")
            print("1. 📦 Estoque | 2. ➕ Novo Produto | 3. 📊 Relatório | 4. 🔙 Sair")
            op = input(">> ")
            if op == '1': self.listar_produtos_cliente() # Reaproveitando visualização
            elif op == '2': self.cadastrar_produto()
            elif op == '3': self.relatorio_vendas()
            elif op == '4': break

    def cadastrar_produto(self):
        nome = input("Nome: ")
        preco = float(input("Preço: "))
        qtd = int(input("Estoque Inicial: "))
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute('INSERT INTO produtos (nome, preco, estoque) VALUES (?,?,?)', (nome, preco, qtd))
            conn.commit()
        print("✅ Produto adicionado!")

    def cadastrar_cliente(self):
        nome = input("Nome: ")
        email = input("Email: ")
        if not self.validar_email(email): return print("❌ Email inválido")
        senha = getpass.getpass("Senha: ")
        with sqlite3.connect(DB_NAME) as conn:
            try:
                conn.execute('INSERT INTO clientes (nome, email, senha) VALUES (?,?,?)', 
                             (nome, email, self.hash_senha(senha)))
                conn.commit()
                print("✅ Cliente cadastrado!")
            except: print("❌ Erro: Email já existe.")

    def minhas_compras_cliente(self, cid):
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT p.nome, v.quantidade, v.total, v.data 
                              FROM vendas v JOIN produtos p ON v.produto_id = p.id 
                              WHERE v.cliente_id = ?''', (cid,))
            for r in cursor.fetchall():
                print(f"📦 {r[0]} | x{r[1]} | R$ {r[2]:.2f} em {r[3]}")

if __name__ == "__main__":
    SistemaComercial().menu_principal()
