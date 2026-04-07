"""
telas/dashboard.py — Dashboard Padaria Da Laine
Adaptado para o banco do sistema PDV
"""
import customtkinter as ctk
import tkinter as tk
from datetime import datetime, date, timedelta
import os, sys

# ── Cores ─────────────────────────────────────────────────────────
BG          = "#F4F6FA"
CARD        = "#FFFFFF"
AZUL        = "#B45309"   # marrom da padaria
AZUL_ESCURO = "#92400E"
AZUL_CLARO  = "#FEF3C7"
VERDE       = "#2E7D32"
VERDE_CLR   = "#E8F5E9"
VERMELHO    = "#C62828"
VERM_CLR    = "#FFEBEE"
LARANJA     = "#E65100"
LAR_CLR     = "#FFF3E0"
AMARELO     = "#F9A825"
CINZA_TXT   = "#546E7A"
BORDA       = "#DDE3ED"
TEXTO       = "#1A1A2E"

def _db():
    from banco.database import get_conn
    return get_conn()

class Dashboard(ctk.CTkFrame):
    def __init__(self, parent, usuario=None, **kw):
        super().__init__(parent, fg_color=BG, **kw)
        self.usuario   = usuario or {"nome": "Administrador", "id": 1}
        self._job_auto = None
        self._build()
        self._carregar()

    def destroy(self):
        if self._job_auto:
            try: self.after_cancel(self._job_auto)
            except: pass
        super().destroy()

    def _build(self):
        # Saudação + relógio
        topo = ctk.CTkFrame(self, fg_color="transparent", height=60)
        topo.pack(fill="x", padx=24, pady=(16,0))
        topo.pack_propagate(False)

        self.lbl_saudacao = ctk.CTkLabel(topo, text="",
            font=ctk.CTkFont("Georgia", 20, "bold"), text_color=TEXTO)
        self.lbl_saudacao.pack(side="left", anchor="w")

        frame_rel = ctk.CTkFrame(topo, fg_color=AZUL, corner_radius=12)
        frame_rel.pack(side="right", anchor="e")
        self.lbl_relogio = ctk.CTkLabel(frame_rel, text="",
            font=ctk.CTkFont("Courier New", 13, "bold"), text_color="white")
        self.lbl_relogio.pack(padx=16, pady=8)
        self._tick_relogio()

        self.lbl_data = ctk.CTkLabel(self, text="",
            font=ctk.CTkFont("Courier New", 11), text_color=CINZA_TXT)
        self.lbl_data.pack(anchor="w", padx=26, pady=(2,12))

        # Scroll
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Linha 1: 4 KPI cards
        self.row_kpi = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.row_kpi.pack(fill="x", padx=20, pady=(0,12))
        for i in range(4):
            self.row_kpi.columnconfigure(i, weight=1)

        # Linha 2: gráfico + status caixa
        self.row2 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.row2.pack(fill="x", padx=20, pady=(0,12))
        self.row2.columnconfigure(0, weight=3)
        self.row2.columnconfigure(1, weight=2)

        # Linha 3: últimas vendas + estoque crítico
        self.row3 = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.row3.pack(fill="x", padx=20, pady=(0,20))
        self.row3.columnconfigure(0, weight=3)
        self.row3.columnconfigure(1, weight=2)

        # Botão atualizar
        bar = ctk.CTkFrame(self.scroll, fg_color="transparent", height=36)
        bar.pack(fill="x", padx=20, pady=(0,8))
        bar.pack_propagate(False)
        ctk.CTkButton(bar, text="Atualizar",
            font=ctk.CTkFont("Courier New", 11), height=30,
            fg_color=AZUL_CLARO, text_color=AZUL,
            hover_color=BORDA, corner_radius=8, width=120,
            command=self._carregar).pack(side="right")
        self.lbl_att = ctk.CTkLabel(bar, text="",
            font=ctk.CTkFont("Courier New", 10), text_color=CINZA_TXT)
        self.lbl_att.pack(side="right", padx=10)

    def _carregar(self):
        dados = self._buscar_dados()
        self._kpis(dados)
        self._grafico(dados)
        self._status_caixa(dados)
        self._ultimas_vendas(dados)
        self._estoque_critico(dados)
        self._saudacao()
        self.lbl_att.configure(
            text=f"Atualizado: {datetime.now().strftime('%H:%M:%S')}")
        if self._job_auto:
            try: self.after_cancel(self._job_auto)
            except: pass
        self._job_auto = self.after(60000, self._carregar)

    def _buscar_dados(self):
        hoje  = date.today().isoformat()
        ontem = (date.today()-timedelta(days=1)).isoformat()
        seg   = (date.today()-timedelta(days=date.today().weekday())).isoformat()
        d = {
            "total_dia":0.0,"qtd_vendas":0,"ticket_medio":0.0,
            "total_ontem":0.0,"total_semana":0.0,
            "forma_pagamento":[],"caixa_aberto":False,"caixa_id":None,
            "caixa_abertura":0.0,"caixa_sangrias":0.0,"caixa_suprimentos":0.0,
            "ultimas_vendas":[],"estoque_critico":[],"vendas_hora":[0]*12,
            "meta_dia":2000.0,
        }
        try:
            conn = _db()
            # Vendas hoje — usando colunas do nosso banco
            r = conn.execute("""
                SELECT COUNT(*) qtd, COALESCE(SUM(total),0) total
                FROM vendas WHERE date(data_hora)=? AND status='CONCLUIDA'
            """, (hoje,)).fetchone()
            d["total_dia"]    = r[1]
            d["qtd_vendas"]   = r[0]
            d["ticket_medio"] = r[1]/r[0] if r[0]>0 else 0

            # Ontem
            r2 = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM vendas
                WHERE date(data_hora)=? AND status='CONCLUIDA'
            """, (ontem,)).fetchone()
            d["total_ontem"] = r2[0]

            # Semana
            r3 = conn.execute("""
                SELECT COALESCE(SUM(total),0) FROM vendas
                WHERE date(data_hora)>=? AND status='CONCLUIDA'
            """, (seg,)).fetchone()
            d["total_semana"] = r3[0]

            # Formas de pagamento
            fps = conn.execute("""
                SELECT forma_pagamento, COALESCE(SUM(total),0) total
                FROM vendas WHERE date(data_hora)=? AND status='CONCLUIDA'
                GROUP BY forma_pagamento ORDER BY total DESC
            """, (hoje,)).fetchall()
            d["forma_pagamento"] = [{"forma_pagamento":r[0],"total":r[1]} for r in fps]

            # Caixa aberto
            cx = conn.execute("""
                SELECT * FROM caixa WHERE status='ABERTO'
                ORDER BY id DESC LIMIT 1
            """).fetchone()
            if cx:
                d["caixa_aberto"]   = True
                d["caixa_id"]       = cx["id"]
                d["caixa_abertura"] = cx["valor_inicial"] or 0

            # Sangrias/suprimentos
            try:
                s = conn.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN tipo='SANGRIA' THEN valor END),0),
                        COALESCE(SUM(CASE WHEN tipo='SUPRIMENTO' THEN valor END),0)
                    FROM sangria_suprimento WHERE caixa_id=?
                """, (d["caixa_id"],)).fetchone() if d["caixa_id"] else None
                if s:
                    d["caixa_sangrias"]    = s[0]
                    d["caixa_suprimentos"] = s[1]
            except: pass

            # Últimas 6 vendas
            ult = conn.execute("""
                SELECT v.id, v.data_hora, v.total, v.forma_pagamento
                FROM vendas v
                WHERE date(v.data_hora)=? AND v.status='CONCLUIDA'
                ORDER BY v.id DESC LIMIT 6
            """, (hoje,)).fetchall()
            d["ultimas_vendas"] = [dict(r) for r in ult]

            # Estoque crítico
            crit = conn.execute("""
                SELECT nome, estoque_atual, estoque_minimo, unidade
                FROM produtos WHERE ativo=1
                  AND estoque_atual <= estoque_minimo
                  AND estoque_minimo > 0
                ORDER BY (estoque_atual - estoque_minimo) LIMIT 6
            """).fetchall()
            d["estoque_critico"] = [dict(r) for r in crit]

            # Vendas por hora
            horas = conn.execute("""
                SELECT CAST(strftime('%H', data_hora) AS INTEGER) hora,
                       COALESCE(SUM(total),0) total
                FROM vendas WHERE date(data_hora)=? AND status='CONCLUIDA'
                GROUP BY hora
            """, (hoje,)).fetchall()
            for h in horas:
                idx = h[0]-8
                if 0 <= idx < 12:
                    d["vendas_hora"][idx] = h[1]

            conn.close()
        except Exception as e:
            print(f"Dashboard erro: {e}")
        return d

    def _kpis(self, d):
        for w in self.row_kpi.winfo_children(): w.destroy()
        var = d["total_dia"]-d["total_ontem"]
        pct = (var/d["total_ontem"]*100) if d["total_ontem"]>0 else 0
        saldo = d["caixa_abertura"]+d["total_dia"]+d["caixa_suprimentos"]-d["caixa_sangrias"]
        prog  = min(100, d["total_dia"]/d["meta_dia"]*100)

        def fmt(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")

        kpis = [
            {"i":"💰","t":"Vendas Hoje","v":fmt(d["total_dia"]),
             "s":f"{'▲' if var>=0 else '▼'} {fmt(abs(var))} vs ontem ({pct:+.1f}%)",
             "cs":VERDE if var>=0 else VERMELHO,"ca":AZUL,"cb":AZUL_CLARO,
             "bar":(prog,AZUL)},
            {"i":"🛒","t":"Vendas Realizadas","v":str(d["qtd_vendas"]),
             "s":f"Ticket médio: {fmt(d['ticket_medio'])}",
             "cs":CINZA_TXT,"ca":VERDE,"cb":VERDE_CLR,"bar":None},
            {"i":"🏦","t":"Saldo em Caixa","v":fmt(saldo),
             "s":"Caixa aberto" if d["caixa_aberto"] else "Caixa fechado",
             "cs":VERDE if d["caixa_aberto"] else LARANJA,
             "ca":LARANJA,"cb":LAR_CLR,"bar":None},
            {"i":"📅","t":"Vendas na Semana","v":fmt(d["total_semana"]),
             "s":f"Meta: {fmt(d['meta_dia'])}",
             "cs":CINZA_TXT,"ca":AMARELO,"cb":"#FFFDE7","bar":None},
        ]
        for i,k in enumerate(kpis):
            c = ctk.CTkFrame(self.row_kpi, fg_color=CARD, corner_radius=16,
                             border_width=1, border_color=BORDA)
            c.grid(row=0, column=i, padx=(0 if i==0 else 8,0), sticky="nsew", ipady=4)
            t = ctk.CTkFrame(c, fg_color="transparent")
            t.pack(fill="x", padx=16, pady=(14,0))
            b = ctk.CTkFrame(t, fg_color=k["cb"], corner_radius=10, width=40, height=40)
            b.pack(side="left"); b.pack_propagate(False)
            ctk.CTkLabel(b, text=k["i"], font=ctk.CTkFont(size=20)).pack(expand=True)
            ctk.CTkLabel(t, text=k["t"], font=ctk.CTkFont("Georgia",11,"bold"),
                         text_color=CINZA_TXT).pack(side="left", padx=10)
            ctk.CTkLabel(c, text=k["v"], font=ctk.CTkFont("Georgia",22,"bold"),
                         text_color=k["ca"]).pack(anchor="w", padx=16, pady=(6,2))
            ctk.CTkLabel(c, text=k["s"], font=ctk.CTkFont("Courier New",10),
                         text_color=k["cs"]).pack(anchor="w", padx=16, pady=(0,6))
            if k["bar"]:
                pb = ctk.CTkProgressBar(c, height=6, corner_radius=4,
                                        fg_color=BORDA, progress_color=k["bar"][1])
                pb.pack(fill="x", padx=16, pady=(0,10))
                pb.set(k["bar"][0]/100)

    def _grafico(self, d):
        for w in self.row2.winfo_children():
            if getattr(w,"_g",False): w.destroy()
        card = ctk.CTkFrame(self.row2, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=BORDA)
        card._g = True
        card.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(card, text="Vendas por Hora — Hoje",
                     font=ctk.CTkFont("Georgia",13,"bold"),
                     text_color=AZUL).pack(anchor="w", padx=18, pady=(14,4))
        canvas = tk.Canvas(card, bg=CARD, highlightthickness=0, height=180)
        canvas.pack(fill="x", padx=18, pady=(0,14))
        def draw(e=None):
            canvas.delete("all")
            W=canvas.winfo_width(); H=canvas.winfo_height()
            if W<10: return
            dados=d["vendas_hora"]; mx=max(dados) if max(dados)>0 else 1
            n=12; ml=50; mb=30; mt=10; aw=W-ml-10; ah=H-mb-mt; bw=(aw/n)*.55; gp=aw/n
            for i in range(5):
                y=mt+ah*i/4; canvas.create_line(ml,y,W-10,y,fill="#EEF0F4")
                canvas.create_text(ml-6,y,text=f"{mx*(4-i)/4:.0f}",
                                   anchor="e",font=("Courier New",8),fill=CINZA_TXT)
            ha=datetime.now().hour
            for i,v in enumerate(dados):
                h=8+i; x=ml+gp*i+gp/2
                hp=(v/mx)*ah if mx>0 else 0
                y1=mt+ah-hp; y2=mt+ah
                cor=AZUL if h==ha else "#F0C070"
                if v==0: cor="#F5F5F0"
                if hp>8:
                    canvas.create_rectangle(x-bw/2,y1+4,x+bw/2,y2,fill=cor,outline="")
                    canvas.create_oval(x-bw/2,y1,x+bw/2,y1+8,fill=cor,outline="")
                elif hp>0:
                    canvas.create_rectangle(x-bw/2,y1,x+bw/2,y2,fill=cor,outline="")
                if v>0: canvas.create_text(x,y1-4,text=f"{v:.0f}",
                                           anchor="s",font=("Courier New",7,"bold"),fill=AZUL_ESCURO)
                canvas.create_text(x,H-6,text=f"{h:02d}h",
                                   anchor="s",font=("Courier New",8),fill=CINZA_TXT)
        canvas.bind("<Configure>", draw)
        canvas.after(50, draw)

    def _status_caixa(self, d):
        for w in self.row2.winfo_children():
            if getattr(w,"_c",False): w.destroy()
        card = ctk.CTkFrame(self.row2, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=BORDA)
        card._c = True
        card.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(card, text="Status do Caixa",
                     font=ctk.CTkFont("Georgia",13,"bold"),
                     text_color=AZUL).pack(anchor="w", padx=18, pady=(14,8))
        cor = VERDE if d["caixa_aberto"] else LARANJA
        bg  = VERDE_CLR if d["caixa_aberto"] else LAR_CLR
        txt = "ABERTO" if d["caixa_aberto"] else "FECHADO"
        bg_f = ctk.CTkFrame(card, fg_color=bg, corner_radius=12)
        bg_f.pack(fill="x", padx=18, pady=(0,10))
        ctk.CTkLabel(bg_f, text=txt,
                     font=ctk.CTkFont("Georgia",16,"bold"),
                     text_color=cor).pack(pady=10)
        saldo = d["caixa_abertura"]+d["total_dia"]+d["caixa_suprimentos"]-d["caixa_sangrias"]
        for lbl,val in [
            ("Fundo inicial", f"R$ {d['caixa_abertura']:.2f}"),
            ("+ Vendas",      f"R$ {d['total_dia']:.2f}"),
            ("+ Suprimentos", f"R$ {d['caixa_suprimentos']:.2f}"),
            ("- Sangrias",    f"R$ {d['caixa_sangrias']:.2f}"),
        ]:
            f = ctk.CTkFrame(card, fg_color="transparent", height=26)
            f.pack(fill="x", padx=18); f.pack_propagate(False)
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont("Courier New",10),
                         text_color=CINZA_TXT).pack(side="left")
            ctk.CTkLabel(f, text=val, font=ctk.CTkFont("Courier New",10,"bold"),
                         text_color=TEXTO).pack(side="right")
        ctk.CTkFrame(card, fg_color=BORDA, height=1).pack(fill="x", padx=18, pady=6)
        f2 = ctk.CTkFrame(card, fg_color="transparent", height=30)
        f2.pack(fill="x", padx=18); f2.pack_propagate(False)
        ctk.CTkLabel(f2, text="Saldo esperado",
                     font=ctk.CTkFont("Georgia",11,"bold"),
                     text_color=TEXTO).pack(side="left")
        ctk.CTkLabel(f2, text=f"R$ {saldo:.2f}",
                     font=ctk.CTkFont("Georgia",13,"bold"),
                     text_color=AZUL).pack(side="right")

    def _ultimas_vendas(self, d):
        for w in self.row3.winfo_children():
            if getattr(w,"_v",False): w.destroy()
        card = ctk.CTkFrame(self.row3, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=BORDA)
        card._v = True
        card.grid(row=0, column=0, sticky="nsew", padx=(0,8))
        ctk.CTkLabel(card, text="Últimas Vendas do Dia",
                     font=ctk.CTkFont("Georgia",13,"bold"),
                     text_color=AZUL).pack(anchor="w", padx=18, pady=(14,6))
        h = ctk.CTkFrame(card, fg_color=AZUL_CLARO, corner_radius=8, height=28)
        h.pack(fill="x", padx=18, pady=(0,4)); h.pack_propagate(False)
        for col,w2 in [("Nº",40),("Hora",60),("Pagamento",120),("Total",80)]:
            ctk.CTkLabel(h, text=col, font=ctk.CTkFont("Courier New",9,"bold"),
                         text_color=AZUL, width=w2).pack(side="left", padx=4)
        if not d["ultimas_vendas"]:
            ctk.CTkLabel(card, text="Nenhuma venda hoje.",
                         font=ctk.CTkFont("Courier New",11),
                         text_color=CINZA_TXT).pack(pady=20)
        else:
            for i,v in enumerate(d["ultimas_vendas"]):
                bg = "#F8FAFF" if i%2==0 else CARD
                l = ctk.CTkFrame(card, fg_color=bg, corner_radius=6, height=30)
                l.pack(fill="x", padx=18, pady=1); l.pack_propagate(False)
                hora = v["data_hora"][11:16] if v.get("data_hora") else "—"
                for txt,w2,cor,bold in [
                    (f"#{v['id']}",40,CINZA_TXT,False),
                    (hora,60,TEXTO,False),
                    (v.get("forma_pagamento","—")[:16],120,CINZA_TXT,False),
                    (f"R$ {v['total']:.2f}",80,VERDE,True),
                ]:
                    ctk.CTkLabel(l, text=txt,
                                 font=ctk.CTkFont("Courier New",10,
                                                  "bold" if bold else "normal"),
                                 text_color=cor, width=w2).pack(side="left", padx=4)

    def _estoque_critico(self, d):
        for w in self.row3.winfo_children():
            if getattr(w,"_e",False): w.destroy()
        card = ctk.CTkFrame(self.row3, fg_color=CARD, corner_radius=16,
                            border_width=1, border_color=BORDA)
        card._e = True
        card.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(card, text="Estoque Crítico",
                     font=ctk.CTkFont("Georgia",13,"bold"),
                     text_color=VERMELHO).pack(anchor="w", padx=18, pady=(14,8))
        if not d["estoque_critico"]:
            f = ctk.CTkFrame(card, fg_color=VERDE_CLR, corner_radius=10)
            f.pack(fill="x", padx=18, pady=4)
            ctk.CTkLabel(f, text="Todos os produtos OK!",
                         font=ctk.CTkFont("Georgia",12,"bold"),
                         text_color=VERDE).pack(pady=16)
        else:
            for p in d["estoque_critico"]:
                pct = (p["estoque_atual"]/p["estoque_minimo"]) if p["estoque_minimo"]>0 else 0
                cor = VERMELHO if pct<=0.25 else (LARANJA if pct<=0.75 else AMARELO)
                bg  = VERM_CLR if pct<=0.25 else (LAR_CLR if pct<=0.75 else "#FFFDE7")
                item = ctk.CTkFrame(card, fg_color=bg, corner_radius=10)
                item.pack(fill="x", padx=18, pady=3)
                t = ctk.CTkFrame(item, fg_color="transparent")
                t.pack(fill="x", padx=10, pady=(6,2))
                ctk.CTkLabel(t, text=p["nome"],
                             font=ctk.CTkFont("Georgia",11,"bold"),
                             text_color=TEXTO).pack(side="left")
                ctk.CTkLabel(t, text=f"{p['estoque_atual']:.1f}/{p['estoque_minimo']:.1f} {p['unidade']}",
                             font=ctk.CTkFont("Courier New",10,"bold"),
                             text_color=cor).pack(side="right")
                pb = ctk.CTkProgressBar(item, height=5, corner_radius=3,
                                        fg_color="#E0E0E0", progress_color=cor)
                pb.pack(fill="x", padx=10, pady=(0,6))
                pb.set(min(1, pct))

    def _saudacao(self):
        h = datetime.now().hour
        s = "Bom dia" if h<12 else ("Boa tarde" if h<18 else "Boa noite")
        nome = self.usuario.get("nome","").split()[0]
        self.lbl_saudacao.configure(text=f"{s}, {nome}!")
        self.lbl_data.configure(
            text=datetime.now().strftime("  %d/%m/%Y  —  %A").capitalize())

    def _tick_relogio(self):
        self.lbl_relogio.configure(
            text=datetime.now().strftime("  %H:%M:%S"))
        self.after(1000, self._tick_relogio)
