"""
telas/menu_principal.py — Menu Principal 6 ícones
"""
import customtkinter as ctk
import os, sys
from tema import *
from banco.database import get_config

class TelaMenuPrincipal(ctk.CTkFrame):
    def __init__(self, master, usuario, abrir_modulo):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario      = usuario
        self.abrir_modulo = abrir_modulo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build()

    def _build(self):
        # ── Marca d'água PRIMEIRO (fica atrás de tudo) ───────────────────
        self._desenhar_marca_dagua()

        # Frame central (criado DEPOIS da marca d'água = fica na frente)
        centro = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        # Topbar
        top = ctk.CTkFrame(self, fg_color=COR_ACENTO, corner_radius=0, height=50)
        top.place(relx=0, rely=0, relwidth=1)
        top.grid_columnconfigure(1, weight=1)

        nome_emp = get_config("empresa_nome") or "Padaria Da Laine"
        cnpj     = get_config("empresa_cnpj") or ""
        txt      = f"{nome_emp}  —  CNPJ: {cnpj}" if cnpj else nome_emp
        ctk.CTkLabel(top, text=txt,
                     font=("Georgia",13,"bold"),
                     text_color="white").grid(row=0, column=0, padx=20, pady=14, sticky="w")

        nome_user = self.usuario.get("nome", "")
        perfil    = self.usuario.get("perfil", "")
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.grid(row=0, column=1, padx=20, sticky="e")
        ctk.CTkLabel(info, text=f"  {nome_user}  |  {perfil}",
                     font=("Courier New",11), text_color="white").pack(side="left", padx=8)
        ctk.CTkButton(info, text="Senha", font=("Courier New",10),
                      fg_color="transparent", hover_color=COR_ACENTO2,
                      text_color="white", width=70, height=28,
                      command=self._alterar_senha).pack(side="left", padx=4)
        ctk.CTkButton(info, text="Sair", font=("Courier New",10),
                      fg_color="transparent", hover_color="#B91C1C",
                      text_color="white", width=60, height=28,
                      command=self._sair).pack(side="left", padx=4)

        # Logo
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(os.path.join(base, "logo.png")), size=(110,110))
            ctk.CTkLabel(centro, image=img, text="").pack(pady=(0,8))
        except Exception:
            ctk.CTkLabel(centro, text="🥐", font=("Arial",52)).pack(pady=(0,8))

        nome_emp = get_config("empresa_nome") or "Padaria Da Laine"
        ctk.CTkLabel(centro, text=nome_emp,
                     font=("Georgia",22,"bold"),
                     text_color=COR_ACENTO).pack(pady=(0,2))
        ctk.CTkLabel(centro, text="PADARIA, CONFEITARIA, SALGADERIA",
                     font=("Courier New",10),
                     text_color=COR_TEXTO_SUB).pack(pady=(0,20))

        # Grade de ícones 3x2
        grade = ctk.CTkFrame(centro, fg_color="transparent")
        grade.pack()

        perfil_u = self.usuario.get("perfil", "OPERADOR")
        bloqueios = {
            "OPERADOR":    ["configuracoes"],
            "FUNCIONARIO": ["configuracoes", "financeiro"],
        }
        bloq = bloqueios.get(perfil_u, [])

        icones = [
            ("🛒", "PDV / Caixa",   "caixa"),
            ("📊", "Estoque",       "estoque"),
            ("👥", "Clientes",      "clientes"),
            ("💰", "Financeiro",    "financeiro"),
            ("🧁", "Producao",      "producao"),
            ("⚙️", "Configuracoes", "configuracoes"),
        ]

        for i, (emoji, label, destino) in enumerate(icones):
            linha = i // 3
            col   = i % 3
            bloqueado = destino in bloq
            cor_fundo = COR_CARD if not bloqueado else "#F3F4F6"
            cor_texto = COR_TEXTO if not bloqueado else "#D1D5DB"
            cor_icone = COR_ACENTO if not bloqueado else "#D1D5DB"

            btn = ctk.CTkFrame(grade, fg_color=cor_fundo,
                               corner_radius=16, border_width=1,
                               border_color=COR_BORDA,
                               width=195, height=135)
            btn.grid(row=linha, column=col, padx=12, pady=12)
            btn.grid_propagate(False)

            lbl_i = ctk.CTkLabel(btn, text=emoji,
                                  font=("Arial",42), text_color=cor_icone)
            lbl_i.place(relx=0.5, rely=0.38, anchor="center")

            lbl_t = ctk.CTkLabel(btn, text=label,
                                  font=("Georgia",12,"bold"),
                                  text_color=cor_texto, justify="center")
            lbl_t.place(relx=0.5, rely=0.78, anchor="center")

            if not bloqueado:
                d = destino
                for w in [btn, lbl_i, lbl_t]:
                    w.bind("<Button-1>", lambda e, d=d: self.abrir_modulo(d))
                    w.bind("<Enter>",    lambda e, f=btn: f.configure(
                        fg_color=COR_ACENTO_LIGHT, border_color=COR_ACENTO))
                    w.bind("<Leave>",    lambda e, f=btn: f.configure(
                        fg_color=COR_CARD, border_color=COR_BORDA))

    def _desenhar_marca_dagua(self):
        """Logo como marca d'água — blend com fundo, atrás de tudo"""
        import os, sys
        if getattr(sys,"frozen",False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            from PIL import Image
            img = Image.open(os.path.join(base,"logo.png")).convert("RGBA")
            img = img.resize((420,420), Image.LANCZOS)

            # Cor de fundo COR_FUNDO = #F5F5F0
            fundo = Image.new("RGBA", img.size, (245, 245, 240, 255))

            # Blend 6% de opacidade — bem suave
            mistura = Image.blend(fundo, img, alpha=0.06)
            mistura = mistura.convert("RGB")

            self._wm_img = ctk.CTkImage(
                light_image=mistura,
                dark_image=mistura,
                size=(300,300))

            lbl = ctk.CTkLabel(self, image=self._wm_img, text="",
                               fg_color="transparent")
            lbl.place(relx=0.5, rely=0.54, anchor="center")
        except Exception as e:
            print(f"Marca dagua erro: {e}")

    def _alterar_senha(self):
        from telas.login import TelaAlterarSenha
        uid  = self.usuario.get("id")
        nome = self.usuario.get("nome", "")
        if uid: TelaAlterarSenha(self, uid, nome)

    def _sair(self):
        from tkinter import messagebox
        from telas.login import registrar_log
        if messagebox.askyesno("Sair", "Deseja sair do sistema?"):
            registrar_log(self.usuario.get("nome", "?"), "LOGOUT")
            self.winfo_toplevel().withdraw()
            self.winfo_toplevel()._abrir_login()
