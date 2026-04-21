"""telas/produtos.py — Cadastro de Produtos Completo — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox
from tema import *
from banco.database import listar_produtos, salvar_produto, excluir_produto

GRUPOS   = ["PADARIA","CONFEITARIA","SALGADOS","BEBIDAS","FRIOS/LATICÍNIOS",
            "INGREDIENTES","EMBALAGENS","GERAL"]
UNIDADES = ["UN","KG","G","L","ML","CX","PCT","DZ"]


class TelaProdutos(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.produto_selecionado = None
        self._build_header()
        self._build_corpo()
        self._carregar_lista()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="📦  Cadastro de Produtos",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")

        self.ent_busca = ctk.CTkEntry(
            bf, width=280, font=FONTE_LABEL,
            placeholder_text="Pesquisar...",
            fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.ent_busca.pack(side="left")
        self.idx_nav = -1

        def on_key_produtos(e):
            if e.keysym in ("Up", "Down", "Return", "Escape"):
                return "break"
            self._carregar_lista()

        def on_down_prod(e):
            if not self.linhas: return "break"
            self.idx_nav = min((self.idx_nav + 1) if self.idx_nav >= 0 else 0,
                               len(self.linhas) - 1)
            self._selecionar(self.idx_nav)
            return "break"

        def on_up_prod(e):
            if not self.linhas: return "break"
            self.idx_nav = max((self.idx_nav - 1) if self.idx_nav >= 0 else 0, 0)
            self._selecionar(self.idx_nav)
            return "break"

        self.ent_busca.bind("<KeyRelease>", on_key_produtos)
        self.ent_busca.bind("<Down>",       on_down_prod)
        self.ent_busca.bind("<Up>",         on_up_prod)

        for txt, cor, hover, cmd in [
            ("➕ Novo Produto", COR_SUCESSO, COR_SUCESSO2, self._novo_produto),
            ("✏️ Editar",       COR_ACENTO,  COR_ACENTO2,  self._editar_produto),
            ("🗑️ Excluir",      COR_PERIGO,  COR_PERIGO2,  self._excluir_produto),
        ]:
            ctk.CTkButton(bf, text=txt, font=FONTE_BTN, height=36,
                          fg_color=cor, hover_color=hover,
                          text_color="white", command=cmd).pack(side="left", padx=4)

    def _build_corpo(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        cols   = ["Cód.Barras","Cód.Int","Nome do Produto","UN","Grupo",
                  "Custo","Venda","Margem","Estoque","Local"]
        WIDTHS = [110,70,180,40,100,75,75,65,70,80]

        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=40)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        cab.grid_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=4)
        for c, w in zip(cols, WIDTHS):
            ctk.CTkLabel(hdr, text=c, font=("Courier New",14, "bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(
                side="left", padx=2, pady=8)

        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.linhas = []
        self.produto_id_map = []

    def _carregar_lista(self, event=None):
        busca = self.ent_busca.get() if hasattr(self, "ent_busca") else ""
        prods = listar_produtos(busca)
        for w in self.scroll.winfo_children():
            w.destroy()
        self.linhas.clear()
        self.produto_id_map.clear()
        self.produto_selecionado = None

        if not prods:
            ctk.CTkLabel(self.scroll, text="Nenhum produto encontrado.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(pady=40)
            return

        WIDTHS = [110,70,180,40,100,75,75,65,70,80]
        for idx, p in enumerate(prods):
            self.produto_id_map.append(p["id"])
            alerta = p["estoque_atual"] <= p["estoque_minimo"]
            cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD

            row_f = ctk.CTkFrame(self.scroll, fg_color=cor_bg, corner_radius=4, height=36)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)

            p_dict = dict(p)
            margem  = p_dict.get("margem_lucro", 0) or 0
            local   = p_dict.get("localizacao", "") or ""
            cod_int = p_dict.get("codigo_interno", "") or ""

            vals = [(p_dict.get("codigo_barras") or "—")[:13],
                    (cod_int or "—")[:7],
                    p_dict["nome"][:22],
                    p_dict["unidade"],
                    p_dict["grupo"][:12],
                    f'R$ {p_dict["preco_custo"]:.2f}',
                    f'R$ {p_dict["preco_venda"]:.2f}',
                    f'{margem:.1f}%',
                    f'{p_dict["estoque_atual"]:.2f}',
                    (local or "—")[:10]]
            cores = [COR_TEXTO_SUB,COR_TEXTO_SUB,COR_TEXTO,COR_TEXTO_SUB,COR_TEXTO_SUB,
                     COR_TEXTO,COR_ACENTO,
                     COR_SUCESSO if margem >= 20 else COR_AVISO,
                     COR_PERIGO if alerta else COR_SUCESSO,
                     COR_TEXTO_SUB]

            row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
            row_inner.pack(fill="x", padx=4, pady=3)
            for v, c, w in zip(vals, cores, WIDTHS):
                ctk.CTkLabel(row_inner, text=v, font=("Courier New",14),
                             text_color=c, width=w, anchor="w").pack(side="left", padx=2)

            i_cap = idx
            row_f.bind("<Button-1>",     lambda e, i=i_cap: self._selecionar(i))
            row_inner.bind("<Button-1>", lambda e, i=i_cap: self._selecionar(i))
            self.linhas.append(row_f)

    def _selecionar(self, idx):
        for i, f in enumerate(self.linhas):
            f.configure(fg_color=COR_LINHA_PAR if i % 2 == 0 else COR_CARD)
        self.linhas[idx].configure(fg_color=COR_LINHA_SEL)
        self.produto_selecionado = self.produto_id_map[idx]

    def _novo_produto(self):
        FormularioProduto(self, None, self._carregar_lista)

    def _editar_produto(self):
        if not self.produto_selecionado:
            messagebox.showwarning("Selecione", "Selecione um produto.")
            return
        FormularioProduto(self, self.produto_selecionado, self._carregar_lista)

    def _excluir_produto(self):
        if not self.produto_selecionado:
            messagebox.showwarning("Selecione", "Selecione um produto.")
            return
        if messagebox.askyesno("Excluir", "Deseja excluir o produto?"):
            excluir_produto(self.produto_selecionado)
            self._carregar_lista()


class FormularioProduto(ctk.CTkToplevel):
    def __init__(self, master, produto_id, callback):
        super().__init__(master)
        self.produto_id = produto_id
        self.callback   = callback
        self.title("Editar Produto" if produto_id else "Novo Produto")
        self.geometry("680x820")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self.resizable(False, True)
        self.campos = {}
        self._build()
        if produto_id:
            self._preencher(produto_id)
        self.after(300, self._focar_scan)

    def _secao(self, parent, row, titulo):
        frame = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=6, height=28)
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 4))
        frame.grid_propagate(False)
        ctk.CTkLabel(frame, text=titulo, font=("Courier New",15, "bold"),
                     text_color=COR_ACENTO).pack(anchor="w", padx=8, pady=4)
        return row + 1

    def _campo(self, parent, row, label, key, placeholder=""):
        ctk.CTkLabel(parent, text=label, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(
            row=row, column=0, padx=(0, 12), pady=5, sticky="w")
        ent = ctk.CTkEntry(parent, font=FONTE_LABEL, height=34,
                           placeholder_text=placeholder,
                           fg_color=COR_CARD2, border_color=COR_BORDA2,
                           text_color=COR_TEXTO)
        ent.grid(row=row, column=1, sticky="ew", pady=5)
        self.campos[key] = ent
        return row + 1

    def _focar_scan(self):
        """Força foco no campo do leitor de código de barras"""
        try:
            self.lift()
            self.focus_force()
            self.ent_scan.focus_set()
            self.ent_scan.select_range(0, "end")
        except Exception:
            pass

    def _build(self):
        ctk.CTkLabel(
            self,
            text="✏️ Editar" if self.produto_id else "➕ Novo Produto",
            font=FONTE_TITULO, text_color=COR_ACENTO
        ).pack(pady=(16, 4))

        # Leitor
        frame_scan = ctk.CTkFrame(self, fg_color=COR_ACENTO_LIGHT,
                                  corner_radius=10, border_width=2,
                                  border_color=COR_ACENTO)
        frame_scan.pack(fill="x", padx=20, pady=(4, 8))
        ctk.CTkLabel(frame_scan, text="📷  Leitor de Código de Barras",
                     font=("Courier New",15, "bold"),
                     text_color=COR_ACENTO).pack(anchor="w", padx=12, pady=(8, 2))
        fsr = ctk.CTkFrame(frame_scan, fg_color="transparent")
        fsr.pack(fill="x", padx=12, pady=(0, 8))
        self.ent_scan = ctk.CTkEntry(fsr,
            placeholder_text="🔍  Aponte o leitor aqui...",
            font=("Courier New",17), height=40,
            fg_color=COR_CARD, border_color=COR_ACENTO,
            border_width=2, text_color=COR_TEXTO)
        self.ent_scan.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.ent_scan.bind("<Return>", lambda e: self._on_scan())
        ctk.CTkButton(fsr, text="🔍 Buscar", font=FONTE_BTN,
                      width=90, height=40,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white", command=self._on_scan).pack(side="left")

        # Scroll principal
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20)
        scroll.grid_columnconfigure(1, weight=1)

        row = 0

        # Seção 1: Identificação
        row = self._secao(scroll, row, "📋  Identificação")
        row = self._campo(scroll, row, "Nome *", "nome")
        row = self._campo(scroll, row, "Código de Barras", "codigo_barras")
        row = self._campo(scroll, row, "Código Interno", "codigo_interno", "ex: 001")
        row = self._campo(scroll, row, "NCM", "ncm")
        row = self._campo(scroll, row, "Marca", "marca")

        ctk.CTkLabel(scroll, text="Unidade", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(row=row, column=0, pady=6, sticky="w")
        self.cmb_unidade = ctk.CTkComboBox(scroll, values=UNIDADES, font=FONTE_LABEL,
                           fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.cmb_unidade.grid(row=row, column=1, sticky="ew", pady=6)
        self.cmb_unidade.set("UN"); row += 1

        ctk.CTkLabel(scroll, text="Grupo", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(row=row, column=0, pady=6, sticky="w")
        self.cmb_grupo = ctk.CTkComboBox(scroll, values=GRUPOS, font=FONTE_LABEL,
                          fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.cmb_grupo.grid(row=row, column=1, sticky="ew", pady=6)
        self.cmb_grupo.set("GERAL"); row += 1

        # Seção 2: Precificação
        row = self._secao(scroll, row, "💰  Precificação")
        row = self._campo(scroll, row, "Preço Custo (R$)", "preco_custo")
        row = self._campo(scroll, row, "Preço Venda (R$) *", "preco_venda")

        ctk.CTkLabel(scroll, text="Margem de Lucro", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(row=row, column=0, pady=6, sticky="w")
        self.lbl_margem = ctk.CTkLabel(scroll, text="—",
                          font=("Georgia",17, "bold"), text_color=COR_SUCESSO)
        self.lbl_margem.grid(row=row, column=1, pady=6, sticky="w"); row += 1

        self.campos["preco_custo"].bind("<KeyRelease>", self._calcular_margem)
        self.campos["preco_venda"].bind("<KeyRelease>", self._calcular_margem)

        row = self._campo(scroll, row, "Preço Promocional (R$)", "preco_promocional")
        row = self._campo(scroll, row, "Preço Atacado (R$)", "preco_atacado")
        row = self._campo(scroll, row, "Qtd Mínima Atacado", "qtd_atacado")

        # Seção 3: Estoque
        row = self._secao(scroll, row, "📦  Estoque")
        row = self._campo(scroll, row, "Estoque Atual", "estoque_atual")
        row = self._campo(scroll, row, "Estoque Mínimo", "estoque_minimo")
        row = self._campo(scroll, row, "Estoque Máximo", "estoque_maximo")
        row = self._campo(scroll, row, "Localização (ex: A2)", "localizacao")

        # Seção 4: Observações
        row = self._secao(scroll, row, "📝  Observações")
        ctk.CTkLabel(scroll, text="Observações", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(row=row, column=0, pady=6, sticky="nw")
        self.txt_obs = ctk.CTkTextbox(scroll, height=70, font=FONTE_LABEL,
                        fg_color=COR_CARD2, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.txt_obs.grid(row=row, column=1, sticky="ew", pady=6)

        ctk.CTkButton(self, text="💾  Salvar Produto",
                      font=FONTE_BTN, fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white", height=46, corner_radius=10,
                      command=self._salvar).pack(fill="x", padx=20, pady=16)

    def _calcular_margem(self, event=None):
        try:
            pc = float(self.campos["preco_custo"].get().replace(",", ".") or "0")
            pv = float(self.campos["preco_venda"].get().replace(",", ".") or "0")
            if pc > 0:
                margem = (pv - pc) / pc * 100
                cor = COR_SUCESSO if margem >= 20 else (COR_AVISO if margem >= 10 else COR_PERIGO)
                self.lbl_margem.configure(
                    text=f"{margem:.1f}%  (R$ {pv-pc:.2f} de lucro)", text_color=cor)
            else:
                self.lbl_margem.configure(text="—", text_color=COR_TEXTO_SUB)
        except Exception:
            pass

    def _on_scan(self, event=None):
        codigo = self.ent_scan.get().strip()
        if not codigo:
            messagebox.showwarning("Campo vazio", "Escaneie um código.", parent=self)
            return
        from banco.database import buscar_produto_por_codigo
        prod = buscar_produto_por_codigo(codigo)
        if prod:
            if messagebox.askyesno("✅ Encontrado",
                f"📦  {prod['nome']}\n💰  R$ {prod['preco_venda']:.2f}\n\nCarregar para edição?",
                parent=self):
                self._preencher_dados(dict(prod))
                self.produto_id = prod["id"]
        else:
            self.campos["codigo_barras"].delete(0, "end")
            self.campos["codigo_barras"].insert(0, codigo)
            messagebox.showinfo("Novo", f"Código '{codigo}' não cadastrado.\nPreencha os dados.", parent=self)
            self.campos["nome"].focus_set()
        self.ent_scan.delete(0, "end")

    def _preencher_dados(self, p: dict):
        mapa = {"nome": p.get("nome",""), "codigo_barras": p.get("codigo_barras","") or "",
                "codigo_interno": p.get("codigo_interno","") or "",
                "ncm": p.get("ncm","") or "", "marca": p.get("marca","") or "",
                "preco_custo": str(p.get("preco_custo","")),
                "preco_venda": str(p.get("preco_venda","")),
                "preco_promocional": str(p.get("preco_promocional","") or ""),
                "preco_atacado": str(p.get("preco_atacado","") or ""),
                "qtd_atacado": str(p.get("qtd_atacado","") or ""),
                "estoque_atual": str(p.get("estoque_atual","")),
                "estoque_minimo": str(p.get("estoque_minimo","")),
                "estoque_maximo": str(p.get("estoque_maximo","") or ""),
                "localizacao": p.get("localizacao","") or ""}
        for key, val in mapa.items():
            if key in self.campos:
                self.campos[key].delete(0, "end")
                self.campos[key].insert(0, val)
        self.cmb_unidade.set(p.get("unidade","UN") or "UN")
        self.cmb_grupo.set(p.get("grupo","GERAL") or "GERAL")
        self.txt_obs.delete("1.0","end")
        self.txt_obs.insert("1.0", p.get("observacao","") or "")
        self._calcular_margem()

    def _preencher(self, produto_id):
        from banco.database import get_conn
        conn = get_conn()
        p = conn.execute("SELECT * FROM produtos WHERE id=?",(produto_id,)).fetchone()
        conn.close()
        if p: self._preencher_dados(dict(p))

    def _get_float(self, key, default=0.0):
        try: return float(self.campos[key].get().replace(",",".") or str(default))
        except: return default

    def _salvar(self):
        nome = self.campos["nome"].get().strip()
        if not nome:
            messagebox.showerror("Erro","Nome é obrigatório.",parent=self); return
        dados = {
            "nome": nome,
            "codigo_barras": self.campos["codigo_barras"].get().strip() or None,
            "codigo_interno": self.campos["codigo_interno"].get().strip(),
            "ncm": self.campos["ncm"].get().strip(),
            "marca": self.campos["marca"].get().strip(),
            "preco_custo": self._get_float("preco_custo"),
            "preco_venda": self._get_float("preco_venda"),
            "preco_promocional": self._get_float("preco_promocional"),
            "preco_atacado": self._get_float("preco_atacado"),
            "qtd_atacado": self._get_float("qtd_atacado"),
            "estoque_atual": self._get_float("estoque_atual"),
            "estoque_minimo": self._get_float("estoque_minimo"),
            "estoque_maximo": self._get_float("estoque_maximo"),
            "localizacao": self.campos["localizacao"].get().strip(),
            "observacao": self.txt_obs.get("1.0","end").strip(),
            "unidade": self.cmb_unidade.get(),
            "grupo": self.cmb_grupo.get(),
        }
        salvar_produto(dados, self.produto_id)
        self.callback()
        self.destroy()
