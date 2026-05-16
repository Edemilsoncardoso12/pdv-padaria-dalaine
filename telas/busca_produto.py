"""
telas/busca_produto.py
"""
import customtkinter as ctk
import tkinter as tk
from tema import *

class BuscaProdutoWidget:
    def __init__(self, parent, callback_selecao, width=300):
        self.callback  = callback_selecao
        self.lista     = []
        self.idx_sel   = -1
        self.win       = None
        self.labels    = []

        self.entry = ctk.CTkEntry(
            parent, width=width, font=FONTE_LABEL,
            placeholder_text="Código ou nome do produto...",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)

        self.entry.bind("<Down>",        self._baixo)
        self.entry.bind("<Up>",          self._cima)
        self.entry.bind("<Return>",      self._enter)
        self.entry.bind("<Escape>",      lambda e: self._fechar())
        self.entry.bind("<FocusOut>",    lambda e: self.entry.after(300, self._fechar))
        self.entry.bind("<KeyRelease>",  self._on_key_release)

    def _on_key_release(self, event):
        if event.keysym in {"Up","Down","Left","Right","Return","Escape",
                            "Tab","Home","End","Prior","Next","Shift_L",
                            "Shift_R","Control_L","Control_R","Alt_L","Alt_R",
                            "caps_lock","F1","F2","F3","F4","F5","F6","F7","F8",
                            "F9","F10","F11","F12"}:
            return "break"

        texto = self.entry.get().strip()
        if len(texto) < 1:
            self._fechar()
            return

        from banco.database import listar_produtos
        nova = listar_produtos(texto)[:12]

        if [p["id"] for p in nova] != [p["id"] for p in self.lista]:
            self.lista   = nova
            self.idx_sel = -1
            if self.lista:
                self._mostrar()
            else:
                self._fechar()

    def _mostrar(self):
        if self.win:
            try: self.win.destroy()
            except: pass
        self.win    = None
        self.labels = []

        try:
            if not self.entry.winfo_exists():
                return
            self.entry.update_idletasks()
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
            w = max(self.entry.winfo_width(), 620)
            h = len(self.lista) * 34 + 28
        except Exception:
            return

        root = self.entry.winfo_toplevel()
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.configure(bg="#B45309")

        f = tk.Frame(self.win, bg="white")
        f.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(f,
            text="  Código           Nome                           UN   Estq    Preço",
            font=("Courier New",13,"bold"),
            fg="#B45309", bg="#FEF3C7", anchor="w").pack(fill="x")

        for i, p in enumerate(self.lista):
            cod  = (p["codigo_barras"] or "S/COD")[:13]
            nome = p["nome"][:28]
            txt  = f"  {cod:13}  {nome:28}  {p['unidade']:3}  {p['estoque_atual']:5.1f}  R${p['preco_venda']:.2f}"
            bg   = "#F5F5F0" if i % 2 == 0 else "white"
            lbl  = tk.Label(f, text=txt,
                           font=("Courier New",15),
                           fg="#1A1A2E", bg=bg,
                           anchor="w", cursor="hand2")
            lbl.pack(fill="x", pady=1)
            lbl.bind("<Button-1>", lambda e, pp=p: self._selecionar(pp))
            self.labels.append((lbl, bg))

        self.entry.focus_set()

    def _highlight(self, idx):
        for i, (lbl, bg_orig) in enumerate(self.labels):
            lbl.configure(
                bg="#B45309" if i == idx else bg_orig,
                fg="white"   if i == idx else "#1A1A2E")
        self.idx_sel = idx

    def _baixo(self, event=None):
        if not self.labels:
            return "break"
        novo = min(self.idx_sel + 1, len(self.labels) - 1)
        if self.idx_sel == -1:
            novo = 0
        self._highlight(novo)
        return "break"

    def _cima(self, event=None):
        if not self.labels:
            return "break"
        novo = max(self.idx_sel - 1, 0)
        self._highlight(novo)
        return "break"

    def _enter(self, event=None):
        texto = self.entry.get().strip()
        if not texto:
            return "break"

        if len(texto) == 13 and texto.startswith("2") and texto.isdigit():
            self._fechar()
            self.entry.delete(0, "end")
            self.callback({"_balanca": True, "_codigo": texto})
            return "break"

        if 0 <= self.idx_sel < len(self.lista):
            self._selecionar(self.lista[self.idx_sel])
        elif len(self.lista) == 1:
            self._selecionar(self.lista[0])
        else:
            from banco.database import buscar_produto_por_codigo
            prod = buscar_produto_por_codigo(texto)
            if prod:
                self._selecionar(prod)
            elif self.lista:
                self._selecionar(self.lista[0])
            else:
                self._fechar()
                self._abrir_cadastro(texto)
        return "break"

    def _abrir_cadastro(self, codigo):
        try:
            from telas.produtos import FormularioProduto

            def pos_cadastro():
                from banco.database import buscar_produto_por_codigo
                prod = buscar_produto_por_codigo(codigo)
                if prod:
                    self.entry.delete(0, "end")
                    self.callback(prod)
                else:
                    self.entry.delete(0, "end")
                try:
                    self.entry.focus_set()
                except Exception:
                    pass

            root = self.entry.winfo_toplevel()
            form = FormularioProduto(root, None, pos_cadastro)

            if codigo.isdigit():
                form.ent_scan.delete(0, "end")
                form.ent_scan.insert(0, codigo)
                form.after(200, form._on_scan)
            else:
                form.campos["nome"].delete(0, "end")
                form.campos["nome"].insert(0, codigo)
                form.campos["nome"].focus_set()

        except Exception as e:
            import tkinter.messagebox as mb
            mb.showwarning(
                "Produto não encontrado",
                f"Produto '{codigo}' não cadastrado.\n\n"
                f"Abra o módulo Estoque > Produtos para cadastrar.",
                parent=self.entry.winfo_toplevel())
            self.entry.delete(0, "end")
            try:
                self.entry.focus_set()
            except Exception:
                pass

    def _selecionar(self, produto):
        self._fechar()
        self.entry.delete(0, "end")
        self.entry.focus_set()
        self.callback(produto)

    def _fechar(self):
        win = self.win
        self.win     = None
        self.labels  = []
        self.lista   = []
        self.idx_sel = -1
        if win:
            try: win.destroy()
            except: pass

    def focus_set(self):
        self.entry.focus_set()
