"""telas/producao.py — Producao e Fichas Tecnicas — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from tema import *
from banco.database import get_conn, listar_produtos, movimentar_estoque

def inicializar_producao():
    conn=get_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS fichas_tecnicas(id INTEGER PRIMARY KEY AUTOINCREMENT,produto_id INTEGER REFERENCES produtos(id),ingrediente_id INTEGER REFERENCES produtos(id),quantidade REAL,unidade TEXT DEFAULT \'UN\',observacao TEXT DEFAULT \'\' )")
    conn.execute("CREATE TABLE IF NOT EXISTS ordens_producao(id INTEGER PRIMARY KEY AUTOINCREMENT,produto_id INTEGER REFERENCES produtos(id),quantidade REAL,status TEXT DEFAULT \'PENDENTE\',data_hora TEXT DEFAULT(datetime(\'now\',\'localtime\')),observacao TEXT DEFAULT \'\' )")
    conn.commit(); conn.close()

def get_ficha(produto_id):
    conn=get_conn()
    rows=conn.execute("SELECT f.*,p.nome as ingrediente_nome,p.estoque_atual,p.unidade as unidade_estoque FROM fichas_tecnicas f JOIN produtos p ON p.id=f.ingrediente_id WHERE f.produto_id=?",(produto_id,)).fetchall()
    conn.close(); return rows

def verificar_estoque_producao(produto_id,quantidade):
    ficha=get_ficha(produto_id); faltando=[]
    for ing in ficha:
        necessario=ing["quantidade"]*quantidade; disponivel=ing["estoque_atual"]
        if disponivel<necessario: faltando.append({"nome":ing["ingrediente_nome"],"necessario":necessario,"disponivel":disponivel,"falta":necessario-disponivel})
    return faltando

def executar_producao(produto_id,quantidade,obs=""):
    ficha=get_ficha(produto_id)
    for ing in ficha:
        movimentar_estoque(ing["ingrediente_id"],"SAIDA",ing["quantidade"]*quantidade,f"Producao {quantidade}x #{produto_id}")
    movimentar_estoque(produto_id,"ENTRADA",quantidade,f"Producao realizada {obs}")
    conn=get_conn(); conn.execute("INSERT INTO ordens_producao(produto_id,quantidade,status,observacao) VALUES(?,?,\'CONCLUIDA\',?)",(produto_id,quantidade,obs)); conn.commit(); conn.close()

class TelaProducao(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(1,weight=1)
        self.produto_sel=None; inicializar_producao(); self._build_header(); self._build_lista(); self._build_ficha()

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,columnspan=2,sticky="ew"); hdr.grid_propagate(False); hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="Producao / Fichas Tecnicas",font=FONTE_TITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=24,pady=18,sticky="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=24,sticky="e")
        ctk.CTkButton(bf,text="Produzir",font=FONTE_BTN,width=100,fg_color=COR_SUCESSO,hover_color=COR_SUCESSO2,text_color="white",command=self._produzir).pack(side="left",padx=4)
        ctk.CTkButton(bf,text="Historico",font=FONTE_BTN,width=100,fg_color="#6B7280",hover_color="#4B5563",text_color="white",command=self._historico).pack(side="left",padx=4)

    def _build_lista(self):
        frame=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=1,column=0,padx=(16,8),pady=16,sticky="nsew"); frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(frame,text="Produtos com Ficha Tecnica",font=FONTE_SUBTITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=12,pady=10,sticky="w")
        self.scroll_prod=ctk.CTkScrollableFrame(frame,fg_color="transparent")
        self.scroll_prod.grid(row=1,column=0,sticky="nsew",padx=8,pady=8); self.scroll_prod.grid_columnconfigure(0,weight=1)
        self._carregar_produtos()

    def _carregar_produtos(self):
        for w in self.scroll_prod.winfo_children(): w.destroy()
        prods=listar_produtos(); conn=get_conn()
        for p in prods:
            tem=conn.execute("SELECT COUNT(*) FROM fichas_tecnicas WHERE produto_id=?",(p["id"],)).fetchone()[0]
            icone="OK" if tem>0 else "SEM FICHA"; cor=COR_SUCESSO if tem>0 else COR_TEXTO_SUB
            ctk.CTkButton(self.scroll_prod,text=f"{icone} | {p["nome"][:35]}",font=FONTE_LABEL,height=36,anchor="w",fg_color="transparent",hover_color=COR_ACENTO_LIGHT,text_color=cor,command=lambda pp=p:self._selecionar(pp)).pack(fill="x",pady=1)
        conn.close()

    def _build_ficha(self):
        self.frame_ficha=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        self.frame_ficha.grid(row=1,column=1,padx=(8,16),pady=16,sticky="nsew")
        self.frame_ficha.grid_rowconfigure(2,weight=1); self.frame_ficha.grid_columnconfigure(0,weight=1)
        self.lbl_produto=ctk.CTkLabel(self.frame_ficha,text="Selecione um produto",font=FONTE_SUBTITULO,text_color=COR_TEXTO_SUB)
        self.lbl_produto.grid(row=0,column=0,padx=12,pady=10,sticky="w")
        bf=ctk.CTkFrame(self.frame_ficha,fg_color="transparent"); bf.grid(row=1,column=0,padx=12,sticky="w")
        ctk.CTkButton(bf,text="Add Ingrediente",font=FONTE_BTN,width=140,fg_color=COR_ACENTO,hover_color=COR_ACENTO2,text_color="white",command=self._add_ingrediente).pack(side="left",padx=4)
        ctk.CTkButton(bf,text="Remover",font=FONTE_BTN,width=90,fg_color=COR_PERIGO,hover_color=COR_PERIGO2,text_color="white",command=self._remover_ingrediente).pack(side="left",padx=4)
        self.scroll_ficha=ctk.CTkScrollableFrame(self.frame_ficha,fg_color="transparent")
        self.scroll_ficha.grid(row=2,column=0,sticky="nsew",padx=8,pady=8); self.scroll_ficha.grid_columnconfigure(0,weight=1)
        self.ficha_sel=None; self.ficha_id_map=[]

    def _selecionar(self,prod):
        self.produto_sel=prod; self.lbl_produto.configure(text=prod["nome"],text_color=COR_ACENTO); self._carregar_ficha()

    def _carregar_ficha(self):
        if not self.produto_sel: return
        for w in self.scroll_ficha.winfo_children(): w.destroy()
        self.ficha_id_map.clear(); self.ficha_sel=None
        ficha=get_ficha(self.produto_sel["id"])
        if not ficha:
            ctk.CTkLabel(self.scroll_ficha,text="Nenhum ingrediente.\nClique em Add Ingrediente",font=FONTE_LABEL,text_color=COR_TEXTO_SUB,justify="center").pack(pady=20); return
        for idx,ing in enumerate(ficha):
            self.ficha_id_map.append(ing["id"]); ok=ing["estoque_atual"]>=ing["quantidade"]
            cor_bg=COR_LINHA_PAR if idx%2==0 else COR_CARD
            row_f=ctk.CTkFrame(self.scroll_ficha,fg_color=cor_bg,corner_radius=6,height=36); row_f.pack(fill="x",pady=1)
            ctk.CTkLabel(row_f,text=ing["ingrediente_nome"],font=FONTE_LABEL,text_color=COR_TEXTO).pack(side="left",padx=10)
            ctk.CTkLabel(row_f,text=f'{ing["quantidade"]} {ing["unidade"]}  |  Estoque: {ing["estoque_atual"]:.2f}',font=FONTE_SMALL,text_color=COR_SUCESSO if ok else COR_PERIGO).pack(side="right",padx=10)
            i_cap=idx; row_f.bind("<Button-1>",lambda e,i=i_cap:self._sel_ficha(i))

    def _sel_ficha(self,idx): self.ficha_sel=self.ficha_id_map[idx] if idx<len(self.ficha_id_map) else None

    def _add_ingrediente(self):
        if not self.produto_sel: messagebox.showwarning("Aviso","Selecione um produto."); return
        DialogoIngrediente(self,self.produto_sel["id"],self._carregar_ficha)

    def _remover_ingrediente(self):
        if not self.ficha_sel: messagebox.showwarning("Aviso","Selecione um ingrediente."); return
        if messagebox.askyesno("Remover","Remover ingrediente?"):
            conn=get_conn(); conn.execute("DELETE FROM fichas_tecnicas WHERE id=?",(self.ficha_sel,)); conn.commit(); conn.close(); self._carregar_ficha()

    def _produzir(self):
        if not self.produto_sel: messagebox.showwarning("Aviso","Selecione um produto."); return
        if not get_ficha(self.produto_sel["id"]): messagebox.showwarning("Aviso","Cadastre ingredientes primeiro."); return
        qtd=simpledialog.askfloat("Produzir",f"Quantas unidades de {self.produto_sel["nome"]}?",minvalue=0.001)
        if not qtd: return
        faltando=verificar_estoque_producao(self.produto_sel["id"],qtd)
        if faltando:
            msg="Estoque insuficiente:\n"; 
            for f in faltando: msg+=f"  {f["nome"]} precisa {f["necessario"]:.3f} tem {f["disponivel"]:.3f}\n"
            messagebox.showwarning("Estoque",msg); return
        executar_producao(self.produto_sel["id"],qtd)
        messagebox.showinfo("Producao",f"{qtd:.2f}x {self.produto_sel["nome"]} produzido!")
        self._carregar_ficha(); self._carregar_produtos()

    def _historico(self):
        conn=get_conn()
        ordens=conn.execute("SELECT o.*,p.nome as produto_nome FROM ordens_producao o JOIN produtos p ON p.id=o.produto_id ORDER BY o.data_hora DESC LIMIT 100").fetchall()
        conn.close()
        win=ctk.CTkToplevel(self); win.title("Historico"); win.geometry("600x400"); win.configure(fg_color=COR_CARD)
        ctk.CTkLabel(win,text="Historico de Producao",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=12)
        scroll=ctk.CTkScrollableFrame(win,fg_color=COR_CARD2); scroll.pack(fill="both",expand=True,padx=16,pady=(0,16))
        for o in ordens:
            ctk.CTkLabel(scroll,text=f'{o["data_hora"][:16]}  |  {o["produto_nome"]:<30}  |  Qtde: {o["quantidade"]:.2f}  |  {o["status"]}',font=FONTE_SMALL,text_color=COR_SUCESSO,anchor="w").pack(fill="x",pady=1,padx=8)

class DialogoIngrediente(ctk.CTkToplevel):
    def __init__(self, master, produto_id, callback):
        super().__init__(master)
        self.produto_id = produto_id
        self.callback   = callback
        self.ing_sel    = None
        self.title("Adicionar Ingrediente")
        self.geometry("520x480")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Adicionar Ingrediente",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20,8))

        # Busca
        ctk.CTkLabel(self, text="Buscar ingrediente:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(anchor="w", padx=24)
        self.ent_busca = ctk.CTkEntry(
            self, font=FONTE_LABEL, width=440,
            placeholder_text="Digite o nome do produto...",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_busca.pack(padx=24, pady=4)
        self.ent_busca.bind("<KeyRelease>", self._popular)
        self.ent_busca.focus_set()

        # Lista de produtos
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=COR_CARD2, height=140, corner_radius=8)
        self.scroll.pack(fill="x", padx=24, pady=4)

        # Selecionado
        self.lbl_sel = ctk.CTkLabel(
            self, text="Clique em um produto para selecionar",
            font=FONTE_SMALL, text_color=COR_TEXTO_SUB)
        self.lbl_sel.pack(pady=(4,2))

        # Qtde + Unidade + Botão na mesma linha
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(padx=24, fill="x", pady=4)

        ctk.CTkLabel(f, text="Qtde:",
                     font=FONTE_LABEL,
                     text_color=COR_TEXTO_SUB).pack(side="left")
        self.ent_qtd = ctk.CTkEntry(
            f, font=FONTE_LABEL, width=70,
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_qtd.insert(0, "1")
        self.ent_qtd.pack(side="left", padx=6)

        ctk.CTkLabel(f, text="Unid:",
                     font=FONTE_LABEL,
                     text_color=COR_TEXTO_SUB).pack(side="left")
        self.ent_und = ctk.CTkEntry(
            f, font=FONTE_LABEL, width=60,
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_und.insert(0, "UN")
        self.ent_und.pack(side="left", padx=6)

        # Botão GRANDE e visível
        ctk.CTkButton(
            f, text="✅ ADICIONAR",
            font=("Georgia",17,"bold"),
            width=160, height=40,
            fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
            text_color="white",
            command=self._salvar).pack(side="left", padx=10)

        # Popular lista inicial
        self._popular()

    def _popular(self, event=None):
        for w in self.scroll.winfo_children():
            w.destroy()
        busca = self.ent_busca.get().strip() if hasattr(self, "ent_busca") else ""
        from banco.database import listar_produtos
        prods = listar_produtos(busca)[:20]
        for p in prods:
            txt = f'{p["codigo_barras"] or "":>12}  {p["nome"][:35]}  ({p["unidade"]})'
            ctk.CTkButton(
                self.scroll, text=txt,
                font=("Courier New",15),
                height=32, anchor="w",
                fg_color="transparent",
                hover_color=COR_ACENTO_LIGHT,
                text_color=COR_TEXTO,
                command=lambda pp=p: self._sel_ing(pp)
            ).pack(fill="x", pady=1)

    def _sel_ing(self, prod):
        self.ing_sel = prod
        self.lbl_sel.configure(
            text=f"Selecionado: {prod['nome']} ({prod['unidade']})",
            text_color=COR_ACENTO)
        self.ent_und.delete(0, "end")
        self.ent_und.insert(0, prod["unidade"])

    def _salvar(self):
        if not self.ing_sel:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Selecione um ingrediente.", parent=self)
            return
        try:
            qtd = float(self.ent_qtd.get().replace(",", "."))
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Erro", "Quantidade invalida.", parent=self)
            return
        from banco.database import get_conn
        conn = get_conn()
        conn.execute(
            "INSERT INTO fichas_tecnicas(produto_id,ingrediente_id,quantidade,unidade) VALUES(?,?,?,?)",
            (self.produto_id, self.ing_sel["id"], qtd, self.ent_und.get()))
        conn.commit()
        conn.close()
        self.callback()
        self.destroy()
