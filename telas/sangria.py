"""
telas/sangria.py — Movimentação de Caixa
RETIRADA    = Sangria durante o dia (impacto negativo)
SUPRIMENTO  = Entrada de dinheiro (impacto positivo)
RECOLHIMENTO= Retirada total ao fechar o caixa (impacto negativo)
DESPESA     = Despesa operacional (impacto negativo)
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn, caixa_aberto


def inicializar_sangria():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sangria_suprimento (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id    INTEGER REFERENCES caixa(id),
            tipo        TEXT,
            valor       REAL,
            motivo      TEXT DEFAULT '',
            usuario     TEXT DEFAULT '',
            data_hora   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("UPDATE sangria_suprimento SET tipo='RETIRADA' WHERE tipo='SANGRIA'")
    conn.commit()
    conn.close()


def registrar_movimentacao(caixa_id, tipo, valor, motivo, usuario):
    conn = get_conn()
    conn.execute("""
        INSERT INTO sangria_suprimento
            (caixa_id, tipo, valor, motivo, usuario)
        VALUES (?,?,?,?,?)
    """, (caixa_id, tipo, valor, motivo, usuario))
    conn.commit()
    conn.close()


def listar_movimentacoes_caixa(caixa_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM sangria_suprimento
        WHERE caixa_id=? ORDER BY data_hora ASC
    """, (caixa_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def total_movimentacoes(caixa_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT tipo, COALESCE(SUM(valor),0) as total
        FROM sangria_suprimento
        WHERE caixa_id=?
        GROUP BY tipo
    """, (caixa_id,)).fetchall()
    conn.close()
    return {r["tipo"]: r["total"] for r in rows}


def total_sangria(caixa_id):
    totais   = total_movimentacoes(caixa_id)
    saidas   = (totais.get("RETIRADA",0) + totais.get("RECOLHIMENTO",0) + totais.get("DESPESA",0))
    entradas = totais.get("SUPRIMENTO",0)
    return saidas, entradas


class TelaSangria(ctk.CTkFrame):
    def __init__(self, master, usuario="Sistema"):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        inicializar_sangria()
        cx = caixa_aberto()
        self.caixa_id = cx["id"] if cx else None
        self._build_header()
        self._build_corpo()
        if self.caixa_id:
            self._carregar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="💵  Movimentação de Caixa",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")
        if not self.caixa_id:
            ctk.CTkLabel(hdr, text="⚠️  Nenhum caixa aberto!",
                         font=FONTE_LABEL, text_color=COR_PERIGO).grid(
                row=0, column=1, padx=24, sticky="e")
            return
        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")
        for txt, cor, hover, tipo in [
            ("📤 Retirada",     COR_PERIGO,  COR_PERIGO2,  "RETIRADA"),
            ("📥 Suprimento",   COR_SUCESSO, COR_SUCESSO2, "SUPRIMENTO"),
            ("💰 Recolhimento", "#6B7280",   "#4B5563",    "RECOLHIMENTO"),
            ("🧾 Despesa",      "#B45309",   "#92400E",    "DESPESA"),
        ]:
            ctk.CTkButton(bf, text=txt, font=FONTE_BTN, height=36,
                         fg_color=cor, hover_color=hover, text_color="white",
                         command=lambda t=tipo: self._nova_movimentacao(t)
                         ).pack(side="left", padx=3)

    def _build_corpo(self):
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="nsew")
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_rowconfigure(1, weight=1)
        resumo = ctk.CTkFrame(cards, fg_color="transparent")
        resumo.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        resumo.grid_columnconfigure((0,1,2,3), weight=1)
        self.card_retiradas    = self._card(resumo, 0, "📤 Retiradas",    "R$ 0,00", COR_PERIGO)
        self.card_suprimentos  = self._card(resumo, 1, "📥 Suprimentos",  "R$ 0,00", COR_SUCESSO)
        self.card_recolhimento = self._card(resumo, 2, "💰 Recolhimento", "R$ 0,00", "#6B7280")
        self.card_saldo        = self._card(resumo, 3, "💰 Saldo Líquido","R$ 0,00", COR_ACENTO)
        frame = ctk.CTkFrame(cards, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        COLS = ["Data/Hora","Tipo","Motivo","Usuário","Valor","Saldo"]
        WIDS = [130,120,220,100,100,110]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.pack_propagate(False)
        h = ctk.CTkFrame(cab, fg_color="transparent")
        h.pack(fill="x", padx=8, pady=4)
        for col, w in zip(COLS, WIDS):
            ctk.CTkLabel(h, text=col, font=("Courier New",13,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)
        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        lbl = ctk.CTkLabel(card, text=valor,
                           font=("Georgia",20,"bold"), text_color=cor)
        lbl.pack(pady=(0,14))
        return lbl

    def _carregar(self):
        if not self.caixa_id: return
        movs   = listar_movimentacoes_caixa(self.caixa_id)
        totais = total_movimentacoes(self.caixa_id)
        retiradas    = totais.get("RETIRADA",0) + totais.get("DESPESA",0)
        suprimentos  = totais.get("SUPRIMENTO",0)
        recolhimento = totais.get("RECOLHIMENTO",0)
        conn = get_conn()
        cx = conn.execute("SELECT valor_inicial FROM caixa WHERE id=?", (self.caixa_id,)).fetchone()
        fundo = cx["valor_inicial"] if cx else 0
        vd = conn.execute("""
            SELECT COALESCE(SUM(total),0) FROM vendas
            WHERE caixa_id=? AND status='CONCLUIDA' AND forma_pagamento LIKE '%DINHEIRO%'
        """, (self.caixa_id,)).fetchone()[0]
        conn.close()
        saldo = fundo + vd + suprimentos - retiradas - recolhimento
        self.card_retiradas.configure(text=f"R$ {retiradas:.2f}")
        self.card_suprimentos.configure(text=f"R$ {suprimentos:.2f}")
        self.card_recolhimento.configure(text=f"R$ {recolhimento:.2f}")
        self.card_saldo.configure(text=f"R$ {saldo:.2f}",
                                   text_color=COR_SUCESSO if saldo >= 0 else COR_PERIGO)
        for w in self.scroll.winfo_children(): w.destroy()
        if not movs:
            ctk.CTkLabel(self.scroll, text="Nenhuma movimentação neste caixa.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=40)
            return
        WIDS = [130,120,220,100,100,110]
        TIPOS_COR = {"RETIRADA":COR_PERIGO,"DESPESA":COR_PERIGO,
                     "RECOLHIMENTO":"#6B7280","SUPRIMENTO":COR_SUCESSO}
        saldo_prog = fundo + vd  # começa com fundo + vendas dinheiro já realizadas
        for idx, m in enumerate(movs):
            cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
            cor_t  = TIPOS_COR.get(m["tipo"], COR_TEXTO)
            if m["tipo"] == "SUPRIMENTO":
                sinal = "+"
                saldo_prog += m["valor"]
            else:
                sinal = "-"
                saldo_prog -= m["valor"]
            cor_saldo = COR_SUCESSO if saldo_prog >= 0 else COR_PERIGO
            row_f = ctk.CTkFrame(self.scroll, fg_color=cor_bg, corner_radius=4, height=34)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)
            row_i = ctk.CTkFrame(row_f, fg_color="transparent")
            row_i.pack(fill="x", padx=8, pady=4)
            vals  = [m["data_hora"][:16], m["tipo"], m["motivo"] or "—",
                     m["usuario"] or "—", f"{sinal}R$ {m['valor']:.2f}",
                     f"R$ {saldo_prog:.2f}"]
            cores = [COR_TEXTO_SUB, cor_t, COR_TEXTO, COR_TEXTO_SUB, cor_t, cor_saldo]
            for v, c, w in zip(vals, cores, WIDS):
                ctk.CTkLabel(row_i, text=v, font=FONTE_SMALL,
                             text_color=c, width=w, anchor="w").pack(side="left", padx=2)

    def _nova_movimentacao(self, tipo):
        DialogoMovimentacao(self, tipo, self.caixa_id, self.usuario, self._carregar)


class DialogoMovimentacao(ctk.CTkToplevel):
    def __init__(self, master, tipo, caixa_id, usuario, callback):
        super().__init__(master)
        self.tipo=tipo; self.caixa_id=caixa_id; self.usuario=usuario; self.callback=callback
        CONFIGS = {
            "RETIRADA":     ("📤  Retirada de Caixa",    COR_PERIGO,  COR_PERIGO2),
            "SUPRIMENTO":   ("📥  Suprimento de Caixa",  COR_SUCESSO, COR_SUCESSO2),
            "RECOLHIMENTO": ("💰  Recolhimento de Caixa","#6B7280",   "#4B5563"),
            "DESPESA":      ("🧾  Despesa Operacional",  "#B45309",   "#92400E"),
        }
        titulo, cor, hover = CONFIGS.get(tipo, (tipo, COR_ACENTO, COR_ACENTO2))
        self.title(titulo); self.geometry("420x380")
        self.configure(fg_color=COR_CARD); self.grab_set(); self.resizable(False,False)
        self._build(titulo, cor, hover)

    def _build(self, titulo, cor, hover):
        ctk.CTkLabel(self, text=titulo, font=FONTE_TITULO, text_color=cor).pack(pady=(24,4))
        desc = {"RETIRADA":"Retirada de dinheiro durante o dia",
                "SUPRIMENTO":"Adição de dinheiro ao caixa",
                "RECOLHIMENTO":"Retirada total para guardar ao fechar",
                "DESPESA":"Pagamento de despesa operacional"}.get(self.tipo,"")
        ctk.CTkLabel(self, text=desc, font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(0,12))
        ctk.CTkFrame(self, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24, pady=(0,12))
        ctk.CTkLabel(self, text="Valor (R$) *", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=28)
        self.ent_valor = ctk.CTkEntry(self, font=("Georgia",24), width=200, justify="center",
                                      fg_color=COR_CARD2, border_color=cor, border_width=2,
                                      text_color=COR_TEXTO)
        self.ent_valor.pack(pady=(4,12)); self.ent_valor.focus_set()
        ctk.CTkLabel(self, text="Motivo", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=28)
        motivos = {"RETIRADA":["Sangria manhã","Sangria tarde","Pagamento fornecedor","Outros"],
                   "SUPRIMENTO":["Fundo de troco","Reposição","Outros"],
                   "RECOLHIMENTO":["Fechamento do caixa","Recolhimento parcial","Outros"],
                   "DESPESA":["Energia","Água","Ingredientes","Manutenção","Outros"]}.get(self.tipo,["Outros"])
        self.cmb_motivo = ctk.CTkComboBox(self, values=motivos, font=FONTE_LABEL, width=340,
                                          fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.cmb_motivo.set(motivos[0]); self.cmb_motivo.pack(pady=(4,16))
        ctk.CTkButton(self, text=f"✅  Confirmar {self.tipo.title()}",
                      font=FONTE_BTN, height=46, corner_radius=10,
                      fg_color=cor, hover_color=hover, text_color="white",
                      command=self._confirmar).pack(fill="x", padx=28, pady=4)
        self.ent_valor.bind("<Return>", lambda e: self._confirmar())

    def _confirmar(self):
        try:
            valor = float(self.ent_valor.get().replace(",","."))
        except ValueError:
            messagebox.showerror("Erro","Valor inválido.",parent=self); return
        if valor <= 0:
            messagebox.showerror("Erro","Valor deve ser maior que zero.",parent=self); return
        registrar_movimentacao(self.caixa_id, self.tipo, valor,
                               self.cmb_motivo.get(), self.usuario)
        messagebox.showinfo("✅ Registrado",
                            f"{self.tipo.title()} de R$ {valor:.2f} registrada!", parent=self)
        self.callback()
        self.destroy()
