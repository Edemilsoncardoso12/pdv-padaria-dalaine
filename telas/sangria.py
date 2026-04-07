"""
telas/sangria.py — Sangria e Suprimento de Caixa
Sangria = retirar dinheiro do caixa
Suprimento = adicionar dinheiro ao caixa
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn, caixa_aberto

def inicializar_sangria():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sangria_suprimento (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            caixa_id    INTEGER REFERENCES caixa(id),
            tipo        TEXT,   -- SANGRIA / SUPRIMENTO
            valor       REAL,
            motivo      TEXT DEFAULT '',
            usuario     TEXT DEFAULT '',
            data_hora   TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

def registrar_movimentacao(caixa_id, tipo, valor, motivo, usuario):
    conn = get_conn()
    conn.execute("""
        INSERT INTO sangria_suprimento
            (caixa_id, tipo, valor, motivo, usuario)
        VALUES (?,?,?,?,?)
    """, (caixa_id, tipo, valor, motivo, usuario))
    conn.commit()
    conn.close()

def listar_movimentacoes_caixa(caixa_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM sangria_suprimento
        WHERE caixa_id=? ORDER BY data_hora DESC
    """, (caixa_id,)).fetchall()
    conn.close()
    return rows

def total_sangria(caixa_id):
    conn = get_conn()
    s = conn.execute("""
        SELECT COALESCE(SUM(valor),0) FROM sangria_suprimento
        WHERE caixa_id=? AND tipo='SANGRIA'
    """, (caixa_id,)).fetchone()[0]
    sup = conn.execute("""
        SELECT COALESCE(SUM(valor),0) FROM sangria_suprimento
        WHERE caixa_id=? AND tipo='SUPRIMENTO'
    """, (caixa_id,)).fetchone()[0]
    conn.close()
    return s, sup


class TelaSangria(ctk.CTkFrame):
    def __init__(self, master, usuario="Sistema"):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        inicializar_sangria()

        cx = caixa_aberto()
        self.caixa_id = cx["id"] if cx else None

        self._build_header()
        self._build_corpo()
        if self.caixa_id:
            self._carregar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="💵  Sangria e Suprimento",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        if not self.caixa_id:
            ctk.CTkLabel(hdr, text="⚠️  Nenhum caixa aberto!",
                         font=FONTE_LABEL, text_color=COR_PERIGO).grid(
                row=0, column=1, padx=24, sticky="e")
            return

        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")

        ctk.CTkButton(bf, text="📤  Sangria (Retirada)",
                      font=FONTE_BTN, width=180, height=40,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                      text_color="white",
                      command=self._nova_sangria).pack(side="left", padx=6)

        ctk.CTkButton(bf, text="📥  Suprimento (Entrada)",
                      font=FONTE_BTN, width=180, height=40,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=self._novo_suprimento).pack(side="left", padx=6)

    def _build_corpo(self):
        # Cards de resumo
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="nsew")
        cards.grid_columnconfigure(0, weight=1)
        cards.grid_rowconfigure(1, weight=1)

        resumo = ctk.CTkFrame(cards, fg_color="transparent")
        resumo.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        resumo.grid_columnconfigure((0,1,2), weight=1)

        self.card_sangria   = self._card(resumo, 0, "📤 Total Sangrias",   "R$ 0,00", COR_PERIGO)
        self.card_suprimento= self._card(resumo, 1, "📥 Total Suprimentos","R$ 0,00", COR_SUCESSO)
        self.card_saldo     = self._card(resumo, 2, "💰 Saldo Líquido",    "R$ 0,00", COR_ACENTO)

        # Tabela
        frame = ctk.CTkFrame(cards, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        cols  = ["Data/Hora", "Tipo", "Valor", "Motivo", "Usuário"]
        pesos = [3, 2, 2, 5, 2]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.grid_propagate(False)
        for i, (c, p) in enumerate(zip(cols, pesos)):
            cab.grid_columnconfigure(i, weight=p)
            ctk.CTkLabel(cab, text=c, font=("Courier New",10,"bold"),
                         text_color=COR_ACENTO).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.scroll.grid_columnconfigure(0, weight=1)

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        lbl = ctk.CTkLabel(card, text=valor,
                           font=("Georgia",20,"bold"), text_color=cor)
        lbl.pack(pady=(0,14))
        return lbl

    def _carregar(self):
        if not self.caixa_id:
            return
        movs = listar_movimentacoes_caixa(self.caixa_id)
        s, sup = total_sangria(self.caixa_id)
        saldo = sup - s

        self.card_sangria.configure(text=f"R$ {s:.2f}")
        self.card_suprimento.configure(text=f"R$ {sup:.2f}")
        cor = COR_SUCESSO if saldo >= 0 else COR_PERIGO
        self.card_saldo.configure(text=f"R$ {saldo:.2f}", text_color=cor)

        for w in self.scroll.winfo_children():
            w.destroy()

        if not movs:
            ctk.CTkLabel(self.scroll,
                         text="Nenhuma movimentação neste caixa.",
                         font=FONTE_LABEL,
                         text_color=COR_TEXTO_SUB).grid(pady=40)
            return

        pesos = [3, 2, 2, 5, 2]
        for idx, m in enumerate(movs):
            cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            cor_t  = COR_PERIGO if m["tipo"] == "SANGRIA" else COR_SUCESSO
            row_f  = ctk.CTkFrame(self.scroll, fg_color=cor_bg,
                                  corner_radius=6, height=36)
            row_f.grid(row=idx, column=0, sticky="ew", pady=1)
            row_f.grid_propagate(False)
            for i, p in enumerate(pesos):
                row_f.grid_columnconfigure(i, weight=p)

            vals  = [m["data_hora"][:16], m["tipo"],
                     f'R$ {m["valor"]:.2f}',
                     m["motivo"] or "—", m["usuario"] or "—"]
            cores = [COR_TEXTO_SUB, cor_t, cor_t, COR_TEXTO, COR_TEXTO_SUB]

            for i, (v, c) in enumerate(zip(vals, cores)):
                ctk.CTkLabel(row_f, text=v, font=FONTE_SMALL,
                             text_color=c).grid(
                    row=0, column=i, padx=6, sticky="w")

    def _nova_sangria(self):
        DialogoMovimentacao(self, "SANGRIA", self.caixa_id,
                            self.usuario, self._carregar)

    def _novo_suprimento(self):
        DialogoMovimentacao(self, "SUPRIMENTO", self.caixa_id,
                            self.usuario, self._carregar)


class DialogoMovimentacao(ctk.CTkToplevel):
    def __init__(self, master, tipo, caixa_id, usuario, callback):
        super().__init__(master)
        self.tipo     = tipo
        self.caixa_id = caixa_id
        self.usuario  = usuario
        self.callback = callback

        cor   = COR_PERIGO if tipo == "SANGRIA" else COR_SUCESSO
        icone = "📤" if tipo == "SANGRIA" else "📥"
        nome  = "Sangria (Retirada)" if tipo == "SANGRIA" else "Suprimento (Entrada)"

        self.title(nome)
        self.geometry("420x360")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self.resizable(False, False)
        self._build(icone, nome, cor)

    def _build(self, icone, nome, cor):
        ctk.CTkLabel(self, text=f"{icone}  {nome}",
                     font=FONTE_TITULO, text_color=cor).pack(pady=(24,4))

        if self.tipo == "SANGRIA":
            desc = "Retirada de dinheiro do caixa"
        else:
            desc = "Adição de dinheiro ao caixa"
        ctk.CTkLabel(self, text=desc, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(0,12))

        ctk.CTkFrame(self, height=1, fg_color=COR_BORDA).pack(
            fill="x", padx=24, pady=(0,12))

        # Valor
        ctk.CTkLabel(self, text="Valor (R$) *",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(
            anchor="w", padx=28)
        self.ent_valor = ctk.CTkEntry(
            self, font=("Georgia",20), width=200,
            justify="center",
            fg_color=COR_CARD2, border_color=cor,
            text_color=COR_TEXTO)
        self.ent_valor.pack(pady=(4,12))
        self.ent_valor.focus_set()

        # Motivo
        ctk.CTkLabel(self, text="Motivo",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(
            anchor="w", padx=28)

        motivos_sangria    = ["Pagamento de fornecedor","Despesa operacional",
                              "Retirada de lucro","Troco","Outros"]
        motivos_suprimento = ["Fundo de troco","Reposição de caixa",
                              "Troco inicial","Outros"]
        motivos = motivos_sangria if self.tipo == "SANGRIA" else motivos_suprimento

        self.cmb_motivo = ctk.CTkComboBox(
            self, values=motivos, font=FONTE_LABEL, width=340,
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.cmb_motivo.set(motivos[0])
        self.cmb_motivo.pack(pady=(4,16))

        # Confirmar
        ctk.CTkButton(
            self, text=f"✅  Confirmar {self.tipo.title()}",
            font=FONTE_BTN, height=46, corner_radius=10,
            fg_color=cor,
            hover_color=COR_PERIGO2 if self.tipo=="SANGRIA" else COR_SUCESSO2,
            text_color="white",
            command=self._confirmar
        ).pack(fill="x", padx=28, pady=4)

        self.ent_valor.bind("<Return>", lambda e: self._confirmar())

    def _confirmar(self):
        try:
            valor = float(self.ent_valor.get().replace(",","."))
        except ValueError:
            messagebox.showerror("Erro","Valor inválido.",parent=self)
            return
        if valor <= 0:
            messagebox.showerror("Erro","Valor deve ser maior que zero.",parent=self)
            return

        registrar_movimentacao(
            self.caixa_id, self.tipo, valor,
            self.cmb_motivo.get(), self.usuario)

        tipo_txt = "Sangria" if self.tipo == "SANGRIA" else "Suprimento"
        messagebox.showinfo("Sucesso",
            f"✅ {tipo_txt} de R$ {valor:.2f} registrada!",
            parent=self)

        # Imprimir comprovante
        self._imprimir_comprovante(valor)
        self.callback()
        self.destroy()

    def _imprimir_comprovante(self, valor):
        """Salva comprovante em txt"""
        try:
            import os, sys
            if getattr(sys,"frozen",False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome  = f"{self.tipo.lower()}_{agora}.txt"
            path  = os.path.join(pasta, nome)

            from banco.database import get_config
            empresa = get_config("empresa_nome") or "Padaria Da Laine"

            with open(path, "w", encoding="utf-8") as f:
                f.write("=" * 40 + "\n")
                f.write(f"{empresa:^40}\n")
                f.write("=" * 40 + "\n")
                f.write(f"{'COMPROVANTE DE ' + self.tipo:^40}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Tipo:      {self.tipo}\n")
                f.write(f"Valor:     R$ {valor:.2f}\n")
                f.write(f"Motivo:    {self.cmb_motivo.get()}\n")
                f.write(f"Usuário:   {self.usuario}\n")
                f.write("=" * 40 + "\n")
        except Exception:
            pass
