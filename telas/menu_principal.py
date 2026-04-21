"""
telas/menu_principal.py — Menu Principal 6 ícones
"""
import customtkinter as ctk
import os, sys
from datetime import datetime
from tema import *
from banco.database import get_config, caixa_aberto

class TelaMenuPrincipal(ctk.CTkFrame):
    def __init__(self, master, usuario, abrir_modulo):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario      = usuario
        self.abrir_modulo = abrir_modulo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build()

    # ── Saudação por horário ───────────────────────────────────────────────
    def _get_saudacao(self):
        hora = datetime.now().hour
        if hora < 12:
            return "☀️  Bom dia"
        elif hora < 18:
            return "🌤️  Boa tarde"
        else:
            return "🌙  Boa noite"

    def _atualizar_saudacao(self):
        """Atualiza o label de saudação a cada 60s"""
        if hasattr(self, "_lbl_saudacao"):
            try:
                self._lbl_saudacao.configure(text=self._get_saudacao())
            except Exception:
                return
        self.after(60_000, self._atualizar_saudacao)

    def _build(self):
        self._desenhar_marca_dagua()

        centro = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        centro.place(relx=0.5, rely=0.5, anchor="center")

        self._frame_msg = None
        self.after(2000, self._carregar_mensagem)

        # Topbar
        top = ctk.CTkFrame(self, fg_color=COR_ACENTO, corner_radius=0, height=50)
        top.place(relx=0, rely=0, relwidth=1)
        top.grid_columnconfigure(1, weight=1)

        nome_emp = get_config("empresa_nome") or "Padaria Da Laine"
        cnpj     = get_config("empresa_cnpj") or ""
        txt      = f"{nome_emp}  —  CNPJ: {cnpj}" if cnpj else nome_emp
        ctk.CTkLabel(top, text=txt,
                     font=("Georgia",17,"bold"),
                     text_color="white").grid(row=0, column=0, padx=20, pady=14, sticky="w")

        nome_user = self.usuario.get("nome", "")
        perfil    = self.usuario.get("perfil", "")
        info = ctk.CTkFrame(top, fg_color="transparent")
        info.grid(row=0, column=1, padx=20, sticky="e")

        # Saudação discreta — amarelo suave, itálico, antes do nome
        self._lbl_saudacao = ctk.CTkLabel(
            info,
            text=self._get_saudacao(),
            font=("Courier New",15, "italic"),
            text_color="#FDE68A"
        )
        self._lbl_saudacao.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(info, text=f"  {nome_user}  |  {perfil}",
                     font=("Courier New",15), text_color="white").pack(side="left", padx=8)
        ctk.CTkButton(info, text="Senha", font=("Courier New",14),
                      fg_color="transparent", hover_color=COR_ACENTO2,
                      text_color="white", width=70, height=28,
                      command=self._alterar_senha).pack(side="left", padx=4)
        ctk.CTkButton(info, text="Sair", font=("Courier New",14),
                      fg_color="transparent", hover_color="#B91C1C",
                      text_color="white", width=60, height=28,
                      command=self._sair).pack(side="left", padx=4)

        # Inicia o loop de atualização da saudação
        self.after(60_000, self._atualizar_saudacao)

        # Logo
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        try:
            from PIL import Image
            possiveis = [
                os.path.join(base, "logo.png"),
                os.path.join(os.path.dirname(base), "logo.png"),
                os.path.join(os.getcwd(), "logo.png"),
                "logo.png",
            ]
            if getattr(sys, "frozen", False):
                import sys as _sys
                possiveis.insert(0, os.path.join(os.path.dirname(_sys.executable), "logo.png"))
                if hasattr(_sys, "_MEIPASS"):
                    possiveis.insert(0, os.path.join(_sys._MEIPASS, "logo.png"))

            logo_path = None
            for p in possiveis:
                if os.path.exists(p):
                    logo_path = p
                    break

            if logo_path:
                img = ctk.CTkImage(Image.open(logo_path), size=(110,110))
                self._logo_img = img
                ctk.CTkLabel(centro, image=img, text="").pack(pady=(0,8))
            else:
                ctk.CTkLabel(centro, text="🥐", font=("Arial",56)).pack(pady=(0,8))
        except Exception as e:
            print(f"Logo erro: {e}")
            ctk.CTkLabel(centro, text="🥐", font=("Arial",56)).pack(pady=(0,8))

        nome_emp = get_config("empresa_nome") or "Padaria Da Laine"
        ctk.CTkLabel(centro, text=nome_emp,
                     font=("Georgia",26,"bold"),
                     text_color=COR_ACENTO).pack(pady=(0,2))
        ctk.CTkLabel(centro, text="PADARIA, CONFEITARIA, SALGADERIA",
                     font=("Courier New",14),
                     text_color=COR_TEXTO_SUB).pack(pady=(0,16))

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
                                  font=("Arial",46), text_color=cor_icone)
            lbl_i.place(relx=0.5, rely=0.38, anchor="center")

            lbl_t = ctk.CTkLabel(btn, text=label,
                                  font=("Georgia",16,"bold"),
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

        # ── Botão Abrir/Fechar Caixa ──────────────────────────────────────
        self.frame_caixa = ctk.CTkFrame(centro, fg_color="transparent")
        self.frame_caixa.pack(pady=(12,0))
        self._build_btn_caixa()

    def _build_btn_caixa(self):
        """Constrói botão de abrir/fechar caixa com status"""
        for w in self.frame_caixa.winfo_children():
            w.destroy()

        cx = caixa_aberto()

        if cx:
            # Caixa aberto — mostra status e botão fechar
            status = ctk.CTkFrame(self.frame_caixa, fg_color=COR_CARD,
                                   corner_radius=12, border_width=1,
                                   border_color=COR_SUCESSO)
            status.pack(fill="x")
            f = ctk.CTkFrame(status, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=8)

            ctk.CTkLabel(f, text="● Caixa Aberto",
                         font=("Georgia",16,"bold"),
                         text_color=COR_SUCESSO).pack(side="left")

            ab = dict(cx).get("data_abertura","")[:16]
            ctk.CTkLabel(f, text=f"desde {ab}",
                         font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).pack(side="left", padx=8)

            ctk.CTkButton(f, text="🔒 Fechar Caixa",
                          font=FONTE_BTN, height=34, width=140,
                          fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                          text_color="white", corner_radius=8,
                          command=self._fechar_caixa_menu
                          ).pack(side="right")
        else:
            # Caixa fechado — botão abrir
            ctk.CTkButton(self.frame_caixa,
                          text="💰  Abrir Caixa",
                          font=("Georgia",17,"bold"),
                          height=44, width=300,
                          fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                          text_color="white", corner_radius=12,
                          command=self._abrir_caixa_menu
                          ).pack()

    def _abrir_caixa_menu(self):
        """Abre caixa direto do menu principal"""
        from tkinter import messagebox
        from banco.database import abrir_caixa
        import customtkinter as ctk

        win = ctk.CTkToplevel(self)
        win.title("Abrir Caixa")
        win.geometry("380x220")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text="💰  Abrir Caixa",
                     font=FONTE_TITULO, text_color=COR_SUCESSO).pack(pady=(24,8))
        ctk.CTkFrame(win, height=1, fg_color=COR_BORDA).pack(fill="x", padx=24)

        ctk.CTkLabel(win, text=f"Operador: {self.usuario.get('nome','')}",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(12,4))

        ctk.CTkLabel(win, text="Fundo de caixa (R$):",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(anchor="w", padx=24, pady=(4,2))
        ent_fundo = ctk.CTkEntry(win, font=("Georgia",26), height=46,
                                  justify="center",
                                  fg_color=COR_CARD2, border_color=COR_ACENTO,
                                  border_width=2, text_color=COR_TEXTO)
        ent_fundo.insert(0, "0,00")
        ent_fundo.pack(fill="x", padx=24)
        ent_fundo.focus_set()
        ent_fundo.select_range(0, "end")

        def confirmar():
            try:
                fundo = float(ent_fundo.get().replace(",","."))
            except ValueError:
                fundo = 0.0
            abrir_caixa(fundo)
            win.destroy()
            self._build_btn_caixa()
            messagebox.showinfo("Caixa Aberto",
                                f"Caixa aberto! Fundo: R$ {fundo:.2f}", parent=self)

        ctk.CTkButton(win, text="✅  Abrir Caixa",
                      font=FONTE_BTN, height=44,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=confirmar).pack(fill="x", padx=24, pady=16)
        ent_fundo.bind("<Return>", lambda e: confirmar())

    def _fechar_caixa_menu(self):
        """Abre tela de fechamento do menu principal"""
        from telas.fechamento import TelaFechamentoCaixa
        win = ctk.CTkToplevel(self)
        win.title("Fechamento de Caixa")
        win.geometry("1000x700")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        tela = TelaFechamentoCaixa(frame, usuario=self.usuario.get("nome","Sistema"))
        tela.grid(row=0, column=0, sticky="nsew")
        win.protocol("WM_DELETE_WINDOW", lambda: [win.destroy(), self._build_btn_caixa()])

    def _desenhar_marca_dagua(self):
        import os, sys
        if getattr(sys,"frozen",False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            from PIL import Image
            img = Image.open(os.path.join(base,"logo.png")).convert("RGBA")
            img = img.resize((420,420), Image.LANCZOS)
            fundo = Image.new("RGBA", img.size, (245, 245, 240, 255))
            mistura = Image.blend(fundo, img, alpha=0.06)
            mistura = mistura.convert("RGB")
            self._wm_img = ctk.CTkImage(light_image=mistura, dark_image=mistura, size=(300,300))
            lbl = ctk.CTkLabel(self, image=self._wm_img, text="", fg_color="transparent")
            lbl.place(relx=0.5, rely=0.54, anchor="center")
        except Exception as e:
            print(f"Marca dagua erro: {e}")

    def _carregar_mensagem(self):
        import threading, urllib.request, json, ssl
        def _buscar():
            try:
                url = "https://raw.githubusercontent.com/edemilsonrussin12/pdv-padaria-dalaine/main/mensagem.json"
                ctx = ssl.create_default_context()
                req = urllib.request.Request(url, headers={"User-Agent":"PDV-PadariaLaine/2.0"})
                with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                    dados = json.loads(r.read().decode())
                if dados.get("ativa"):
                    self.after(0, lambda: self._exibir_mensagem(dados))
            except Exception:
                pass
        threading.Thread(target=_buscar, daemon=True).start()

    def _exibir_mensagem(self, dados):
        try:
            tipo  = dados.get("tipo", "info")
            cores = {
                "info":       ("#1D4ED8", "#EFF6FF"),
                "verde":      ("#15803D", "#F0FDF4"),
                "aviso":      ("#B45309", "#FFFBEB"),
                "manutencao": ("#DC2626", "#FEF2F2"),
            }
            cor_txt, cor_bg = cores.get(tipo, cores["info"])
            if hasattr(self, "_frame_msg") and self._frame_msg:
                try: self._frame_msg.destroy()
                except: pass

            # Coluna direita — fixada na borda direita, centralizada verticalmente
            self._frame_msg = ctk.CTkFrame(self, fg_color=cor_bg, corner_radius=12,
                                            border_width=1, border_color=cor_txt,
                                            width=220)
            self._frame_msg.place(relx=1.0, rely=0.5, anchor="e",
                                  x=-16)          # 16px de margem da borda direita
            self._frame_msg.pack_propagate(False)

            titulo = dados.get("titulo","")
            texto  = dados.get("texto","")

            # Ícone do tipo
            icone = {"info":"ℹ️","verde":"✅","aviso":"⚠️","manutencao":"🔧"}.get(tipo,"ℹ️")
            ctk.CTkLabel(self._frame_msg, text=icone,
                         font=("Arial",26)).pack(pady=(14,2))

            if titulo:
                ctk.CTkLabel(self._frame_msg, text=titulo,
                             font=("Georgia",16,"bold"),
                             text_color=cor_txt,
                             wraplength=190).pack(padx=12, pady=(0,4))
            if texto:
                ctk.CTkLabel(self._frame_msg, text=texto,
                             font=("Courier New",14),
                             text_color=cor_txt,
                             wraplength=190,
                             justify="left").pack(padx=12, pady=(0,14))
        except Exception as e:
            print(f"Mensagem: {e}")

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
