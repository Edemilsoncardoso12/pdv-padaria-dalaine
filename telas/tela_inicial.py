"""
telas/tela_inicial.py — Menu Principal estilo Eccus
Logo centralizado + ícones de acesso rápido
"""
import customtkinter as ctk
import os, sys
from tema import *

class TelaInicial(ctk.CTkFrame):
    def __init__(self, master, navegar_func, usuario):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.navegar = navegar_func
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_corpo()

    def _build_topbar(self):
        top = ctk.CTkFrame(self, fg_color=COR_ACENTO, corner_radius=0, height=48)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        # CNPJ / Nome empresa
        from banco.database import get_config
        nome = get_config("empresa_nome") or "Padaria Da Laine"
        cnpj = get_config("empresa_cnpj") or ""
        txt  = f"{nome}  —  {cnpj}" if cnpj else nome
        ctk.CTkLabel(top, text=txt,
                     font=("Georgia", 13, "bold"),
                     text_color="white").grid(
            row=0, column=0, padx=20, pady=12, sticky="w")

        # Usuario logado
        nome_user = self.usuario.get("nome", "")
        perfil     = self.usuario.get("perfil", "")
        ctk.CTkLabel(top, text=f"👤  {nome_user}  |  {perfil}",
                     font=("Courier New", 11),
                     text_color="white").grid(
            row=0, column=1, padx=20, sticky="e")

    def _build_corpo(self):
        corpo = ctk.CTkFrame(self, fg_color=COR_FUNDO, corner_radius=0)
        corpo.grid(row=1, column=0, sticky="nsew")
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_rowconfigure(1, weight=1)

        # ── Logo centralizado ─────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(corpo, fg_color="transparent")
        logo_frame.grid(row=0, column=0, pady=(40, 20))

        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        logo_path = os.path.join(base, "logo.png")
        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(logo_path), size=(220, 220))
            ctk.CTkLabel(logo_frame, image=img, text="").pack()
        except Exception:
            ctk.CTkLabel(logo_frame, text="🥐",
                         font=("Arial", 80)).pack()

        from banco.database import get_config
        nome_emp = get_config("empresa_nome") or "Padaria Da Laine"
        ctk.CTkLabel(logo_frame, text=nome_emp,
                     font=("Georgia", 28, "bold"),
                     text_color=COR_ACENTO).pack(pady=(12, 4))
        ctk.CTkLabel(logo_frame, text="PADARIA, CONFEITARIA, SALGADERIA",
                     font=("Courier New", 12),
                     text_color=COR_TEXTO_SUB).pack()

        # ── Grade de ícones ───────────────────────────────────────────────────
        grade = ctk.CTkFrame(corpo, fg_color="transparent")
        grade.grid(row=1, column=0, pady=(20, 40))

        icones = [
            ("🛒", "PDV/Caixa",       "caixa"),
            ("📦", "Produtos",          "produtos"),
            ("📊", "Estoque",           "estoque"),
            ("👥", "Clientes",          "clientes"),
            ("💰", "Financeiro",        "financeiro"),
            ("🧁", "Produção",          "producao"),
            ("📈", "Relatórios",        "relatorios"),
            ("👤", "Usuários",          "usuarios"),
            ("⚙️", "Configurações",     "configuracoes"),
        ]

        perfil = self.usuario.get("perfil", "OPERADOR")
        bloqueios = {
            "OPERADOR":    ["configuracoes", "usuarios", "financeiro"],
            "FUNCIONARIO": ["configuracoes", "usuarios", "financeiro", "relatorios"],
        }
        bloq = bloqueios.get(perfil, [])

        cols = 5
        for i, (icone, label, destino) in enumerate(icones):
            row = i // cols
            col = i % cols

            bloqueado = destino in bloq
            cor_fundo = COR_CARD if not bloqueado else "#F3F4F6"
            cor_texto = COR_TEXTO if not bloqueado else "#D1D5DB"
            cor_icone = COR_ACENTO if not bloqueado else "#D1D5DB"

            btn_frame = ctk.CTkFrame(
                grade, fg_color=cor_fundo,
                corner_radius=16,
                border_width=1,
                border_color=COR_BORDA,
                width=140, height=110)
            btn_frame.grid(row=row, column=col, padx=10, pady=10)
            btn_frame.grid_propagate(False)

            if not bloqueado:
                btn_frame.bind("<Button-1>",
                    lambda e, d=destino: self.navegar(d))
                btn_frame.bind("<Enter>",
                    lambda e, f=btn_frame: f.configure(fg_color=COR_ACENTO_LIGHT))
                btn_frame.bind("<Leave>",
                    lambda e, f=btn_frame: f.configure(fg_color=COR_CARD))

            lbl_icone = ctk.CTkLabel(
                btn_frame, text=icone,
                font=("Arial", 34),
                text_color=cor_icone)
            lbl_icone.place(relx=0.5, rely=0.38, anchor="center")
            if not bloqueado:
                lbl_icone.bind("<Button-1>",
                    lambda e, d=destino: self.navegar(d))

            lbl_texto = ctk.CTkLabel(
                btn_frame, text=label,
                font=("Georgia", 11, "bold"),
                text_color=cor_texto,
                justify="center")
            lbl_texto.place(relx=0.5, rely=0.78, anchor="center")
            if not bloqueado:
                lbl_texto.bind("<Button-1>",
                    lambda e, d=destino: self.navegar(d))
