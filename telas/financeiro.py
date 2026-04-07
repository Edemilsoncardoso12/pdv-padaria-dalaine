"""telas/financeiro.py — Financeiro — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn

CATEGORIAS=["Aluguel","Energia","Agua","Internet","Ingredientes","Embalagens","Salarios","Impostos","Manutencao","Outros"]

def inicializar_financeiro():
    conn=get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS lancamentos(id INTEGER PRIMARY KEY AUTOINCREMENT,tipo TEXT,categoria TEXT,descricao TEXT,valor REAL,data TEXT DEFAULT(date(\'now\',\'localtime\')),forma_pagamento TEXT DEFAULT \'DINHEIRO\',status TEXT DEFAULT \'PAGO\',observacao TEXT DEFAULT \'\',criado_em TEXT DEFAULT(datetime(\'now\',\'localtime\')))")
    conn.commit(); conn.close()

def resumo_periodo(data_ini,data_fim):
    conn=get_conn()
    rv=conn.execute("SELECT COALESCE(SUM(valor),0) FROM lancamentos WHERE tipo=\'RECEITA\' AND data BETWEEN ? AND ?",(data_ini,data_fim)).fetchone()[0]
    vv=conn.execute("SELECT COALESCE(SUM(total),0) FROM vendas WHERE date(data_hora) BETWEEN ? AND ? AND status=\'CONCLUIDA\'",(data_ini,data_fim)).fetchone()[0]
    dv=conn.execute("SELECT COALESCE(SUM(valor),0) FROM lancamentos WHERE tipo=\'DESPESA\' AND data BETWEEN ? AND ?",(data_ini,data_fim)).fetchone()[0]
    conn.close()
    return {"receitas_vendas":vv,"receitas_manuais":rv,"total_receitas":rv+vv,"despesas":dv,"saldo":rv+vv-dv}

def listar_lancamentos(data_ini=None,data_fim=None):
    conn=get_conn()
    q="SELECT * FROM lancamentos WHERE 1=1"; p=[]
    if data_ini: q+=" AND data>=?"; p.append(data_ini)
    if data_fim: q+=" AND data<=?"; p.append(data_fim)
    q+=" ORDER BY data DESC,id DESC"
    rows=conn.execute(q,p).fetchall(); conn.close(); return rows

class TelaFinanceiro(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(2,weight=1)
        inicializar_financeiro(); self._build_header(); self._build_cards(); self._build_tabela(); self._carregar_mes()

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False); hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="Financeiro",font=FONTE_TITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=24,pady=18,sticky="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=24,sticky="e")
        for txt,cor,hover,cmd in[
            ("Receita",  COR_SUCESSO, COR_SUCESSO2, self._nova_receita),
            ("Despesa",  COR_PERIGO,  COR_PERIGO2,  self._nova_despesa),
            ("Hoje",     "#6B7280",   "#4B5563",    self._hoje),
            ("Mes",      "#6B7280",   "#4B5563",    self._carregar_mes),
            ("Ano",      "#6B7280",   "#4B5563",    self._ano),
            ("Relatorios","#1D4ED8",  "#1E40AF",    self._ver_relatorios),
        ]:
            ctk.CTkButton(bf,text=txt,font=FONTE_BTN,width=90,fg_color=cor,hover_color=hover,text_color="white",command=cmd).pack(side="left",padx=3)

    def _build_cards(self):
        f=ctk.CTkFrame(self,fg_color="transparent"); f.grid(row=1,column=0,padx=16,pady=(12,0),sticky="ew")
        f.grid_columnconfigure((0,1,2,3),weight=1)
        self.c_rec=self._card(f,0,"Vendas PDV","R$ 0,00",COR_SUCESSO)
        self.c_des=self._card(f,1,"Despesas","R$ 0,00",COR_PERIGO)
        self.c_sal=self._card(f,2,"Saldo","R$ 0,00",COR_ACENTO)
        self.c_out=self._card(f,3,"Outras Receitas","R$ 0,00","#8B5CF6")

    def _card(self,parent,col,titulo,valor,cor):
        card=ctk.CTkFrame(parent,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        card.grid(row=0,column=col,padx=6,sticky="ew")
        ctk.CTkLabel(card,text=titulo,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        lbl=ctk.CTkLabel(card,text=valor,font=FONTE_CARD_VAL,text_color=cor); lbl.pack(pady=(0,14)); return lbl

    def _build_tabela(self):
        frame=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=2,column=0,padx=16,pady=12,sticky="nsew")
        frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        cols=["Data","Tipo","Categoria","Descricao","Valor","Forma"]; pesos=[2,2,3,5,2,2]
        cab=ctk.CTkFrame(frame,fg_color=COR_ACENTO_LIGHT,corner_radius=8,height=36)
        cab.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,0)); cab.grid_propagate(False)
        for i,(c,p) in enumerate(zip(cols,pesos)):
            cab.grid_columnconfigure(i,weight=p)
            ctk.CTkLabel(cab,text=c,font=("Courier New",10,"bold"),text_color=COR_ACENTO).grid(row=0,column=i,padx=6,pady=6,sticky="w")
        self.scroll=ctk.CTkScrollableFrame(frame,fg_color="transparent")
        self.scroll.grid(row=1,column=0,sticky="nsew",padx=8,pady=8); self.scroll.grid_columnconfigure(0,weight=1)

    def _popular(self,data_ini,data_fim):
        res=resumo_periodo(data_ini,data_fim)
        self.c_rec.configure(text=f'R$ {res["receitas_vendas"]:.2f}')
        self.c_des.configure(text=f'R$ {res["despesas"]:.2f}')
        self.c_out.configure(text=f'R$ {res["receitas_manuais"]:.2f}')
        cor=COR_SUCESSO if res["saldo"]>=0 else COR_PERIGO
        self.c_sal.configure(text=f'R$ {res["saldo"]:.2f}',text_color=cor)
        lancs=listar_lancamentos(data_ini,data_fim)
        for w in self.scroll.winfo_children(): w.destroy()
        pesos=[2,2,3,5,2,2]
        for idx,l in enumerate(lancs):
            cor_bg=COR_LINHA_PAR if idx%2==0 else COR_CARD
            row_f=ctk.CTkFrame(self.scroll,fg_color=cor_bg,corner_radius=6,height=34)
            row_f.grid(row=idx,column=0,sticky="ew",pady=1); row_f.grid_propagate(False)
            for i,p in enumerate(pesos): row_f.grid_columnconfigure(i,weight=p)
            cor_t=COR_SUCESSO if l["tipo"]=="RECEITA" else COR_PERIGO
            vals=[l["data"],l["tipo"],l["categoria"] or "-",l["descricao"] or "-",f'R$ {l["valor"]:.2f}',l["forma_pagamento"]]
            cores=[COR_TEXTO_SUB,cor_t,COR_TEXTO_SUB,COR_TEXTO,cor_t,COR_TEXTO_SUB]
            for i,(v,c) in enumerate(zip(vals,cores)):
                ctk.CTkLabel(row_f,text=v,font=FONTE_SMALL,text_color=c).grid(row=0,column=i,padx=6,sticky="w")

    def _hoje(self): h=datetime.now().strftime("%Y-%m-%d"); self._popular(h,h)
    def _carregar_mes(self): ini=datetime.now().strftime("%Y-%m-01"); fim=datetime.now().strftime("%Y-%m-%d"); self._popular(ini,fim)
    def _ano(self): ini=datetime.now().strftime("%Y-01-01"); fim=datetime.now().strftime("%Y-%m-%d"); self._popular(ini,fim)
    def _nova_receita(self): FormularioLancamento(self,"RECEITA",self._carregar_mes)
    def _nova_despesa(self): FormularioLancamento(self,"DESPESA",self._carregar_mes)

    def _ver_relatorios(self):
        """Abre relatórios dentro do Financeiro"""
        from telas.relatorios import TelaRelatorios
        win = ctk.CTkToplevel(self)
        win.title("Relatórios de Vendas")
        win.geometry("1100x700")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        TelaRelatorios(frame).grid(row=0, column=0, sticky="nsew")



class FormularioLancamento(ctk.CTkToplevel):
    def __init__(self,master,tipo,callback):
        super().__init__(master); self.tipo=tipo; self.callback=callback
        cor=COR_SUCESSO if tipo=="RECEITA" else COR_PERIGO
        self.title("Lancamento"); self.geometry("440x440"); self.configure(fg_color=COR_CARD); self.grab_set(); self._build(cor)
    def _build(self,cor):
        icone="Receita" if self.tipo=="RECEITA" else "Despesa"
        ctk.CTkLabel(self,text=f"Nova {icone}",font=FONTE_TITULO,text_color=cor).pack(pady=(20,12))
        sc=ctk.CTkScrollableFrame(self,fg_color="transparent"); sc.pack(fill="both",expand=True,padx=24); sc.grid_columnconfigure(1,weight=1)
        self.campos={}
        for i,(label,key) in enumerate([("Descricao *","descricao"),("Valor R$ *","valor"),("Data AAAA-MM-DD","data"),("Observacao","observacao")]):
            ctk.CTkLabel(sc,text=label,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=i,column=0,pady=6,sticky="w",padx=(0,12))
            ent=ctk.CTkEntry(sc,font=FONTE_LABEL,height=34,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); ent.grid(row=i,column=1,sticky="ew",pady=6); self.campos[key]=ent
        self.campos["data"].insert(0,datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkLabel(sc,text="Categoria",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=4,column=0,pady=6,sticky="w",padx=(0,12))
        self.cmb=ctk.CTkComboBox(sc,values=CATEGORIAS,font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb.grid(row=4,column=1,sticky="ew",pady=6); self.cmb.set("Outros")
        ctk.CTkLabel(sc,text="Forma Pgto",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=5,column=0,pady=6,sticky="w",padx=(0,12))
        self.cmb_f=ctk.CTkComboBox(sc,values=["DINHEIRO","PIX","DEBITO","CREDITO","BOLETO"],font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb_f.grid(row=5,column=1,sticky="ew",pady=6)
        ctk.CTkButton(self,text="Salvar",font=FONTE_BTN,fg_color=cor,hover_color="#333",text_color="white",height=44,corner_radius=10,command=self._salvar).pack(fill="x",padx=24,pady=16)
    def _salvar(self):
        desc=self.campos["descricao"].get().strip()
        if not desc: messagebox.showerror("Erro","Descricao obrigatoria.",parent=self); return
        try: valor=float(self.campos["valor"].get().replace(",","."))
        except: messagebox.showerror("Erro","Valor invalido.",parent=self); return
        conn=get_conn()
        conn.execute("INSERT INTO lancamentos(tipo,categoria,descricao,valor,data,forma_pagamento,observacao) VALUES(?,?,?,?,?,?,?)",(self.tipo,self.cmb.get(),desc,valor,self.campos["data"].get(),self.cmb_f.get(),self.campos["observacao"].get()))
        conn.commit(); conn.close(); self.callback(); self.destroy()
