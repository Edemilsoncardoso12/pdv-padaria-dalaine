"""telas/relatorios.py — Relatórios de Vendas — Canvas fluido"""
import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime, timedelta, date
from tema import *
from banco.database import listar_vendas, get_conn


# ── Altura de cada linha na tabela Canvas ─────────────────────────────────────
ROW_H = 32
COLS  = ["#", "Data/Hora", "Total", "Desconto", "Forma Pagamento", "Troco", "NFC-e"]
WIDS  = [40,  145,         90,      85,          255,               80,      75]
XPOS  = []
_x = 8
for w in WIDS:
    XPOS.append(_x)
    _x += w


class TelaRelatorios(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._vendas_atuais   = []
        self._vendas_filtradas = []
        self._idx_selecionado  = -1
        self._filtro_forma     = "TODAS"
        self._pagina_atual     = 0
        self._POR_PAGINA       = 25

        self._build_header()
        self._build_corpo()
        self._carregar_hoje()

    # ── HEADER ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=100)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        # Linha 1: título + filtros de data
        linha1 = ctk.CTkFrame(hdr, fg_color="transparent")
        linha1.grid(row=0, column=0, sticky="ew", padx=16, pady=(8, 2))
        linha1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(linha1, text="📈  Relatórios de Vendas",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, sticky="w")

        bf = ctk.CTkFrame(linha1, fg_color="transparent")
        bf.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(bf, text="De:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.ent_ini = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                                    fg_color=COR_CARD2, border_color=COR_BORDA2,
                                    text_color=COR_TEXTO)
        self.ent_ini.pack(side="left", padx=(0, 8))
        self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))

        ctk.CTkLabel(bf, text="Até:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.ent_fim = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                                    fg_color=COR_CARD2, border_color=COR_BORDA2,
                                    text_color=COR_TEXTO)
        self.ent_fim.pack(side="left", padx=(0, 8))
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))

        for txt, cmd in [("Hoje",      self._carregar_hoje),
                         ("7 dias",    self._carregar_7dias),
                         ("30 dias",   self._carregar_30dias),
                         ("🔍 Filtrar", self._carregar_personalizado)]:
            ctk.CTkButton(bf, text=txt, width=80, font=FONTE_BTN,
                          fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                          text_color="white", command=cmd).pack(side="left", padx=3)

        ctk.CTkButton(bf, text="📄 Exportar TXT", width=110, font=FONTE_BTN,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white", command=self._exportar).pack(side="left", padx=3)

        ctk.CTkButton(bf, text="🖨️ Exportar PDF", width=110, font=FONTE_BTN,
                      fg_color="#B45309", hover_color="#92400E",
                      text_color="white", command=self._exportar_pdf).pack(side="left", padx=3)

        # Linha 2: filtros por forma de pagamento
        linha2 = ctk.CTkFrame(hdr, fg_color="transparent")
        linha2.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 8))

        ctk.CTkLabel(linha2, text="Forma:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 8))

        self._btns_forma = {}
        formas = [
            ("Todas",       "TODAS",            COR_ACENTO,  COR_ACENTO2),
            ("💵 Dinheiro", "DINHEIRO",         COR_SUCESSO, COR_SUCESSO2),
            ("📱 PIX",      "PIX",              "#0891B2",   "#0E7490"),
            ("💳 Débito",   "DEBITO",           "#1D4ED8",   "#1E40AF"),
            ("💳 Crédito",  "CREDITO",          "#7C3AED",   "#6D28D9"),
            ("🎫 Vale",     "VALE ALIMENTACAO", "#B45309",   "#92400E"),
        ]
        for txt, val, cor, hover in formas:
            btn = ctk.CTkButton(linha2, text=txt, font=FONTE_BTN_SM,
                                height=28, width=90,
                                fg_color=cor if val == "TODAS" else COR_CARD2,
                                hover_color=hover,
                                border_width=1, border_color=cor,
                                text_color="white" if val == "TODAS" else COR_TEXTO,
                                command=lambda v=val, c=cor: self._filtrar_forma(v, c))
            btn.pack(side="left", padx=3)
            self._btns_forma[val] = (btn, cor)

    # ── CORPO ─────────────────────────────────────────────────────────────────

    def _build_corpo(self):
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(1, weight=1)

        # Cards KPI
        cards = ctk.CTkFrame(corpo, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        cards.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.card_total    = self._card(cards, 0, "💰 Total Vendas", "R$ 0,00", COR_ACENTO)
        self.card_qtde     = self._card(cards, 1, "🧾 Nº Vendas",    "0",       COR_SUCESSO)
        self.card_ticket   = self._card(cards, 2, "🎫 Ticket Médio", "R$ 0,00", COR_INFO)
        self.card_dinheiro = self._card(cards, 3, "💵 Dinheiro",     "R$ 0,00", "#8B5CF6")
        self.card_pix      = self._card(cards, 4, "📱 PIX",          "R$ 0,00", "#0891B2")

        # Frame da tabela
        frame = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Cabeçalho da tabela
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        cab.grid_propagate(False)
        for col, w in zip(COLS, WIDS):
            ctk.CTkLabel(cab, text=col, font=("Courier New", 13, "bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(
                side="left", padx=4, pady=6)

        # Canvas + scrollbar
        canvas_frame = ctk.CTkFrame(frame, fg_color="transparent")
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 4))
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(canvas_frame, bg=COR_CARD,
                                 highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        sb = tk.Scrollbar(canvas_frame, orient="vertical",
                          command=self._canvas.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=sb.set)

        # Bind scroll do mouse
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(
                              int(-1*(e.delta/120)), "units"))
        self._canvas.bind("<Button-4>",
                          lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>",
                          lambda e: self._canvas.yview_scroll(1, "units"))

        # Paginação
        self._frame_pag = ctk.CTkFrame(frame, fg_color="transparent", height=36)
        self._frame_pag.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self._frame_pag.grid_propagate(False)

        self._lbl_info = ctk.CTkLabel(self._frame_pag, text="",
                                      font=FONTE_SMALL, text_color=COR_TEXTO_SUB)
        self._lbl_info.pack(side="left", padx=8)

        self._btn_prox = ctk.CTkButton(self._frame_pag, text="Próxima ▶", width=90,
                                       font=FONTE_BTN, fg_color=COR_ACENTO,
                                       hover_color=COR_ACENTO2, text_color="white",
                                       command=self._proxima_pagina)
        self._btn_prox.pack(side="right", padx=4)

        self._lbl_pag = ctk.CTkLabel(self._frame_pag, text="",
                                     font=FONTE_SMALL, text_color=COR_TEXTO)
        self._lbl_pag.pack(side="right", padx=8)

        self._btn_ant = ctk.CTkButton(self._frame_pag, text="◀ Anterior", width=90,
                                      font=FONTE_BTN, fg_color=COR_ACENTO,
                                      hover_color=COR_ACENTO2, text_color="white",
                                      command=self._pagina_anterior)
        self._btn_ant.pack(side="right", padx=4)

        self.after(100, self._bind_teclas)

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=4, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(12, 2))
        lbl = ctk.CTkLabel(card, text=valor,
                           font=("Georgia", 18, "bold"), text_color=cor)
        lbl.pack(pady=(0, 12))
        return lbl

    # ── RENDERIZAÇÃO NO CANVAS ────────────────────────────────────────────────

    def _popular(self, vendas):
        self._pagina_atual = 0
        self._atualizar_kpis(vendas)
        self._desenhar_pagina()

    def _atualizar_kpis(self, vendas):
        if not vendas:
            for lbl, v in [(self.card_total, "R$ 0,00"), (self.card_qtde, "0"),
                           (self.card_ticket, "R$ 0,00"), (self.card_dinheiro, "R$ 0,00"),
                           (self.card_pix, "R$ 0,00")]:
                lbl.configure(text=v)
            return
        total_geral = sum(v["total"] for v in vendas)
        dinheiro    = sum(v["total"] for v in vendas if "DINHEIRO" in v["forma_pagamento"])
        pix         = sum(v["total"] for v in vendas if "PIX"      in v["forma_pagamento"])
        ticket      = total_geral / len(vendas)
        self.card_total.configure(text=f"R$ {total_geral:.2f}")
        self.card_qtde.configure(text=str(len(vendas)))
        self.card_ticket.configure(text=f"R$ {ticket:.2f}")
        self.card_dinheiro.configure(text=f"R$ {dinheiro:.2f}")
        self.card_pix.configure(text=f"R$ {pix:.2f}")

    def _desenhar_pagina(self):
        vendas = self._vendas_filtradas
        c = self._canvas
        c.delete("all")
        self._idx_selecionado = -1

        if not vendas:
            c.create_text(400, 60, text="Nenhuma venda no período.",
                          font=("Courier New", 13), fill=COR_TEXTO_SUB)
            c.configure(scrollregion=(0, 0, 800, 120))
            self._atualizar_paginacao(0, 0)
            return

        total  = len(vendas)
        npags  = max(1, -(-total // self._POR_PAGINA))
        self._pagina_atual = max(0, min(self._pagina_atual, npags - 1))
        ini    = self._pagina_atual * self._POR_PAGINA
        fim    = min(ini + self._POR_PAGINA, total)
        pagina = vendas[ini:fim]

        altura_total = len(pagina) * ROW_H + 4
        c.configure(scrollregion=(0, 0, 800, altura_total))

        for i, v in enumerate(pagina):
            y      = i * ROW_H
            cor_bg = COR_LINHA_PAR if i % 2 == 0 else COR_CARD
            # fundo da linha
            c.create_rectangle(0, y, 2000, y + ROW_H,
                               fill=cor_bg, outline="")
            # separador
            c.create_line(0, y + ROW_H - 1, 2000, y + ROW_H - 1,
                          fill=COR_BORDA, width=1)

            nfce_cor = COR_SUCESSO if v["nfce_status"] == "EMITIDA" else COR_PERIGO
            vals  = [str(v["id"]), v["data_hora"][:16],
                     f'R$ {v["total"]:.2f}', f'R$ {v["desconto"]:.2f}',
                     v["forma_pagamento"][:35], f'R$ {v["troco"]:.2f}',
                     v["nfce_status"]]
            cores = [COR_TEXTO_SUB, COR_TEXTO, COR_SUCESSO, COR_PERIGO,
                     COR_TEXTO, COR_TEXTO_SUB, nfce_cor]

            for val, cor, x in zip(vals, cores, XPOS):
                c.create_text(x, y + ROW_H // 2, text=val,
                              font=("Courier New", 12), fill=cor,
                              anchor="w")

            # Tag de clique por linha
            tag = f"row_{i}"
            c.create_rectangle(0, y, 2000, y + ROW_H,
                               fill="", outline="", tags=tag)
            idx_cap = ini + i
            c.tag_bind(tag, "<Button-1>",
                       lambda e, idx=idx_cap, row=i: self._selecionar(idx, row))

        self._atualizar_paginacao(npags, total)

    def _selecionar(self, idx_global, row_local):
        self._idx_selecionado = idx_global
        self._destacar_canvas(row_local)

    def _destacar_canvas(self, row_local):
        c = self._canvas
        ini = self._pagina_atual * self._POR_PAGINA
        pagina = self._vendas_filtradas[ini:ini + self._POR_PAGINA]
        for i in range(len(pagina)):
            y      = i * ROW_H
            cor_bg = COR_ACENTO_LIGHT if i == row_local else (
                COR_LINHA_PAR if i % 2 == 0 else COR_CARD)
            c.create_rectangle(0, y, 2000, y + ROW_H,
                               fill=cor_bg, outline="")
            # redesenha texto por cima
            v = pagina[i]
            nfce_cor = COR_SUCESSO if v["nfce_status"] == "EMITIDA" else COR_PERIGO
            vals  = [str(v["id"]), v["data_hora"][:16],
                     f'R$ {v["total"]:.2f}', f'R$ {v["desconto"]:.2f}',
                     v["forma_pagamento"][:35], f'R$ {v["troco"]:.2f}',
                     v["nfce_status"]]
            cores = [COR_TEXTO_SUB, COR_TEXTO, COR_SUCESSO, COR_PERIGO,
                     COR_TEXTO, COR_TEXTO_SUB, nfce_cor]
            for val, cor, x in zip(vals, cores, XPOS):
                c.create_text(x, y + ROW_H // 2, text=val,
                              font=("Courier New", 12), fill=cor, anchor="w")
            c.create_line(0, y + ROW_H - 1, 2000, y + ROW_H - 1,
                          fill=COR_BORDA, width=1)

    # ── PAGINAÇÃO ─────────────────────────────────────────────────────────────

    def _atualizar_paginacao(self, npags, total):
        if npags <= 1:
            self._lbl_info.configure(text=f"{total} venda(s) no período")
            self._lbl_pag.configure(text="")
            self._btn_ant.configure(state="disabled")
            self._btn_prox.configure(state="disabled")
            return
        ini = self._pagina_atual * self._POR_PAGINA + 1
        fim = min((self._pagina_atual + 1) * self._POR_PAGINA, total)
        self._lbl_info.configure(text=f"Mostrando {ini}–{fim} de {total} vendas")
        self._lbl_pag.configure(text=f"Pág. {self._pagina_atual + 1}/{npags}")
        self._btn_ant.configure(
            state="normal" if self._pagina_atual > 0 else "disabled")
        self._btn_prox.configure(
            state="normal" if self._pagina_atual < npags - 1 else "disabled")

    def _pagina_anterior(self):
        if self._pagina_atual > 0:
            self._pagina_atual -= 1
            self._desenhar_pagina()
            self._canvas.yview_moveto(0)

    def _proxima_pagina(self):
        total = len(self._vendas_filtradas)
        npags = max(1, -(-total // self._POR_PAGINA))
        if self._pagina_atual < npags - 1:
            self._pagina_atual += 1
            self._desenhar_pagina()
            self._canvas.yview_moveto(0)

    # ── NAVEGAÇÃO POR TECLADO ─────────────────────────────────────────────────

    def _bind_teclas(self):
        try:
            root = self.winfo_toplevel()
            root.bind("<Up>",   self._navegar_cima)
            root.bind("<Down>", self._navegar_baixo)
        except Exception:
            pass

    def _navegar_cima(self, event=None):
        if not self._vendas_filtradas:
            return
        if self._idx_selecionado > 0:
            self._idx_selecionado -= 1
        else:
            self._idx_selecionado = 0
        self._sync_selecao()

    def _navegar_baixo(self, event=None):
        if not self._vendas_filtradas:
            return
        n = len(self._vendas_filtradas)
        if self._idx_selecionado < n - 1:
            self._idx_selecionado += 1
        else:
            self._idx_selecionado = n - 1
        self._sync_selecao()

    def _sync_selecao(self):
        """Garante que a página exibe a linha selecionada e a destaca."""
        idx = self._idx_selecionado
        pagina_correta = idx // self._POR_PAGINA
        if pagina_correta != self._pagina_atual:
            self._pagina_atual = pagina_correta
            self._desenhar_pagina()
        row_local = idx % self._POR_PAGINA
        self._destacar_canvas(row_local)
        # scroll para linha visível
        total_linhas = len(self._vendas_filtradas[
            self._pagina_atual * self._POR_PAGINA:
            (self._pagina_atual + 1) * self._POR_PAGINA])
        if total_linhas > 0:
            frac = row_local / total_linhas
            self._canvas.yview_moveto(frac)

    # ── FILTROS ───────────────────────────────────────────────────────────────

    def _filtrar_forma(self, forma, cor):
        self._filtro_forma = forma
        for val, (btn, c) in self._btns_forma.items():
            if val == forma:
                btn.configure(fg_color=c, text_color="white")
            else:
                btn.configure(fg_color=COR_CARD2, text_color=COR_TEXTO)
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        if self._filtro_forma == "TODAS":
            self._vendas_filtradas = list(self._vendas_atuais)
        else:
            self._vendas_filtradas = [
                v for v in self._vendas_atuais
                if self._filtro_forma in v["forma_pagamento"].upper()
            ]
        self._pagina_atual = 0
        self._popular(self._vendas_filtradas)

    # ── CARREGAMENTO ──────────────────────────────────────────────────────────

    def _carregar_com_thread(self, ini, fim):
        def carregar():
            try:
                vendas = listar_vendas(ini, fim)
                self._vendas_atuais    = vendas
                self._vendas_filtradas = list(vendas)
                self._idx_selecionado  = -1
                self.after(0, lambda: self._popular(self._vendas_filtradas))
            except Exception:
                self.after(0, lambda: self._popular([]))
        threading.Thread(target=carregar, daemon=True).start()

    def _carregar_hoje(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0, "end")
        self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fim.delete(0, "end")
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        self._carregar_com_thread(hoje, hoje)

    def _carregar_7dias(self):
        ini = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0, "end")
        self.ent_ini.insert(0, (date.today() - timedelta(days=7)).strftime("%d/%m/%Y"))
        self.ent_fim.delete(0, "end")
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        self._carregar_com_thread(ini, fim)

    def _carregar_30dias(self):
        ini = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0, "end")
        self.ent_ini.insert(0, (date.today() - timedelta(days=30)).strftime("%d/%m/%Y"))
        self.ent_fim.delete(0, "end")
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        self._carregar_com_thread(ini, fim)

    def _carregar_personalizado(self):
        from tkinter import messagebox
        try:
            ini = datetime.strptime(self.ent_ini.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            fim = datetime.strptime(self.ent_fim.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
            return
        self._carregar_com_thread(ini, fim)

    # ── EXPORTAR TXT ──────────────────────────────────────────────────────────

    def _exportar(self):
        from tkinter import filedialog, messagebox
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")],
            initialfile=f"relatorio_{date.today().strftime('%Y%m%d')}.txt")
        if not path:
            return
        vendas = self._vendas_filtradas or []
        total  = sum(v["total"] for v in vendas)
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 56 + "\n")
            f.write(f"{'RELATÓRIO DE VENDAS':^56}\n")
            f.write("=" * 56 + "\n")
            f.write(f"Total vendas: R$ {total:.2f}\n")
            f.write(f"Qtd vendas:   {len(vendas)}\n")
            if self._filtro_forma != "TODAS":
                f.write(f"Filtro forma: {self._filtro_forma}\n")
            f.write("-" * 56 + "\n")
            f.write(f"{'#':<6}{'Data/Hora':<18}{'Forma':<20}{'Total':>10}\n")
            f.write("-" * 56 + "\n")
            for v in vendas:
                f.write(f"{v['id']:<6}{v['data_hora'][:16]:<18}"
                        f"{v['forma_pagamento'][:20]:<20}"
                        f"R$ {v['total']:>7.2f}\n")
        messagebox.showinfo("Exportado", f"Relatório salvo em:\n{path}")

    # ── EXPORTAR PDF ──────────────────────────────────────────────────────────

    def _exportar_pdf(self):
        from tkinter import filedialog, messagebox
        import os, sys
        from datetime import datetime as dt

        vendas = self._vendas_atuais or []
        if not vendas:
            messagebox.showwarning("Aviso", "Nenhuma venda para exportar!")
            return

        ini    = self.ent_ini.get()
        fim    = self.ent_fim.get()
        periodo = ini if ini == fim else f"{ini} a {fim}"

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"relatorio_vendas_{dt.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not path:
            return

        # Loading overlay
        loading = ctk.CTkToplevel(self)
        loading.title("")
        loading.resizable(False, False)
        loading.geometry("280x90")
        loading.grab_set()
        ctk.CTkLabel(loading, text="⏳  Gerando PDF, aguarde...",
                     font=FONTE_LABEL, text_color=COR_TEXTO).pack(expand=True)
        loading.update()

        def gerar():
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import cm
                from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                                Table, TableStyle, HRFlowable)
                from reportlab.lib.styles import ParagraphStyle
                from reportlab.lib import colors
                from reportlab.lib.enums import TA_CENTER, TA_LEFT

                doc = SimpleDocTemplate(path, pagesize=A4,
                                        topMargin=1.5*cm, bottomMargin=1.5*cm,
                                        leftMargin=2*cm, rightMargin=2*cm)
                story = []
                COR_PDF   = colors.HexColor("#8B1A1A")
                COR_CINZA = colors.HexColor("#F5F0E8")

                T = lambda txt, size=10, bold=False, cor=colors.black, align=TA_LEFT: \
                    Paragraph(txt, ParagraphStyle("x", fontSize=size,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              textColor=cor, alignment=align, spaceAfter=2,
                              leading=size * 1.4))

                base_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
                           else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                logo_path = os.path.join(base_dir, "logo.png")

                if os.path.exists(logo_path):
                    try:
                        from reportlab.platypus import Image
                        from banco.database import get_config
                        empresa  = get_config("empresa_nome") or "Padaria"
                        endereco = get_config("empresa_endereco") or ""
                        cnpj     = get_config("empresa_cnpj") or ""
                        fone     = get_config("empresa_fone") or ""
                        logo_img = Image(logo_path, width=3*cm, height=3*cm)
                        info_txt = (f'<b><font size=14 color="#8B1A1A">{empresa.upper()}</font></b><br/>'
                                    f'<font size=9 color="#6B7280">{endereco}</font><br/>'
                                    f'<font size=9 color="#6B7280">CNPJ: {cnpj}   Fone: {fone}</font>')
                        cab_tab = Table([[logo_img,
                                         Paragraph(info_txt, ParagraphStyle(
                                             "cab", alignment=TA_LEFT, leading=14))]],
                                        colWidths=[3.5*cm, 13.5*cm])
                        cab_tab.setStyle(TableStyle([
                            ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
                            ("LEFTPADDING", (0,0),(-1,-1), 0),
                            ("TOPPADDING",  (0,0),(-1,-1), 0),
                            ("BOTTOMPADDING",(0,0),(-1,-1),0),
                        ]))
                        story.append(cab_tab)
                    except Exception:
                        story.append(T("PADARIA DA LAINE", 16, True, COR_PDF, TA_CENTER))
                else:
                    story.append(T("PADARIA DA LAINE", 16, True, COR_PDF, TA_CENTER))

                story.append(Spacer(1, 0.2*cm))
                story.append(HRFlowable(width="100%", thickness=2, color=COR_PDF))

                tit = Table([[f"RELATÓRIO DE VENDAS — {periodo}"]],
                            colWidths=[17*cm])
                tit.setStyle(TableStyle([
                    ("BACKGROUND", (0,0),(-1,-1), COR_PDF),
                    ("TEXTCOLOR",  (0,0),(-1,-1), colors.white),
                    ("FONTNAME",   (0,0),(-1,-1), "Helvetica-Bold"),
                    ("FONTSIZE",   (0,0),(-1,-1), 12),
                    ("ALIGN",      (0,0),(-1,-1), "CENTER"),
                    ("TOPPADDING", (0,0),(-1,-1), 7),
                    ("BOTTOMPADDING",(0,0),(-1,-1),7),
                ]))
                story.append(tit)
                story.append(Spacer(1, 0.3*cm))

                formas_cfg = [
                    ("DINHEIRO",                 "DINHEIRO",          colors.HexColor("#059669")),
                    ("CARTAO - DEBITO",           "CARTAO - DEBITO",   colors.HexColor("#1D4ED8")),
                    ("PIX",                       "PIX",               colors.HexColor("#0891B2")),
                    ("CARTAO - CREDITO",          "CARTAO - CREDITO",  colors.HexColor("#7C3AED")),
                    ("CARTAO - VALE ALIMENTACAO", "VALE ALIMENTACAO",  colors.HexColor("#B45309")),
                ]

                grupos = {}
                outras = []
                for v in vendas:
                    forma   = v["forma_pagamento"]
                    matched = False
                    for fk, fl, fc in formas_cfg:
                        if fk in forma.upper() or forma.upper() == fk:
                            if fk not in grupos:
                                grupos[fk] = {"label": fl, "cor": fc,
                                              "vendas": [], "total": 0}
                            grupos[fk]["vendas"].append(v)
                            grupos[fk]["total"] += v["total"]
                            matched = True
                            break
                    if not matched:
                        outras.append(v)

                total_geral = 0
                qtde_geral  = 0

                for fk, fl, fc in formas_cfg:
                    if fk not in grupos:
                        continue
                    g        = grupos[fk]
                    subtotal = g["total"]
                    total_geral += subtotal
                    qtde_geral  += len(g["vendas"])

                    story.append(Spacer(1, 0.2*cm))
                    sec = Table([[f"{g['label']}  —  {len(g['vendas'])} vendas  —  R$ {subtotal:.2f}"]],
                                colWidths=[17*cm])
                    sec.setStyle(TableStyle([
                        ("BACKGROUND",    (0,0),(-1,-1), g["cor"]),
                        ("TEXTCOLOR",     (0,0),(-1,-1), colors.white),
                        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
                        ("FONTSIZE",      (0,0),(-1,-1), 10),
                        ("TOPPADDING",    (0,0),(-1,-1), 5),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                        ("LEFTPADDING",   (0,0),(-1,-1), 10),
                    ]))
                    story.append(sec)

                    cab = Table([["#", "Horário", "Total", "Troco", "Desconto"]],
                                colWidths=[1.2*cm, 2.5*cm, 4*cm, 4*cm, 5.3*cm])
                    cab.setStyle(TableStyle([
                        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#FEF3C7")),
                        ("TEXTCOLOR",     (0,0),(-1,-1), colors.HexColor("#92400E")),
                        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
                        ("FONTSIZE",      (0,0),(-1,-1), 8),
                        ("ALIGN",         (2,0),(-1,-1), "RIGHT"),
                        ("TOPPADDING",    (0,0),(-1,-1), 3),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                        ("LEFTPADDING",   (0,0),(-1,-1), 4),
                        ("LINEBELOW",     (0,0),(-1,-1), 1, g["cor"]),
                    ]))
                    story.append(cab)

                    rows_data = []
                    for idx, v in enumerate(g["vendas"]):
                        troco = f"R$ {v['troco']:.2f}" if v["troco"] > 0 else "—"
                        desc  = f"R$ {v['desconto']:.2f}" if v["desconto"] > 0 else "—"
                        rows_data.append([str(idx+1), v["data_hora"][11:16],
                                          f"R$ {v['total']:.2f}", troco, desc])

                    t = Table(rows_data, colWidths=[1.2*cm, 2.5*cm, 4*cm, 4*cm, 5.3*cm])
                    t.setStyle(TableStyle([
                        ("FONTNAME",      (0,0),(-1,-1), "Helvetica"),
                        ("FONTSIZE",      (0,0),(-1,-1), 8),
                        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, COR_CINZA]),
                        ("ALIGN",         (2,0),(-1,-1), "RIGHT"),
                        ("TOPPADDING",    (0,0),(-1,-1), 3),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                        ("LEFTPADDING",   (0,0),(-1,-1), 4),
                        ("TEXTCOLOR",     (2,0),(2,-1),  g["cor"]),
                        ("FONTNAME",      (2,0),(2,-1),  "Helvetica-Bold"),
                    ]))
                    story.append(t)

                    sub = Table([[f"Sub-Total: R$ {subtotal:.2f}"]], colWidths=[17*cm])
                    sub.setStyle(TableStyle([
                        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
                        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
                        ("FONTSIZE",      (0,0),(-1,-1), 9),
                        ("TEXTCOLOR",     (0,0),(-1,-1), g["cor"]),
                        ("TOPPADDING",    (0,0),(-1,-1), 3),
                        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
                        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
                        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F9FAFB")),
                        ("LINEABOVE",     (0,0),(-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                    ]))
                    story.append(sub)

                story.append(Spacer(1, 0.4*cm))
                story.append(HRFlowable(width="100%", thickness=1.5, color=COR_PDF))
                tot = Table([[f"TOTAL GERAL: {qtde_geral} vendas  —  R$ {total_geral:.2f}"]],
                            colWidths=[17*cm])
                tot.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,-1), COR_PDF),
                    ("TEXTCOLOR",     (0,0),(-1,-1), colors.white),
                    ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0),(-1,-1), 12),
                    ("ALIGN",         (0,0),(-1,-1), "CENTER"),
                    ("TOPPADDING",    (0,0),(-1,-1), 8),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 8),
                ]))
                story.append(tot)
                story.append(Spacer(1, 0.4*cm))
                story.append(T(
                    f"Gerado em: {dt.now().strftime('%d/%m/%Y %H:%M')}  —  Padaria Da Laine",
                    8, align=TA_CENTER))

                doc.build(story)
                self.after(0, loading.destroy)
                try:
                    import subprocess
                    subprocess.Popen(["start", "", path], shell=True)
                except Exception:
                    pass
                self.after(0, lambda: messagebox.showinfo(
                    "PDF Exportado", f"Relatório salvo em:\n{path}"))

            except Exception as e:
                err = str(e)
                self.after(0, loading.destroy)
                self.after(0, lambda: messagebox.showerror(
                    "Erro", f"Erro ao gerar PDF:\n{err}"))

        threading.Thread(target=gerar, daemon=True).start()
