"""
telas/recebimento.py — Recebimento de Mercadorias
Leitor de código de barras/QR code (pistola USB), entrada no estoque,
boletos vinculados, avisos de vencimento
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, date, timedelta
from tema import *
from banco.database import get_conn, movimentar_estoque



def _geometry_responsiva(win, largura_pct=0.6, altura_pct=0.75, min_w=500, min_h=400):
    """Ajusta a janela proporcionalmente à resolução da tela."""
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        w  = max(min_w, int(sw * largura_pct))
        h  = max(min_h, int(sh * altura_pct))
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.minsize(min_w, min_h)
    except Exception:
        pass

def _configurar_tab_scroll(campos, scroll_frame=None):
    """Liga Tab/Shift-Tab entre campos e faz scroll automático ao focar."""
    entradas = [c for c in campos if hasattr(c, 'bind')]
    for i, campo in enumerate(entradas):
        prox  = entradas[(i + 1) % len(entradas)]
        prev  = entradas[(i - 1) % len(entradas)]

        def _ir_para(w, event=None):
            try:
                w.focus_set()
                if hasattr(w, 'select_range'):
                    w.select_range(0, 'end')
            except Exception:
                pass
            return "break"

        def _scroll_ao_focar(w, sf, event=None):
            if sf is None:
                return
            try:
                sf.update_idletasks()
                canvas = sf._parent_canvas
                cy = canvas.winfo_height()
                wy = w.winfo_y()
                total = sf.winfo_height()
                if total > 0:
                    canvas.yview_moveto(max(0, (wy - cy // 2) / total))
            except Exception:
                pass

        campo.bind("<Tab>",       lambda e, p=prox,  sf=scroll_frame: (_ir_para(p), _scroll_ao_focar(p, sf)) and None or "break")
        campo.bind("<Shift-Tab>", lambda e, p=prev,  sf=scroll_frame: (_ir_para(p), _scroll_ao_focar(p, sf)) and None or "break")
        campo.bind("<FocusIn>",   lambda e, w=campo, sf=scroll_frame: _scroll_ao_focar(w, sf))



# ── Banco de dados ─────────────────────────────────────────────────────────────

def inicializar_recebimento():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recebimentos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor   TEXT NOT NULL,
            numero_nota  TEXT DEFAULT '',
            chave_nfe    TEXT DEFAULT '',
            data_entrada TEXT DEFAULT (date('now','localtime')),
            valor_total  REAL DEFAULT 0,
            status       TEXT DEFAULT 'PENDENTE',
            observacao   TEXT DEFAULT '',
            criado_em    TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS itens_recebimento (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            recebimento_id   INTEGER REFERENCES recebimentos(id),
            produto_id       INTEGER REFERENCES produtos(id),
            nome_produto     TEXT,
            codigo_barras    TEXT,
            quantidade       REAL DEFAULT 1,
            custo_unitario   REAL DEFAULT 0,
            preco_venda_ant  REAL DEFAULT 0,
            preco_venda_novo REAL DEFAULT 0,
            atualizou_preco  INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS boletos_recebimento (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            recebimento_id  INTEGER REFERENCES recebimentos(id),
            descricao       TEXT DEFAULT '',
            banco           TEXT DEFAULT '',
            valor           REAL DEFAULT 0,
            vencimento      TEXT NOT NULL,
            status          TEXT DEFAULT 'PENDENTE',
            data_pagamento  TEXT DEFAULT '',
            observacao      TEXT DEFAULT '',
            criado_em       TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()


def listar_recebimentos(busca=''):
    conn = get_conn()
    q = """SELECT r.*,
               COUNT(DISTINCT b.id) as qtde_boletos,
               SUM(CASE WHEN b.status='PENDENTE' THEN b.valor ELSE 0 END) as total_pendente,
               SUM(CASE WHEN b.status='PAGO'     THEN b.valor ELSE 0 END) as total_pago
           FROM recebimentos r
           LEFT JOIN boletos_recebimento b ON b.recebimento_id=r.id
           WHERE 1=1"""
    p = []
    if busca:
        q += " AND (r.fornecedor LIKE ? OR r.numero_nota LIKE ? OR r.chave_nfe LIKE ?)"
        p += [f'%{busca}%', f'%{busca}%', f'%{busca}%']
    q += " GROUP BY r.id ORDER BY r.data_entrada DESC, r.id DESC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_boletos(recebimento_id=None, apenas_pendentes=False):
    conn = get_conn()
    q = """SELECT b.*, r.fornecedor, r.numero_nota
           FROM boletos_recebimento b
           JOIN recebimentos r ON r.id=b.recebimento_id
           WHERE 1=1"""
    p = []
    if recebimento_id:
        q += " AND b.recebimento_id=?"; p.append(recebimento_id)
    if apenas_pendentes:
        q += " AND b.status='PENDENTE'"
    q += " ORDER BY b.vencimento ASC"
    rows = conn.execute(q, p).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def boletos_vencendo(dias=7):
    conn = get_conn()
    limit = (date.today() + timedelta(days=dias)).strftime('%Y-%m-%d')
    rows = conn.execute("""
        SELECT b.*, r.fornecedor, r.numero_nota
        FROM boletos_recebimento b
        JOIN recebimentos r ON r.id=b.recebimento_id
        WHERE b.status='PENDENTE' AND b.vencimento <= ?
        ORDER BY b.vencimento ASC
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def dar_baixa_boleto(boleto_id):
    conn = get_conn()
    conn.execute("""UPDATE boletos_recebimento
                    SET status='PAGO', data_pagamento=date('now','localtime')
                    WHERE id=?""", (boleto_id,))
    conn.commit(); conn.close()


def salvar_recebimento(fornecedor, numero_nota, chave_nfe,
                       data_entrada, valor_total, observacao):
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO recebimentos
            (fornecedor, numero_nota, chave_nfe, data_entrada, valor_total, observacao)
        VALUES (?,?,?,?,?,?)
    """, (fornecedor, numero_nota, chave_nfe, data_entrada, valor_total, observacao))
    rid = cur.lastrowid
    conn.commit(); conn.close()
    return rid


def salvar_boleto(recebimento_id, descricao, banco, valor, vencimento, observacao):
    conn = get_conn()
    conn.execute("""
        INSERT INTO boletos_recebimento
            (recebimento_id, descricao, banco, valor, vencimento, observacao)
        VALUES (?,?,?,?,?,?)
    """, (recebimento_id, descricao, banco, valor, vencimento, observacao))
    conn.commit(); conn.close()


def atualizar_preco_produto(produto_id, novo_preco, novo_custo):
    conn = get_conn()
    conn.execute("""UPDATE produtos SET preco_venda=?, preco_custo=? WHERE id=?""",
                 (novo_preco, novo_custo, produto_id))
    conn.commit(); conn.close()


# ── Tela Principal ─────────────────────────────────────────────────────────────

class TelaRecebimento(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        inicializar_recebimento()
        self.rec_selecionado = None
        self._build_header()
        self._build_corpo()
        self._carregar()
        self.after(500, self._verificar_avisos)

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="📦  Recebimento de Mercadorias",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")

        self.ent_busca = ctk.CTkEntry(bf, width=220, font=FONTE_LABEL,
                                      placeholder_text="Buscar fornecedor...",
                                      fg_color=COR_CARD2, border_color=COR_BORDA2,
                                      text_color=COR_TEXTO)
        self.ent_busca.pack(side="left", padx=(0, 8))
        self.ent_busca.bind("<KeyRelease>", lambda e: self._carregar())

        for txt, cor, hover, cmd in [
            ("➕ Nova Nota",    COR_SUCESSO, COR_SUCESSO2, self._nova_nota),
            ("🔔 Vencimentos",  COR_AVISO,   "#D97706",    self._ver_vencimentos),
            ("🔄 Atualizar",    "#6B7280",   "#4B5563",    self._carregar),
        ]:
            ctk.CTkButton(bf, text=txt, font=FONTE_BTN, width=130,
                          fg_color=cor, hover_color=hover,
                          text_color="white", command=cmd).pack(side="left", padx=3)

    # ── Corpo ─────────────────────────────────────────────────────────────────
    def _build_corpo(self):
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        corpo.grid_columnconfigure(0, weight=2)
        corpo.grid_columnconfigure(1, weight=3)
        corpo.grid_rowconfigure(0, weight=1)

        # Painel esquerdo — lista de notas
        frame_notas = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                                   border_width=1, border_color=COR_BORDA)
        frame_notas.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        frame_notas.grid_rowconfigure(2, weight=1)
        frame_notas.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_notas, text="📋  Notas de Entrada",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        ctk.CTkFrame(frame_notas, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=16)
        self.scroll_notas = ctk.CTkScrollableFrame(frame_notas, fg_color="transparent")
        self.scroll_notas.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll_notas.grid_columnconfigure(0, weight=1)

        # Painel direito — boletos
        self.frame_dir = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                                      border_width=1, border_color=COR_BORDA)
        self.frame_dir.grid(row=0, column=1, sticky="nsew")
        self.frame_dir.grid_rowconfigure(2, weight=1)
        self.frame_dir.grid_columnconfigure(0, weight=1)

        self.lbl_titulo_dir = ctk.CTkLabel(
            self.frame_dir, text="💳  Boletos",
            font=FONTE_SUBTITULO, text_color=COR_ACENTO)
        self.lbl_titulo_dir.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        ctk.CTkFrame(self.frame_dir, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=16)

        self.scroll_boletos = ctk.CTkScrollableFrame(self.frame_dir, fg_color="transparent")
        self.scroll_boletos.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll_boletos.grid_columnconfigure(0, weight=1)

        self.btn_add_boleto = ctk.CTkButton(
            self.frame_dir, text="➕  Adicionar Boleto",
            font=FONTE_BTN, height=40,
            fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
            text_color="white", command=self._novo_boleto)
        self.btn_add_boleto.grid(row=3, column=0, padx=16, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(self.scroll_boletos,
                     text="← Selecione uma nota para ver os boletos",
                     font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=40)

    # ── Carregar notas ────────────────────────────────────────────────────────
    def _carregar(self):
        for w in self.scroll_notas.winfo_children():
            w.destroy()

        busca = self.ent_busca.get().strip() if hasattr(self, 'ent_busca') else ''
        notas = listar_recebimentos(busca)

        if not notas:
            ctk.CTkLabel(self.scroll_notas,
                         text="Nenhuma nota cadastrada.\nClique em '➕ Nova Nota'",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB,
                         justify="center").pack(pady=40)
            return

        for idx, n in enumerate(notas):
            pendente = n.get('total_pendente') or 0
            cor_bg   = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            venc_cor = COR_PERIGO if pendente > 0 else COR_SUCESSO

            card = ctk.CTkFrame(self.scroll_notas, fg_color=cor_bg,
                                corner_radius=8, border_width=1,
                                border_color=COR_BORDA)
            card.pack(fill="x", pady=3)

            f1 = ctk.CTkFrame(card, fg_color="transparent")
            f1.pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(f1, text=n['fornecedor'][:28],
                         font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                         text_color=COR_TEXTO).pack(side="left")
            ctk.CTkLabel(f1, text=n['data_entrada'],
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="right")

            f2 = ctk.CTkFrame(card, fg_color="transparent")
            f2.pack(fill="x", padx=12, pady=(0, 8))
            nota_txt = f"NF: {n['numero_nota']}" if n['numero_nota'] else "Sem NF"
            ctk.CTkLabel(f2, text=nota_txt,
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="left")
            ctk.CTkLabel(f2, text=f"R$ {n['valor_total']:.2f}",
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=COR_ACENTO).pack(side="left", padx=8)
            status_txt = f"⚠️ R$ {pendente:.2f} pendente" if pendente > 0 else "✅ Quitado"
            ctk.CTkLabel(f2, text=status_txt,
                         font=FONTE_SMALL, text_color=venc_cor).pack(side="right")

            for w in [card, f1, f2]:
                w.bind("<Button-1>", lambda e, r=n: self._selecionar_nota(r))
            card.bind("<Enter>", lambda e, c=card: c.configure(fg_color=COR_ACENTO_LIGHT))
            card.bind("<Leave>", lambda e, c=card, bg=cor_bg: c.configure(fg_color=bg))

    # ── Selecionar nota ───────────────────────────────────────────────────────
    def _selecionar_nota(self, nota):
        self.rec_selecionado = nota
        self.lbl_titulo_dir.configure(
            text=f"💳  Boletos — {nota['fornecedor'][:20]}")
        self._carregar_boletos()

    def _carregar_boletos(self):
        for w in self.scroll_boletos.winfo_children():
            w.destroy()
        if not self.rec_selecionado:
            return

        boletos = listar_boletos(self.rec_selecionado['id'])
        hoje    = date.today().strftime('%Y-%m-%d')

        if not boletos:
            ctk.CTkLabel(self.scroll_boletos,
                         text="Nenhum boleto.\nClique em '➕ Adicionar Boleto'",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB,
                         justify="center").pack(pady=40)
            return

        for idx, b in enumerate(boletos):
            pago     = b['status'] == 'PAGO'
            vencido  = b['vencimento'] < hoje and not pago
            vence_hj = b['vencimento'] == hoje and not pago

            if pago:
                cor_s = COR_SUCESSO; s_txt = "✅ PAGO";       cor_bg = "#F0FDF4"
            elif vencido:
                cor_s = COR_PERIGO;  s_txt = "⚠️ VENCIDO";    cor_bg = "#FEF2F2"
            elif vence_hj:
                cor_s = COR_AVISO;   s_txt = "🔔 VENCE HOJE"; cor_bg = "#FFFBEB"
            else:
                dias  = (date.fromisoformat(b['vencimento']) - date.today()).days
                cor_s = COR_INFO;    s_txt = f"📅 {dias}d"
                cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD

            card = ctk.CTkFrame(self.scroll_boletos, fg_color=cor_bg,
                                corner_radius=8, border_width=1, border_color=COR_BORDA)
            card.pack(fill="x", pady=3)

            f1 = ctk.CTkFrame(card, fg_color="transparent")
            f1.pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(f1, text=b['descricao'] or b['banco'] or "Boleto",
                         font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                         text_color=COR_TEXTO).pack(side="left")
            ctk.CTkLabel(f1, text=s_txt,
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=cor_s).pack(side="right")

            f2 = ctk.CTkFrame(card, fg_color="transparent")
            f2.pack(fill="x", padx=12, pady=(0, 8))
            if b['banco']:
                ctk.CTkLabel(f2, text=b['banco'],
                             font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="left")
            ctk.CTkLabel(f2, text=f"Venc: {b['vencimento']}",
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="left", padx=8)
            ctk.CTkLabel(f2, text=f"R$ {b['valor']:.2f}",
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=cor_s).pack(side="left")

            if not pago:
                ctk.CTkButton(f2, text="✅ Dar Baixa",
                              font=FONTE_BTN_SM, width=100, height=28,
                              fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                              text_color="white",
                              command=lambda bid=b['id']: self._confirmar_baixa(bid)
                              ).pack(side="right")
            else:
                pg = b.get('data_pagamento', '')
                if pg:
                    ctk.CTkLabel(f2, text=f"Pago em {pg}",
                                 font=FONTE_SMALL, text_color=COR_SUCESSO).pack(side="right")

    def _confirmar_baixa(self, boleto_id):
        if messagebox.askyesno("Dar Baixa",
                               "Confirma o pagamento deste boleto?", parent=self):
            dar_baixa_boleto(boleto_id)
            self._carregar_boletos()
            self._carregar()
            messagebox.showinfo("✅ Pago", "Boleto marcado como pago!", parent=self)

    def _nova_nota(self):
        FormularioNota(self, callback=self._carregar)

    def _novo_boleto(self):
        if not self.rec_selecionado:
            messagebox.showwarning("Aviso", "Selecione uma nota primeiro.", parent=self)
            return
        FormularioBoleto(self, self.rec_selecionado['id'], callback=self._carregar_boletos)

    def _verificar_avisos(self):
        boletos = boletos_vencendo(dias=3)
        if not boletos:
            return
        hoje     = date.today().strftime('%Y-%m-%d')
        vencidos = [b for b in boletos if b['vencimento'] < hoje]
        vencendo = [b for b in boletos if b['vencimento'] >= hoje]
        msg = ""
        if vencidos:
            msg += f"⚠️ {len(vencidos)} boleto(s) VENCIDO(S):\n"
            for b in vencidos:
                msg += f"  • {b['fornecedor']} — R$ {b['valor']:.2f} — venceu {b['vencimento']}\n"
        if vencendo:
            msg += f"\n🔔 {len(vencendo)} boleto(s) vencendo em breve:\n"
            for b in vencendo:
                msg += f"  • {b['fornecedor']} — R$ {b['valor']:.2f} — vence {b['vencimento']}\n"
        if msg:
            messagebox.showwarning("⚠️ Atenção — Boletos", msg.strip(), parent=self)

    def _ver_vencimentos(self):
        JanelaBoletosPendentes(self)


# ── Formulário Nova Nota com leitor de código de barras/QR ────────────────────

class FormularioNota(ctk.CTkToplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback  = callback
        self.itens     = []          # lista de produtos escaneados
        self.title("Nova Nota de Entrada")
        _geometry_responsiva(self, 0.66, 0.89, 800, 600)
        self.configure(fg_color=COR_FUNDO)
        self.grab_set()
        self._build()
        # Foca no campo de QR ao abrir
        self.after(200, lambda: self.ent_qr.focus_set())

    def _build(self):
        # ── Título ────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="📦  Nova Nota de Entrada",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(16, 4))
        ctk.CTkFrame(self, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24)

        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=24, pady=12)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_columnconfigure(1, weight=1)
        corpo.grid_rowconfigure(1, weight=1)

        # ── Coluna esquerda: dados da nota ────────────────────────────────────
        frame_dados = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                                   border_width=1, border_color=COR_BORDA)
        frame_dados.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        ctk.CTkLabel(frame_dados, text="📄  Dados da Nota",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
            anchor="w", padx=16, pady=(12, 4))
        ctk.CTkFrame(frame_dados, height=1, fg_color=COR_BORDA).pack(fill="x", padx=16)

        form = ctk.CTkFrame(frame_dados, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=12)
        form.grid_columnconfigure(1, weight=1)

        # QR Code / Chave NF-e — leitor de pistola
        ctk.CTkLabel(form, text="🔍 QR/Chave NF-e:",
                     font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                     text_color=COR_ACENTO).grid(
            row=0, column=0, pady=6, sticky="w", padx=(0, 8))
        self.ent_qr = ctk.CTkEntry(
            form, font=FONTE_LABEL, height=40,
            placeholder_text="Aponte a pistola para o QR code da nota...",
            fg_color=COR_ACENTO_LIGHT, border_color=COR_ACENTO,
            border_width=2, text_color=COR_TEXTO)
        self.ent_qr.grid(row=0, column=1, sticky="ew", pady=6)
        self.ent_qr.bind("<Return>", self._processar_qr)

        # Campos manuais
        campos = [
            ("Fornecedor *",      "fornecedor"),
            ("Nº da Nota",        "numero_nota"),
            ("Data (AAAA-MM-DD)", "data_entrada"),
            ("Valor Total R$",    "valor_total"),
            ("Observação",        "observacao"),
        ]
        self.campos = {}
        for i, (label, key) in enumerate(campos, start=1):
            ctk.CTkLabel(form, text=label, font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).grid(
                row=i, column=0, pady=5, sticky="w", padx=(0, 8))
            ent = ctk.CTkEntry(form, font=FONTE_LABEL, height=36,
                               fg_color=COR_CARD2, border_color=COR_BORDA2,
                               text_color=COR_TEXTO)
            ent.grid(row=i, column=1, sticky="ew", pady=5)
            self.campos[key] = ent

        self.campos["data_entrada"].insert(0, date.today().strftime('%Y-%m-%d'))

        # ── Coluna direita: scanner de produtos ───────────────────────────────
        frame_prod = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                                  border_width=1, border_color=COR_BORDA)
        frame_prod.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8),
                        rowspan=2)
        frame_prod.grid_rowconfigure(3, weight=1)
        frame_prod.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_prod, text="📷  Escanear Produtos",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=16, pady=(12, 4), sticky="w")
        ctk.CTkFrame(frame_prod, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=16)

        # Campo de scan do produto
        scan_f = ctk.CTkFrame(frame_prod, fg_color="transparent")
        scan_f.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        scan_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scan_f, text="Código de barras / nome:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        self.ent_scan = ctk.CTkEntry(
            scan_f, font=FONTE_LABEL, height=42,
            placeholder_text="Escaneie ou digite o código...",
            fg_color=COR_ACENTO_LIGHT, border_color=COR_ACENTO,
            border_width=2, text_color=COR_TEXTO)
        self.ent_scan.grid(row=1, column=0, sticky="ew", pady=4)
        self.ent_scan.bind("<Return>", self._escanear_produto)

        # Qtde e custo
        sub_f = ctk.CTkFrame(scan_f, fg_color="transparent")
        sub_f.grid(row=2, column=0, sticky="ew", pady=4)

        ctk.CTkLabel(sub_f, text="Qtde:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left")
        self.ent_qtde = ctk.CTkEntry(sub_f, font=FONTE_LABEL, width=70,
                                      height=34, justify="center",
                                      fg_color=COR_CARD2, border_color=COR_BORDA2,
                                      text_color=COR_TEXTO)
        self.ent_qtde.insert(0, "1")
        self.ent_qtde.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(sub_f, text="Custo Unit R$:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left")
        self.ent_custo = ctk.CTkEntry(sub_f, font=FONTE_LABEL, width=90,
                                       height=34, justify="center",
                                       fg_color=COR_CARD2, border_color=COR_BORDA2,
                                       text_color=COR_TEXTO)
        self.ent_custo.insert(0, "0,00")
        self.ent_custo.pack(side="left", padx=4)

        ctk.CTkButton(sub_f, text="➕ Add",
                      font=FONTE_BTN, width=80, height=34,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white",
                      command=self._escanear_produto).pack(side="left", padx=8)

        # Lista de itens escaneados
        self.scroll_itens = ctk.CTkScrollableFrame(frame_prod, fg_color="transparent")
        self.scroll_itens.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.scroll_itens.grid_columnconfigure(0, weight=1)

        self.lbl_total_itens = ctk.CTkLabel(frame_prod, text="0 itens  —  R$ 0,00",
                                             font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                                             text_color=COR_ACENTO)
        self.lbl_total_itens.grid(row=4, column=0, pady=(0, 8))

        # ── Botões finais ─────────────────────────────────────────────────────
        btn_f = ctk.CTkFrame(corpo, fg_color="transparent")
        btn_f.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))
        btn_f.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_f, text="❌  Cancelar",
                      font=FONTE_BTN, height=46,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white", command=self.destroy
                      ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkButton(btn_f, text="✅  Confirmar Recebimento",
                      font=FONTE_BTN, height=46,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white", command=self._confirmar
                      ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    # ── Processar QR code da NF-e ─────────────────────────────────────────────
    def _processar_qr(self, event=None):
        """Lê o QR code escaneado pela pistola e extrai dados da nota"""
        texto = self.ent_qr.get().strip()
        if not texto:
            return

        # Tenta extrair chave de 44 dígitos (padrão NF-e/NFC-e)
        import re
        chave = re.findall(r'\d{44}', texto)
        numero = ""
        if chave:
            chave_str = chave[0]
            # Número da nota fica nas posições 25-34 da chave NF-e
            numero = str(int(chave_str[25:34]))
            self.campos["numero_nota"].delete(0, "end")
            self.campos["numero_nota"].insert(0, numero)
            # Emite bip visual
            self.ent_qr.configure(border_color=COR_SUCESSO)
            self.after(800, lambda: self.ent_qr.configure(border_color=COR_ACENTO))
        else:
            # QR simples — usa texto como referência
            self.campos["numero_nota"].delete(0, "end")
            self.campos["numero_nota"].insert(0, texto[:30])

        # Foca no campo de scan de produtos
        self.after(100, lambda: self.ent_scan.focus_set())

    # ── Escanear produto ──────────────────────────────────────────────────────
    def _escanear_produto(self, event=None):
        codigo = self.ent_scan.get().strip()
        if not codigo:
            return

        # Busca produto no banco
        conn = get_conn()
        prod = conn.execute("""
            SELECT * FROM produtos
            WHERE codigo_barras=? OR nome LIKE ?
            LIMIT 1
        """, (codigo, f'%{codigo}%')).fetchone()
        conn.close()

        if not prod:
            messagebox.showwarning("Produto não encontrado",
                                   f"Código '{codigo}' não cadastrado.\n"
                                   f"Cadastre o produto no Estoque primeiro.",
                                   parent=self)
            self.ent_scan.delete(0, "end")
            self.ent_scan.focus_set()
            return

        prod = dict(prod)
        try:
            qtde  = float(self.ent_qtde.get().replace(",", "."))
            custo = float(self.ent_custo.get().replace(",", ".") or "0")
        except ValueError:
            qtde = 1; custo = 0

        # Adiciona na lista de itens
        self.itens.append({
            "produto_id":    prod["id"],
            "nome":          prod["nome"],
            "codigo_barras": prod.get("codigo_barras", ""),
            "quantidade":    qtde,
            "custo":         custo,
            "preco_venda":   prod.get("preco_venda", 0),
            "preco_custo":   prod.get("preco_custo", 0),
        })

        self._atualizar_lista_itens()

        # Limpa campos e volta foco ao scan
        self.ent_scan.delete(0, "end")
        self.ent_qtde.delete(0, "end"); self.ent_qtde.insert(0, "1")
        self.ent_custo.delete(0, "end"); self.ent_custo.insert(0, "0,00")
        self.ent_scan.focus_set()

        # Flash verde no campo de scan
        self.ent_scan.configure(border_color=COR_SUCESSO)
        self.after(600, lambda: self.ent_scan.configure(border_color=COR_ACENTO))

    def _atualizar_lista_itens(self):
        for w in self.scroll_itens.winfo_children():
            w.destroy()

        total = 0
        for idx, item in enumerate(self.itens):
            subtotal = item["quantidade"] * item["custo"]
            total   += subtotal
            cor_bg   = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD

            row = ctk.CTkFrame(self.scroll_itens, fg_color=cor_bg,
                               corner_radius=6, height=36)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            f = ctk.CTkFrame(row, fg_color="transparent")
            f.pack(fill="x", padx=8, pady=6)

            ctk.CTkLabel(f, text=item["nome"][:22],
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=COR_TEXTO).pack(side="left")
            ctk.CTkLabel(f, text=f"{item['quantidade']:.1f}x",
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="left", padx=6)
            ctk.CTkLabel(f, text=f"R$ {subtotal:.2f}",
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=COR_SUCESSO).pack(side="left")

            # Botão remover
            i_cap = idx
            ctk.CTkButton(f, text="✕", width=24, height=24,
                          font=(FONTE_SMALL[0], FONTE_SMALL[1]),
                          fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                          text_color="white", corner_radius=4,
                          command=lambda i=i_cap: self._remover_item(i)
                          ).pack(side="right")

        self.lbl_total_itens.configure(
            text=f"{len(self.itens)} item(ns)  —  R$ {total:.2f}")

        # Atualiza valor total da nota automaticamente
        self.campos["valor_total"].delete(0, "end")
        self.campos["valor_total"].insert(0, f"{total:.2f}")

    def _remover_item(self, idx):
        if 0 <= idx < len(self.itens):
            self.itens.pop(idx)
            self._atualizar_lista_itens()

    # ── Confirmar recebimento ─────────────────────────────────────────────────
    def _confirmar(self):
        forn = self.campos["fornecedor"].get().strip()
        if not forn:
            messagebox.showerror("Erro", "Fornecedor obrigatório.", parent=self)
            return

        try:
            valor = float(self.campos["valor_total"].get().replace(",", ".") or "0")
        except ValueError:
            valor = 0.0

        chave_nfe = self.ent_qr.get().strip()

        # Salva o recebimento
        rid = salvar_recebimento(
            forn,
            self.campos["numero_nota"].get().strip(),
            chave_nfe,
            self.campos["data_entrada"].get().strip(),
            valor,
            self.campos["observacao"].get().strip()
        )

        # Processa cada item: dá entrada no estoque e verifica preço
        for item in self.itens:
            self._processar_item(item, rid)

        messagebox.showinfo("✅ Recebimento Confirmado",
                            f"Nota registrada!\n"
                            f"{len(self.itens)} produto(s) adicionado(s) ao estoque.",
                            parent=self)
        self.callback()
        self.destroy()

    def _processar_item(self, item, recebimento_id):
        """Dá entrada no estoque e pergunta sobre atualização de preço"""
        # Entrada no estoque
        movimentar_estoque(
            item["produto_id"], "ENTRADA", item["quantidade"],
            f"Recebimento #{recebimento_id} — {item['nome']}"
        )

        # Verifica se o custo mudou
        custo_ant = item.get("preco_custo", 0)
        custo_nov = item.get("custo", 0)

        if custo_nov > 0 and abs(custo_nov - custo_ant) > 0.001:
            # Sugere novo preço de venda proporcional
            margem = 0
            if custo_ant > 0 and item["preco_venda"] > 0:
                margem = (item["preco_venda"] - custo_ant) / custo_ant
            novo_preco_sugerido = custo_nov * (1 + margem) if margem > 0 else item["preco_venda"]

            resp = messagebox.askyesno(
                "💰 Custo Alterado",
                f"Produto: {item['nome']}\n\n"
                f"Custo anterior: R$ {custo_ant:.2f}\n"
                f"Custo novo:     R$ {custo_nov:.2f}\n\n"
                f"Preço de venda atual:    R$ {item['preco_venda']:.2f}\n"
                f"Preço sugerido (mesma margem): R$ {novo_preco_sugerido:.2f}\n\n"
                f"Deseja atualizar o preço de venda?\n"
                f"(O estoque antigo não será alterado)",
                parent=self
            )
            if resp:
                # Abre diálogo para confirmar/ajustar o novo preço
                DialogoAtualizaPreco(self, item, custo_nov, novo_preco_sugerido)
            else:
                # Só atualiza o custo, mantém preço de venda
                atualizar_preco_produto(item["produto_id"], item["preco_venda"], custo_nov)


# ── Diálogo de atualização de preço ───────────────────────────────────────────

class DialogoAtualizaPreco(ctk.CTkToplevel):
    def __init__(self, master, item, novo_custo, preco_sugerido):
        super().__init__(master)
        self.item          = item
        self.novo_custo    = novo_custo
        self.title("Atualizar Preço de Venda")
        _geometry_responsiva(self, 0.31, 0.39, 400, 300)
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self.resizable(True, True)
        self._build(preco_sugerido)

    def _build(self, preco_sugerido):
        ctk.CTkLabel(self, text="💰  Atualizar Preço de Venda",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20, 4))
        ctk.CTkFrame(self, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24)

        ctk.CTkLabel(self, text=self.item["nome"],
                     font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                     text_color=COR_TEXTO).pack(pady=(12, 4))

        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=24, pady=8)
        f.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Novo custo:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).grid(
            row=0, column=0, sticky="w", pady=4)
        ctk.CTkLabel(f, text=f"R$ {self.novo_custo:.2f}",
                     font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                     text_color=COR_PERIGO).grid(row=0, column=1, sticky="w", padx=8)

        ctk.CTkLabel(f, text="Novo preço venda:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).grid(
            row=1, column=0, sticky="w", pady=4)
        self.ent_preco = ctk.CTkEntry(f, font=("Georgia", 20), height=42,
                                       justify="center",
                                       fg_color=COR_CARD2, border_color=COR_ACENTO,
                                       border_width=2, text_color=COR_TEXTO)
        self.ent_preco.insert(0, f"{preco_sugerido:.2f}")
        self.ent_preco.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self.ent_preco.focus_set()
        self.ent_preco.select_range(0, "end")

        ctk.CTkLabel(self,
                     text="⚠️ O estoque antigo não será alterado.\nSó as vendas futuras usarão o novo preço.",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB,
                     justify="center").pack(pady=4)

        ctk.CTkButton(self, text="✅  Confirmar Novo Preço",
                      font=FONTE_BTN, height=44,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white", command=self._salvar
                      ).pack(fill="x", padx=24, pady=12)

    def _salvar(self):
        try:
            novo_preco = float(self.ent_preco.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Preço inválido.", parent=self)
            return
        atualizar_preco_produto(self.item["produto_id"], novo_preco, self.novo_custo)
        self.destroy()


# ── Formulário Boleto ──────────────────────────────────────────────────────────

class FormularioBoleto(ctk.CTkToplevel):
    def __init__(self, master, recebimento_id, callback):
        super().__init__(master)
        self.recebimento_id = recebimento_id
        self.callback       = callback
        self.title("Adicionar Boleto")
        _geometry_responsiva(self, 0.32, 0.49, 400, 300)
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self.resizable(True, True)
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="💳  Novo Boleto",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(24, 4))
        ctk.CTkFrame(self, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=24, pady=12)
        form.grid_columnconfigure(1, weight=1)

        campos = [
            ("Descrição",        "descricao"),
            ("Banco / Emissor",  "banco"),
            ("Valor R$ *",       "valor"),
            ("Vencimento *",     "vencimento"),
            ("Observação",       "observacao"),
        ]
        self.campos = {}
        for i, (label, key) in enumerate(campos):
            ctk.CTkLabel(form, text=label, font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).grid(
                row=i, column=0, pady=6, sticky="w", padx=(0, 12))
            ent = ctk.CTkEntry(form, font=FONTE_LABEL, height=36,
                               fg_color=COR_CARD2, border_color=COR_BORDA2,
                               text_color=COR_TEXTO)
            ent.grid(row=i, column=1, sticky="ew", pady=6)
            self.campos[key] = ent

        venc_pad = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
        self.campos["vencimento"].insert(0, venc_pad)
        self.campos["descricao"].focus_set()
        _configurar_tab_scroll(list(self.campos.values()))

        ctk.CTkButton(self, text="✅  Salvar Boleto",
                      font=FONTE_BTN, height=46,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white", command=self._salvar
                      ).pack(fill="x", padx=24, pady=16)

    def _salvar(self):
        venc = self.campos["vencimento"].get().strip()
        if not venc:
            messagebox.showerror("Erro", "Vencimento obrigatório.", parent=self)
            return
        try:
            valor = float(self.campos["valor"].get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Valor inválido.", parent=self)
            return
        salvar_boleto(self.recebimento_id, self.campos["descricao"].get().strip(),
                      self.campos["banco"].get().strip(), valor, venc,
                      self.campos["observacao"].get().strip())
        messagebox.showinfo("✅ Salvo", "Boleto adicionado!", parent=self)
        self.callback()
        self.destroy()


# ── Janela Boletos Pendentes ───────────────────────────────────────────────────

class JanelaBoletosPendentes(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Boletos Pendentes")
        _geometry_responsiva(self, 0.51, 0.68, 600, 440)
        self.configure(fg_color=COR_FUNDO)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🔔  Boletos Pendentes",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20, 4))
        ctk.CTkLabel(self, text="Ordenados por data de vencimento",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        boletos = listar_boletos(apenas_pendentes=True)
        hoje    = date.today().strftime('%Y-%m-%d')

        if not boletos:
            ctk.CTkLabel(scroll, text="✅ Nenhum boleto pendente!",
                         font=FONTE_TITULO, text_color=COR_SUCESSO).pack(pady=60)
            return

        # Cabeçalho
        cab = ctk.CTkFrame(scroll, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=40)
        cab.pack(fill="x", pady=(0, 4))
        cab.pack_propagate(False)
        h = ctk.CTkFrame(cab, fg_color="transparent")
        h.pack(fill="x", padx=8, pady=6)
        for txt, w in [("Fornecedor",190),("Descrição",140),("Vencimento",110),
                       ("Valor",100),("Status",110)]:
            ctk.CTkLabel(h, text=txt,
                         font=(FONTE_SMALL[0], FONTE_SMALL[1], "bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)

        total_pend = 0
        for idx, b in enumerate(boletos):
            vencido  = b['vencimento'] < hoje
            vence_hj = b['vencimento'] == hoje
            if vencido:
                cor_bg = "#FEF2F2"; cor_s = COR_PERIGO; s_txt = "⚠️ VENCIDO"
            elif vence_hj:
                cor_bg = "#FFFBEB"; cor_s = COR_AVISO;  s_txt = "🔔 HOJE"
            else:
                dias   = (date.fromisoformat(b['vencimento']) - date.today()).days
                cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
                cor_s  = COR_INFO;   s_txt = f"📅 {dias}d"

            row = ctk.CTkFrame(scroll, fg_color=cor_bg, corner_radius=6, height=36)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            r = ctk.CTkFrame(row, fg_color="transparent")
            r.pack(fill="x", padx=8, pady=6)

            for txt, w, cor in [
                (b['fornecedor'][:24], 190, COR_TEXTO),
                (b['descricao'][:18],  140, COR_TEXTO_SUB),
                (b['vencimento'],      110, cor_s),
                (f"R$ {b['valor']:.2f}", 100, COR_ACENTO),
                (s_txt,                110, cor_s),
            ]:
                ctk.CTkLabel(r, text=txt, font=FONTE_SMALL,
                             text_color=cor, width=w, anchor="w").pack(side="left", padx=2)

            total_pend += b['valor']

        # Rodapé
        rod = ctk.CTkFrame(scroll, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=40)
        rod.pack(fill="x", pady=(8, 0))
        rod.pack_propagate(False)
        r = ctk.CTkFrame(rod, fg_color="transparent")
        r.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(r, text="Total Pendente:",
                     font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                     text_color=COR_ACENTO).pack(side="left")
        ctk.CTkLabel(r, text=f"R$ {total_pend:.2f}",
                     font=(FONTE_LABEL[0], FONTE_LABEL[1], "bold"),
                     text_color=COR_PERIGO).pack(side="right")
