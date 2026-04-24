"""
telas/fechamento.py — Fechamento de Caixa completo
Igual ao Eccus: relatório PDF com marca d'água, movimentações, resumo por forma
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import (get_conn, caixa_aberto, fechar_caixa,
                              get_config, registrar_movimentacao_caixa,
                              listar_movimentacoes_caixa)


def get_resumo_caixa(caixa_id):
    conn = get_conn()
    cx = conn.execute("SELECT * FROM caixa WHERE id=?", (caixa_id,)).fetchone()
    vendas = conn.execute("""
        SELECT forma_pagamento, COUNT(*) as qtde,
               SUM(total) as total, SUM(troco) as troco
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
        GROUP BY forma_pagamento ORDER BY total DESC
    """, (caixa_id,)).fetchall()
    total_geral = conn.execute("""
        SELECT COALESCE(SUM(total),0), COUNT(*)
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
    """, (caixa_id,)).fetchone()
    produtos_top = conn.execute("""
        SELECT iv.nome_produto, SUM(iv.quantidade) as qtde,
               SUM(iv.total_item) as total
        FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
        WHERE v.caixa_id=? AND v.status='CONCLUIDA'
        GROUP BY iv.nome_produto ORDER BY total DESC LIMIT 10
    """, (caixa_id,)).fetchall()
    movs = conn.execute("""
        SELECT * FROM movimentacao_caixa WHERE caixa_id=? ORDER BY data_hora
    """, (caixa_id,)).fetchall()
    vendas_detalhe = conn.execute("""
        SELECT id, data_hora, forma_pagamento, total, troco, desconto
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
        ORDER BY data_hora ASC
    """, (caixa_id,)).fetchall()
    conn.close()
    sangria    = sum(m["valor"] for m in movs if m["tipo"] in ("SANGRIA","RETIRADA","RECOLHIMENTO"))
    suprimento = sum(m["valor"] for m in movs if m["tipo"] == "SUPRIMENTO")
    detalhe_por_forma = {}
    for v in vendas_detalhe:
        forma = v["forma_pagamento"]
        if forma not in detalhe_por_forma:
            detalhe_por_forma[forma] = []
        detalhe_por_forma[forma].append(dict(v))
    return {
        "caixa":            dict(cx) if cx else {},
        "vendas":           [dict(v) for v in vendas],
        "total_vendas":     total_geral[0],
        "qtde_vendas":      total_geral[1],
        "sangria":          sangria,
        "suprimento":       suprimento,
        "produtos_top":     [dict(p) for p in produtos_top],
        "movimentacoes":    [dict(m) for m in movs],
        "vendas_detalhe":   [dict(v) for v in vendas_detalhe],
        "detalhe_por_forma":detalhe_por_forma,
    }


class TelaFechamentoCaixa(ctk.CTkFrame):
    def __init__(self, master, usuario="Sistema"):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cx = caixa_aberto()
        self.caixa_id = cx["id"] if cx else None
        self.cx_dados = dict(cx) if cx else {}
        self._build_header()
        if self.caixa_id:
            self._build_corpo()
        else:
            self._build_sem_caixa()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="🔒  Fechamento de Caixa",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")
        if self.caixa_id:
            ab = self.cx_dados.get("data_abertura","")[:16]
            ctk.CTkLabel(hdr, text=f"Caixa #{self.caixa_id} — Aberto em {ab}",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(
                row=0, column=1, padx=24, sticky="e")

    def _build_sem_caixa(self):
        f = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12)
        f.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        ctk.CTkLabel(f, text="⚠️  Nenhum caixa aberto!",
                     font=FONTE_TITULO, text_color=COR_PERIGO).pack(pady=60)

    def _build_corpo(self):
        res = get_resumo_caixa(self.caixa_id)
        val_ini   = self.cx_dados.get("valor_inicial", 0)
        total_v   = res["total_vendas"]
        sangria   = res["sangria"]
        suprim    = res["suprimento"]
        saldo_esp = val_ini + total_v + suprim - sangria
        self.saldo_esperado = saldo_esp
        self.res = res

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # ── KPI Cards ─────────────────────────────────────────────────────
        cards = ctk.CTkFrame(scroll, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(0,12))
        for i in range(4): cards.grid_columnconfigure(i, weight=1)
        self._card(cards, 0, "💰 Fundo Inicial",  f"R$ {val_ini:.2f}", COR_TEXTO)
        self._card(cards, 1, "🛒 Total Vendas",   f"R$ {total_v:.2f}", COR_SUCESSO)
        self._card(cards, 2, "📤 Sangrias/Retir", f"R$ {sangria:.2f}", COR_PERIGO)
        self._card(cards, 3, "💵 Saldo Esperado", f"R$ {saldo_esp:.2f}", COR_ACENTO)

        # ── Movimentação de Caixa ─────────────────────────────────────────
        sec_mov = self._secao(scroll, 1, "💼  Movimentação de Caixa")
        self._build_movimentacao(sec_mov)

        # ── Vendas por forma de pagamento ─────────────────────────────────
        sec1 = self._secao(scroll, 2, "📊  Vendas por Forma de Pagamento")
        self._build_tabela_vendas(sec1, res, total_v)

        # ── Produtos mais vendidos ─────────────────────────────────────────
        sec3 = self._secao(scroll, 3, "🏆  Produtos Mais Vendidos")
        self._build_produtos_top(sec3, res)

        # ── Conferência de caixa ──────────────────────────────────────────
        sec2 = self._secao(scroll, 4, "🔍  Conferência — Valor em Caixa")
        self._build_conferencia(sec2, saldo_esp)

        # ── Botões ────────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=16, sticky="ew")
        btn_frame.grid_columnconfigure((0,1,2,3), weight=1)

        ctk.CTkButton(btn_frame, text="💼  Movimentar Caixa",
                      font=FONTE_BTN, height=48,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white",
                      command=self._abrir_movimentacao
                      ).grid(row=0, column=0, padx=6, sticky="ew")

        ctk.CTkButton(btn_frame, text="📄  Gerar PDF",
                      font=FONTE_BTN, height=48,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white",
                      command=lambda: self._gerar_pdf(res)
                      ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(btn_frame, text="🖨️  Imprimir Relatório",
                      font=FONTE_BTN, height=48,
                      fg_color="#374151", hover_color="#1F2937",
                      text_color="white",
                      command=lambda: self._imprimir_relatorio(res)
                      ).grid(row=0, column=2, padx=6, sticky="ew")

        ctk.CTkButton(btn_frame, text="🔒  FECHAR CAIXA",
                      font=("Georgia",17,"bold"), height=48,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                      text_color="white",
                      command=lambda: self._fechar(res)
                      ).grid(row=0, column=3, padx=6, sticky="ew")

    def _build_movimentacao(self, parent):
        """Lista movimentações + botões de ação rápida"""
        f_btns = ctk.CTkFrame(parent, fg_color="transparent")
        f_btns.pack(fill="x", pady=(0,8))
        tipos = [
            ("💸 Despesa",     "DESPESA",     "#DC2626"),
            ("📤 Retirada",    "RETIRADA",    "#D97706"),
            ("📥 Suprimento",  "SUPRIMENTO",  "#059669"),
            ("🏦 Recolhimento","RECOLHIMENTO","#2563EB"),
        ]
        for label, tipo, cor in tipos:
            ctk.CTkButton(f_btns, text=label, font=FONTE_SMALL,
                          height=32, fg_color=cor, hover_color=cor,
                          text_color="white", corner_radius=8,
                          command=lambda t=tipo: self._registrar_mov(t)
                          ).pack(side="left", padx=4)

        # Lista movimentações
        self.frame_movs = ctk.CTkFrame(parent, fg_color=COR_CARD2, corner_radius=8)
        self.frame_movs.pack(fill="x")
        self._atualizar_lista_movs()

    def _atualizar_lista_movs(self):
        for w in self.frame_movs.winfo_children(): w.destroy()
        movs = listar_movimentacoes_caixa(self.caixa_id)
        if not movs:
            ctk.CTkLabel(self.frame_movs,
                         text="Nenhuma movimentação registrada.",
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB
                         ).pack(pady=8)
            return
        cores_tipo = {
            "DESPESA":      COR_PERIGO,
            "RETIRADA":     "#D97706",
            "SUPRIMENTO":   COR_SUCESSO,
            "RECOLHIMENTO": "#2563EB",
            "SANGRIA":      COR_PERIGO,
        }
        for m in movs:
            f = ctk.CTkFrame(self.frame_movs, fg_color="transparent")
            f.pack(fill="x", padx=8, pady=2)
            cor = cores_tipo.get(m["tipo"], COR_TEXTO)
            ctk.CTkLabel(f, text=m["tipo"], font=FONTE_SMALL,
                         text_color=cor, width=100).pack(side="left")
            ctk.CTkLabel(f, text=m["descricao"][:30],
                         font=FONTE_SMALL, text_color=COR_TEXTO).pack(side="left", padx=8)
            ctk.CTkLabel(f, text=m["data_hora"][11:16],
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(side="left")
            ctk.CTkLabel(f, text=f"R$ {m['valor']:.2f}",
                         font=("Georgia",16,"bold"),
                         text_color=cor).pack(side="right", padx=8)

    def _registrar_mov(self, tipo):
        win = ctk.CTkToplevel(self)
        win.title(f"Registrar {tipo.title()}")
        win.geometry("380x260")
        win.configure(fg_color=COR_CARD)
        win.grab_set()

        ctk.CTkLabel(win, text=f"💼  {tipo.title()}",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20,8))
        ctk.CTkFrame(win, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24)

        ctk.CTkLabel(win, text="Descrição:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=24, pady=(12,2))
        ent_desc = ctk.CTkEntry(win, font=FONTE_LABEL, height=36,
                                placeholder_text="Ex: Compra de ingredientes",
                                fg_color=COR_CARD2, border_color=COR_BORDA2,
                                text_color=COR_TEXTO)
        ent_desc.pack(fill="x", padx=24)

        ctk.CTkLabel(win, text="Valor (R$):", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=24, pady=(8,2))
        ent_val = ctk.CTkEntry(win, font=("Georgia",22), height=40,
                               justify="center",
                               fg_color=COR_CARD2, border_color=COR_ACENTO,
                               border_width=2, text_color=COR_TEXTO)
        ent_val.pack(fill="x", padx=24)
        ent_val.focus_set()

        def confirmar():
            try:
                valor = float(ent_val.get().replace(",","."))
                if valor <= 0: raise ValueError
            except ValueError:
                messagebox.showerror("Erro","Valor inválido.", parent=win); return
            desc = ent_desc.get().strip() or tipo.title()
            registrar_movimentacao_caixa(
                self.caixa_id, tipo, desc, valor, self.usuario)
            win.destroy()
            self._atualizar_lista_movs()
            # Atualiza res e cards
            res = get_resumo_caixa(self.caixa_id)
            self.res = res
            messagebox.showinfo("✅", f"{tipo.title()} registrada: R$ {valor:.2f}", parent=self)

        ctk.CTkButton(win, text="✅  Confirmar",
                      font=FONTE_BTN, height=44,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=confirmar).pack(fill="x", padx=24, pady=16)
        ent_val.bind("<Return>", lambda e: confirmar())

    def _abrir_movimentacao(self):
        """Abre janela de seleção de tipo de movimentação"""
        win = ctk.CTkToplevel(self)
        win.title("Movimentação de Caixa")
        win.geometry("360x320")
        win.configure(fg_color=COR_CARD)
        win.grab_set()

        ctk.CTkLabel(win, text="💼  Movimentação de Caixa",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20,8))
        ctk.CTkLabel(win, text="Selecione o tipo de operação:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(0,16))

        ops = [
            ("💸  Despesa",      "DESPESA",      "#DC2626"),
            ("📤  Retirada",     "RETIRADA",     "#D97706"),
            ("📥  Suprimento",   "SUPRIMENTO",   "#059669"),
            ("🏦  Recolhimento", "RECOLHIMENTO", "#2563EB"),
        ]
        for label, tipo, cor in ops:
            ctk.CTkButton(win, text=label, font=FONTE_BTN,
                          height=44, fg_color=cor, hover_color=cor,
                          text_color="white", corner_radius=8,
                          command=lambda t=tipo, w=win: [w.destroy(), self._registrar_mov(t)]
                          ).pack(fill="x", padx=24, pady=4)

    def _build_tabela_vendas(self, parent, res, total_v):
        COLS = ["Forma de Pagamento", "Qtde", "Total", "Troco"]
        WIDS = [280, 60, 120, 100]

        # Cabeçalho
        cab = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.pack(fill="x", pady=(0,2))
        cab.pack_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=4)
        for c, w in zip(COLS, WIDS):
            ctk.CTkLabel(hdr, text=c, font=("Courier New",14,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)

        if res["vendas"]:
            for idx, v in enumerate(res["vendas"]):
                cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
                row_f = ctk.CTkFrame(parent, fg_color=cor_bg, corner_radius=6, height=34)
                row_f.pack(fill="x", pady=1)
                row_f.pack_propagate(False)
                row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
                row_inner.pack(fill="x", padx=8, pady=4)
                vals  = [v["forma_pagamento"], str(v["qtde"]),
                         f'R$ {v["total"]:.2f}', f'R$ {v["troco"]:.2f}']
                cores = [COR_TEXTO, COR_TEXTO_SUB, COR_SUCESSO, COR_TEXTO_SUB]
                for val, cor, w in zip(vals, cores, WIDS):
                    ctk.CTkLabel(row_inner, text=val, font=FONTE_SMALL,
                                 text_color=cor, width=w, anchor="w").pack(side="left", padx=2)
        else:
            ctk.CTkLabel(parent, text="Nenhuma venda neste caixa.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=20)

        # Total
        tot_f = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=6, height=36)
        tot_f.pack(fill="x", pady=(4,0))
        tot_f.pack_propagate(False)
        f_tot = ctk.CTkFrame(tot_f, fg_color="transparent")
        f_tot.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(f_tot, text="TOTAL GERAL",
                     font=("Courier New",15,"bold"),
                     text_color=COR_ACENTO).pack(side="left")
        ctk.CTkLabel(f_tot,
                     text=f"{res['qtde_vendas']} vendas  —  R$ {total_v:.2f}",
                     font=("Courier New",15,"bold"),
                     text_color=COR_ACENTO).pack(side="right")

    def _build_produtos_top(self, parent, res):
        COLS = ["Produto", "Qtde", "Total"]
        WIDS = [300, 80, 120]

        cab = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.pack(fill="x", pady=(0,2))
        cab.pack_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=4)
        for c, w in zip(COLS, WIDS):
            ctk.CTkLabel(hdr, text=c, font=("Courier New",14,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)

        if res["produtos_top"]:
            for idx, p in enumerate(res["produtos_top"]):
                cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
                row_f = ctk.CTkFrame(parent, fg_color=cor_bg, corner_radius=6, height=32)
                row_f.pack(fill="x", pady=1)
                row_f.pack_propagate(False)
                row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
                row_inner.pack(fill="x", padx=8, pady=4)
                vals = [p["nome_produto"][:35],
                        f'{p["qtde"]:.1f}'.rstrip("0").rstrip("."),
                        f'R$ {p["total"]:.2f}']
                cores = [COR_TEXTO, COR_TEXTO_SUB, COR_SUCESSO]
                for val, cor, w in zip(vals, cores, WIDS):
                    ctk.CTkLabel(row_inner, text=val, font=FONTE_SMALL,
                                 text_color=cor, width=w, anchor="w").pack(side="left", padx=2)
        else:
            ctk.CTkLabel(parent, text="Nenhum item vendido.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=12)

    def _build_conferencia(self, parent, saldo_esp):
        parent.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(parent, text="Valor contado (R$):",
                     font=FONTE_LABEL, text_color=COR_TEXTO_SUB
                     ).grid(row=0, column=0, pady=8, sticky="w")
        self.ent_valor_final = ctk.CTkEntry(
            parent, font=("Georgia",22), width=200, justify="center",
            fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.ent_valor_final.insert(0, f"{saldo_esp:.2f}")
        self.ent_valor_final.grid(row=0, column=1, pady=8, padx=(12,0), sticky="w")
        self.ent_valor_final.bind("<KeyRelease>", self._calcular_diferenca)

        ctk.CTkLabel(parent, text="Diferença:",
                     font=FONTE_LABEL, text_color=COR_TEXTO_SUB
                     ).grid(row=1, column=0, pady=4, sticky="w")
        self.lbl_diferenca = ctk.CTkLabel(
            parent, text="R$ 0,00",
            font=("Georgia",17,"bold"), text_color=COR_SUCESSO)
        self.lbl_diferenca.grid(row=1, column=1, pady=4, padx=(12,0), sticky="w")

    def _calcular_diferenca(self, event=None):
        try:
            contado = float(self.ent_valor_final.get().replace(",","."))
            diff    = contado - self.saldo_esperado
            cor     = COR_SUCESSO if abs(diff) < 0.01 else COR_PERIGO
            sinal   = "+" if diff >= 0 else ""
            self.lbl_diferenca.configure(
                text=f"{sinal}R$ {diff:.2f}", text_color=cor)
        except Exception:
            pass

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        ctk.CTkLabel(card, text=valor,
                     font=("Georgia",22,"bold"), text_color=cor).pack(pady=(0,14))

    def _secao(self, parent, row, titulo):
        frame = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=titulo, font=FONTE_SUBTITULO,
                     text_color=COR_ACENTO).grid(row=0,column=0,padx=16,pady=(12,4),sticky="w")
        ctk.CTkFrame(frame, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0,8))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.grid(row=2, column=0, sticky="ew", padx=16, pady=(0,14))
        return inner

    def _fechar(self, res):
        try:
            valor_final = float(self.ent_valor_final.get().replace(",","."))
        except ValueError:
            messagebox.showerror("Erro","Valor inválido."); return

        diff = valor_final - self.saldo_esperado
        sinal = "+" if diff >= 0 else ""
        msg_diff = f"✅ Caixa OK!" if abs(diff) < 0.01 else f"⚠️ Diferença: {sinal}R$ {diff:.2f}"

        if not messagebox.askyesno("Fechar Caixa",
            f"Confirma o fechamento?\n\n"
            f"Total vendas:  R$ {res['total_vendas']:.2f}\n"
            f"Saldo esperado: R$ {self.saldo_esperado:.2f}\n"
            f"Valor contado:  R$ {valor_final:.2f}\n"
            f"{msg_diff}\n\n"
            f"Esta ação não pode ser desfeita!"):
            return

        fechar_caixa(self.caixa_id, valor_final)
        self._gerar_pdf(res, valor_final, fechando=True)
        self._imprimir_relatorio(res, valor_final)
        messagebox.showinfo("✅ Caixa Fechado",
                            "Caixa fechado com sucesso!\nRelatório salvo em cupons\\")
        self.caixa_id = None
        for w in self.winfo_children(): w.destroy()
        self._build_header()
        self._build_sem_caixa()

    def _gerar_pdf(self, res, valor_final=None, fechando=False):
        """Gera PDF profissional estilo Eccus com dados da empresa,
           resumo por forma de pagamento + detalhe de cada venda por forma."""
        try:
            import subprocess
            subprocess.run(["pip", "install", "reportlab", "--quiet",
                           "--break-system-packages"], capture_output=True)
        except Exception:
            pass

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                            Paragraph, Spacer, HRFlowable)
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            import os, sys

            if getattr(sys, "frozen", False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            path  = os.path.join(pasta, f"fechamento_{agora}.pdf")
            logo_path = os.path.join(base, "logo.png")

            empresa = get_config("empresa_nome") or "Padaria Da Laine"
            cnpj    = get_config("empresa_cnpj") or ""
            end_    = get_config("empresa_end")  or ""
            tel     = get_config("empresa_tel")  or ""
            email   = get_config("empresa_email") or ""
            cidade  = get_config("empresa_cidade") or ""

            COR_PRINCIPAL = colors.HexColor("#B45309")
            COR_CINZA     = colors.HexColor("#6B7280")
            COR_VERDE     = colors.HexColor("#059669")
            COR_VERM      = colors.HexColor("#DC2626")
            COR_FUNDO_TAB = colors.HexColor("#FEF3C7")
            COR_LINHA     = colors.HexColor("#F3F4F6")
            COR_AZUL      = colors.HexColor("#1D4ED8")
            COR_LARANJA   = colors.HexColor("#D97706")

            # Cores por forma de pagamento
            CORES_FORMA = {
                "DINHEIRO":  colors.HexColor("#059669"),
                "PIX":       colors.HexColor("#2563EB"),
                "DEBITO":    colors.HexColor("#7C3AED"),
                "CREDITO":   colors.HexColor("#DC2626"),
                "CARTAO":    colors.HexColor("#7C3AED"),
                "FIADO":     colors.HexColor("#D97706"),
            }

            s_titulo = ParagraphStyle("titulo", fontSize=15, fontName="Helvetica-Bold",
                                      textColor=COR_PRINCIPAL, alignment=TA_CENTER, spaceAfter=2)
            s_sub    = ParagraphStyle("sub", fontSize=9, fontName="Helvetica",
                                      textColor=COR_CINZA, alignment=TA_CENTER, spaceAfter=2)
            s_sec    = ParagraphStyle("sec", fontSize=11, fontName="Helvetica-Bold",
                                      textColor=COR_PRINCIPAL, spaceBefore=10, spaceAfter=4)
            s_sec2   = ParagraphStyle("sec2", fontSize=10, fontName="Helvetica-Bold",
                                      textColor=colors.white, spaceBefore=0, spaceAfter=0)
            s_normal = ParagraphStyle("normal", fontSize=9, fontName="Helvetica",
                                      textColor=colors.black)

            # ── Marca d'água + faixas coloridas ─────────────────────────────
            class MarcaDagua:
                def __init__(self, logo_path, empresa_nome):
                    self.logo_path   = logo_path
                    self.empresa_nome = empresa_nome

                def __call__(self, canvas_obj, doc):
                    canvas_obj.saveState()
                    if os.path.exists(self.logo_path):
                        canvas_obj.setFillAlpha(0.05)
                        w = 10*cm; h = 10*cm
                        x = (A4[0] - w) / 2
                        y = (A4[1] - h) / 2
                        canvas_obj.drawImage(self.logo_path, x, y, w, h,
                                             preserveAspectRatio=True, mask="auto")
                    canvas_obj.setFillColor(COR_PRINCIPAL)
                    canvas_obj.setFillAlpha(1)
                    canvas_obj.rect(0, A4[1]-8, A4[0], 8, fill=1, stroke=0)
                    canvas_obj.rect(0, 0, A4[0], 6, fill=1, stroke=0)
                    canvas_obj.setFont("Helvetica", 7)
                    canvas_obj.setFillColor(COR_CINZA)
                    canvas_obj.drawCentredString(A4[0]/2, 12,
                        f"Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} — {self.empresa_nome}")
                    canvas_obj.restoreState()

            doc = SimpleDocTemplate(path, pagesize=A4,
                                    leftMargin=1.8*cm, rightMargin=1.8*cm,
                                    topMargin=2.2*cm, bottomMargin=2*cm)
            story = []

            # ── CABEÇALHO DA EMPRESA ─────────────────────────────────────────
            if os.path.exists(logo_path):
                from reportlab.platypus import Image as RLImage
                logo = RLImage(logo_path, width=2.8*cm, height=2.8*cm)
                story.append(logo)
                story.append(Spacer(1, 0.2*cm))

            story.append(Paragraph(empresa.upper(), s_titulo))

            # Linha de dados da empresa
            dados_emp = []
            if cnpj:    dados_emp.append(f"CNPJ: {cnpj}")
            if tel:     dados_emp.append(f"Tel: {tel}")
            if email:   dados_emp.append(f"Email: {email}")
            if end_:    dados_emp.append(end_)
            if cidade:  dados_emp.append(cidade)
            for d in dados_emp:
                story.append(Paragraph(d, s_sub))

            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=2,
                                    color=COR_PRINCIPAL, spaceAfter=4))
            story.append(Paragraph("RELATÓRIO DE FECHAMENTO DE CAIXA", s_titulo))
            story.append(HRFlowable(width="100%", thickness=1,
                                    color=COR_PRINCIPAL, spaceAfter=6))

            # ── INFO DO CAIXA ────────────────────────────────────────────────
            ab = self.cx_dados.get("data_abertura","")[:16]
            fe = datetime.now().strftime("%d/%m/%Y %H:%M")
            info_data = [
                ["Caixa Nº:", str(self.caixa_id), "Operador:", self.usuario],
                ["Abertura:", ab,                  "Fechamento:", fe],
            ]
            t_info = Table(info_data, colWidths=[2.8*cm,5.5*cm,2.8*cm,5.5*cm])
            t_info.setStyle(TableStyle([
                ("FONTNAME",      (0,0),(-1,-1), "Helvetica"),
                ("FONTSIZE",      (0,0),(-1,-1), 9),
                ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
                ("FONTNAME",      (2,0),(2,-1),  "Helvetica-Bold"),
                ("TEXTCOLOR",     (0,0),(0,-1),  COR_CINZA),
                ("TEXTCOLOR",     (2,0),(2,-1),  COR_CINZA),
                ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, COR_LINHA]),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ]))
            story.append(t_info)
            story.append(Spacer(1, 0.4*cm))

            # ── KPI CARDS ────────────────────────────────────────────────────
            val_ini   = self.cx_dados.get("valor_inicial", 0)
            sangria   = res["sangria"]
            suprim    = res["suprimento"]
            saldo_esp = val_ini + res["total_vendas"] + suprim - sangria
            vf        = valor_final if valor_final is not None else saldo_esp
            diff      = vf - saldo_esp

            kpi_data = [
                ["Fundo Inicial", "Total Vendas", "Sangrias/Retir.", "Saldo Esperado"],
                [f"R$ {val_ini:.2f}", f"R$ {res['total_vendas']:.2f}",
                 f"R$ {sangria:.2f}",  f"R$ {saldo_esp:.2f}"],
            ]
            t_kpi = Table(kpi_data, colWidths=[4.1*cm]*4)
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND",   (0,0),(-1,0),  COR_PRINCIPAL),
                ("TEXTCOLOR",    (0,0),(-1,0),  colors.white),
                ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",     (0,0),(-1,0),  9),
                ("ALIGN",        (0,0),(-1,-1), "CENTER"),
                ("BACKGROUND",   (0,1),(-1,-1), COR_FUNDO_TAB),
                ("FONTNAME",     (0,1),(-1,-1), "Helvetica-Bold"),
                ("FONTSIZE",     (0,1),(-1,-1), 12),
                ("TEXTCOLOR",    (0,1),(-1,-1), COR_PRINCIPAL),
                ("BOX",          (0,0),(-1,-1), 1, COR_PRINCIPAL),
                ("INNERGRID",    (0,0),(-1,-1), 0.5, colors.white),
                ("TOPPADDING",   (0,0),(-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 0.5*cm))

            # ── RESUMO POR FORMA DE PAGAMENTO ────────────────────────────────
            story.append(Paragraph("RESUMO POR FORMA DE PAGAMENTO", s_sec))
            venda_data = [["Forma de Pagamento", "Qtde Vendas", "Total Recebido", "Troco Dado"]]
            for v in res["vendas"]:
                venda_data.append([
                    v["forma_pagamento"],
                    str(v["qtde"]),
                    f'R$ {v["total"]:.2f}',
                    f'R$ {v["troco"]:.2f}'
                ])
            venda_data.append(["TOTAL GERAL", str(res["qtde_vendas"]),
                               f'R$ {res["total_vendas"]:.2f}', ""])

            t_vendas = Table(venda_data, colWidths=[6*cm,3*cm,4.5*cm,3.1*cm])
            t_vendas.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,0),  COR_PRINCIPAL),
                ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
                ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0),(-1,-1), 9),
                ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.white, COR_LINHA]),
                ("BACKGROUND",    (0,-1),(-1,-1), COR_FUNDO_TAB),
                ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
                ("TEXTCOLOR",     (2,1),(2,-1),   COR_VERDE),
                ("BOX",           (0,0),(-1,-1),  1, COR_PRINCIPAL),
                ("INNERGRID",     (0,0),(-1,-1),  0.25, colors.lightgrey),
                ("TOPPADDING",    (0,0),(-1,-1),  6),
                ("BOTTOMPADDING", (0,0),(-1,-1),  6),
                ("LEFTPADDING",   (0,0),(-1,-1),  8),
            ]))
            story.append(t_vendas)
            story.append(Spacer(1, 0.5*cm))

            # ── DETALHE DE VENDAS POR FORMA DE PAGAMENTO ────────────────────
            detalhe = res.get("detalhe_por_forma", {})
            if detalhe:
                story.append(Paragraph("DETALHE DE VENDAS POR FORMA DE PAGAMENTO", s_sec))

                for forma, vendas_f in detalhe.items():
                    total_forma = sum(v["total"] for v in vendas_f)
                    cor_forma   = CORES_FORMA.get(forma.upper().split("+")[0].strip(),
                                                  COR_PRINCIPAL)

                    # Cabeçalho colorido da forma
                    cab_forma = Table(
                        [[Paragraph(f"  {forma}  —  {len(vendas_f)} venda(s)  —  R$ {total_forma:.2f}", s_sec2)]],
                        colWidths=[16.4*cm])
                    cab_forma.setStyle(TableStyle([
                        ("BACKGROUND",   (0,0),(-1,-1), cor_forma),
                        ("TOPPADDING",   (0,0),(-1,-1), 5),
                        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
                        ("LEFTPADDING",  (0,0),(-1,-1), 8),
                    ]))
                    story.append(cab_forma)

                    # Linhas de cada venda
                    det_data = [["#Venda", "Horário", "Total", "Troco", "Desconto"]]
                    for v in vendas_f:
                        hora = v["data_hora"][11:16] if len(v.get("data_hora","")) >= 16 else "--:--"
                        det_data.append([
                            f'#{v["id"]}',
                            hora,
                            f'R$ {v["total"]:.2f}',
                            f'R$ {v["troco"]:.2f}',
                            f'R$ {v.get("desconto",0):.2f}'
                        ])
                    det_data.append(["", "SUBTOTAL",
                                     f"R$ {total_forma:.2f}", "", ""])

                    t_det = Table(det_data, colWidths=[2.5*cm,3*cm,4*cm,4*cm,2.9*cm])
                    t_det.setStyle(TableStyle([
                        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#F3F4F6")),
                        ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                        ("FONTSIZE",      (0,0),(-1,-1), 8),
                        ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.white, COR_LINHA]),
                        ("BACKGROUND",    (0,-1),(-1,-1), COR_FUNDO_TAB),
                        ("FONTNAME",      (0,-1),(-1,-1), "Helvetica-Bold"),
                        ("TEXTCOLOR",     (2,1),(2,-1),   COR_VERDE),
                        ("BOX",           (0,0),(-1,-1),  0.5, colors.lightgrey),
                        ("INNERGRID",     (0,0),(-1,-1),  0.25, colors.HexColor("#E5E7EB")),
                        ("TOPPADDING",    (0,0),(-1,-1),  4),
                        ("BOTTOMPADDING", (0,0),(-1,-1),  4),
                        ("LEFTPADDING",   (0,0),(-1,-1),  6),
                    ]))
                    story.append(t_det)
                    story.append(Spacer(1, 0.3*cm))

                story.append(Spacer(1, 0.2*cm))

            # ── MOVIMENTAÇÕES DE CAIXA ───────────────────────────────────────
            if res["movimentacoes"]:
                story.append(Paragraph("MOVIMENTAÇÕES DE CAIXA", s_sec))
                mov_data = [["Tipo", "Descrição", "Hora", "Valor"]]
                for m in res["movimentacoes"]:
                    mov_data.append([
                        m["tipo"], m["descricao"][:30],
                        m["data_hora"][11:16],
                        f'R$ {m["valor"]:.2f}'
                    ])
                t_mov = Table(mov_data, colWidths=[3.5*cm,7.5*cm,2*cm,3.6*cm])
                t_mov.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,0),  COR_PRINCIPAL),
                    ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
                    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0),(-1,-1), 9),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, COR_LINHA]),
                    ("BOX",           (0,0),(-1,-1), 1, COR_PRINCIPAL),
                    ("INNERGRID",     (0,0),(-1,-1), 0.25, colors.lightgrey),
                    ("TOPPADDING",    (0,0),(-1,-1), 6),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                    ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ]))
                story.append(t_mov)
                story.append(Spacer(1, 0.4*cm))

            # ── PRODUTOS MAIS VENDIDOS ───────────────────────────────────────
            if res["produtos_top"]:
                story.append(Paragraph("PRODUTOS MAIS VENDIDOS", s_sec))
                prod_data = [["Produto", "Qtde", "Total"]]
                for p in res["produtos_top"]:
                    prod_data.append([
                        p["nome_produto"][:40],
                        f'{p["qtde"]:.1f}'.rstrip("0").rstrip("."),
                        f'R$ {p["total"]:.2f}'
                    ])
                t_prod = Table(prod_data, colWidths=[9.5*cm,2.5*cm,4.6*cm])
                t_prod.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,0),  COR_PRINCIPAL),
                    ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
                    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0),(-1,-1), 9),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, COR_LINHA]),
                    ("TEXTCOLOR",     (2,1),(2,-1),  COR_VERDE),
                    ("BOX",           (0,0),(-1,-1), 1, COR_PRINCIPAL),
                    ("INNERGRID",     (0,0),(-1,-1), 0.25, colors.lightgrey),
                    ("TOPPADDING",    (0,0),(-1,-1), 6),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                    ("LEFTPADDING",   (0,0),(-1,-1), 8),
                ]))
                story.append(t_prod)
                story.append(Spacer(1, 0.4*cm))

            # ── CONFERÊNCIA FINAL ────────────────────────────────────────────
            story.append(Paragraph("CONFERÊNCIA FINAL", s_sec))
            sinal      = "+" if diff >= 0 else ""
            cor_diff   = COR_VERDE if abs(diff) < 0.01 else COR_VERM
            status_txt = "✓ CAIXA OK" if abs(diff) < 0.01 else "⚠ DIFERENÇA ENCONTRADA"
            conf_data  = [
                ["Saldo Esperado:",  f"R$ {saldo_esp:.2f}"],
                ["Valor Contado:",   f"R$ {vf:.2f}"],
                ["Diferença:",       f"{sinal}R$ {abs(diff):.2f}"],
                ["Status:",          status_txt],
            ]
            t_conf = Table(conf_data, colWidths=[5*cm,11.6*cm])
            t_conf.setStyle(TableStyle([
                ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
                ("FONTSIZE",      (0,0),(-1,-1), 10),
                ("TEXTCOLOR",     (0,0),(0,-1),  COR_CINZA),
                ("FONTNAME",      (1,2),(1,3),   "Helvetica-Bold"),
                ("TEXTCOLOR",     (1,2),(1,3),   cor_diff),
                ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, COR_LINHA]),
                ("BOX",           (0,0),(-1,-1), 1, COR_PRINCIPAL),
                ("TOPPADDING",    (0,0),(-1,-1), 8),
                ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ]))
            story.append(t_conf)

            # ── ASSINATURA ───────────────────────────────────────────────────
            story.append(Spacer(1, 1.5*cm))
            ass_data = [
                ["_______________________________", "_______________________________"],
                [f"{self.usuario}", "Conferente"],
            ]
            t_ass = Table(ass_data, colWidths=[8*cm, 8*cm])
            t_ass.setStyle(TableStyle([
                ("ALIGN",        (0,0),(-1,-1), "CENTER"),
                ("FONTSIZE",     (0,0),(-1,-1), 9),
                ("TEXTCOLOR",    (0,0),(-1,-1), COR_CINZA),
                ("TOPPADDING",   (0,1),(-1,1),  4),
            ]))
            story.append(t_ass)

            doc.build(story,
                      onFirstPage=MarcaDagua(logo_path, empresa),
                      onLaterPages=MarcaDagua(logo_path, empresa))

            import subprocess, platform
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])

            if not fechando:
                messagebox.showinfo("✅ PDF Gerado",
                                    f"PDF salvo em:\n{path}", parent=self)
            return path

        except ImportError:
            messagebox.showerror("Erro",
                "ReportLab não instalado!\n\nRode no CMD:\npip install reportlab",
                parent=self)
        except Exception as e:
            messagebox.showerror("Erro ao gerar PDF", str(e), parent=self)
    def _imprimir_relatorio(self, res, valor_final=None):
        """Salva relatório TXT para impressora térmica"""
        try:
            import os, sys
            if getattr(sys,"frozen",False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            path  = os.path.join(pasta, f"fechamento_{agora}.txt")
            empresa = get_config("empresa_nome") or "Padaria Da Laine"
            val_ini = self.cx_dados.get("valor_inicial", 0)
            saldo_esp = val_ini + res["total_vendas"] + res["suprimento"] - res["sangria"]
            vf = valor_final if valor_final is not None else saldo_esp
            diff = vf - saldo_esp
            sinal = "+" if diff >= 0 else ""

            with open(path, "w", encoding="utf-8") as f:
                f.write("=" * 48 + "\n")
                f.write(f"{empresa:^48}\n")
                f.write("FECHAMENTO DE CAIXA".center(48) + "\n")
                f.write("=" * 48 + "\n")
                f.write(f"Caixa #: {self.caixa_id}\n")
                f.write(f"Abertura: {self.cx_dados.get('data_abertura','')[:16]}\n")
                f.write(f"Fechamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                f.write(f"Operador: {self.usuario}\n")
                f.write("-" * 48 + "\n")
                f.write("RESUMO:\n")
                f.write(f"  Fundo inicial:  R$ {val_ini:.2f}\n")
                f.write(f"  Total vendas:   R$ {res['total_vendas']:.2f}\n")
                f.write(f"  Suprimentos:    R$ {res['suprimento']:.2f}\n")
                f.write(f"  Sangrias:       R$ {res['sangria']:.2f}\n")
                f.write(f"  Saldo esperado: R$ {saldo_esp:.2f}\n")
                f.write("-" * 48 + "\n")
                f.write("VENDAS POR FORMA:\n")
                for v in res["vendas"]:
                    f.write(f"  {v['forma_pagamento']:<20} R$ {v['total']:.2f}\n")
                f.write(f"  {'TOTAL':<20} R$ {res['total_vendas']:.2f}\n")
                if res["movimentacoes"]:
                    f.write("-" * 48 + "\n")
                    f.write("MOVIMENTAÇÕES:\n")
                    for m in res["movimentacoes"]:
                        f.write(f"  {m['tipo']:<15} R$ {m['valor']:.2f}  {m['descricao'][:15]}\n")
                f.write("-" * 48 + "\n")
                f.write("CONFERÊNCIA:\n")
                f.write(f"  Saldo esperado: R$ {saldo_esp:.2f}\n")
                f.write(f"  Valor contado:  R$ {vf:.2f}\n")
                f.write(f"  Diferença:      {sinal}R$ {abs(diff):.2f}\n")
                status = "CAIXA OK" if abs(diff) < 0.01 else "DIFERENÇA!"
                f.write(f"  Status: {status}\n")
                f.write("=" * 48 + "\n")

            # Tenta imprimir na térmica se disponível
            try:
                from utils.impressora import imprimir_cupom
            except Exception:
                pass

        except Exception as e:
            print(f"Erro ao gerar TXT: {e}")
