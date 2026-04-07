"""telas/relatorios.py — Relatórios — Tema Branco"""
import customtkinter as ctk
from datetime import datetime, timedelta
from tema import *
from banco.database import listar_vendas

class TelaRelatorios(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        self._build_header(); self._build_corpo(); self._carregar_hoje()

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False); hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="📈  Relatórios de Vendas",font=FONTE_TITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=24,pady=18,sticky="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=24,sticky="e")
        for txt,cmd in[("Hoje",self._carregar_hoje),("7 dias",self._carregar_7dias),("30 dias",self._carregar_30dias),("Tudo",self._carregar_tudo)]:
            ctk.CTkButton(bf,text=txt,width=90,font=FONTE_BTN,fg_color=COR_ACENTO_LIGHT,hover_color=COR_BORDA,text_color=COR_ACENTO,border_width=1,border_color=COR_ACENTO,command=cmd).pack(side="left",padx=4)

    def _build_corpo(self):
        corpo=ctk.CTkFrame(self,fg_color="transparent"); corpo.grid(row=1,column=0,sticky="nsew",padx=16,pady=16)
        corpo.grid_columnconfigure(0,weight=1); corpo.grid_rowconfigure(1,weight=1)
        cards_frame=ctk.CTkFrame(corpo,fg_color="transparent"); cards_frame.grid(row=0,column=0,sticky="ew"); cards_frame.grid_columnconfigure((0,1,2,3),weight=1)
        self.card_total=self._card(cards_frame,0,"💰 Total Vendas","R$ 0,00",COR_ACENTO)
        self.card_qtde=self._card(cards_frame,1,"🧾 Nº de Vendas","0",COR_SUCESSO)
        self.card_ticket=self._card(cards_frame,2,"🎫 Ticket Médio","R$ 0,00",COR_INFO)
        self.card_dinheiro=self._card(cards_frame,3,"💵 Em Dinheiro","R$ 0,00","#8B5CF6")
        frame=ctk.CTkFrame(corpo,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=1,column=0,sticky="nsew",pady=(12,0)); frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        cols=["#","Data/Hora","Total","Desconto","Forma Pagto","Troco","Status NFC-e"]
        pesos=[1,4,2,2,2,2,2]
        cab=ctk.CTkFrame(frame,fg_color=COR_ACENTO_LIGHT,corner_radius=8,height=36)
        cab.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,0)); cab.grid_propagate(False)
        for i,(c,p) in enumerate(zip(cols,pesos)):
            cab.grid_columnconfigure(i,weight=p)
            ctk.CTkLabel(cab,text=c,font=("Courier New",10,"bold"),text_color=COR_ACENTO).grid(row=0,column=i,padx=6,pady=6,sticky="w")
        self.scroll=ctk.CTkScrollableFrame(frame,fg_color="transparent")
        self.scroll.grid(row=1,column=0,sticky="nsew",padx=8,pady=8); self.scroll.grid_columnconfigure(0,weight=1)

    def _card(self,parent,col,titulo,valor,cor):
        card=ctk.CTkFrame(parent,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        card.grid(row=0,column=col,padx=6,sticky="ew")
        ctk.CTkLabel(card,text=titulo,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        lbl=ctk.CTkLabel(card,text=valor,font=FONTE_CARD_VAL,text_color=cor); lbl.pack(pady=(0,14)); return lbl

    def _popular(self,vendas):
        for w in self.scroll.winfo_children(): w.destroy()
        if not vendas:
            ctk.CTkLabel(self.scroll,text="Nenhuma venda no período.",font=FONTE_LABEL,text_color=COR_TEXTO_SUB).grid(pady=40)
            for lbl,v in[(self.card_total,"R$ 0,00"),(self.card_qtde,"0"),(self.card_ticket,"R$ 0,00"),(self.card_dinheiro,"R$ 0,00")]: lbl.configure(text=v); return
        total_geral=sum(v["total"] for v in vendas); dinheiro=sum(v["total"] for v in vendas if v["forma_pagamento"]=="DINHEIRO"); ticket=total_geral/len(vendas)
        self.card_total.configure(text=f"R$ {total_geral:.2f}"); self.card_qtde.configure(text=str(len(vendas)))
        self.card_ticket.configure(text=f"R$ {ticket:.2f}"); self.card_dinheiro.configure(text=f"R$ {dinheiro:.2f}")
        pesos=[1,4,2,2,2,2,2]
        for idx,v in enumerate(vendas):
            cor_bg=COR_LINHA_PAR if idx%2==0 else COR_CARD
            row_f=ctk.CTkFrame(self.scroll,fg_color=cor_bg,corner_radius=6,height=36)
            row_f.grid(row=idx,column=0,sticky="ew",pady=1); row_f.grid_propagate(False)
            for i,p in enumerate(pesos): row_f.grid_columnconfigure(i,weight=p)
            nfce_cor=COR_SUCESSO if v["nfce_status"]=="EMITIDA" else COR_PERIGO
            vals=[str(v["id"]),v["data_hora"][:16],f'R$ {v["total"]:.2f}',f'R$ {v["desconto"]:.2f}',v["forma_pagamento"],f'R$ {v["troco"]:.2f}',v["nfce_status"]]
            cores=[COR_TEXTO_SUB,COR_TEXTO,COR_SUCESSO,COR_PERIGO,COR_TEXTO,COR_TEXTO_SUB,nfce_cor]
            for i,(val,cor) in enumerate(zip(vals,cores)):
                ctk.CTkLabel(row_f,text=val,font=FONTE_SMALL,text_color=cor).grid(row=0,column=i,padx=6,sticky="w")

    def _carregar_hoje(self):
        hoje=datetime.now().strftime("%Y-%m-%d"); self._popular(listar_vendas(hoje,hoje))
    def _carregar_7dias(self):
        ini=(datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d"); fim=datetime.now().strftime("%Y-%m-%d"); self._popular(listar_vendas(ini,fim))
    def _carregar_30dias(self):
        ini=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"); fim=datetime.now().strftime("%Y-%m-%d"); self._popular(listar_vendas(ini,fim))
    def _carregar_tudo(self): self._popular(listar_vendas())
