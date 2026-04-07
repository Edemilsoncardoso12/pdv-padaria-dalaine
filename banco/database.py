import sqlite3
import os
import sys

# Detecta BASE_DIR igual ao main.py
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(BASE_DIR, "banco", "padaria.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco():
    conn = get_conn()
    c = conn.cursor()

    # Produtos
    c.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras   TEXT UNIQUE,
            nome            TEXT NOT NULL,
            ncm             TEXT DEFAULT '',
            unidade         TEXT DEFAULT 'UN',
            grupo           TEXT DEFAULT 'GERAL',
            marca           TEXT DEFAULT '',
            preco_custo     REAL DEFAULT 0,
            preco_venda     REAL DEFAULT 0,
            estoque_atual   REAL DEFAULT 0,
            estoque_minimo  REAL DEFAULT 0,
            ativo           INTEGER DEFAULT 1,
            criado_em       TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Caixa
    c.execute("""
        CREATE TABLE IF NOT EXISTS caixa (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            data_abertura   TEXT,
            data_fechamento TEXT,
            valor_inicial   REAL DEFAULT 0,
            valor_final     REAL DEFAULT 0,
            status          TEXT DEFAULT 'ABERTO'
        )
    """)

    # Vendas
    c.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id        INTEGER REFERENCES caixa(id),
            data_hora       TEXT DEFAULT (datetime('now','localtime')),
            subtotal        REAL DEFAULT 0,
            desconto        REAL DEFAULT 0,
            total           REAL DEFAULT 0,
            forma_pagamento TEXT DEFAULT 'DINHEIRO',
            valor_pago      REAL DEFAULT 0,
            troco           REAL DEFAULT 0,
            cpf_cliente     TEXT DEFAULT '',
            status          TEXT DEFAULT 'CONCLUIDA',
            nfce_numero     TEXT DEFAULT '',
            nfce_chave      TEXT DEFAULT '',
            nfce_status     TEXT DEFAULT 'PENDENTE'
        )
    """)
    # Adiciona coluna nfce_chave se não existir (migração)
    try:
        c.execute("ALTER TABLE vendas ADD COLUMN nfce_chave TEXT DEFAULT ''")
    except Exception:
        pass

    # Itens da venda
    c.execute("""
        CREATE TABLE IF NOT EXISTS itens_venda (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id        INTEGER REFERENCES vendas(id),
            produto_id      INTEGER REFERENCES produtos(id),
            nome_produto    TEXT,
            codigo_barras   TEXT,
            quantidade      REAL DEFAULT 1,
            preco_unitario  REAL DEFAULT 0,
            desconto        REAL DEFAULT 0,
            total_item      REAL DEFAULT 0
        )
    """)

    # Movimentações de estoque
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id  INTEGER REFERENCES produtos(id),
            tipo        TEXT,   -- ENTRADA / SAIDA / AJUSTE
            quantidade  REAL,
            saldo_apos  REAL,
            observacao  TEXT DEFAULT '',
            data_hora   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    # Configurações
    c.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave   TEXT PRIMARY KEY,
            valor   TEXT
        )
    """)

    # Dados padrão de configuração
    configs = [
        ("empresa_nome",    "Padaria Da Laine"),
        ("empresa_cnpj",    ""),
        ("empresa_ie",      ""),
        ("empresa_end",     ""),
        ("focusnfe_token",  ""),
        ("focusnfe_amb",    "homologacao"),
        ("impressora",      ""),
    ]
    for chave, valor in configs:
        c.execute("INSERT OR IGNORE INTO configuracoes VALUES (?,?)", (chave, valor))

    conn.commit()
    conn.close()


# ── PRODUTOS ─────────────────────────────────────────────────────────────────

def listar_produtos(busca=""):
    conn = get_conn()
    if busca:
        rows = conn.execute("""
            SELECT * FROM produtos
            WHERE ativo=1 AND (
                nome LIKE ? OR codigo_barras LIKE ? OR grupo LIKE ?
            ) ORDER BY nome
        """, (f"%{busca}%", f"%{busca}%", f"%{busca}%")).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM produtos WHERE ativo=1 ORDER BY nome"
        ).fetchall()
    conn.close()
    return rows


def buscar_produto_por_codigo(codigo):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM produtos WHERE codigo_barras=? AND ativo=1", (codigo,)
    ).fetchone()
    conn.close()
    return row


def salvar_produto(dados: dict, produto_id=None):
    conn = get_conn()
    if produto_id:
        conn.execute("""
            UPDATE produtos SET
                codigo_barras=:codigo_barras, nome=:nome, ncm=:ncm,
                unidade=:unidade, grupo=:grupo, marca=:marca,
                preco_custo=:preco_custo, preco_venda=:preco_venda,
                estoque_minimo=:estoque_minimo
            WHERE id=:id
        """, {**dados, "id": produto_id})
    else:
        conn.execute("""
            INSERT INTO produtos
                (codigo_barras,nome,ncm,unidade,grupo,marca,
                 preco_custo,preco_venda,estoque_minimo)
            VALUES
                (:codigo_barras,:nome,:ncm,:unidade,:grupo,:marca,
                 :preco_custo,:preco_venda,:estoque_minimo)
        """, dados)
    conn.commit()
    conn.close()


def excluir_produto(produto_id):
    conn = get_conn()
    conn.execute("UPDATE produtos SET ativo=0 WHERE id=?", (produto_id,))
    conn.commit()
    conn.close()


# ── ESTOQUE ──────────────────────────────────────────────────────────────────

def movimentar_estoque(produto_id, tipo, quantidade, obs=""):
    conn = get_conn()
    prod = conn.execute("SELECT estoque_atual FROM produtos WHERE id=?",
                        (produto_id,)).fetchone()
    if not prod:
        conn.close()
        return
    if tipo == "ENTRADA":
        novo = prod["estoque_atual"] + quantidade
    elif tipo == "SAIDA":
        novo = prod["estoque_atual"] - quantidade
    else:  # AJUSTE
        novo = quantidade

    conn.execute("UPDATE produtos SET estoque_atual=? WHERE id=?", (novo, produto_id))
    conn.execute("""
        INSERT INTO movimentacoes_estoque (produto_id,tipo,quantidade,saldo_apos,observacao)
        VALUES (?,?,?,?,?)
    """, (produto_id, tipo, quantidade, novo, obs))
    conn.commit()
    conn.close()


def listar_movimentacoes(produto_id=None):
    conn = get_conn()
    if produto_id:
        rows = conn.execute("""
            SELECT m.*, p.nome as produto_nome FROM movimentacoes_estoque m
            JOIN produtos p ON p.id=m.produto_id
            WHERE m.produto_id=? ORDER BY m.data_hora DESC LIMIT 200
        """, (produto_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.*, p.nome as produto_nome FROM movimentacoes_estoque m
            JOIN produtos p ON p.id=m.produto_id
            ORDER BY m.data_hora DESC LIMIT 200
        """).fetchall()
    conn.close()
    return rows


# ── CAIXA / VENDAS ────────────────────────────────────────────────────────────

def caixa_aberto():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM caixa WHERE status='ABERTO' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row


def abrir_caixa(valor_inicial=0.0):
    conn = get_conn()
    conn.execute("""
        INSERT INTO caixa (data_abertura, valor_inicial, status)
        VALUES (datetime('now','localtime'), ?, 'ABERTO')
    """, (valor_inicial,))
    conn.commit()
    conn.close()


def fechar_caixa(caixa_id, valor_final):
    conn = get_conn()
    conn.execute("""
        UPDATE caixa SET status='FECHADO',
            data_fechamento=datetime('now','localtime'),
            valor_final=?
        WHERE id=?
    """, (valor_final, caixa_id))
    conn.commit()
    conn.close()


def registrar_venda(caixa_id, itens, forma_pagamento,
                    valor_pago, desconto=0, cpf=""):
    conn = get_conn()
    subtotal = sum(i["total_item"] for i in itens)
    total    = subtotal - desconto
    troco    = max(0, valor_pago - total)

    cur = conn.execute("""
        INSERT INTO vendas
            (caixa_id,subtotal,desconto,total,forma_pagamento,
             valor_pago,troco,cpf_cliente)
        VALUES (?,?,?,?,?,?,?,?)
    """, (caixa_id, subtotal, desconto, total,
          forma_pagamento, valor_pago, troco, cpf))
    venda_id = cur.lastrowid

    for item in itens:
        conn.execute("""
            INSERT INTO itens_venda
                (venda_id,produto_id,nome_produto,codigo_barras,
                 quantidade,preco_unitario,desconto,total_item)
            VALUES (?,?,?,?,?,?,?,?)
        """, (venda_id, item["produto_id"], item["nome_produto"],
              item["codigo_barras"], item["quantidade"],
              item["preco_unitario"], item.get("desconto", 0),
              item["total_item"]))
        # Baixa estoque
        prod = conn.execute("SELECT estoque_atual FROM produtos WHERE id=?",
                            (item["produto_id"],)).fetchone()
        if prod:
            novo = prod["estoque_atual"] - item["quantidade"]
            conn.execute("UPDATE produtos SET estoque_atual=? WHERE id=?",
                         (novo, item["produto_id"]))
            conn.execute("""
                INSERT INTO movimentacoes_estoque
                    (produto_id,tipo,quantidade,saldo_apos,observacao)
                VALUES (?,?,?,?,?)
            """, (item["produto_id"], "SAIDA", item["quantidade"],
                  novo, f"Venda #{venda_id}"))

    conn.commit()
    conn.close()
    return venda_id, total, troco


def listar_vendas(data_ini=None, data_fim=None):
    conn = get_conn()
    query = "SELECT * FROM vendas WHERE 1=1"
    params = []
    if data_ini:
        query += " AND date(data_hora) >= ?"
        params.append(data_ini)
    if data_fim:
        query += " AND date(data_hora) <= ?"
        params.append(data_fim)
    query += " ORDER BY data_hora DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_config(chave):
    conn = get_conn()
    row = conn.execute("SELECT valor FROM configuracoes WHERE chave=?",
                       (chave,)).fetchone()
    conn.close()
    return row["valor"] if row else ""


def set_config(chave, valor):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO configuracoes VALUES (?,?)", (chave, valor))
    conn.commit()
    conn.close()
