"""telas/relatorios.py — Relatórios Completos — Tema Branco"""
import customtkinter as ctk
import tkinter as tk
import threading
from datetime import datetime, timedelta, date
from tema import *
from banco.database import listar_vendas, get_conn


class TelaRelatorios(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._vendas_atuais = []
        self._vendas_filtradas = []
        self._idx_selecionado = -1
        self._filtro_forma = "TODAS"
        self._build_header()
        self._build_corpo()
        self._carregar_hoje()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=100)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(0, weight=1)

        # Linha 1: título + filtros de data
        linha1 = ctk.CTkFrame(hdr, fg_color="transparent")
        linha1.grid(row=0, column=0, sticky="ew", padx=16, pady=(8,2))
        linha1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(linha1, text="📈  Relatórios de Vendas",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, sticky="w")

        bf = ctk.CTkFrame(linha1, fg_color="transparent")
        bf.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(bf, text="De:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0,4))
        self.ent_ini = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                        fg_color=COR_CARD2, border_color=COR_BORDA2,
                        text_color=COR_TEXTO)
        self.ent_ini.pack(side="left", padx=(0,8))
        self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))

        ctk.CTkLabel(bf, text="Até:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0,4))
        self.ent_fim = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                        fg_color=COR_CARD2, border_color=COR_BORDA2,
                        text_color=COR_TEXTO)
        self.ent_fim.pack(side="left", padx=(0,8))
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))

        for txt, cmd in [("Hoje",    self._carregar_hoje),
                         ("7 dias",  self._carregar_7dias),
                         ("30 dias", self._carregar_30dias),
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
        linha2.grid(row=1, column=0, sticky="ew", padx=16, pady=(2,8))

        ctk.CTkLabel(linha2, text="Forma:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0,8))

        self._btns_forma = {}
        formas = [
            ("Todas",         "TODAS",            COR_ACENTO,  COR_ACENTO2),
            ("💵 Dinheiro",   "DINHEIRO",         COR_SUCESSO, COR_SUCESSO2),
            ("📱 PIX",        "PIX",              "#0891B2",   "#0E7490"),
            ("💳 Débito",     "DEBITO",           "#1D4ED8",   "#1E40AF"),
            ("💳 Crédito",    "CREDITO",          "#7C3AED",   "#6D28D9"),
            ("🎫 Vale",       "VALE ALIMENTACAO", "#B45309",   "#92400E"),
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

    def _filtrar_forma(self, forma, cor):
        self._filtro_forma = forma
        # Atualiza visual dos botões
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
        self._idx_selecionado = -1
        self._popular(self._vendas_filtradas)

    def _build_corpo(self):
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(2, weight=1)

        # Cards KPI
        cards = ctk.CTkFrame(corpo, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew")
        cards.grid_columnconfigure((0,1,2,3,4), weight=1)

        self.card_total    = self._card(cards, 0, "💰 Total Vendas",  "R$ 0,00", COR_ACENTO)
        self.card_qtde     = self._card(cards, 1, "🧾 Nº Vendas",     "0",       COR_SUCESSO)
        self.card_ticket   = self._card(cards, 2, "🎫 Ticket Médio",  "R$ 0,00", COR_INFO)
        self.card_dinheiro = self._card(cards, 3, "💵 Dinheiro",      "R$ 0,00", "#8B5CF6")
        self.card_pix      = self._card(cards, 4, "📱 PIX",           "R$ 0,00", "#0891B2")

        # Linha 2: gráfico + ranking
        linha2 = ctk.CTkFrame(corpo, fg_color="transparent")
        linha2.grid(row=1, column=0, sticky="ew", pady=(12,0))
        linha2.grid_columnconfigure(0, weight=3)
        linha2.grid_columnconfigure(1, weight=2)

        frame_graf = ctk.CTkFrame(linha2, fg_color=COR_CARD, corner_radius=12,
                                  border_width=1, border_color=COR_BORDA)
        frame_graf.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(frame_graf, text="📊  Vendas por Dia",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
            anchor="w", padx=16, pady=(12,4))
        self.canvas_graf = tk.Canvas(frame_graf, bg=COR_CARD,
                                     highlightthickness=0, height=140)
        self.canvas_graf.pack(fill="x", padx=16, pady=(0,12))
        self.canvas_graf.bind("<Configure>", self._desenhar_grafico)

        frame_rank = ctk.CTkFrame(linha2, fg_color=COR_CARD, corner_radius=12,
                                  border_width=1, border_color=COR_BORDA)
        frame_rank.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(frame_rank, text="🏆  Mais Vendidos",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
            anchor="w", padx=16, pady=(12,4))
        self.scroll_rank = ctk.CTkScrollableFrame(frame_rank, fg_color="transparent",
                                                   height=120)
        self.scroll_rank.pack(fill="both", expand=True, padx=12, pady=(0,12))

        # Tabela de vendas
        frame = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=2, column=0, sticky="nsew", pady=(12,0))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Cabeçalho da tabela + instrução de navegação
        cab_frame = ctk.CTkFrame(frame, fg_color="transparent")
        cab_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab_frame.grid_columnconfigure(0, weight=1)

        cab = ctk.CTkFrame(cab_frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew")
        cab.grid_propagate(False)

        COLS  = ["#", "Data/Hora", "Total", "Desconto", "Forma Pagamento", "Troco", "NFC-e"]
        WIDS  = [40,  140,         90,      80,         260,               80,      70]
        for col, w in zip(COLS, WIDS):
            ctk.CTkLabel(cab, text=col, font=("Courier New",13,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(
                side="left", padx=4, pady=6)

        ctk.CTkLabel(cab_frame,
                     text="↑↓ para navegar",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).grid(
            row=0, column=1, padx=8, sticky="e")

        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Bind teclas de navegação na janela raiz
        self.after(100, self._bind_teclas)

        self._vendas_grafico = []

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=4, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(12,2))
        lbl = ctk.CTkLabel(card, text=valor,
                           font=("Georgia",18,"bold"), text_color=cor)
        lbl.pack(pady=(0,12))
        return lbl

    def _popular(self, vendas):
        for w in self.scroll.winfo_children():
            w.destroy()

        if not vendas:
            ctk.CTkLabel(self.scroll, text="Nenhuma venda no período.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=40)
            for lbl, v in [(self.card_total,"R$ 0,00"),(self.card_qtde,"0"),
                           (self.card_ticket,"R$ 0,00"),(self.card_dinheiro,"R$ 0,00"),
                           (self.card_pix,"R$ 0,00")]:
                lbl.configure(text=v)
            self._vendas_grafico = []
            self._atualizar_ranking([])
            return

        total_geral = sum(v["total"] for v in vendas)
        dinheiro    = sum(v["total"] for v in vendas if "DINHEIRO" in v["forma_pagamento"])
        pix         = sum(v["total"] for v in vendas if "PIX"      in v["forma_pagamento"])
        ticket      = total_geral / len(vendas) if vendas else 0

        self.card_total.configure(text=f"R$ {total_geral:.2f}")
        self.card_qtde.configure(text=str(len(vendas)))
        self.card_ticket.configure(text=f"R$ {ticket:.2f}")
        self.card_dinheiro.configure(text=f"R$ {dinheiro:.2f}")
        self.card_pix.configure(text=f"R$ {pix:.2f}")

        por_dia = {}
        for v in vendas:
            dia = v["data_hora"][:10]
            por_dia[dia] = por_dia.get(dia, 0) + v["total"]
        self._vendas_grafico = sorted(por_dia.items())
        self._desenhar_grafico()
        self._atualizar_ranking(vendas)

        WIDS = [40, 140, 90, 80, 260, 80, 70]
        self._rows_widgets = []

        for idx, v in enumerate(vendas):
            cor_bg   = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            row_f    = ctk.CTkFrame(self.scroll, fg_color=cor_bg,
                                    corner_radius=4, height=32)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)
            row_i = ctk.CTkFrame(row_f, fg_color="transparent")
            row_i.pack(fill="x", padx=4, pady=4)

            nfce_cor = COR_SUCESSO if v["nfce_status"] == "EMITIDA" else COR_PERIGO
            vals  = [str(v["id"]), v["data_hora"][:16],
                     f'R$ {v["total"]:.2f}', f'R$ {v["desconto"]:.2f}',
                     v["forma_pagamento"][:35], f'R$ {v["troco"]:.2f}',
                     v["nfce_status"]]
            cores = [COR_TEXTO_SUB, COR_TEXTO, COR_SUCESSO, COR_PERIGO,
                     COR_TEXTO, COR_TEXTO_SUB, nfce_cor]

            for val, cor, w in zip(vals, cores, WIDS):
                ctk.CTkLabel(row_i, text=val, font=("Courier New",12),
                             text_color=cor, width=w, anchor="w").pack(
                    side="left", padx=2)

            # Clique para selecionar
            idx_cap = idx
            for widget in [row_f, row_i]:
                widget.bind("<Button-1>",
                           lambda e, i=idx_cap: self._selecionar(i))

            self._rows_widgets.append((row_f, row_i, cor_bg))

    def _bind_teclas(self):
        try:
            root = self.winfo_toplevel()
            root.bind("<Up>",   self._navegar_cima)
            root.bind("<Down>", self._navegar_baixo)
        except Exception:
            pass

    def _selecionar(self, idx):
        self._idx_selecionado = idx
        self._destacar()

    def _destacar(self):
        for i, (row_f, row_i, cor_bg) in enumerate(self._rows_widgets):
            if i == self._idx_selecionado:
                row_f.configure(fg_color=COR_ACENTO_LIGHT)
                row_i.configure(fg_color=COR_ACENTO_LIGHT)
            else:
                row_f.configure(fg_color=cor_bg)
                row_i.configure(fg_color=cor_bg)

    def _navegar_cima(self, event=None):
        if not self._rows_widgets:
            return
        if self._idx_selecionado > 0:
            self._idx_selecionado -= 1
        else:
            self._idx_selecionado = 0
        self._destacar()
        self._scroll_para_selecionado()

    def _navegar_baixo(self, event=None):
        if not self._rows_widgets:
            return
        n = len(self._rows_widgets)
        if self._idx_selecionado < n - 1:
            self._idx_selecionado += 1
        else:
            self._idx_selecionado = n - 1
        self._destacar()
        self._scroll_para_selecionado()

    def _scroll_para_selecionado(self):
        try:
            n = len(self._rows_widgets)
            if n > 0:
                frac = self._idx_selecionado / n
                self.scroll._parent_canvas.yview_moveto(frac)
        except Exception:
            pass

    def _atualizar_ranking(self, vendas):
        for w in self.scroll_rank.winfo_children():
            w.destroy()
        if not vendas:
            return
        try:
            ids = [v["id"] for v in vendas]
            conn = get_conn()
            rows = conn.execute(f"""
                SELECT nome_produto, SUM(quantidade) as qtde, SUM(total_item) as total
                FROM itens_venda WHERE venda_id IN ({','.join('?'*len(ids))})
                GROUP BY nome_produto ORDER BY total DESC LIMIT 8
            """, ids).fetchall()
            conn.close()
            for i, r in enumerate(rows):
                f = ctk.CTkFrame(self.scroll_rank,
                                 fg_color=COR_LINHA_PAR if i%2==0 else COR_CARD,
                                 corner_radius=4, height=26)
                f.pack(fill="x", pady=1)
                f.pack_propagate(False)
                ctk.CTkLabel(f, text=f"{i+1}. {r['nome_produto'][:25]}",
                             font=("Courier New",12), text_color=COR_TEXTO).pack(
                    side="left", padx=6, pady=4)
                ctk.CTkLabel(f, text=f"R$ {r['total']:.2f}",
                             font=("Courier New",12,"bold"),
                             text_color=COR_SUCESSO).pack(side="right", padx=6, pady=4)
        except Exception:
            pass

    def _desenhar_grafico(self, event=None):
        c = self.canvas_graf
        c.delete("all")
        dados = self._vendas_grafico
        if not dados:
            return

        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10:
            return

        max_val = max(v for _, v in dados) or 1
        n       = len(dados)
        ml      = 50; mb = 24; mt = 10
        aw      = W - ml - 10
        ah      = H - mb - mt
        bw      = (aw / n) * 0.6
        gap     = aw / n

        for i in range(5):
            y = mt + ah * i / 4
            c.create_line(ml, y, W-10, y, fill="#EEF0F4", width=1)
            c.create_text(ml-4, y, text=f"{max_val*(4-i)/4:.0f}",
                         anchor="e", font=("Courier New",9), fill=COR_TEXTO_SUB)

        for i, (dia, val) in enumerate(dados):
            x    = ml + gap * i + gap / 2
            h_px = (val / max_val) * ah
            y1   = mt + ah - h_px
            y2   = mt + ah
            c.create_rectangle(x-bw/2, y1, x+bw/2, y2,
                              fill=COR_ACENTO, outline="")
            if val > 0:
                c.create_text(x, y1-3, text=f"R${val:.0f}",
                             anchor="s", font=("Courier New",9), fill=COR_ACENTO)
            label = dia[8:] + "/" + dia[5:7]
            c.create_text(x, H-4, text=label, anchor="s",
                         font=("Courier New",9), fill=COR_TEXTO_SUB)

    def _exportar(self):
        from tkinter import filedialog, messagebox
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto","*.txt")],
            initialfile=f"relatorio_{date.today().strftime('%Y%m%d')}.txt")
        if not path:
            return
        vendas = self._vendas_filtradas or []
        total  = sum(v["total"] for v in vendas)
        with open(path, "w", encoding="utf-8") as f:
            f.write("="*56+"\n")
            f.write(f"{'RELATÓRIO DE VENDAS':^56}\n")
            f.write("="*56+"\n")
            f.write(f"Total vendas: R$ {total:.2f}\n")
            f.write(f"Qtd vendas:   {len(vendas)}\n")
            if self._filtro_forma != "TODAS":
                f.write(f"Filtro forma: {self._filtro_forma}\n")
            f.write("-"*56+"\n")
            f.write(f"{'#':<6}{'Data/Hora':<18}{'Forma':<20}{'Total':>10}\n")
            f.write("-"*56+"\n")
            for v in vendas:
                f.write(f"{v['id']:<6}{v['data_hora'][:16]:<18}"
                        f"{v['forma_pagamento'][:20]:<20}"
                        f"R$ {v['total']:>7.2f}\n")
        messagebox.showinfo("Exportado", f"Relatório salvo em:\n{path}")

    def _exportar_pdf(self):
        from tkinter import filedialog, messagebox
        import os, sys
        from datetime import datetime as dt

        vendas = self._vendas_atuais or []
        if not vendas:
            messagebox.showwarning("Aviso", "Nenhuma venda para exportar!")
            return

        # Datas do período
        ini = self.ent_ini.get()
        fim = self.ent_fim.get()
        periodo = f"{ini}" if ini == fim else f"{ini} a {fim}"

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF","*.pdf")],
            initialfile=f"relatorio_vendas_{dt.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not path:
            return

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

            T = lambda txt, size=10, bold=False, cor=colors.black, align=TA_LEFT:                 Paragraph(txt, ParagraphStyle("x", fontSize=size,
                          fontName="Helvetica-Bold" if bold else "Helvetica",
                          textColor=cor, alignment=align, spaceAfter=2, leading=size*1.4))

            # Tenta carregar logo
            base_dir = os.path.dirname(sys.executable) if getattr(sys,"frozen",False)                        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_dir, "logo.png")

            # Cabeçalho com logo
            if os.path.exists(logo_path):
                try:
                    from reportlab.platypus import Image
                    from banco.database import get_config
                    empresa  = get_config("empresa_nome") or "Padaria"
                    endereco = get_config("empresa_endereco") or ""
                    cnpj     = get_config("empresa_cnpj") or ""
                    fone     = get_config("empresa_fone") or ""
                    logo_img = Image(logo_path, width=3*cm, height=3*cm)
                    info_txt = f"""<b><font size=14 color="#8B1A1A">{empresa.upper()}</font></b><br/>
<font size=9 color="#6B7280">{endereco}</font><br/>
<font size=9 color="#6B7280">CNPJ: {cnpj}   Fone: {fone}</font>"""
                    cab_tab = Table([[logo_img,
                                     Paragraph(info_txt, ParagraphStyle("cab",
                                         alignment=TA_LEFT, leading=14))]],
                                   colWidths=[3.5*cm, 13.5*cm])
                    cab_tab.setStyle(TableStyle([
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                        ("LEFTPADDING",(0,0),(-1,-1),0),
                        ("TOPPADDING",(0,0),(-1,-1),0),
                        ("BOTTOMPADDING",(0,0),(-1,-1),0),
                    ]))
                    story.append(cab_tab)
                except Exception:
                    story.append(T("PADARIA DA LAINE", 16, True, COR_PDF, TA_CENTER))
            else:
                story.append(T("PADARIA DA LAINE", 16, True, COR_PDF, TA_CENTER))

            story.append(Spacer(1, 0.2*cm))
            story.append(HRFlowable(width="100%", thickness=2, color=COR_PDF))

            # Título
            tit = Table([[f"RELATÓRIO DE VENDAS — {periodo}"]],
                        colWidths=[17*cm])
            tit.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), COR_PDF),
                ("TEXTCOLOR",(0,0),(-1,-1), colors.white),
                ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),12),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("TOPPADDING",(0,0),(-1,-1),7),
                ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ]))
            story.append(tit)
            story.append(Spacer(1, 0.3*cm))

            # Agrupar vendas por forma
            formas_cfg = [
                ("DINHEIRO",              "DINHEIRO",         colors.HexColor("#059669")),
                ("CARTAO - DEBITO",       "CARTAO - DEBITO",  colors.HexColor("#1D4ED8")),
                ("PIX",                   "PIX",              colors.HexColor("#0891B2")),
                ("CARTAO - CREDITO",      "CARTAO - CREDITO", colors.HexColor("#7C3AED")),
                ("CARTAO - VALE ALIMENTACAO","VALE ALIMENTACAO",colors.HexColor("#B45309")),
            ]

            # Agrupa vendas por forma
            grupos = {}
            outras = []
            formas_conhecidas = {f[0] for f in formas_cfg}
            for v in vendas:
                forma = v["forma_pagamento"]
                matched = False
                for fk, fl, fc in formas_cfg:
                    if fk in forma.upper() or forma.upper() == fk:
                        if fk not in grupos:
                            grupos[fk] = {"label": fl, "cor": fc, "vendas": [], "total": 0}
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
                g = grupos[fk]
                subtotal = g["total"]
                total_geral += subtotal
                qtde_geral  += len(g["vendas"])

                story.append(Spacer(1, 0.2*cm))

                # Seção
                sec = Table([[f"{g['label']}  —  {len(g['vendas'])} vendas  —  R$ {subtotal:.2f}"]],
                            colWidths=[17*cm])
                sec.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,-1), g["cor"]),
                    ("TEXTCOLOR",(0,0),(-1,-1), colors.white),
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                    ("FONTSIZE",(0,0),(-1,-1),10),
                    ("TOPPADDING",(0,0),(-1,-1),5),
                    ("BOTTOMPADDING",(0,0),(-1,-1),5),
                    ("LEFTPADDING",(0,0),(-1,-1),10),
                ]))
                story.append(sec)

                # Cabeçalho tabela
                cab = Table([["#","Horário","Total","Troco","Desconto"]],
                            colWidths=[1.2*cm, 2.5*cm, 4*cm, 4*cm, 5.3*cm])
                cab.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#FEF3C7")),
                    ("TEXTCOLOR",(0,0),(-1,-1), colors.HexColor("#92400E")),
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                    ("FONTSIZE",(0,0),(-1,-1),8),
                    ("ALIGN",(2,0),(-1,-1),"RIGHT"),
                    ("TOPPADDING",(0,0),(-1,-1),3),
                    ("BOTTOMPADDING",(0,0),(-1,-1),3),
                    ("LEFTPADDING",(0,0),(-1,-1),4),
                    ("LINEBELOW",(0,0),(-1,-1),1, g["cor"]),
                ]))
                story.append(cab)

                # Linhas
                rows_data = []
                for idx, v in enumerate(g["vendas"]):
                    troco = f"R$ {v['troco']:.2f}" if v["troco"] > 0 else "—"
                    desc  = f"R$ {v['desconto']:.2f}" if v["desconto"] > 0 else "—"
                    rows_data.append([
                        str(idx+1),
                        v["data_hora"][11:16],
                        f"R$ {v['total']:.2f}",
                        troco,
                        desc
                    ])

                t = Table(rows_data, colWidths=[1.2*cm, 2.5*cm, 4*cm, 4*cm, 5.3*cm])
                t.setStyle(TableStyle([
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                    ("FONTSIZE",(0,0),(-1,-1),8),
                    ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, COR_CINZA]),
                    ("ALIGN",(2,0),(-1,-1),"RIGHT"),
                    ("TOPPADDING",(0,0),(-1,-1),3),
                    ("BOTTOMPADDING",(0,0),(-1,-1),3),
                    ("LEFTPADDING",(0,0),(-1,-1),4),
                    ("TEXTCOLOR",(2,0),(2,-1), g["cor"]),
                    ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
                ]))
                story.append(t)

                # Subtotal
                sub = Table([[f"Sub-Total: R$ {subtotal:.2f}"]], colWidths=[17*cm])
                sub.setStyle(TableStyle([
                    ("ALIGN",(0,0),(-1,-1),"RIGHT"),
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                    ("FONTSIZE",(0,0),(-1,-1),9),
                    ("TEXTCOLOR",(0,0),(-1,-1), g["cor"]),
                    ("TOPPADDING",(0,0),(-1,-1),3),
                    ("BOTTOMPADDING",(0,0),(-1,-1),3),
                    ("RIGHTPADDING",(0,0),(-1,-1),8),
                    ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#F9FAFB")),
                    ("LINEABOVE",(0,0),(-1,-1),0.5, colors.HexColor("#E5E7EB")),
                ]))
                story.append(sub)

            # Total geral
            story.append(Spacer(1, 0.4*cm))
            story.append(HRFlowable(width="100%", thickness=1.5, color=COR_PDF))
            tot = Table([[f"TOTAL GERAL: {qtde_geral} vendas  —  R$ {total_geral:.2f}"]],
                        colWidths=[17*cm])
            tot.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), COR_PDF),
                ("TEXTCOLOR",(0,0),(-1,-1), colors.white),
                ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),12),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("TOPPADDING",(0,0),(-1,-1),8),
                ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ]))
            story.append(tot)

            story.append(Spacer(1, 0.4*cm))
            story.append(T(f"Gerado em: {dt.now().strftime('%d/%m/%Y %H:%M')}  —  Padaria Da Laine",
                           8, align=TA_CENTER))

            doc.build(story)

            # Abre o PDF
            try:
                import subprocess
                subprocess.Popen(["start","",path], shell=True)
            except Exception:
                pass

            messagebox.showinfo("PDF Exportado", f"Relatório salvo em:\n{path}")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao gerar PDF:\n{e}")

    def _carregar_com_thread(self, ini, fim):
        def carregar():
            try:
                vendas = listar_vendas(ini, fim)
                self._vendas_atuais   = vendas
                self._vendas_filtradas = vendas
                self._idx_selecionado  = -1
                self._rows_widgets     = []
                self.after(0, lambda: self._aplicar_filtro())
            except Exception:
                self.after(0, lambda: self._popular([]))
        threading.Thread(target=carregar, daemon=True).start()

    def _carregar_hoje(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0,"end")
        self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fim.delete(0,"end")
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        self._carregar_com_thread(hoje, hoje)

    def _carregar_7dias(self):
        ini = (datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0,"end")
        self.ent_ini.insert(0, (date.today()-timedelta(days=7)).strftime("%d/%m/%Y"))
        self.ent_fim.delete(0,"end")
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        self._carregar_com_thread(ini, fim)

    def _carregar_30dias(self):
        ini = (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0,"end")
        self.ent_ini.insert(0, (date.today()-timedelta(days=30)).strftime("%d/%m/%Y"))
        self.ent_fim.delete(0,"end")
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
