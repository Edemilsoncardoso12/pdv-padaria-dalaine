"""telas/clientes.py — Clientes e Fiado — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox, simpledialog
from tema import *
from banco.database import get_conn

def inicializar_clientes():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS clientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, cpf TEXT UNIQUE, telefone TEXT,
        endereco TEXT, limite_fiado REAL DEFAULT 0,
        saldo_fiado REAL DEFAULT 0, observacao TEXT DEFAULT '',
        ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT(datetime('now','localtime')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS fiado(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER REFERENCES clientes(id),
        venda_id INTEGER, descricao TEXT, valor REAL,
        valor_pago REAL DEFAULT 0,
        data TEXT DEFAULT(datetime('now','localtime')),
        data_pagamento TEXT, status TEXT DEFAULT 'ABERTO')""")
    conn.commit(); conn.close()

def listar_clientes(busca=""):
    conn = get_conn()
    if busca:
        rows = conn.execute(
            "SELECT * FROM clientes WHERE ativo=1 AND(nome LIKE ? OR cpf LIKE ? OR telefone LIKE ?) ORDER BY nome",
            (f"%{busca}%", f"%{busca}%", f"%{busca}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM clientes WHERE ativo=1 ORDER BY nome").fetchall()
    conn.close()
    return rows

def get_fiado_cliente(cliente_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM fiado WHERE cliente_id=? AND status='ABERTO' ORDER BY data DESC",
        (cliente_id,)).fetchall()
    conn.close()
    return rows

def lancar_fiado(cliente_id, descricao, valor, venda_id=None):
    conn = get_conn()
    conn.execute("INSERT INTO fiado(cliente_id,venda_id,descricao,valor) VALUES(?,?,?,?)",
                 (cliente_id, venda_id, descricao, valor))
    conn.execute("UPDATE clientes SET saldo_fiado=saldo_fiado+? WHERE id=?", (valor, cliente_id))
    conn.commit(); conn.close()

def receber_fiado(fiado_id, valor_pago):
    conn = get_conn()
    f = conn.execute("SELECT * FROM fiado WHERE id=?", (fiado_id,)).fetchone()
    if not f: conn.close(); return
    novo_pago = f["valor_pago"] + valor_pago
    status = "PAGO" if novo_pago >= f["valor"] else "ABERTO"
    conn.execute("UPDATE fiado SET valor_pago=?,status=?,data_pagamento=datetime('now','localtime') WHERE id=?",
                 (novo_pago, status, fiado_id))
    conn.execute("UPDATE clientes SET saldo_fiado=saldo_fiado-? WHERE id=?",
                 (valor_pago, f["cliente_id"]))
    conn.commit(); conn.close()


class TelaClientes(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.cliente_sel = None
        inicializar_clientes()
        self._build_header()
        self._build_corpo()
        self._carregar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="Clientes e Fiado",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")
        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")
        self.ent_busca = ctk.CTkEntry(bf, width=220, font=FONTE_LABEL,
                                      placeholder_text="Buscar cliente...",
                                      fg_color=COR_CARD2, border_color=COR_BORDA2,
                                      text_color=COR_TEXTO)
        self.ent_busca.pack(side="left", padx=(0, 8))
        self.idx_nav = -1

        def on_key_cli(e):
            if e.keysym in ("Up","Down","Return","Escape"): return "break"
            self._carregar()

        def on_down_cli(e):
            if not self.linhas: return "break"
            self.idx_nav = min(self.idx_nav+1, len(self.linhas)-1) if self.idx_nav >= 0 else 0
            self._sel(self.idx_nav)
            return "break"

        def on_up_cli(e):
            if not self.linhas: return "break"
            self.idx_nav = max(self.idx_nav-1, 0) if self.idx_nav > 0 else 0
            self._sel(self.idx_nav)
            return "break"

        self.ent_busca.bind("<KeyRelease>", on_key_cli)
        self.ent_busca.bind("<Down>",       on_down_cli)
        self.ent_busca.bind("<Up>",         on_up_cli)
        for txt, cor, hover, cmd in [
            ("Novo",   COR_SUCESSO, COR_SUCESSO2, self._novo),
            ("Editar", COR_ACENTO,  COR_ACENTO2,  self._editar),
            ("Fiado",  "#8B5CF6",   "#7C3AED",    self._ver_fiado),
            ("Excluir",COR_PERIGO,  COR_PERIGO2,  self._excluir),
        ]:
            ctk.CTkButton(bf, text=txt, font=FONTE_BTN, width=80,
                          fg_color=cor, hover_color=hover, text_color="white",
                          command=cmd).pack(side="left", padx=3)

    def _build_corpo(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        cols   = ["Nome", "CPF", "Telefone", "Fiado", "Limite", "Status"]
        WIDTHS = [220, 110, 120, 90, 90, 70]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=40)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        cab.grid_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=4)
        for c, w in zip(cols, WIDTHS):
            ctk.CTkLabel(hdr, text=c,
                         font=("Courier New",11,"bold"),
                         text_color=COR_ACENTO,
                         width=w, anchor="w").pack(side="left", padx=2, pady=8)
        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.linhas = []; self.id_map = []

    def _carregar(self):
        busca = self.ent_busca.get() if hasattr(self, "ent_busca") else ""
        clientes = listar_clientes(busca)
        for w in self.scroll.winfo_children(): w.destroy()
        self.linhas.clear(); self.id_map.clear(); self.cliente_sel = None
        if not clientes:
            ctk.CTkLabel(self.scroll, text="Nenhum cliente.\nClique em Novo.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB,
                         justify="center").grid(pady=40)
            return
        WIDTHS = [220, 110, 120, 90, 90, 70]
        for idx, c in enumerate(clientes):
            self.id_map.append(c["id"])
            alerta  = c["saldo_fiado"] > c["limite_fiado"] and c["limite_fiado"] > 0
            cor_bg  = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            row_f   = ctk.CTkFrame(self.scroll, fg_color=cor_bg,
                                   corner_radius=4, height=40)
            row_f.pack(fill="x", pady=1)
            row_f.pack_propagate(False)

            sit     = "ACIMA" if alerta else ("FIADO" if c["saldo_fiado"] > 0 else "OK")
            cor_sit = COR_PERIGO if alerta else (COR_ACENTO if c["saldo_fiado"] > 0 else COR_SUCESSO)
            vals  = [c["nome"][:25], c["cpf"] or "-", c["telefone"] or "-",
                     f'R$ {c["saldo_fiado"]:.2f}', f'R$ {c["limite_fiado"]:.2f}', sit]
            cores = [COR_TEXTO, COR_TEXTO_SUB, COR_TEXTO_SUB,
                     COR_PERIGO if c["saldo_fiado"] > 0 else COR_TEXTO,
                     COR_TEXTO_SUB, cor_sit]

            row_inner = ctk.CTkFrame(row_f, fg_color="transparent")
            row_inner.pack(fill="x", padx=4, pady=4)
            for v, cor, w in zip(vals, cores, WIDTHS):
                ctk.CTkLabel(row_inner, text=v,
                             font=("Courier New",12),
                             text_color=cor,
                             width=w, anchor="w").pack(side="left", padx=2)

            i_cap = idx
            row_f.bind("<Button-1>",    lambda e, i=i_cap: self._sel(i))
            row_inner.bind("<Button-1>",lambda e, i=i_cap: self._sel(i))
            self.linhas.append(row_f)

    def _sel(self, idx):
        for i, f in enumerate(self.linhas):
            f.configure(fg_color=COR_LINHA_PAR if i % 2 == 0 else COR_CARD)
        self.linhas[idx].configure(fg_color=COR_LINHA_SEL)
        self.cliente_sel = self.id_map[idx]
        self.idx_nav = idx
        try:
            self.scroll._parent_canvas.yview_moveto(idx / max(len(self.linhas),1))
        except Exception:
            pass

    def _get_sel(self):
        if not self.cliente_sel:
            messagebox.showwarning("Selecione", "Selecione um cliente.")
            return None
        return self.cliente_sel

    def _novo(self): FormularioCliente(self, None, self._carregar)
    def _editar(self):
        pid = self._get_sel()
        if pid: FormularioCliente(self, pid, self._carregar)
    def _excluir(self):
        pid = self._get_sel()
        if not pid: return
        if messagebox.askyesno("Excluir", "Excluir este cliente?"):
            conn = get_conn()
            conn.execute("UPDATE clientes SET ativo=0 WHERE id=?", (pid,))
            conn.commit(); conn.close(); self._carregar()
    def _ver_fiado(self):
        pid = self._get_sel()
        if pid: TelaFiado(self, pid, self._carregar)


class FormularioCliente(ctk.CTkToplevel):
    def __init__(self, master, cliente_id, callback):
        super().__init__(master)
        self.cliente_id = cliente_id
        self.callback   = callback
        self.title("Cliente")
        self.geometry("460x480")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self._build()
        if cliente_id: self._preencher()

    def _build(self):
        titulo = "Editar Cliente" if self.cliente_id else "Novo Cliente"
        ctk.CTkLabel(self, text=titulo, font=FONTE_TITULO,
                     text_color=COR_ACENTO).pack(pady=(20, 12))
        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=24)
        sc.grid_columnconfigure(1, weight=1)
        self.campos = {}
        for i, (label, key) in enumerate([
            ("Nome *", "nome"), ("CPF", "cpf"), ("Telefone", "telefone"),
            ("Endereco", "endereco"), ("Observacao", "observacao")
        ]):
            ctk.CTkLabel(sc, text=label, font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).grid(
                row=i, column=0, pady=6, sticky="w", padx=(0, 12))
            ent = ctk.CTkEntry(sc, font=FONTE_LABEL, height=34,
                               fg_color=COR_CARD2, border_color=COR_BORDA2,
                               text_color=COR_TEXTO)
            ent.grid(row=i, column=1, sticky="ew", pady=6)
            self.campos[key] = ent
        ctk.CTkLabel(sc, text="Limite Fiado R$", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).grid(
            row=5, column=0, pady=6, sticky="w", padx=(0, 12))
        self.ent_limite = ctk.CTkEntry(sc, font=FONTE_LABEL, height=34,
                                       fg_color=COR_CARD2, border_color=COR_BORDA2,
                                       text_color=COR_TEXTO)
        self.ent_limite.insert(0, "0")
        self.ent_limite.grid(row=5, column=1, sticky="ew", pady=6)
        ctk.CTkButton(self, text="Salvar", font=FONTE_BTN,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white", height=44, corner_radius=10,
                      command=self._salvar).pack(fill="x", padx=24, pady=16)

    def _preencher(self):
        conn = get_conn()
        c = conn.execute("SELECT * FROM clientes WHERE id=?", (self.cliente_id,)).fetchone()
        conn.close()
        if c:
            for key in ["nome", "cpf", "telefone", "endereco", "observacao"]:
                self.campos[key].insert(0, c[key] or "")
            self.ent_limite.delete(0, "end")
            self.ent_limite.insert(0, str(c["limite_fiado"]))

    def _salvar(self):
        nome = self.campos["nome"].get().strip()
        if not nome:
            messagebox.showerror("Erro", "Nome obrigatorio.", parent=self)
            return
        try:
            limite = float(self.ent_limite.get().replace(",", ".") or "0")
        except ValueError:
            limite = 0.0
        dados = {
            "nome": nome,
            "cpf": self.campos["cpf"].get().strip() or None,
            "telefone": self.campos["telefone"].get().strip(),
            "endereco": self.campos["endereco"].get().strip(),
            "observacao": self.campos["observacao"].get().strip(),
            "limite_fiado": limite,
        }
        conn = get_conn()
        if self.cliente_id:
            conn.execute(
                "UPDATE clientes SET nome=:nome,cpf=:cpf,telefone=:telefone,"
                "endereco=:endereco,observacao=:observacao,limite_fiado=:limite_fiado WHERE id=:id",
                {**dados, "id": self.cliente_id})
        else:
            conn.execute(
                "INSERT INTO clientes(nome,cpf,telefone,endereco,observacao,limite_fiado) "
                "VALUES(:nome,:cpf,:telefone,:endereco,:observacao,:limite_fiado)", dados)
        conn.commit(); conn.close()
        self.callback(); self.destroy()


class TelaFiado(ctk.CTkToplevel):
    def __init__(self, master, cliente_id, callback):
        super().__init__(master)
        self.cliente_id = cliente_id
        self.callback   = callback
        self.fiado_sel  = None
        conn = get_conn()
        c = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        conn.close()
        self.cliente = dict(c) if c else {}
        nome = self.cliente.get("nome", "")
        self.title(f"Fiado — {nome}")
        self.geometry("680x520")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self._build()
        self._carregar()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD2, corner_radius=10,
                           border_width=1, border_color=COR_BORDA)
        hdr.pack(fill="x", padx=16, pady=(16, 8))
        hdr.grid_columnconfigure(1, weight=1)
        nome = self.cliente.get("nome", "")
        ctk.CTkLabel(hdr, text=f"Cliente: {nome}",
                     font=("Georgia", 14, "bold"),
                     text_color=COR_ACENTO).grid(row=0, column=0, padx=16, pady=10, sticky="w")
        self.lbl_saldo = ctk.CTkLabel(hdr, text="Saldo: R$ 0,00",
                                      font=("Georgia", 13, "bold"),
                                      text_color=COR_PERIGO)
        self.lbl_saldo.grid(row=0, column=1, padx=16, sticky="e")
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(btns, text="Lancar Fiado", font=FONTE_BTN,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                      text_color="white", command=self._lancar).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="Receber Pagamento", font=FONTE_BTN,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white", command=self._receber).pack(side="left", padx=4)
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=10,
                             border_width=1, border_color=COR_BORDA)
        frame.pack(fill="both", expand=True, padx=16, pady=8)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        cols  = ["ID", "Descricao", "Valor", "Pago", "Restante", "Data"]
        pesos = [1, 5, 2, 2, 2, 3]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT, corner_radius=6, height=32)
        cab.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        cab.grid_propagate(False)
        for i, (c, p) in enumerate(zip(cols, pesos)):
            cab.grid_columnconfigure(i, weight=p)
            ctk.CTkLabel(cab, text=c, font=("Courier New", 10, "bold"),
                         text_color=COR_ACENTO).grid(row=0, column=i, padx=4, pady=4, sticky="w")
        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.scroll.grid_columnconfigure(0, weight=1)
        self.fiado_id_map = []; self.fiado_linhas = []

    def _carregar(self):
        conn = get_conn()
        c = conn.execute("SELECT * FROM clientes WHERE id=?", (self.cliente_id,)).fetchone()
        conn.close()
        if c:
            saldo = c["saldo_fiado"]
            self.lbl_saldo.configure(
                text=f"Saldo: R$ {saldo:.2f}",
                text_color=COR_PERIGO if saldo > 0 else COR_SUCESSO)
        fiados = get_fiado_cliente(self.cliente_id)
        for w in self.scroll.winfo_children(): w.destroy()
        self.fiado_id_map.clear(); self.fiado_linhas.clear()
        if not fiados:
            ctk.CTkLabel(self.scroll, text="Nenhum fiado em aberto!",
                         font=FONTE_LABEL, text_color=COR_SUCESSO).grid(pady=20)
            return
        pesos = [1, 5, 2, 2, 2, 3]
        for idx, f in enumerate(fiados):
            self.fiado_id_map.append(f["id"])
            restante = f["valor"] - f["valor_pago"]
            cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            row_f = ctk.CTkFrame(self.scroll, fg_color=cor_bg, corner_radius=6, height=34)
            row_f.grid(row=idx, column=0, sticky="ew", pady=1)
            row_f.grid_propagate(False)
            for i, p in enumerate(pesos): row_f.grid_columnconfigure(i, weight=p)
            vals = [str(f["id"]),
                    f["descricao"][:28] if f["descricao"] else "-",
                    f'R$ {f["valor"]:.2f}',
                    f'R$ {f["valor_pago"]:.2f}',
                    f'R$ {restante:.2f}',
                    f["data"][:10]]
            cores = [COR_TEXTO_SUB, COR_TEXTO, COR_TEXTO, COR_SUCESSO, COR_PERIGO, COR_TEXTO_SUB]
            for i, (v, cor) in enumerate(zip(vals, cores)):
                ctk.CTkLabel(row_f, text=v, font=FONTE_SMALL,
                             text_color=cor).grid(row=0, column=i, padx=4, sticky="w")
            i_cap = idx
            row_f.bind("<Button-1>", lambda e, i=i_cap: self._sel_fiado(i))
            self.fiado_linhas.append(row_f)

    def _sel_fiado(self, idx):
        for f in self.fiado_linhas:
            f.configure(fg_color=COR_LINHA_PAR if self.fiado_linhas.index(f) % 2 == 0 else COR_CARD)
        self.fiado_linhas[idx].configure(fg_color=COR_LINHA_SEL)
        self.fiado_sel = self.fiado_id_map[idx]

    def _lancar(self):
        desc = simpledialog.askstring("Fiado", "Descricao:", parent=self)
        if not desc: return
        v = simpledialog.askfloat("Valor", "Valor R$:", minvalue=0.01, parent=self)
        if v:
            lancar_fiado(self.cliente_id, desc, v)
            self._carregar(); self.callback()

    def _receber(self):
        if not self.fiado_sel:
            messagebox.showwarning("Selecione", "Selecione um fiado.", parent=self)
            return
        v = simpledialog.askfloat("Receber", "Valor recebido R$:", minvalue=0.01, parent=self)
        if v:
            receber_fiado(self.fiado_sel, v)
            self._carregar(); self.callback()
