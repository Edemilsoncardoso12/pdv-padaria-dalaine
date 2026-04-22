"""telas/estoque.py — Estoque — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from tema import *
from banco.database import listar_produtos, movimentar_estoque, listar_movimentacoes

class TelaEstoque(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        self.produto_selecionado=None
        # Detecta resolução da tela para ajuste responsivo
        self.after(1, self._init_responsivo)

    def _init_responsivo(self):
        try:
            sw = self.winfo_screenwidth()
        except Exception:
            sw = 1366
        # Escala baseada na largura da tela
        if sw < 1024:
            self._escala = 0.75
        elif sw < 1280:
            self._escala = 0.85
        elif sw < 1600:
            self._escala = 1.0
        else:
            self._escala = 1.15

        self._build_header()
        self._build_corpo()
        self._carregar()

    def _s(self, valor):
        """Escala um valor baseado na resolução da tela"""
        return max(1, int(valor * self._escala))

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False); hdr.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(hdr,text="📊  Controle de Estoque",font=FONTE_TITULO,text_color=COR_ACENTO).grid(row=0,column=0,padx=24,pady=18,sticky="w")
        bf=ctk.CTkFrame(hdr,fg_color="transparent"); bf.grid(row=0,column=1,padx=24,sticky="e")
        self.ent_busca = ctk.CTkEntry(bf, width=self._s(200), font=FONTE_LABEL,
                                      placeholder_text="Pesquisar...",
                                      fg_color=COR_CARD2,
                                      border_color=COR_BORDA2,
                                      text_color=COR_TEXTO)
        self.ent_busca.pack(side="left")
        self.idx_nav = -1

        def on_key_est(e):
            if e.keysym in ("Up","Down","Return","Escape"): return "break"
            self._carregar()

        def on_down_est(e):
            if not self.linhas: return "break"
            self.idx_nav = min(self.idx_nav+1, len(self.linhas)-1) if self.idx_nav >= 0 else 0
            self._sel(self.idx_nav)
            return "break"

        def on_up_est(e):
            if not self.linhas: return "break"
            self.idx_nav = max(self.idx_nav-1, 0) if self.idx_nav > 0 else 0
            self._sel(self.idx_nav)
            return "break"

        self.ent_busca.bind("<KeyRelease>", on_key_est)
        self.ent_busca.bind("<Down>",       on_down_est)
        self.ent_busca.bind("<Up>",         on_up_est)
        fsize = self._s(11)
        for txt,cor,hover,cmd in[
            ("📥 Entrada",  COR_SUCESSO, COR_SUCESSO2, self._entrada),
            ("📤 Saída",    COR_PERIGO,  COR_PERIGO2,  self._saida),
            ("🔧 Ajuste",   COR_ACENTO,  COR_ACENTO2,  self._ajuste),
            ("📋 Histórico","#6B7280",   "#4B5563",    self._historico),
            ("📦 Produtos", "#1D4ED8",   "#1E40AF",    self._ver_produtos),
        ]:
            ctk.CTkButton(bf,text=txt,font=("Georgia",fsize,"bold"),fg_color=cor,hover_color=hover,text_color="white",command=cmd).pack(side="left",padx=2)

    # Larguras fixas em pixels para cada coluna
    COLS_EST  = ["Produto","Unid","Grupo","Estoque Atual","Estoque Mín.","Situação"]
    WIDTHS_EST_BASE = [220, 45, 110, 100, 100, 85]

    @property
    def WIDTHS_EST(self):
        return [self._s(w) for w in self.WIDTHS_EST_BASE]

    def _build_corpo(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Cabeçalho com larguras fixas
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=40)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.pack_propagate(False)
        cab.grid_propagate(False)

        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=4)
        for col, w in zip(self.COLS_EST, self.WIDTHS_EST):
            ctk.CTkLabel(hdr, text=col,
                         font=("Courier New",self._s(13),"bold"),
                         text_color=COR_ACENTO,
                         width=w, anchor="w").pack(side="left", padx=2)

        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.linhas = []
        self.id_map = []

    def _carregar(self):
        busca=self.ent_busca.get() if hasattr(self,"ent_busca") else ""
        prods=listar_produtos(busca)
        for w in self.scroll.winfo_children(): w.destroy()
        self.linhas.clear(); self.id_map.clear(); self.produto_selecionado=None
        for idx, p in enumerate(prods):
            self.id_map.append(p["id"])
            alerta = p["estoque_atual"] <= p["estoque_minimo"]
            cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD

            row_f = ctk.CTkFrame(self.scroll, fg_color=cor_bg,
                                 corner_radius=4, height=40)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)

            sit   = "⚠️ BAIXO" if alerta else "✅ OK"
            vals  = [
                p["nome"][:32],
                p["unidade"],
                p["grupo"][:14],
                f'{p["estoque_atual"]:.2f}',
                f'{p["estoque_minimo"]:.2f}',
                sit
            ]
            cores = [
                COR_TEXTO, COR_TEXTO_SUB, COR_TEXTO_SUB,
                COR_PERIGO if alerta else COR_SUCESSO,
                COR_TEXTO_SUB,
                COR_PERIGO if alerta else COR_SUCESSO
            ]
            row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
            row_inner.pack(fill="x", padx=4, pady=4)

            for v, c, w in zip(vals, cores, self.WIDTHS_EST):
                ctk.CTkLabel(row_inner, text=v,
                             font=("Courier New",self._s(13)),
                             text_color=c,
                             width=w, anchor="w").pack(side="left", padx=2)

            i_cap = idx
            row_f.bind("<Button-1>",   lambda e, i=i_cap: self._sel(i))
            row_inner.bind("<Button-1>",lambda e, i=i_cap: self._sel(i))
            self.linhas.append(row_f)

    def _sel(self, idx):
        for i, f in enumerate(self.linhas):
            f.configure(fg_color=COR_LINHA_PAR if i%2==0 else COR_CARD)
        self.linhas[idx].configure(fg_color=COR_LINHA_SEL)
        self.produto_selecionado = self.id_map[idx]
        self.idx_nav = idx
        # Scroll para item visível
        try:
            self.scroll._parent_canvas.yview_moveto(idx / max(len(self.linhas),1))
        except Exception:
            pass

    def _get_sel(self):
        if not self.produto_selecionado: messagebox.showwarning("Selecione","Selecione um produto.",parent=self); return None
        return self.produto_selecionado

    def _entrada(self):
        pid=self._get_sel()
        if not pid: return
        v=simpledialog.askfloat("Entrada","Quantidade de entrada:",minvalue=0.001,parent=self)
        if v: obs=simpledialog.askstring("Obs","Observação:",parent=self) or ""; movimentar_estoque(pid,"ENTRADA",v,obs or "Entrada manual"); self._carregar()

    def _saida(self):
        pid=self._get_sel()
        if not pid: return
        v=simpledialog.askfloat("Saída","Quantidade de saída:",minvalue=0.001,parent=self)
        if v: obs=simpledialog.askstring("Obs","Observação:",parent=self) or ""; movimentar_estoque(pid,"SAIDA",v,obs or "Saída manual"); self._carregar()

    def _ajuste(self):
        pid=self._get_sel()
        if not pid: return
        v=simpledialog.askfloat("Ajuste","Novo saldo:",minvalue=0,parent=self)
        if v is not None: movimentar_estoque(pid,"AJUSTE",v,"Ajuste de inventário"); self._carregar()

    def _ver_produtos(self):
        """Abre cadastro de produtos direto do Estoque"""
        from telas.produtos import TelaProdutos
        win = ctk.CTkToplevel(self)
        win.title("Cadastro de Produtos")
        win.state("zoomed")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        TelaProdutos(frame).grid(row=0, column=0, sticky="nsew")

    def _historico(self):
        pid=self._get_sel(); movs=listar_movimentacoes(pid)
        win = ctk.CTkToplevel(self)
        win.title("Histórico")
        win.state("zoomed")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.lift()
        win.focus_force()
        win.attributes("-topmost", True)
        win.after(200, lambda: win.attributes("-topmost", False))
        ctk.CTkLabel(win,text="📋  Histórico de Movimentações",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=16)
        scroll=ctk.CTkScrollableFrame(win,fg_color=COR_CARD2); scroll.pack(fill="both",expand=True,padx=16,pady=(0,16))
        for m in movs:
            cor=COR_SUCESSO if m["tipo"]=="ENTRADA" else COR_PERIGO
            txt=f'{m["data_hora"][:16]}  |  {m["tipo"]:8}  |  Qtde: {m["quantidade"]:.3f}  |  Saldo: {m["saldo_apos"]:.3f}  |  {m["produto_nome"]}'
            ctk.CTkLabel(scroll,text=txt,font=FONTE_SMALL,text_color=cor,anchor="w").pack(fill="x",pady=1,padx=8)
