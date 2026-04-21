"""telas/relatorios.py — Relatórios Completos — Tema Branco"""
import customtkinter as ctk
import tkinter as tk
from datetime import datetime, timedelta, date
from tema import *
from banco.database import listar_vendas, get_conn

class TelaRelatorios(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_corpo()
        self._carregar_hoje()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="📈  Relatórios de Vendas",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")

        # Filtro por data personalizada
        ctk.CTkLabel(bf, text="De:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0,4))
        self.ent_ini = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                        fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.ent_ini.pack(side="left", padx=(0,8))
        self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))

        ctk.CTkLabel(bf, text="Até:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0,4))
        self.ent_fim = ctk.CTkEntry(bf, width=100, font=FONTE_LABEL,
                        fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.ent_fim.pack(side="left", padx=(0,8))
        self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))

        for txt, cmd in [("Hoje", self._carregar_hoje),
                         ("7 dias", self._carregar_7dias),
                         ("30 dias", self._carregar_30dias),
                         ("🔍 Filtrar", self._carregar_personalizado)]:
            ctk.CTkButton(bf, text=txt, width=80, font=FONTE_BTN,
                          fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                          text_color="white", command=cmd).pack(side="left", padx=3)

        ctk.CTkButton(bf, text="📄 Exportar", width=90, font=FONTE_BTN,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white", command=self._exportar).pack(side="left", padx=3)

    def _build_corpo(self):
        corpo = ctk.CTkFrame(self, fg_color="transparent")
        corpo.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(2, weight=1)

        # Cards KPI
        cards = ctk.CTkFrame(corpo, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew")
        cards.grid_columnconfigure((0,1,2,3,4), weight=1)

        self.card_total    = self._card(cards, 0, "💰 Total Vendas",   "R$ 0,00", COR_ACENTO)
        self.card_qtde     = self._card(cards, 1, "🧾 Nº Vendas",      "0",       COR_SUCESSO)
        self.card_ticket   = self._card(cards, 2, "🎫 Ticket Médio",   "R$ 0,00", COR_INFO)
        self.card_dinheiro = self._card(cards, 3, "💵 Dinheiro",       "R$ 0,00", "#8B5CF6")
        self.card_pix      = self._card(cards, 4, "📱 PIX",            "R$ 0,00", "#0891B2")

        # Linha 2: gráfico + ranking
        linha2 = ctk.CTkFrame(corpo, fg_color="transparent")
        linha2.grid(row=1, column=0, sticky="ew", pady=(12,0))
        linha2.grid_columnconfigure(0, weight=3)
        linha2.grid_columnconfigure(1, weight=2)

        # Gráfico de barras por dia
        frame_graf = ctk.CTkFrame(linha2, fg_color=COR_CARD, corner_radius=12,
                                  border_width=1, border_color=COR_BORDA)
        frame_graf.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(frame_graf, text="📊  Vendas por Dia",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(anchor="w", padx=16, pady=(12,4))
        self.canvas_graf = tk.Canvas(frame_graf, bg=COR_CARD, highlightthickness=0, height=140)
        self.canvas_graf.pack(fill="x", padx=16, pady=(0,12))
        self.canvas_graf.bind("<Configure>", self._desenhar_grafico)

        # Ranking produtos
        frame_rank = ctk.CTkFrame(linha2, fg_color=COR_CARD, corner_radius=12,
                                  border_width=1, border_color=COR_BORDA)
        frame_rank.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(frame_rank, text="🏆  Mais Vendidos",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(anchor="w", padx=16, pady=(12,4))
        self.scroll_rank = ctk.CTkScrollableFrame(frame_rank, fg_color="transparent", height=120)
        self.scroll_rank.pack(fill="both", expand=True, padx=12, pady=(0,12))

        # Tabela de vendas
        frame = ctk.CTkFrame(corpo, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=2, column=0, sticky="nsew", pady=(12,0))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        cols  = ["#","Data/Hora","Total","Desconto","Forma Pagto","Troco","NFC-e"]
        pesos = [1,4,2,2,3,2,2]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.grid_propagate(False)
        for i,(c,p) in enumerate(zip(cols,pesos)):
            cab.grid_columnconfigure(i, weight=p)
            ctk.CTkLabel(cab, text=c, font=("Courier New",14,"bold"),
                         text_color=COR_ACENTO).grid(row=0,column=i,padx=6,pady=6,sticky="w")

        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Guarda dados para o gráfico
        self._vendas_grafico = []
        self._ranking = []

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=4, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(12,2))
        lbl = ctk.CTkLabel(card, text=valor,
                           font=("Georgia",19,"bold"), text_color=cor)
        lbl.pack(pady=(0,12))
        return lbl

    def _popular(self, vendas):
        for w in self.scroll.winfo_children(): w.destroy()

        if not vendas:
            ctk.CTkLabel(self.scroll, text="Nenhuma venda no período.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(pady=40)
            for lbl, v in [(self.card_total,"R$ 0,00"),(self.card_qtde,"0"),
                           (self.card_ticket,"R$ 0,00"),(self.card_dinheiro,"R$ 0,00"),
                           (self.card_pix,"R$ 0,00")]:
                lbl.configure(text=v)
            self._vendas_grafico = []
            self._ranking = []
            self._atualizar_ranking()
            return

        total_geral = sum(v["total"] for v in vendas)
        dinheiro    = sum(v["total"] for v in vendas if "DINHEIRO" in v["forma_pagamento"])
        pix         = sum(v["total"] for v in vendas if "PIX" in v["forma_pagamento"])
        ticket      = total_geral / len(vendas)

        self.card_total.configure(text=f"R$ {total_geral:.2f}")
        self.card_qtde.configure(text=str(len(vendas)))
        self.card_ticket.configure(text=f"R$ {ticket:.2f}")
        self.card_dinheiro.configure(text=f"R$ {dinheiro:.2f}")
        self.card_pix.configure(text=f"R$ {pix:.2f}")

        # Agrupa por dia para o gráfico
        por_dia = {}
        for v in vendas:
            dia = v["data_hora"][:10]
            por_dia[dia] = por_dia.get(dia, 0) + v["total"]
        self._vendas_grafico = sorted(por_dia.items())
        self._desenhar_grafico()

        # Ranking de produtos
        self._carregar_ranking(vendas)

        # Tabela
        pesos = [1,4,2,2,3,2,2]
        for idx, v in enumerate(vendas):
            cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            row_f = ctk.CTkFrame(self.scroll, fg_color=cor_bg, corner_radius=6, height=34)
            row_f.grid(row=idx, column=0, sticky="ew", pady=1)
            row_f.grid_propagate(False)
            for i, p in enumerate(pesos): row_f.grid_columnconfigure(i, weight=p)
            nfce_cor = COR_SUCESSO if v["nfce_status"] == "EMITIDA" else COR_PERIGO
            vals = [str(v["id"]), v["data_hora"][:16],
                    f'R$ {v["total"]:.2f}', f'R$ {v["desconto"]:.2f}',
                    v["forma_pagamento"], f'R$ {v["troco"]:.2f}', v["nfce_status"]]
            cores = [COR_TEXTO_SUB,COR_TEXTO,COR_SUCESSO,COR_PERIGO,COR_TEXTO,COR_TEXTO_SUB,nfce_cor]
            for i,(val,cor) in enumerate(zip(vals,cores)):
                ctk.CTkLabel(row_f, text=val, font=FONTE_SMALL,
                             text_color=cor).grid(row=0,column=i,padx=6,sticky="w")

    def _desenhar_grafico(self, event=None):
        c = self.canvas_graf
        c.delete("all")
        dados = self._vendas_grafico
        if not dados: return

        W = c.winfo_width()
        H = c.winfo_height()
        if W < 10: return

        max_val = max(v for _, v in dados) or 1
        n = len(dados)
        ml = 50; mb = 24; mt = 10
        aw = W - ml - 10
        ah = H - mb - mt
        bw = (aw / n) * 0.6
        gap = aw / n

        for i in range(5):
            y = mt + ah * i / 4
            c.create_line(ml, y, W-10, y, fill="#EEF0F4", width=1)
            c.create_text(ml-4, y, text=f"{max_val*(4-i)/4:.0f}",
                         anchor="e", font=("Courier New",9), fill=COR_TEXTO_SUB)

        for i, (dia, val) in enumerate(dados):
            x = ml + gap * i + gap / 2
            h_px = (val / max_val) * ah
            y1 = mt + ah - h_px
            y2 = mt + ah
            c.create_rectangle(x-bw/2, y1, x+bw/2, y2,
                              fill=COR_ACENTO, outline="")
            if val > 0:
                c.create_text(x, y1-3, text=f"R${val:.0f}",
                             anchor="s", font=("Courier New",9), fill=COR_ACENTO)
            label = dia[8:] + "/" + dia[5:7]
            c.create_text(x, H-4, text=label, anchor="s",
                         font=("Courier New",9), fill=COR_TEXTO_SUB)

    def _carregar_ranking(self, vendas):
        # Busca ranking de produtos do período
        for w in self.scroll_rank.winfo_children(): w.destroy()
        try:
            ids = [v["id"] for v in vendas]
            if not ids: return
            conn = get_conn()
            rows = conn.execute(f"""
                SELECT nome_produto, SUM(quantidade) as qtde, SUM(total_item) as total
                FROM itens_venda WHERE venda_id IN ({','.join('?'*len(ids))})
                GROUP BY nome_produto ORDER BY total DESC LIMIT 8
            """, ids).fetchall()
            conn.close()
            for i, r in enumerate(rows):
                f = ctk.CTkFrame(self.scroll_rank, fg_color=COR_LINHA_PAR if i%2==0 else COR_CARD,
                                 corner_radius=4, height=26)
                f.pack(fill="x", pady=1)
                f.pack_propagate(False)
                ctk.CTkLabel(f, text=f"{i+1}. {r['nome_produto'][:25]}",
                             font=("Courier New",14), text_color=COR_TEXTO).pack(side="left", padx=6)
                ctk.CTkLabel(f, text=f"R$ {r['total']:.2f}",
                             font=("Courier New",14,"bold"), text_color=COR_SUCESSO).pack(side="right", padx=6)
        except Exception:
            pass

    def _atualizar_ranking(self):
        for w in self.scroll_rank.winfo_children(): w.destroy()

    def _exportar(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto","*.txt")],
            initialfile=f"relatorio_{date.today().strftime('%Y%m%d')}.txt")
        if not path: return
        # Gera relatório baseado nos dados atuais
        vendas = self._vendas_atuais if hasattr(self, "_vendas_atuais") else []
        total = sum(v["total"] for v in vendas)
        with open(path, "w", encoding="utf-8") as f:
            f.write("="*48+"\n")
            f.write(f"{'RELATÓRIO DE VENDAS':^48}\n")
            f.write("="*48+"\n")
            f.write(f"Total vendas: R$ {total:.2f}\n")
            f.write(f"Qtd vendas:   {len(vendas)}\n")
            f.write("-"*48+"\n")
            for v in vendas:
                f.write(f"{v['data_hora'][:16]}  {v['forma_pagamento']:<15}  R$ {v['total']:.2f}\n")
        from tkinter import messagebox
        messagebox.showinfo("Exportado", f"Relatório salvo em:\n{path}")

    def _carregar_hoje(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0,"end"); self.ent_ini.insert(0, date.today().strftime("%d/%m/%Y"))
        self.ent_fim.delete(0,"end"); self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        vendas = listar_vendas(hoje, hoje)
        self._vendas_atuais = vendas
        self._popular(vendas)

    def _carregar_7dias(self):
        ini = (datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        self.ent_ini.delete(0,"end"); self.ent_ini.insert(0, (date.today()-timedelta(days=7)).strftime("%d/%m/%Y"))
        self.ent_fim.delete(0,"end"); self.ent_fim.insert(0, date.today().strftime("%d/%m/%Y"))
        vendas = listar_vendas(ini, fim)
        self._vendas_atuais = vendas
        self._popular(vendas)

    def _carregar_30dias(self):
        ini = (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d")
        fim = datetime.now().strftime("%Y-%m-%d")
        vendas = listar_vendas(ini, fim)
        self._vendas_atuais = vendas
        self._popular(vendas)

    def _carregar_personalizado(self):
        try:
            ini = datetime.strptime(self.ent_ini.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            fim = datetime.strptime(self.ent_fim.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Data inválida! Use DD/MM/AAAA")
            return
        vendas = listar_vendas(ini, fim)
        self._vendas_atuais = vendas
        self._popular(vendas)
