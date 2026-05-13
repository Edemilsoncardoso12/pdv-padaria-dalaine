"""telas/caixa.py — PDV Tema Branco + Consignação + Orçamento + Prazo + Peso + F6"""
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from datetime import datetime
from tema import *
from banco.database import (caixa_aberto, abrir_caixa, fechar_caixa,
    buscar_produto_por_codigo, listar_produtos, registrar_venda)

class TelaCaixa(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.itens=[]; self.caixa_id=None; self.desconto_global=0.0
        self.cliente_venda=None; self.vendedor_atual="Operador"
        self.modo_venda="NORMAL"; self.operador_logado=None
        self._verificar_caixa(); self._build_header(); self._build_tabela()
        self._build_painel_direito(); self._build_rodape(); self._bind_teclas()
        # Pedir senha ao abrir o PDV
        self.after(300, self._pedir_senha_operador)

    def _pedir_senha_operador(self):
        """Tela de senha para liberar o PDV — igual ao Eccus"""
        import hashlib, base64
        from banco.database import get_conn

        win = ctk.CTkToplevel(self)
        win.title("Identificação do Operador")
        win.geometry("380x320")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.resizable(False, False)
        # Não permite fechar sem autenticar
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(win, text="🔐  Identificação",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(24,4))
        ctk.CTkLabel(win, text="Digite sua senha para iniciar a venda:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(0,16))

        ctk.CTkLabel(win, text="Usuário:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(anchor="w", padx=32)
        ent_user = ctk.CTkEntry(win, font=FONTE_LABEL, height=38,
                                placeholder_text="login...",
                                fg_color=COR_CARD2, border_color=COR_BORDA2,
                                text_color=COR_TEXTO)
        ent_user.pack(fill="x", padx=32, pady=(2,10))

        ctk.CTkLabel(win, text="Senha:",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(anchor="w", padx=32)
        ent_senha = ctk.CTkEntry(win, font=FONTE_LABEL, height=38,
                                 show="●",
                                 placeholder_text="senha...",
                                 fg_color=COR_CARD2, border_color=COR_BORDA2,
                                 text_color=COR_TEXTO)
        ent_senha.pack(fill="x", padx=32, pady=(2,4))
        ent_user.focus_set()

        lbl_erro = ctk.CTkLabel(win, text="",
                                font=FONTE_SMALL, text_color=COR_PERIGO)
        lbl_erro.pack(pady=4)

        def confirmar():
            import hashlib, base64
            login = ent_user.get().strip()
            senha = ent_senha.get().strip()
            if not login or not senha:
                lbl_erro.configure(text="Preencha usuário e senha.")
                return
            # Hash scrypt
            salt = b"pdv_padaria_laine_2025_fixed"
            h = hashlib.scrypt(senha.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
            hash_novo = "scrypt:" + base64.b64encode(h).decode()
            # Hash legado SHA-256
            salt_leg = "pdv_padaria_laine_2025"
            hash_leg = hashlib.sha256(f"{salt_leg}{senha}".encode()).hexdigest()

            conn = get_conn()
            user = conn.execute(
                "SELECT * FROM usuarios WHERE login=? AND (senha=? OR senha=?) AND ativo=1",
                (login, hash_novo, hash_leg)).fetchone()
            conn.close()

            if user:
                self.operador_logado = dict(user)
                self.vendedor_atual  = user["nome"]
                if hasattr(self, "lbl_vendedor"):
                    self.lbl_vendedor.configure(
                        text=f"Operador: {user['nome']}")
                win.destroy()
                # Garante foco no leitor de código de barras após login
                self.after(150, self._focar_busca)
            else:
                lbl_erro.configure(text="❌ Usuário ou senha incorretos!")
                ent_senha.delete(0, "end")
                ent_senha.focus_set()

        ent_senha.bind("<Return>", lambda e: confirmar())
        ent_user.bind("<Return>",  lambda e: ent_senha.focus_set())

        ctk.CTkButton(win, text="✅  Entrar no Caixa",
                      font=("Georgia",13,"bold"),
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white", height=46, corner_radius=10,
                      command=confirmar).pack(fill="x", padx=32, pady=8)

    def _verificar_caixa(self):
        cx=caixa_aberto()
        if cx: self.caixa_id=cx["id"]
        else: self._dialogo_abrir_caixa()

    def _dialogo_abrir_caixa(self):
        win=ctk.CTkToplevel(self); win.title("Abrir Caixa")
        win.geometry("380x240"); win.configure(fg_color=COR_CARD); win.grab_set()
        ctk.CTkLabel(win,text="💰  Abrir Caixa",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=(24,8))
        ctk.CTkLabel(win,text="Valor inicial (R$):",font=FONTE_LABEL,text_color=COR_TEXTO).pack()
        ent=ctk.CTkEntry(win,font=FONTE_LABEL,width=180,justify="center",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO)
        ent.insert(0,"0,00"); ent.pack(pady=8)
        def confirmar():
            try: v=float(ent.get().replace(",","."))
            except: v=0.0
            abrir_caixa(v); cx=caixa_aberto()
            if cx: self.caixa_id=cx["id"]
            win.destroy()
        ctk.CTkButton(win,text="Abrir Caixa",font=FONTE_BTN,fg_color=COR_SUCESSO,hover_color=COR_SUCESSO2,text_color="white",command=confirmar).pack(pady=12)

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=80)
        hdr.grid(row=0,column=0,columnspan=2,sticky="ew"); hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1,weight=1)
        esq=ctk.CTkFrame(hdr,fg_color="transparent"); esq.grid(row=0,column=0,padx=20,pady=12,sticky="w")
        ctk.CTkLabel(esq,text="🛒  PDV — Ponto de Venda",font=FONTE_TITULO,text_color=COR_ACENTO).pack(anchor="w")
        self.lbl_modo=ctk.CTkLabel(esq,text="● Venda Normal",font=FONTE_SMALL,text_color=COR_SUCESSO); self.lbl_modo.pack(anchor="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=16,sticky="e")
        ctk.CTkLabel(bf,text="Código/Nome:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(side="left",padx=(0,6))
        from telas.busca_produto import BuscaProdutoWidget
        self._busca_widget = BuscaProdutoWidget(bf, self._adicionar_item, width=420)
        self.ent_busca = self._busca_widget.entry
        self.ent_busca.pack(side="left")
        ctk.CTkLabel(bf,text="Qtde:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(side="left",padx=(10,4))
        self.ent_qtde=ctk.CTkEntry(bf,width=60,font=FONTE_LABEL,justify="center",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO)
        self.ent_qtde.insert(0,"1"); self.ent_qtde.pack(side="left")
        ctk.CTkLabel(bf,text="Peso(kg):",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(side="left",padx=(10,4))
        self.ent_peso=ctk.CTkEntry(bf,width=70,font=FONTE_LABEL,justify="center",placeholder_text="0.000",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO)
        self.ent_peso.pack(side="left")
        ctk.CTkButton(bf,text="➕ Add",width=80,font=FONTE_BTN,fg_color=COR_ACENTO,hover_color=COR_ACENTO2,text_color="white",command=self._buscar_produto).pack(side="left",padx=(8,0))
        ctk.CTkButton(bf,text="🔍",width=40,font=FONTE_BTN,fg_color=COR_CARD2,hover_color=COR_BORDA,text_color=COR_TEXTO,border_width=1,border_color=COR_BORDA2,command=self._abrir_pesquisa).pack(side="left",padx=(4,0))

    def _build_tabela(self):
        frame=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=1,column=0,padx=(16,8),pady=12,sticky="nsew")
        frame.grid_rowconfigure(1,weight=1); frame.grid_columnconfigure(0,weight=1)
        cols=["#","Descrição","Cód.Barras","Qtde","Unit.","Desc","Total",""]
        pesos=[1,5,3,1,2,2,2,1]
        cab=ctk.CTkFrame(frame,fg_color=COR_ACENTO_LIGHT,corner_radius=8,height=48)
        cab.grid(row=0,column=0,sticky="ew",padx=8,pady=(8,0)); cab.grid_propagate(False)
        for i,(col,peso) in enumerate(zip(cols,pesos)):
            cab.grid_columnconfigure(i,weight=peso)
            ctk.CTkLabel(cab,text=col,font=("Courier New",13,"bold"),text_color=COR_ACENTO).grid(row=0,column=i,padx=8,pady=8,sticky="w")
        self.scroll_itens=ctk.CTkScrollableFrame(frame,fg_color="transparent")
        self.scroll_itens.grid(row=1,column=0,sticky="nsew",padx=8,pady=8)
        self.scroll_itens.grid_columnconfigure(0,weight=1)
        self._linha_vazia()

    def _linha_vazia(self):
        ctk.CTkLabel(self.scroll_itens,text="Nenhum item adicionado.\nEscaneie ou pesquise um produto.",font=FONTE_LABEL,text_color=COR_TEXTO_SUB,justify="center").grid(row=0,column=0,pady=60)

    def _redesenhar_itens(self):
        for w in self.scroll_itens.winfo_children(): w.destroy()
        if not self.itens: self._linha_vazia(); self._atualizar_totais(); return
        self._item_selecionado = getattr(self, "_item_selecionado", None)
        pesos=[1,6,3,2,2,2,2,2,1]
        for idx,item in enumerate(self.itens):
            selecionado = (self._item_selecionado == idx)
            cor_bg = "#D1E8FF" if selecionado else (COR_LINHA_PAR if idx%2==0 else COR_CARD)
            row_f=ctk.CTkFrame(self.scroll_itens,fg_color=cor_bg,corner_radius=6,height=52)
            row_f.grid(row=idx,column=0,sticky="ew",pady=1); row_f.grid_propagate(False)
            for i,p in enumerate(pesos): row_f.grid_columnconfigure(i,weight=p)
            peso_txt=f'{item.get("peso",0):.3f}' if item.get("peso",0)>0 else "—"
            dados=[str(idx+1),item["nome_produto"][:35],item["codigo_barras"] or "",
                   f'{item["quantidade"]:.3f}'.rstrip("0").rstrip("."),peso_txt,
                   f'R$ {item["preco_unitario"]:.2f}',f'R$ {item.get("desconto",0):.2f}',
                   f'R$ {item["total_item"]:.2f}']
            cores=[COR_TEXTO_SUB,COR_TEXTO,COR_TEXTO_SUB,COR_ACENTO,COR_TEXTO_SUB,COR_TEXTO,COR_PERIGO,COR_SUCESSO]
            for i,(val,cor) in enumerate(zip(dados,cores)):
                lbl = ctk.CTkLabel(row_f,text=val,font=("Courier New",13,"bold"),text_color=cor)
                lbl.grid(row=0,column=i,padx=6,sticky="w")
                lbl.bind("<Button-1>", lambda e, i=idx: self._selecionar_item(i))
            row_f.bind("<Button-1>", lambda e, i=idx: self._selecionar_item(i))
            i_cap=idx
            ctk.CTkButton(row_f,text="✕",width=28,height=24,font=("Arial",10),fg_color=COR_PERIGO,hover_color=COR_PERIGO2,text_color="white",corner_radius=4,command=lambda i=i_cap:self._remover_item(i)).grid(row=0,column=8,padx=4)
        self._atualizar_totais()

    def _selecionar_item(self, idx):
        """Seleciona item na lista — DEL para remover"""
        self._item_selecionado = idx
        self._redesenhar_itens()
        # Garante que DEL funciona na janela principal
        self.winfo_toplevel().bind("<Delete>", self._del_item_selecionado)
        self.winfo_toplevel().bind("<BackSpace>", self._del_item_selecionado)

    def _del_item_selecionado(self, event=None):
        """Remove o item selecionado ao pressionar DEL"""
        idx = getattr(self, "_item_selecionado", None)
        if idx is None or idx >= len(self.itens):
            return
        item = self.itens[idx]
        if messagebox.askyesno(
            "Cancelar Item",
            f"Cancelar item #{idx+1}?\n\n"
            f"{item['nome_produto']}\n"
            f"R$ {item['total_item']:.2f}",
            parent=self
        ):
            self.itens.pop(idx)
            self._item_selecionado = None
            self._redesenhar_itens()

    def _build_painel_direito(self):
        painel=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        painel.grid(row=1,column=1,padx=(8,16),pady=12,sticky="nsew"); painel.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(painel,text="RESUMO DA VENDA",font=("Courier New",10,"bold"),text_color=COR_ACENTO).pack(pady=(10,4))
        def linha_valor(label,var_attr,cor=COR_TEXTO):
            f=ctk.CTkFrame(painel,fg_color="transparent"); f.pack(fill="x",padx=20,pady=2)
            ctk.CTkLabel(f,text=label,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(side="left")
            lbl=ctk.CTkLabel(f,text="R$ 0,00",font=FONTE_LABEL,text_color=cor); lbl.pack(side="right")
            setattr(self,var_attr,lbl)
        linha_valor("Subtotal:","lbl_subtotal"); linha_valor("Desconto:","lbl_desconto",COR_PERIGO)
        ctk.CTkFrame(painel,height=1,fg_color=COR_BORDA).pack(fill="x",padx=20,pady=2)
        self.lbl_total=ctk.CTkLabel(painel,text="R$ 0,00",font=("Georgia",22,"bold"),text_color=COR_ACENTO); self.lbl_total.pack(pady=(0,0))
        ctk.CTkLabel(painel,text="TOTAL",font=("Courier New",10),text_color=COR_TEXTO_SUB).pack()
        ctk.CTkFrame(painel,height=1,fg_color=COR_BORDA).pack(fill="x",padx=20,pady=2)
        f=ctk.CTkFrame(painel,fg_color="transparent"); f.pack(fill="x",padx=20,pady=2)
        ctk.CTkLabel(f,text="Itens:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(side="left")
        self.lbl_qtde_itens=ctk.CTkLabel(f,text="0",font=FONTE_LABEL,text_color=COR_TEXTO); self.lbl_qtde_itens.pack(side="right")
        self.lbl_cliente_venda=ctk.CTkLabel(painel,text="👤 Sem cliente",font=FONTE_SMALL,text_color=COR_TEXTO_SUB); self.lbl_cliente_venda.pack(pady=(1,0))
        ctk.CTkFrame(painel,height=1,fg_color=COR_BORDA).pack(fill="x",padx=20,pady=4)
        ctk.CTkLabel(painel,text="Modo:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack()
        self.cmb_modo=ctk.CTkComboBox(painel,values=["NORMAL","ORÇAMENTO","CONSIGNAÇÃO","PRAZO"],font=FONTE_SMALL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO,command=self._mudar_modo)
        self.cmb_modo.set("NORMAL"); self.cmb_modo.pack(fill="x",padx=16,pady=(1,2))
        for txt,cor,hover,cmd in [
            ("💳  RECEBER",   COR_SUCESSO, COR_SUCESSO2, self._receber),
            ("🏷️  Desconto",  COR_AVISO,   "#D97706",    self._aplicar_desconto),
            ("🗑️  Limpar",    COR_PERIGO,  COR_PERIGO2,  self._limpar_venda),
        ]:
            ctk.CTkButton(painel,text=txt,font=FONTE_BTN,fg_color=cor,hover_color=hover,text_color="white",height=38,corner_radius=8,command=cmd).pack(fill="x",padx=16,pady=2)

        ctk.CTkFrame(painel,height=1,fg_color=COR_BORDA).pack(fill="x",padx=16,pady=2)

        # ── Produto Avulso (salgados, pães, etc sem código) ──
        ctk.CTkLabel(painel, text="🏷️ PRODUTO AVULSO",
                     font=("Courier New",9,"bold"),
                     text_color=COR_ACENTO).pack(pady=(2,1))

        f_av = ctk.CTkFrame(painel, fg_color=COR_CARD2, corner_radius=8)
        f_av.pack(fill="x", padx=16, pady=(0,2))

        self.ent_av_desc = ctk.CTkEntry(
            f_av, placeholder_text="Descrição (ex: Salgado)",
            font=FONTE_SMALL, height=30,
            fg_color=COR_CARD, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_av_desc.pack(fill="x", padx=8, pady=(6,2))

        f_av2 = ctk.CTkFrame(f_av, fg_color="transparent")
        f_av2.pack(fill="x", padx=8, pady=(2,6))
        f_av2.columnconfigure(0, weight=2)
        f_av2.columnconfigure(1, weight=1)
        f_av2.columnconfigure(2, weight=1)

        self.ent_av_valor = ctk.CTkEntry(
            f_av2, placeholder_text="R$ Valor",
            font=FONTE_SMALL, height=30,
            fg_color=COR_CARD, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_av_valor.grid(row=0, column=0, padx=(0,4), sticky="ew")
        self.ent_av_valor.bind("<Return>", lambda e: self._adicionar_avulso())

        self.ent_av_qtde = ctk.CTkEntry(
            f_av2, placeholder_text="Qtd",
            font=FONTE_SMALL, height=30, width=50,
            fg_color=COR_CARD, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_av_qtde.insert(0, "1")
        self.ent_av_qtde.grid(row=0, column=1, padx=(0,4), sticky="ew")

        ctk.CTkButton(
            f_av2, text="➕",
            font=FONTE_BTN, height=30, width=36,
            fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
            text_color="white", corner_radius=6,
            command=self._adicionar_avulso
        ).grid(row=0, column=2, sticky="ew")

        ctk.CTkFrame(painel,height=1,fg_color=COR_BORDA).pack(fill="x",padx=16,pady=2)

        f_rod = ctk.CTkFrame(painel, fg_color="transparent")
        f_rod.pack(fill="x", padx=16, pady=(2,4))
        f_rod.grid_columnconfigure((0,1), weight=1)
        ctk.CTkButton(f_rod,text="💵 Sangria",font=FONTE_BTN_SM,
            fg_color="#6B7280",hover_color="#4B5563",text_color="white",
            height=34,corner_radius=8,
            command=self._abrir_sangria).grid(row=0,column=0,padx=(0,3),sticky="ew")
        ctk.CTkButton(f_rod,text="🔒 Fechar Cx",font=FONTE_BTN_SM,
            fg_color="#374151",hover_color="#1F2937",text_color="white",
            height=34,corner_radius=8,
            command=self._fechar_caixa).grid(row=0,column=1,padx=(3,0),sticky="ew")

    def _build_rodape(self):
        rod=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=32)
        rod.grid(row=2,column=0,columnspan=2,sticky="ew"); rod.grid_propagate(False); rod.grid_columnconfigure(2,weight=1)
        self.lbl_status_cx=ctk.CTkLabel(rod,text=f"● Caixa #{self.caixa_id or '?'} — Aberto",font=FONTE_SMALL,text_color=COR_SUCESSO)
        self.lbl_status_cx.grid(row=0,column=0,padx=16,pady=6,sticky="w")
        self.lbl_vendedor=ctk.CTkLabel(rod,text=f"Vendedor: {self.vendedor_atual}",font=FONTE_SMALL,text_color=COR_TEXTO_SUB)
        self.lbl_vendedor.grid(row=0,column=1,sticky="w",padx=8)
        ctk.CTkLabel(rod,text="F2=Clientes  F3=Produtos  F6=Vendedor  F9=Receber  ESC=Cancelar",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=0,column=2,sticky="e",padx=16)

    def _focar_busca(self):
        """Retorna foco ao campo de busca — essencial para o leitor de código de barras"""
        try:
            self.ent_busca.focus_set()
            self.ent_busca.select_range(0, "end")
        except Exception:
            pass

    def _checar_foco(self):
        """Se não tiver janela filha aberta, devolve foco ao campo de busca (leitor)"""
        try:
            toplevels = [w for w in self.winfo_toplevel().winfo_children()
                         if isinstance(w, ctk.CTkToplevel) and w.winfo_exists()]
            if not toplevels:
                campos_excluidos = []
                if hasattr(self, "ent_qtde"): campos_excluidos.append(self.ent_qtde)
                if hasattr(self, "ent_peso"): campos_excluidos.append(self.ent_peso)
                if self.focus_get() not in campos_excluidos:
                    self.ent_busca.focus_set()
        except Exception:
            pass

    def _bind_teclas(self):
        root = self.winfo_toplevel()
        root.bind("<F2>", lambda e: self._abrir_clientes())
        root.bind("<F3>", lambda e: self._abrir_pesquisa())
        root.bind("<F6>", lambda e: self._trocar_vendedor())
        root.bind("<F9>", lambda e: self._receber())
        def _esc_seguro(e):
            try:
                widget = self.focus_get()
                if widget and str(self) in str(widget):
                    self._limpar_venda()
            except Exception:
                pass
        root.bind("<Escape>", _esc_seguro)
        # FocusIn removido — causava piscar na tela de login
        self.bind("<Destroy>", lambda e: self._fechar_busca())
        self.ent_busca.focus_set()

    def _fechar_busca(self):
        try:
            if hasattr(self, "_busca_widget"):
                self._busca_widget._fechar()
        except Exception:
            pass

    def _mudar_modo(self,modo):
        self.modo_venda=modo
        cores={"NORMAL":(COR_SUCESSO,"● Venda Normal"),"ORÇAMENTO":(COR_INFO,"● Orçamento"),"CONSIGNAÇÃO":(COR_AVISO,"● Consignação"),"PRAZO":("#8B5CF6","● Venda a Prazo")}
        cor,txt=cores.get(modo,(COR_SUCESSO,f"● {modo}"))
        self.lbl_modo.configure(text=txt,text_color=cor)

    def _abrir_clientes(self):
        import tkinter as tk
        from telas.clientes import listar_clientes

        win = ctk.CTkToplevel(self)
        win.title("F2 — Clientes")
        win.geometry("680x480")
        win.configure(fg_color=COR_CARD)
        win.grab_set()

        ctk.CTkLabel(win, text="👥  Selecionar Cliente",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(16,4))
        ctk.CTkLabel(win, text="↑↓ navegar  •  Enter selecionar  •  ESC fechar",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack()

        ent = ctk.CTkEntry(win, font=FONTE_LABEL, width=440,
                           placeholder_text="Buscar cliente...",
                           fg_color=COR_CARD2, border_color=COR_BORDA2,
                           text_color=COR_TEXTO)
        ent.pack(pady=6)

        # Frame nativo para evitar conflito mouse/teclado
        f_outer = tk.Frame(win, bg="#B45309")
        f_outer.pack(fill="both", expand=True, padx=16, pady=8)
        f_inner = tk.Frame(f_outer, bg="white")
        f_inner.pack(fill="both", expand=True, padx=1, pady=1)

        estado = {"idx": -1, "lista": [], "labels": []}

        def popular(busca=""):
            for w in f_inner.winfo_children(): w.destroy()
            estado["labels"].clear()
            estado["idx"] = -1
            clientes = listar_clientes(busca)
            estado["lista"] = clientes
            for i, c in enumerate(clientes):
                fiado = f" | Fiado: R$ {c['saldo_fiado']:.2f}" if c["saldo_fiado"] > 0 else ""
                txt   = f"  {c['nome']:<30}  {c['telefone'] or '':>15}{fiado}"
                bg    = "#F5F5F0" if i % 2 == 0 else "white"
                lbl   = tk.Label(f_inner, text=txt,
                                font=("Courier New", 11),
                                fg="#1A1A2E", bg=bg,
                                anchor="w", cursor="hand2")
                lbl.pack(fill="x", pady=1)
                lbl.bind("<Button-1>", lambda e, cc=c: [self._vincular_cliente(cc), win.destroy()])
                estado["labels"].append((lbl, bg))
            ent.focus_set()

        def destacar(idx):
            estado["idx"] = idx
            for i, (lbl, bg) in enumerate(estado["labels"]):
                lbl.configure(bg="#B45309" if i==idx else bg,
                             fg="white"   if i==idx else "#1A1A2E")

        def on_key(e):
            if e.keysym in ("Up","Down","Return","Escape"): return "break"
            popular(ent.get())

        def on_down(e):
            n = len(estado["labels"])
            if n == 0: return "break"
            novo = min(estado["idx"]+1, n-1) if estado["idx"] >= 0 else 0
            destacar(novo)
            return "break"

        def on_up(e):
            n = len(estado["labels"])
            if n == 0: return "break"
            novo = max(estado["idx"]-1, 0)
            destacar(novo)
            return "break"

        def on_enter(e=None):
            idx = estado["idx"]
            if 0 <= idx < len(estado["lista"]):
                self._vincular_cliente(estado["lista"][idx])
                win.destroy()
            elif len(estado["lista"]) == 1:
                self._vincular_cliente(estado["lista"][0])
                win.destroy()
            return "break"

        ent.bind("<KeyRelease>", on_key)
        ent.bind("<Down>",       on_down)
        ent.bind("<Up>",         on_up)
        ent.bind("<Return>",     on_enter)
        win.bind("<Escape>",     lambda e: win.destroy())

        popular()
        ent.focus_set()

    def _vincular_cliente(self,cliente):
        self.cliente_venda=cliente
        self.lbl_cliente_venda.configure(text=f"👤 {cliente['nome']}",text_color=COR_ACENTO)
        self.lbl_status_cx.configure(text=f"● Caixa #{self.caixa_id} — Aberto  |  👤 {cliente['nome']}")

    def _trocar_vendedor(self):
        from banco.database import get_conn
        conn=get_conn(); vendedores=conn.execute("SELECT nome FROM usuarios WHERE ativo=1 ORDER BY nome").fetchall(); conn.close()
        win=ctk.CTkToplevel(self); win.title("F6 — Vendedor"); win.geometry("320x300")
        win.configure(fg_color=COR_CARD); win.grab_set()
        ctk.CTkLabel(win,text="👤  Selecionar Vendedor",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=(20,12))
        scroll=ctk.CTkScrollableFrame(win,fg_color=COR_CARD2); scroll.pack(fill="both",expand=True,padx=24,pady=8)
        for v in vendedores:
            ctk.CTkButton(scroll,text=v["nome"],font=FONTE_LABEL,fg_color="transparent",hover_color=COR_ACENTO_LIGHT,text_color=COR_TEXTO,height=38,command=lambda n=v["nome"]:[setattr(self,"vendedor_atual",n),self.lbl_vendedor.configure(text=f"Vendedor: {n}"),win.destroy()]).pack(fill="x",pady=2)

    def _buscar_produto(self, event=None):
        codigo = self.ent_busca.get().strip()
        if not codigo: return

        # ── 1. Detectar código de BALANÇA (EAN-13 começando com 2) ──
        if len(codigo) == 13 and codigo.startswith("2") and codigo.isdigit():
            resultado = self._processar_codigo_balanca(codigo)
            if resultado:
                self.ent_busca.delete(0, "end")
                self.after(50, self._focar_busca)
                return

        # ── 3. Produto normal ──
        prod = buscar_produto_por_codigo(codigo)
        if prod:
            self._adicionar_item(prod)
            self.ent_busca.delete(0, "end")
            self.after(50, self._focar_busca)
        else:
            lista = listar_produtos(codigo)
            if len(lista) == 1:
                self._adicionar_item(lista[0])
                self.ent_busca.delete(0, "end")
                self.after(50, self._focar_busca)
            elif len(lista) > 1:
                self._abrir_pesquisa(lista)
            else:
                self._abrir_cadastro_produto(codigo)

    def _processar_codigo_balanca(self, codigo):
        """
        Processa código EAN-13 da balança Toledo Prix 4.
        Formato da etiqueta: 2 PPPPP XX VVVV D
          [0]    = 2 (produto pesado)
          [1-5]  = código PLU do produto (5 dígitos)
          [6-7]  = separador (geralmente 00)
          [8-11] = valor total em centavos (4 dígitos)
          [12]   = dígito verificador
        Exemplo: 2 00003 00 0642 7
          PLU=00003, Valor=R$6,42
        """
        try:
            # Extrai código PLU do produto (posições 1-5)
            cod_plu     = codigo[1:6]          # ex: "00003"
            cod_limpo   = cod_plu.lstrip("0") or "0"  # ex: "3"

            # Extrai valor total em centavos (posições 8-11)
            valor_cents = int(codigo[8:12])
            valor_total = valor_cents / 100     # ex: 642 → R$ 6,42

            if valor_total <= 0:
                return False

            # Busca produto — tenta de várias formas
            prod = None

            # 1. Pelo código PLU com zeros (ex: "00003")
            prod = buscar_produto_por_codigo(cod_plu)

            # 2. Pelo PLU sem zeros (ex: "3")
            if not prod:
                prod = buscar_produto_por_codigo(cod_limpo)

            # 3. Por busca parcial
            if not prod:
                from banco.database import listar_produtos
                lista = listar_produtos(cod_limpo)
                prod  = lista[0] if len(lista) == 1 else None

            if not prod:
                messagebox.showwarning(
                    "⚖️ Balança Toledo Prix 4",
                    f"Código de balança detectado!\n\n"
                    f"PLU do produto: {cod_plu}\n"
                    f"Valor: R$ {valor_total:.2f}\n\n"
                    f"Produto não encontrado no sistema.\n"
                    f"Cadastre o produto com código: {cod_plu}",
                    parent=self)
                return True

            # Calcula quantidade baseado no valor e preço
            if prod["preco_venda"] > 0:
                peso_kg = round(valor_total / prod["preco_venda"], 3)
            else:
                peso_kg = 1.0

            # Adiciona na venda com valor já calculado pela balança
            self.itens.append({
                "produto_id":     prod["id"],
                "nome_produto":   f"{prod['nome']} ({peso_kg:.3f}kg)",
                "codigo_barras":  codigo,
                "unidade":        "KG",
                "quantidade":     peso_kg,
                "peso":           peso_kg,
                "preco_unitario": prod["preco_venda"],
                "desconto":       0.0,
                "total_item":     valor_total,  # usa o valor da balança direto!
            })
            self._redesenhar_itens()
            return True

        except Exception as e:
            print(f"[Toledo Prix 4] Erro: {e}")
            return False

    def _cancelar_item_por_numero(self, numero):
        """Cancela item pelo número na lista (ex: digitar C2 cancela item 2)"""
        idx = numero - 1
        if 0 <= idx < len(self.itens):
            item = self.itens[idx]
            if messagebox.askyesno(
                "Cancelar Item",
                f"Cancelar item #{numero}?\n\n{item['nome_produto']}\n"
                f"R$ {item['total_item']:.2f}",
                parent=self
            ):
                self.itens.pop(idx)
                self._redesenhar_itens()
        else:
            messagebox.showwarning(
                "Item não encontrado",
                f"Item #{numero} não existe na venda atual.",
                parent=self)

    def _adicionar_avulso(self):
        """Adiciona produto avulso sem código de barras na venda"""
        desc      = self.ent_av_desc.get().strip() or "Produto Avulso"
        valor_raw = self.ent_av_valor.get().strip().replace(",", ".")
        qtde_raw  = self.ent_av_qtde.get().strip().replace(",", ".")
        try:
            valor = float(valor_raw)
            if valor <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Valor inválido", "Informe um valor maior que zero!", parent=self)
            self.ent_av_valor.focus_set()
            return
        try:
            qtde = float(qtde_raw) if qtde_raw else 1.0
            if qtde <= 0: qtde = 1.0
        except ValueError:
            qtde = 1.0

        self.itens.append({
            "produto_id":    None,
            "nome_produto":  desc,
            "codigo_barras": "AVULSO",
            "unidade":       "UN",
            "quantidade":    qtde,
            "peso":          0.0,
            "preco_unitario": valor,
            "desconto":      0.0,
            "total_item":    round(valor * qtde, 2),
        })
        self._redesenhar_itens()
        self.ent_av_desc.delete(0, "end")
        self.ent_av_valor.delete(0, "end")
        self.ent_av_qtde.delete(0, "end")
        self.ent_av_qtde.insert(0, "1")
        self.ent_av_desc.focus_set()

    def _abrir_cadastro_produto(self, codigo):
        """Abre formulário de cadastro quando produto não está no sistema"""
        from telas.produtos import FormularioProduto

        def pos_cadastro():
            # Após salvar, tenta adicionar o produto novo na venda automaticamente
            prod = buscar_produto_por_codigo(codigo)
            if prod:
                self._adicionar_item(prod)
            self.ent_busca.delete(0, "end")
            self.after(50, self._focar_busca)

        form = FormularioProduto(self.winfo_toplevel(), None, pos_cadastro)

        # Se for código de barras (só números) — pré-preenche e confirma
        if codigo.isdigit():
            form.ent_scan.delete(0, "end")
            form.ent_scan.insert(0, codigo)
            form.after(200, form._on_scan)
        else:
            # Era busca por nome — preenche campo nome
            form.campos["nome"].delete(0, "end")
            form.campos["nome"].insert(0, codigo)
            form.campos["nome"].focus_set()

    def _abrir_pesquisa(self, lista_pre=None):
        win = ctk.CTkToplevel(self)
        win.title("Pesquisar Produto")
        win.geometry("700x520")
        win.configure(fg_color=COR_CARD)
        win.grab_set()

        ctk.CTkLabel(win, text="🔍  Pesquisar Produto",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(16,8))

        ctk.CTkLabel(win, text="↑↓ para navegar  •  Enter para selecionar  •  ESC para fechar",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack()

        ent = ctk.CTkEntry(win, font=FONTE_LABEL, width=440,
                           placeholder_text="Nome ou código...",
                           fg_color=COR_CARD2, border_color=COR_BORDA2,
                           text_color=COR_TEXTO)
        ent.pack(pady=6)

        scroll = ctk.CTkScrollableFrame(win, fg_color=COR_CARD2)
        scroll.pack(fill="both", expand=True, padx=16, pady=8)

        # Estado da navegação
        estado = {"idx": -1, "botoes": [], "lista": []}

        def destacar(idx):
            estado["idx"] = idx
            n = len(estado["botoes"])
            for i, btn in enumerate(estado["botoes"]):
                btn.configure(
                    fg_color=COR_LINHA_SEL if i == idx else "transparent",
                    text_color=COR_ACENTO if i == idx else COR_TEXTO)

        def popular(lista):
            for w in scroll.winfo_children():
                w.destroy()
            estado["botoes"].clear()
            estado["lista"] = lista
            estado["idx"]   = -1
            for i, p in enumerate(lista):
                cod  = (p["codigo_barras"] or "S/COD")[:13]
                nome = p["nome"][:35]
                txt  = f"{cod:<13}  |  {nome:<35}  |  R$ {p['preco_venda']:.2f}"
                i_cap = i
                btn = ctk.CTkButton(
                    scroll, text=txt,
                    font=("Courier New", 11),
                    fg_color="transparent",
                    hover_color=COR_ACENTO_LIGHT,
                    anchor="w", height=36,
                    text_color=COR_TEXTO,
                    command=lambda pp=p: [self._adicionar_item(pp), win.destroy()])
                btn.pack(fill="x", pady=1)
                btn.bind("<Enter>", lambda e, i=i_cap: destacar(i))
                estado["botoes"].append(btn)

        def navegar(delta):
            n = len(estado["botoes"])
            if n == 0:
                return
            novo = max(0, min(n-1, estado["idx"] + delta))
            destacar(novo)
            # Scroll suave para o item
            try:
                frac = novo / n
                scroll._parent_canvas.yview_moveto(frac)
            except Exception:
                pass

        def selecionar_enter(event=None):
            idx = estado["idx"]
            if idx >= 0 and idx < len(estado["lista"]):
                self._adicionar_item(estado["lista"][idx])
                win.destroy()
            elif len(estado["lista"]) == 1:
                self._adicionar_item(estado["lista"][0])
                win.destroy()
            elif ent.get().strip():
                from banco.database import buscar_produto_por_codigo
                prod = buscar_produto_por_codigo(ent.get().strip())
                if prod:
                    self._adicionar_item(prod)
                    win.destroy()

        IGNORAR = {"Up","Down","Left","Right","Return","Escape",
                   "Tab","Home","End","Prior","Next",
                   "Shift_L","Shift_R","Control_L","Control_R"}

        def on_key_release(e):
            if e.keysym in IGNORAR:
                return "break"
            popular(listar_produtos(ent.get()))

        def on_down(e):
            navegar(+1)
            return "break"

        def on_up(e):
            navegar(-1)
            return "break"

        ent.bind("<KeyRelease>", on_key_release)
        ent.bind("<Down>",  on_down)
        ent.bind("<Up>",    on_up)
        ent.bind("<Return>", selecionar_enter)
        win.bind("<Escape>", lambda e: win.destroy())

        popular(lista_pre or listar_produtos())
        ent.focus_set()

    def _get_qtde(self):
        try: q=float(self.ent_qtde.get().replace(",",".")); return q if q>0 else 1
        except: return 1

    def _get_peso(self):
        try: p=float(self.ent_peso.get().replace(",",".")); return p if p>0 else 0.0
        except: return 0.0

    def _adicionar_item(self, prod):
        # ── Trata sinal de balança vindo do BuscaProdutoWidget ──
        if isinstance(prod, dict) and prod.get("_balanca"):
            self._processar_codigo_balanca(prod["_codigo"])
            return

        qtde=self._get_qtde(); peso=self._get_peso()
        if prod["unidade"] in("KG","G","L","ML") and peso>0: qtde=peso
        for item in self.itens:
            if item["produto_id"]==prod["id"]:
                item["quantidade"]+=qtde; item["peso"]=item.get("peso",0)+peso
                item["total_item"]=round(item["quantidade"]*item["preco_unitario"]-item.get("desconto",0),2)
                self._redesenhar_itens(); self._reset_campos(); return
        self.itens.append({"produto_id":prod["id"],"nome_produto":prod["nome"],"codigo_barras":prod["codigo_barras"] or "","unidade":prod["unidade"],"quantidade":qtde,"peso":peso,"preco_unitario":prod["preco_venda"],"desconto":0.0,"total_item":round(prod["preco_venda"]*qtde,2)})
        self._reset_campos(); self._redesenhar_itens()

    def _reset_campos(self):
        self.ent_qtde.delete(0,"end"); self.ent_qtde.insert(0,"1"); self.ent_peso.delete(0,"end")

    def _remover_item(self,idx): self.itens.pop(idx); self._redesenhar_itens()

    def _atualizar_totais(self):
        subtotal=sum(i["total_item"] for i in self.itens); total=max(0,subtotal-self.desconto_global)
        self.lbl_subtotal.configure(text=f"R$ {subtotal:.2f}"); self.lbl_desconto.configure(text=f"R$ {self.desconto_global:.2f}")
        self.lbl_total.configure(text=f"R$ {total:.2f}"); self.lbl_qtde_itens.configure(text=str(len(self.itens)))

    def _aplicar_desconto(self):
        v=simpledialog.askfloat("Desconto","Valor do desconto (R$):",minvalue=0,parent=self)
        if v is not None: self.desconto_global=v; self._atualizar_totais()

    def _limpar_venda(self):
        if messagebox.askyesno("Limpar","Cancelar a venda atual?"):
            self.itens.clear(); self.desconto_global=0.0; self.cliente_venda=None
            self.lbl_cliente_venda.configure(text="👤 Sem cliente",text_color=COR_TEXTO_SUB)
            self._redesenhar_itens()

    def _receber(self):
        if not self.itens: messagebox.showwarning("Venda vazia","Adicione produtos."); return
        # ── Bloquear venda sem caixa aberto ──────────────────────────────────
        if not self.caixa_id:
            resp = messagebox.askyesno(
                "⚠️ Caixa não aberto",
                "Nenhum caixa aberto!\n\n"
                "Todas as vendas realizadas sem caixa aberto\n"
                "NÃO aparecem no fechamento.\n\n"
                "Deseja abrir o caixa agora?",
                icon="warning"
            )
            if resp:
                self._dialogo_abrir_caixa()
            if not self.caixa_id:
                messagebox.showwarning(
                    "Venda bloqueada",
                    "Abra o caixa antes de realizar vendas."
                )
                return
        # ─────────────────────────────────────────────────────────────────────
        subtotal=sum(i["total_item"] for i in self.itens); total=max(0,subtotal-self.desconto_global)
        modo=self.cmb_modo.get()
        if modo=="ORÇAMENTO": self._salvar_orcamento(total); return
        if modo=="CONSIGNAÇÃO": self._salvar_consignacao(total); return
        if modo=="PRAZO": DialogoPrazo(self,total,self._finalizar_venda_prazo); return
        DialogoReceber(self,total,self._finalizar_venda)

    def _finalizar_venda(self,forma,valor_pago,cpf):
        itens_copia=list(self.itens); subtotal=sum(i["total_item"] for i in itens_copia)
        venda_id,total,troco=registrar_venda(self.caixa_id,itens_copia,forma,valor_pago,self.desconto_global,cpf)
        try:
            from utils.impressora import imprimir_cupom
            ok,msg_imp=imprimir_cupom(venda_id=venda_id,itens=itens_copia,subtotal=subtotal,desconto=self.desconto_global,total=total,forma_pagamento=forma,valor_pago=valor_pago,troco=troco,cpf=cpf)
        except Exception as e: msg_imp=f"Cupom: {e}"
        messagebox.showinfo("Venda Concluída",f"✅  Venda #{venda_id}\n\nTotal: R$ {total:.2f}\nPago: R$ {valor_pago:.2f}\nTroco: R$ {troco:.2f}\nForma: {forma}\n\n{msg_imp}")
        if messagebox.askyesno("NFC-e","Emitir NFC-e?"): self._emitir_nfce(venda_id,itens_copia,total,self.desconto_global,forma,cpf)
        self._limpar_pos_venda()

    def _finalizar_venda_prazo(self,prazo_dias,cpf):
        if not self.cliente_venda: messagebox.showerror("Erro","Selecione cliente (F2)."); return
        itens_copia=list(self.itens); subtotal=sum(i["total_item"] for i in itens_copia)
        total=max(0,subtotal-self.desconto_global)
        venda_id,total,_=registrar_venda(self.caixa_id,itens_copia,"PRAZO",0,self.desconto_global,cpf)
        from telas.clientes import lancar_fiado
        from datetime import timedelta
        venc=(datetime.now()+timedelta(days=prazo_dias)).strftime("%d/%m/%Y")
        lancar_fiado(self.cliente_venda["id"],f"Venda #{venda_id} — vence {venc}",total,venda_id)
        messagebox.showinfo("Venda a Prazo",f"✅ Venda #{venda_id}\nTotal: R$ {total:.2f}\nVencimento: {venc}\nCliente: {self.cliente_venda['nome']}")
        self._limpar_pos_venda()

    def _salvar_orcamento(self,total):
        from banco.database import get_conn
        import json; conn=get_conn()
        conn.execute("CREATE TABLE IF NOT EXISTS orcamentos(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,total REAL,itens TEXT,data TEXT DEFAULT(datetime('now','localtime')),status TEXT DEFAULT 'ABERTO')")
        conn.execute("INSERT INTO orcamentos(cliente,total,itens) VALUES(?,?,?)",(self.cliente_venda["nome"] if self.cliente_venda else "—",total,json.dumps(self.itens,ensure_ascii=False))); conn.commit(); conn.close()
        messagebox.showinfo("Orçamento",f"✅ Orçamento salvo!\nTotal: R$ {total:.2f}"); self._limpar_pos_venda()

    def _salvar_consignacao(self,total):
        if not self.cliente_venda: messagebox.showerror("Erro","Selecione cliente (F2)."); return
        from banco.database import get_conn
        import json; conn=get_conn()
        conn.execute("CREATE TABLE IF NOT EXISTS consignacoes(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente_id INTEGER,cliente_nome TEXT,total REAL,itens TEXT,data TEXT DEFAULT(datetime('now','localtime')),status TEXT DEFAULT 'ABERTO')")
        conn.execute("INSERT INTO consignacoes(cliente_id,cliente_nome,total,itens) VALUES(?,?,?,?)",(self.cliente_venda["id"],self.cliente_venda["nome"],total,json.dumps(self.itens,ensure_ascii=False))); conn.commit(); conn.close()
        messagebox.showinfo("Consignação",f"✅ Consignação!\nCliente: {self.cliente_venda['nome']}\nTotal: R$ {total:.2f}"); self._limpar_pos_venda()

    def _limpar_pos_venda(self):
        self.itens.clear(); self.desconto_global=0.0; self.cliente_venda=None
        self.lbl_cliente_venda.configure(text="👤 Sem cliente",text_color=COR_TEXTO_SUB)
        self.cmb_modo.set("NORMAL"); self._mudar_modo("NORMAL"); self._redesenhar_itens()

    def _emitir_nfce(self,venda_id,itens,total,desconto,forma,cpf):
        try:
            from fiscal.nfce import emitir_nfce
            ok,msg,_=emitir_nfce(venda_id,itens,total,desconto,forma,cpf)
            if ok: messagebox.showinfo("NFC-e",msg)
            else: messagebox.showwarning("NFC-e",msg)
        except Exception as e: messagebox.showerror("NFC-e",f"Erro: {e}")

    def _sangria(self):
        pass  # Sangria no menu principal

    def _suprimento(self):
        pass  # Suprimento no menu principal

    def _abrir_sangria(self):
        """Abre sangria/suprimento direto do PDV"""
        from telas.sangria import TelaSangria
        win = ctk.CTkToplevel(self)
        win.title("Sangria / Suprimento")
        win.geometry("900x600")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        tela = TelaSangria(frame, self.vendedor_atual)
        tela.grid(row=0, column=0, sticky="nsew")

    def _abrir_config(self):
        """Abre configurações direto do PDV"""
        from telas.configuracoes import TelaConfiguracoes
        win = ctk.CTkToplevel(self)
        win.title("Configurações")
        win.geometry("900x680")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        TelaConfiguracoes(win).pack(fill="both", expand=True)

    def _fechar_caixa(self):
        if not self.caixa_id:
            messagebox.showwarning("Aviso","Nenhum caixa aberto."); return
        from telas.fechamento import TelaFechamentoCaixa
        win = ctk.CTkToplevel(self)
        win.title("Fechamento de Caixa")
        win.geometry("900x680")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        def pos_fechar():
            self.caixa_id = None
            self.lbl_status_cx.configure(
                text="● Caixa FECHADO", text_color=COR_PERIGO)
            win.destroy()
        tela = TelaFechamentoCaixa(frame, usuario=self.vendedor_atual)
        tela.grid(row=0, column=0, sticky="nsew")

class DialogoReceber(ctk.CTkToplevel):
    def __init__(self, master, total, callback):
        super().__init__(master)
        self.title("Finalizar Pagamento")
        self.geometry("480x600")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self.resizable(False, False)
        self.total               = total
        self.callback            = callback
        self.forma_sel           = "DINHEIRO"
        self.subcategoria_cartao = None
        self.pagamentos          = []
        self._build()
        self.bind("<F9>", lambda e: self._confirmar())

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_ACENTO_LIGHT, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="Finalizar Pagamento",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(hdr, text=f"R$ {self.total:.2f}",
                     font=("Georgia", 20, "bold"),
                     text_color=COR_SUCESSO).pack(side="right", padx=16)

        ctk.CTkLabel(self, text="Forma:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=16, pady=(8,2))
        self.btns_forma = {}
        grade_f = ctk.CTkFrame(self, fg_color="transparent")
        grade_f.pack(fill="x", padx=16)
        formas = [("Dinheiro","DINHEIRO"),("PIX","PIX"),
                  ("Cartao","CARTAO"),("Fiado","FIADO")]
        for i, (label, val) in enumerate(formas):
            r, c = divmod(i, 2)
            f = ctk.CTkFrame(grade_f, fg_color=COR_CARD2, corner_radius=8,
                             border_width=1, border_color=COR_BORDA,
                             width=110, height=40)
            f.grid(row=r, column=c, padx=3, pady=3, sticky="ew")
            f.pack_propagate(False)
            grade_f.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(f, text=label, font=("Georgia",10,"bold"),
                         text_color=COR_TEXTO).place(relx=0.5, rely=0.5, anchor="center")
            val_cap = val
            for w in [f] + f.winfo_children():
                try: w.bind("<Button-1>", lambda e, v=val_cap: self._sel_forma(v))
                except: pass
            self.btns_forma[val] = f

        self.frame_cartao = ctk.CTkFrame(self, fg_color=COR_ACENTO_LIGHT,
                                          corner_radius=8, border_width=1,
                                          border_color=COR_ACENTO)
        self.btns_cartao = {}
        grade_c = ctk.CTkFrame(self.frame_cartao, fg_color="transparent")
        grade_c.pack(padx=4, pady=4)
        tipos = [("Debito","DEBITO"),("Credito","CREDITO"),
                 ("Cred Parc","CREDITO PARCELADO"),
                 ("Vale Alim","VALE ALIMENTACAO")]
        for i, (label, val) in enumerate(tipos):
            r, c = divmod(i, 2)
            btn = ctk.CTkButton(grade_c, text=label, font=("Courier New",10),
                                width=100, height=28,
                                fg_color=COR_CARD, hover_color=COR_ACENTO_LIGHT,
                                text_color=COR_TEXTO, border_width=1,
                                border_color=COR_BORDA2,
                                command=lambda v=val: self._sel_cartao(v))
            btn.grid(row=r, column=c, padx=2, pady=2)
            self.btns_cartao[val] = btn
        self.frame_parcelas = ctk.CTkFrame(self.frame_cartao, fg_color="transparent")
        ctk.CTkLabel(self.frame_parcelas, text="Parcelas:",
                     font=FONTE_SMALL, text_color=COR_ACENTO).pack(side="left", padx=(8,4))
        self.cmb_parcelas = ctk.CTkComboBox(
            self.frame_parcelas,
            values=["2x","3x","4x","5x","6x","7x","8x","9x","10x","11x","12x"],
            font=FONTE_LABEL, width=70,
            fg_color=COR_CARD, border_color=COR_BORDA2, text_color=COR_TEXTO)
        self.cmb_parcelas.set("2x")
        self.cmb_parcelas.pack(side="left", padx=4, pady=4)

        ctk.CTkLabel(self, text="Valor recebido (R$):", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=16, pady=(8,2))
        self.ent_valor = ctk.CTkEntry(
            self, font=("Georgia", 22), height=42, justify="center",
            fg_color=COR_CARD2, border_color=COR_ACENTO,
            border_width=2, text_color=COR_TEXTO)
        self.ent_valor.pack(fill="x", padx=16, pady=(0,4))
        self.ent_valor.insert(0, f"{self.total:.2f}")
        self.ent_valor.bind("<KeyRelease>", self._atualizar_troco)
        self.ent_valor.select_range(0, "end")
        self.ent_valor.focus_set()

        # Botões rápidos de valor
        grade_v = ctk.CTkFrame(self, fg_color="transparent")
        grade_v.pack(fill="x", padx=16, pady=(0,4))
        for i, v in enumerate([5, 10, 20, 50, 100, 200]):
            grade_v.grid_columnconfigure(i, weight=1)
            ctk.CTkButton(grade_v, text=f"R${v}",
                          font=("Georgia",9,"bold"), height=28,
                          fg_color=COR_CARD2, hover_color=COR_ACENTO_LIGHT,
                          text_color=COR_TEXTO, border_width=1,
                          border_color=COR_BORDA2, corner_radius=6,
                          command=lambda val=v: self._set_valor_rapido(val)
                          ).grid(row=0, column=i, padx=1, sticky="ew")

        # Troco — destaque verde
        self.frame_troco = ctk.CTkFrame(self, fg_color=COR_SUCESSO, corner_radius=8)
        self.frame_troco.pack(fill="x", padx=16, pady=(0,4))
        f_troco_inner = ctk.CTkFrame(self.frame_troco, fg_color="transparent")
        f_troco_inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(f_troco_inner, text="TROCO:",
                     font=("Courier New",11,"bold"), text_color="white").pack(side="left")
        self.lbl_troco = ctk.CTkLabel(
            f_troco_inner, text="R$ 0,00",
            font=("Georgia", 22, "bold"), text_color="white")
        self.lbl_troco.pack(side="right")

        ctk.CTkButton(self, text="Valor Exato",
                      font=FONTE_SMALL, height=28,
                      fg_color=COR_ACENTO_LIGHT, hover_color=COR_BORDA,
                      text_color=COR_ACENTO, corner_radius=6,
                      command=self._valor_exato).pack(fill="x", padx=16, pady=(0,4))

        f_misto = ctk.CTkFrame(self, fg_color=COR_CARD2, corner_radius=8)
        f_misto.pack(fill="x", padx=16, pady=(0,4))
        ctk.CTkButton(f_misto, text="+ Adicionar pagamento parcial",
                      font=FONTE_SMALL, height=28,
                      fg_color="transparent", hover_color=COR_BORDA,
                      text_color=COR_ACENTO, corner_radius=6,
                      command=self._adicionar_pagamento).pack(fill="x", padx=4, pady=(4,0))
        self.lbl_pgtos = ctk.CTkLabel(f_misto, text="",
                                       font=FONTE_SMALL, text_color=COR_SUCESSO)
        self.lbl_pgtos.pack(anchor="w", padx=8)
        self.frame_lista_pgtos = ctk.CTkFrame(f_misto, fg_color="transparent")
        self.frame_lista_pgtos.pack(fill="x", padx=4, pady=(0,4))

        fc = ctk.CTkFrame(self, fg_color="transparent")
        fc.pack(fill="x", padx=16, pady=(0,4))
        ctk.CTkLabel(fc, text="CPF:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left")
        self.ent_cpf = ctk.CTkEntry(fc, font=FONTE_LABEL, height=30,
                                     placeholder_text="000.000.000-00",
                                     fg_color=COR_CARD2, border_color=COR_BORDA2,
                                     text_color=COR_TEXTO)
        self.ent_cpf.pack(side="left", fill="x", expand=True, padx=(8,0))

        ctk.CTkButton(
            self, text="F9  CONFIRMAR PAGAMENTO",
            font=("Georgia", 13, "bold"),
            fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
            text_color="white", height=48, corner_radius=0,
            command=self._confirmar
        ).pack(fill="x", side="bottom")

        self._sel_forma("DINHEIRO")
        self._atualizar_troco()

    def _set_valor_rapido(self, val):
        self.ent_valor.delete(0, "end")
        self.ent_valor.insert(0, f"{val:.2f}")
        self._atualizar_troco()

    def _valor_exato(self):
        total_ja = sum(p["valor"] for p in self.pagamentos)
        restante = round(self.total - total_ja, 2)
        self.ent_valor.delete(0, "end")
        self.ent_valor.insert(0, f"{restante:.2f}")
        self._atualizar_troco()

    def _sel_forma(self, forma):
        self.forma_sel = forma
        cores = {"DINHEIRO": COR_SUCESSO, "PIX": COR_INFO,
                 "CARTAO": COR_ACENTO, "FIADO": COR_AVISO}
        for k, f in self.btns_forma.items():
            sel = k == forma
            f.configure(fg_color=COR_ACENTO_LIGHT if sel else COR_CARD2,
                        border_color=cores.get(k, COR_ACENTO) if sel else COR_BORDA,
                        border_width=2 if sel else 1)
        if forma == "CARTAO":
            self.frame_cartao.pack(fill="x", padx=16, pady=(0,4))
        else:
            self.frame_cartao.pack_forget()
            self.frame_parcelas.pack_forget()
            self.subcategoria_cartao = None
        if forma in ("PIX", "FIADO"):
            self._valor_exato()

    def _sel_cartao(self, tipo):
        self.subcategoria_cartao = tipo
        for k, btn in self.btns_cartao.items():
            sel = k == tipo
            btn.configure(fg_color=COR_ACENTO_LIGHT if sel else COR_CARD,
                          border_color=COR_ACENTO if sel else COR_BORDA2,
                          border_width=2 if sel else 1,
                          text_color=COR_ACENTO if sel else COR_TEXTO)
        if tipo == "CREDITO PARCELADO":
            self.frame_parcelas.pack(pady=(0,4))
        else:
            self.frame_parcelas.pack_forget()

    def _atualizar_troco(self, event=None):
        try:
            pago        = float(self.ent_valor.get().replace(",","."))
            total_pgtos = sum(p["valor"] for p in self.pagamentos)
            total_pago  = pago + total_pgtos
            troco       = total_pago - self.total
            if troco >= 0:
                self.lbl_troco.configure(text=f"R$ {troco:.2f}")
                self.frame_troco.configure(fg_color=COR_SUCESSO)
            else:
                self.lbl_troco.configure(text=f"-R$ {abs(troco):.2f}")
                self.frame_troco.configure(fg_color=COR_PERIGO)
        except Exception:
            pass

    def _get_forma_completa(self):
        if self.forma_sel == "CARTAO":
            sub = self.subcategoria_cartao
            if not sub:
                messagebox.showerror("Erro", "Selecione o tipo do cartao.", parent=self)
                return None
            forma = "CARTAO - " + sub
            if sub == "CREDITO PARCELADO":
                forma += " " + self.cmb_parcelas.get()
            return forma
        return self.forma_sel

    def _adicionar_pagamento(self):
        forma = self._get_forma_completa()
        if not forma: return
        try:
            valor = float(self.ent_valor.get().replace(",","."))
            if valor <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Erro","Valor invalido.",parent=self); return
        total_ja = sum(p["valor"] for p in self.pagamentos)
        restante = round(self.total - total_ja, 2)
        if valor > restante + 0.01:
            valor = restante
        self.pagamentos.append({"forma": forma, "valor": valor})
        self._redesenhar_pgtos()
        self._valor_exato()
        self._atualizar_troco()

    def _redesenhar_pgtos(self):
        for w in self.frame_lista_pgtos.winfo_children():
            w.destroy()
        total_pgtos = sum(p["valor"] for p in self.pagamentos)
        if not self.pagamentos:
            self.lbl_pgtos.configure(text="")
            return
        self.lbl_pgtos.configure(
            text="Lancados: R$ " + str(round(total_pgtos,2)) + " | Falta: R$ " + str(max(0,round(self.total-total_pgtos,2))))
        for i, p in enumerate(self.pagamentos):
            f = ctk.CTkFrame(self.frame_lista_pgtos, fg_color="transparent")
            f.pack(fill="x", pady=1)
            ctk.CTkLabel(f, text="[OK] " + p["forma"] + " — R$ " + str(round(p["valor"],2)),
                         font=FONTE_SMALL, text_color=COR_SUCESSO).pack(side="left", padx=4)
            i_cap = i
            ctk.CTkButton(f, text="X", width=22, height=18,
                          font=("Arial",8), fg_color=COR_PERIGO,
                          hover_color=COR_PERIGO2, text_color="white",
                          command=lambda i=i_cap: self._remover_pgto(i)).pack(side="right", padx=2)

    def _remover_pgto(self, idx):
        self.pagamentos.pop(idx)
        self._redesenhar_pgtos()
        self._valor_exato()
        self._atualizar_troco()

    def _confirmar(self):
        try:
            pago_atual = float(self.ent_valor.get().replace(",",".") or "0")
        except ValueError:
            pago_atual = 0.0
        if pago_atual > 0:
            forma = self._get_forma_completa()
            if not forma: return
            self.pagamentos.append({"forma": forma, "valor": pago_atual})
        total_pago = sum(p["valor"] for p in self.pagamentos)
        if total_pago < self.total - 0.01:
            messagebox.showerror("Erro",
                "Valor insuficiente! Faltam R$ " + str(round(self.total-total_pago,2)),
                parent=self)
            if pago_atual > 0: self.pagamentos.pop()
            return
        if len(self.pagamentos) == 1:
            forma_final = self.pagamentos[0]["forma"]
        else:
            partes = [p["forma"] + "(R$" + str(round(p["valor"],2)) + ")" for p in self.pagamentos]
            forma_final = " + ".join(partes)
        self.callback(forma_final, total_pago, self.ent_cpf.get())
        self.destroy()


class DialogoPrazo(ctk.CTkToplevel):
    def __init__(self,master,total,callback):
        super().__init__(master); self.title("Venda a Prazo"); self.geometry("360x280")
        self.configure(fg_color=COR_CARD); self.grab_set(); self.total=total; self.callback=callback; self._build()
    def _build(self):
        ctk.CTkLabel(self,text="📅  Venda a Prazo",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=(24,8))
        ctk.CTkLabel(self,text=f"Total: R$ {self.total:.2f}",font=("Georgia",18,"bold"),text_color=COR_SUCESSO).pack()
        ctk.CTkFrame(self,height=1,fg_color=COR_BORDA).pack(fill="x",padx=24,pady=12)
        ctk.CTkLabel(self,text="Prazo:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack()
        self.cmb=ctk.CTkComboBox(self,values=["7 dias","15 dias","30 dias","60 dias","90 dias"],font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO)
        self.cmb.set("30 dias"); self.cmb.pack(pady=8,padx=24,fill="x")
        ctk.CTkLabel(self,text="CPF (opcional):",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack()
        self.ent_cpf=ctk.CTkEntry(self,font=FONTE_LABEL,width=200,placeholder_text="000.000.000-00",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.ent_cpf.pack(pady=4)
        ctk.CTkButton(self,text="✅  Confirmar",font=FONTE_BTN,fg_color=COR_ACENTO,hover_color=COR_ACENTO2,text_color="white",height=44,command=self._confirmar).pack(fill="x",padx=24,pady=12)
    def _confirmar(self):
        dias=int(self.cmb.get().split()[0]); self.callback(dias,self.ent_cpf.get()); self.destroy()
