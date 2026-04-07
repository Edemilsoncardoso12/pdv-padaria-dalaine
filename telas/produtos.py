"""telas/produtos.py — Cadastro de Produtos — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox
from tema import *
from banco.database import listar_produtos, salvar_produto, excluir_produto

GRUPOS=["PADARIA","CONFEITARIA","SALGADOS","BEBIDAS","FRIOS/LATICÍNIOS","INGREDIENTES","EMBALAGENS","GERAL"]
UNIDADES=["UN","KG","G","L","ML","CX","PCT","DZ"]

class TelaProdutos(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        self.produto_selecionado=None; self._build_header(); self._build_corpo(); self._carregar_lista()

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False); hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="📦  Cadastro de Produtos",font=FONTE_TITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=24,pady=18,sticky="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=24,sticky="e")
        self.ent_busca = ctk.CTkEntry(bf, width=280, font=FONTE_LABEL,
                                      placeholder_text="Pesquisar...",
                                      fg_color=COR_CARD2,
                                      border_color=COR_BORDA2,
                                      text_color=COR_TEXTO)
        self.ent_busca.pack(side="left")

        def on_key_produtos(e):
            if e.keysym in ("Up","Down","Return","Escape"):
                return "break"
            self._carregar_lista()

        def on_down_prod(e):
            if not self.linhas: return "break"
            if not hasattr(self,"idx_nav") or self.idx_nav < 0:
                self.idx_nav = 0
            else:
                self.idx_nav = min(self.idx_nav + 1, len(self.linhas)-1)
            self._selecionar(self.idx_nav)
            return "break"

        def on_up_prod(e):
            if not self.linhas: return "break"
            if not hasattr(self,"idx_nav") or self.idx_nav < 0:
                self.idx_nav = 0
            else:
                self.idx_nav = max(self.idx_nav - 1, 0)
            self._selecionar(self.idx_nav)
            return "break"

        self.ent_busca.bind("<KeyRelease>", on_key_produtos)
        self.ent_busca.bind("<Down>",       on_down_prod)
        self.ent_busca.bind("<Up>",         on_up_prod)
        self.idx_nav = -1
        for txt,cor,hover,cmd in[("➕ Novo",COR_SUCESSO,COR_SUCESSO2,self._novo_produto),("✏️ Editar",COR_ACENTO,COR_ACENTO2,self._editar_produto),("🗑️ Excluir",COR_PERIGO,COR_PERIGO2,self._excluir_produto)]:
            ctk.CTkButton(bf,text=txt,font=FONTE_BTN,width=100,fg_color=cor,hover_color=hover,text_color="white",command=cmd).pack(side="left",padx=4)

    def _build_corpo(self):
        frame=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=1,column=0,padx=16,pady=16,sticky="nsew"); frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        cols   = ["Cód.Barras","Nome do Produto","UN","Grupo","Custo","Venda","Estoque"]
        WIDTHS = [110, 200, 40, 110, 80, 80, 70]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                          corner_radius=8, height=40)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.grid_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=4)
        for c, w in zip(cols, WIDTHS):
            ctk.CTkLabel(hdr, text=c,
                         font=("Courier New",11,"bold"),
                         text_color=COR_ACENTO,
                         width=w, anchor="w").pack(side="left", padx=2, pady=8)
        self.scroll=ctk.CTkScrollableFrame(frame,fg_color="transparent")
        self.scroll.grid(row=1,column=0,sticky="nsew",padx=8,pady=8); self.scroll.grid_columnconfigure(0,weight=1)
        self.linhas=[]; self.produto_id_map=[]

    def _carregar_lista(self,event=None):
        busca=self.ent_busca.get() if hasattr(self,"ent_busca") else ""
        prods=listar_produtos(busca)
        for w in self.scroll.winfo_children(): w.destroy()
        self.linhas.clear(); self.produto_id_map.clear(); self.produto_selecionado=None
        if not prods:
            ctk.CTkLabel(self.scroll,text="Nenhum produto encontrado.",font=FONTE_LABEL,text_color=COR_TEXTO_SUB).grid(pady=40); return
        WIDTHS = [110, 200, 40, 110, 80, 80, 70]
        for idx, p in enumerate(prods):
            self.produto_id_map.append(p["id"])
            alerta = p["estoque_atual"] <= p["estoque_minimo"]
            cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
            row_f  = ctk.CTkFrame(self.scroll, fg_color=cor_bg,
                                  corner_radius=4, height=40)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)

            cod  = (p["codigo_barras"] or "—")[:13]
            vals = [cod, p["nome"][:25], p["unidade"],
                    p["grupo"][:12],
                    f'R$ {p["preco_custo"]:.2f}',
                    f'R$ {p["preco_venda"]:.2f}',
                    f'{p["estoque_atual"]:.2f}']
            cores = [COR_TEXTO_SUB, COR_TEXTO, COR_TEXTO_SUB,
                     COR_TEXTO_SUB, COR_TEXTO, COR_ACENTO,
                     COR_PERIGO if alerta else COR_SUCESSO]

            row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
            row_inner.pack(fill="x", padx=4, pady=4)
            for v, c, w in zip(vals, cores, WIDTHS):
                ctk.CTkLabel(row_inner, text=v,
                             font=("Courier New",11),
                             text_color=c,
                             width=w, anchor="w").pack(side="left", padx=2)

            i_cap = idx
            row_f.bind("<Button-1>",    lambda e, i=i_cap: self._selecionar(i))
            row_inner.bind("<Button-1>",lambda e, i=i_cap: self._selecionar(i))
            self.linhas.append(row_f)

    def _selecionar(self,idx):
        for f in self.linhas: f.configure(fg_color=COR_LINHA_PAR if self.linhas.index(f)%2==0 else COR_CARD)
        self.linhas[idx].configure(fg_color=COR_LINHA_SEL); self.produto_selecionado=self.produto_id_map[idx]

    def _novo_produto(self): FormularioProduto(self,None,self._carregar_lista)
    def _editar_produto(self):
        if not self.produto_selecionado: messagebox.showwarning("Selecione","Selecione um produto."); return
        FormularioProduto(self,self.produto_selecionado,self._carregar_lista)
    def _excluir_produto(self):
        if not self.produto_selecionado: messagebox.showwarning("Selecione","Selecione um produto."); return
        if messagebox.askyesno("Excluir","Deseja excluir o produto?"): excluir_produto(self.produto_selecionado); self._carregar_lista()

class FormularioProduto(ctk.CTkToplevel):
    def __init__(self,master,produto_id,callback):
        super().__init__(master); self.produto_id=produto_id; self.callback=callback
        self.title("Produto"); self.geometry("560x620"); self.configure(fg_color=COR_CARD); self.grab_set(); self._build()
        if produto_id: self._preencher(produto_id)
    def _build(self):
        ctk.CTkLabel(self,text="✏️ Editar" if self.produto_id else "➕ Novo Produto",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=(20,12))
        scroll=ctk.CTkScrollableFrame(self,fg_color="transparent"); scroll.pack(fill="both",expand=True,padx=24); scroll.grid_columnconfigure(1,weight=1)
        self.campos={}
        for i,(label,key) in enumerate([("Nome *","nome"),("Código de Barras","codigo_barras"),("NCM","ncm"),("Preço Custo","preco_custo"),("Preço Venda *","preco_venda"),("Estoque Mínimo","estoque_minimo"),("Marca","marca")]):
            ctk.CTkLabel(scroll,text=label,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=i,column=0,padx=(0,12),pady=6,sticky="w")
            ent=ctk.CTkEntry(scroll,font=FONTE_LABEL,height=34,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); ent.grid(row=i,column=1,sticky="ew",pady=6); self.campos[key]=ent
        n=7
        ctk.CTkLabel(scroll,text="Unidade",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=n,column=0,pady=6,sticky="w")
        self.cmb_unidade=ctk.CTkComboBox(scroll,values=UNIDADES,font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb_unidade.grid(row=n,column=1,sticky="ew",pady=6); self.cmb_unidade.set("UN")
        ctk.CTkLabel(scroll,text="Grupo",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=n+1,column=0,pady=6,sticky="w")
        self.cmb_grupo=ctk.CTkComboBox(scroll,values=GRUPOS,font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb_grupo.grid(row=n+1,column=1,sticky="ew",pady=6); self.cmb_grupo.set("GERAL")
        ctk.CTkButton(self,text="💾  Salvar Produto",font=FONTE_BTN,fg_color=COR_SUCESSO,hover_color=COR_SUCESSO2,text_color="white",height=44,corner_radius=10,command=self._salvar).pack(fill="x",padx=24,pady=16)
    def _on_scan(self, event=None):
        """Ao escanear código de barras, preenche o campo automaticamente"""
        codigo = self.ent_scan.get().strip()
        if not codigo:
            return
        # Preenche campo código de barras
        self.campos["codigo_barras"].delete(0, "end")
        self.campos["codigo_barras"].insert(0, codigo)
        # Verifica se produto já existe
        from banco.database import buscar_produto_por_codigo
        prod = buscar_produto_por_codigo(codigo)
        if prod:
            from tkinter import messagebox
            if messagebox.askyesno("Produto encontrado",
                f"Produto '{prod['nome']}' já cadastrado!\nDeseja carregar os dados?",
                parent=self):
                self._preencher_dados(dict(prod))
        # Limpa campo scan e foca no nome
        self.ent_scan.delete(0, "end")
        self.campos["nome"].focus_set()

    def _preencher_dados(self, p):
        """Preenche formulário com dados de um produto existente"""
        mapa = {
            "nome": p.get("nome",""),
            "codigo_barras": p.get("codigo_barras","") or "",
            "ncm": p.get("ncm","") or "",
            "preco_custo": str(p.get("preco_custo","")),
            "preco_venda": str(p.get("preco_venda","")),
            "estoque_minimo": str(p.get("estoque_minimo","")),
            "marca": p.get("marca","") or "",
        }
        for key, val in mapa.items():
            self.campos[key].delete(0, "end")
            self.campos[key].insert(0, val)
        if hasattr(self, "cmb_unidade"):
            self.cmb_unidade.set(p.get("unidade","UN"))
        if hasattr(self, "cmb_grupo"):
            self.cmb_grupo.set(p.get("grupo","GERAL"))

    def _preencher_por_codigo(self, event=None):
        """Busca produto pelo código de barras escaneado"""
        codigo = self.ent_scan.get().strip()
        if not codigo:
            return
        from banco.database import buscar_produto_por_codigo
        prod = buscar_produto_por_codigo(codigo)
        if prod:
            # Produto já existe — preenche para editar
            for key in ["nome","codigo_barras","ncm","preco_custo",
                        "preco_venda","estoque_minimo","marca"]:
                self.campos[key].delete(0,"end")
                self.campos[key].insert(0, str(prod[key] or ""))
            if hasattr(self,"cmb_unidade"):
                self.cmb_unidade.set(prod["unidade"] or "UN")
            if hasattr(self,"cmb_grupo"):
                self.cmb_grupo.set(prod["grupo"] or "GERAL")
            self.produto_id = prod["id"]
            from tkinter import messagebox
            messagebox.showinfo("Produto Encontrado",
                f"✅ Produto encontrado:\n{prod['nome']}\n\nCampos preenchidos para edição.",
                parent=self)
        else:
            # Produto novo — só preenche o código
            self.campos["codigo_barras"].delete(0,"end")
            self.campos["codigo_barras"].insert(0, codigo)
            self.campos["nome"].focus_set()
        self.ent_scan.delete(0,"end")

    def _preencher(self,produto_id):
        from banco.database import get_conn
        conn=get_conn(); p=conn.execute("SELECT * FROM produtos WHERE id=?",(produto_id,)).fetchone(); conn.close()
        if not p: return
        for key,val in[("nome",p["nome"]),("codigo_barras",p["codigo_barras"] or ""),("ncm",p["ncm"] or ""),("preco_custo",str(p["preco_custo"])),("preco_venda",str(p["preco_venda"])),("estoque_minimo",str(p["estoque_minimo"])),("marca",p["marca"] or "")]:
            self.campos[key].insert(0,val)
        self.cmb_unidade.set(p["unidade"] or "UN"); self.cmb_grupo.set(p["grupo"] or "GERAL")
    def _salvar(self):
        nome=self.campos["nome"].get().strip()
        if not nome: messagebox.showerror("Erro","Nome obrigatório.",parent=self); return
        try: pv=float(self.campos["preco_venda"].get().replace(",",".") or "0"); pc=float(self.campos["preco_custo"].get().replace(",",".") or "0"); em=float(self.campos["estoque_minimo"].get().replace(",",".") or "0")
        except: messagebox.showerror("Erro","Preço inválido.",parent=self); return
        dados={"nome":nome,"codigo_barras":self.campos["codigo_barras"].get().strip() or None,"ncm":self.campos["ncm"].get().strip(),"preco_custo":pc,"preco_venda":pv,"estoque_minimo":em,"marca":self.campos["marca"].get().strip(),"unidade":self.cmb_unidade.get(),"grupo":self.cmb_grupo.get()}
        salvar_produto(dados,self.produto_id); self.callback(); self.destroy()
