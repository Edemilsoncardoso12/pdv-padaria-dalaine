import customtkinter as ctk

def resource_path(relativo):
    """Retorna caminho correto tanto em .py quanto em .exe"""
    if getattr(sys, "frozen", False):
        # Rodando como .exe — arquivos estão na pasta do executável
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relativo)

def centralizar_janela(win, largura=None, altura=None):
    """Centraliza qualquer janela na tela e garante que não saia dos limites"""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w  = largura  or win.winfo_width()
    h  = altura   or win.winfo_height()
    # Garantir que cabe na tela
    w = min(w, sw - 40)
    h = min(h, sh - 80)
    x = (sw - w) // 2
    y = (sh - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")
import os, sys
from datetime import datetime

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)
for pasta in ["banco","cupons","backups","telas","utils","fiscal"]:
    os.makedirs(os.path.join(BASE_DIR, pasta), exist_ok=True)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

from tema import *
from banco.database import inicializar_banco


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Padaria Da Laine — PDV")
        # Tela cheia total — ocupa tela inteira
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.configure(fg_color=COR_FUNDO)
        # Ícone na barra de tarefas e título
        self.after(100, self._setar_icone)
        # Maximizar
        self.after(150, lambda: self.state("zoomed"))
        self.after(300, self._fullscreen)
        # Maximiza automaticamente ao abrir
        self.usuario_logado = {"nome": "Sistema", "perfil": "ADMIN", "id": 1}
        self.tela_atual = None

        inicializar_banco()

        try:
            from utils.backup import backup_automatico_inicializacao
            backup_automatico_inicializacao()
        except Exception:
            pass

        # Frame principal — ocupa tudo
        self.frame_principal = ctk.CTkFrame(self, fg_color=COR_FUNDO, corner_radius=0)
        self.frame_principal.pack(fill="both", expand=True)
        self.frame_principal.grid_columnconfigure(0, weight=1)
        self.frame_principal.grid_rowconfigure(0, weight=1)

        self.withdraw()
        self._abrir_login()

    # ── Login ─────────────────────────────────────────────────────────────────
    def _setar_icone(self):
        """Define ícone da padaria na barra de tarefas"""
        import os, sys
        if getattr(sys,"frozen",False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(base, "logo.ico")
        png = os.path.join(base, "logo.png")
        try:
            if os.path.exists(ico):
                self.iconbitmap(ico)
            elif os.path.exists(png):
                from PIL import Image, ImageTk
                img = Image.open(png).resize((32,32))
                self._icon_img = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon_img)
        except Exception as e:
            print(f"Icone: {e}")

    def _fullscreen(self):
        """Remove barra de título após maximizar"""
        try:
            self.overrideredirect(True)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{sw}x{sh}+0+0")
        except Exception:
            pass

    def _abrir_login(self):
        from telas.login import TelaLogin
        TelaLogin(self, self._pos_login)

    def _pos_login(self, usuario):
        self.usuario_logado = usuario
        self.deiconify()
        self._abrir_menu_principal()

    # ── Menu Principal (tela de atalhos) ──────────────────────────────────────
    def _abrir_menu_principal(self):
        """Tela central com ícones grandes — sem sidebar"""
        self._limpar_tela()

        from telas.menu_principal import TelaMenuPrincipal
        tela = TelaMenuPrincipal(
            self.frame_principal,
            self.usuario_logado,
            self._abrir_modulo
        )
        tela.grid(row=0, column=0, sticky="nsew")
        self.tela_atual = tela

    # ── Abrir módulo ──────────────────────────────────────────────────────────
    def _abrir_modulo(self, destino):
        """Abre o módulo em tela cheia com botão Voltar"""
        self._limpar_tela()

        from telas.caixa         import TelaCaixa
        from telas.produtos      import TelaProdutos
        from telas.estoque       import TelaEstoque
        from telas.clientes      import TelaClientes
        from telas.financeiro    import TelaFinanceiro
        from telas.producao      import TelaProducao
        from telas.relatorios    import TelaRelatorios
        from telas.login         import TelaUsuarios
        from telas.configuracoes import TelaConfiguracoes
        from telas.sangria       import TelaSangria
        from telas.fechamento    import TelaFechamentoCaixa

        usuario_nome = self.usuario_logado.get("nome", "Sistema")

        mapa = {
            "caixa":         TelaCaixa,
            "produtos":      TelaProdutos,
            "estoque":       TelaEstoque,
            "clientes":      TelaClientes,
            "financeiro":    TelaFinanceiro,
            "producao":      TelaProducao,
            "relatorios":    TelaRelatorios,
            "usuarios":      TelaUsuarios,
            "configuracoes": TelaConfiguracoes,
            "sangria":       lambda master: TelaSangria(master, usuario_nome),
            "fechamento":    lambda master: TelaFechamentoCaixa(master, usuario_nome),
        }

        Tela = mapa.get(destino)
        if not Tela:
            return

        # Container com botão Voltar no topo
        container = ctk.CTkFrame(
            self.frame_principal, fg_color=COR_FUNDO, corner_radius=0)
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)

        # Barra superior com botão Voltar
        topbar = ctk.CTkFrame(
            container, fg_color=COR_ACENTO,
            corner_radius=0, height=46)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            topbar, text="⬅  Voltar ao Menu",
            font=("Georgia", 12, "bold"),
            fg_color="transparent",
            hover_color=COR_ACENTO2,
            text_color="white",
            width=160, height=36,
            command=self._abrir_menu_principal
        ).grid(row=0, column=0, padx=12, pady=5, sticky="w")

        # Nome do módulo
        nomes = {
            "caixa": "🛒 PDV / Caixa",
            "produtos": "📦 Produtos",
            "estoque": "📊 Estoque",
            "clientes": "👥 Clientes",
            "financeiro": "💰 Financeiro",
            "producao": "🧁 Produção",
            "relatorios": "📈 Relatórios",
            "usuarios": "👤 Usuários",
            "configuracoes": "⚙️ Configurações",
        }
        ctk.CTkLabel(
            topbar,
            text=nomes.get(destino, destino),
            font=("Georgia", 14, "bold"),
            text_color="white"
        ).grid(row=0, column=1, pady=5)

        # Usuário logado
        nome_user = self.usuario_logado.get("nome", "")
        ctk.CTkLabel(
            topbar,
            text=f"👤 {nome_user}",
            font=("Courier New", 11),
            text_color="white"
        ).grid(row=0, column=2, padx=12, pady=5, sticky="e")

        # Tela do módulo (suporta classe e lambda)
        if isinstance(Tela, type):
            tela = Tela(container)
        else:
            tela = Tela(container)
        tela.grid(row=1, column=0, sticky="nsew")
        self.tela_atual = container

    def _limpar_tela(self):
        if self.tela_atual:
            self.tela_atual.destroy()
            self.tela_atual = None


if __name__ == "__main__":
    # ── 1. Verificar licença ──────────────────────────────────────────────────
    try:
        from utils.licenca import verificar_licenca
        valido, msg, dados = verificar_licenca()
        if not valido:
            from telas.tela_bloqueio import TelaBloqueio
            b = TelaBloqueio(msg, dados)
            b.mainloop()
            sys.exit(0)
    except Exception:
        pass

    # ── 2. Verificar integridade do banco ─────────────────────────────────────
    try:
        from utils.seguranca import (
            inicializar_auditoria, instalar_tratamento_global,
            verificar_integridade_banco, verificar_hash_banco,
            GerenciadorSessao, log_info)
        ok, msg_banco = verificar_integridade_banco()
        if not ok:
            from tkinter import messagebox
            import tkinter as tk
            rt = tk.Tk(); rt.withdraw()
            messagebox.showerror("Banco de Dados",
                f"Problema no banco:\n{msg_banco}\n\n"
                "Restaure um backup em backups\\")
            sys.exit(1)
    except Exception:
        pass

    # ── 3. Iniciar aplicação ──────────────────────────────────────────────────
    app = App()

    # ── 4. Instalar tratamento global de erros ────────────────────────────────
    try:
        instalar_tratamento_global(app)
        inicializar_auditoria()
        verificar_hash_banco()
        log_info(f"Sistema iniciado — Versão 3.1.3")
    except Exception:
        pass

    # ── 5. Verificar atualização em background ────────────────────────────────
    try:
        from utils.atualizacao import verificar_atualizacao_async, mostrar_dialogo_atualizacao
        def on_update(tem, versao, notas, obrigatorio=False):
            if tem:
                app.after(3000, lambda: mostrar_dialogo_atualizacao(
                    app, versao, notas, obrigatorio))
        verificar_atualizacao_async(on_update)
    except Exception:
        pass

    # ── 6. Timeout de sessão (15 minutos) ─────────────────────────────────────
    try:
        sessao = GerenciadorSessao(app, minutos=60)
        app.bind_all("<Button-1>", lambda e: sessao.registrar_atividade())
        app.bind_all("<Key>",      lambda e: sessao.registrar_atividade())
        app.bind_all("<Motion>",   lambda e: sessao.registrar_atividade())
    except Exception:
        pass

    # ── 7. Backup automático criptografado ────────────────────────────────────
    try:
        from utils.backup import fazer_backup_async
        # Backup 30 segundos após iniciar
        app.after(30000, lambda: fazer_backup_async())
        # Backup a cada 4 horas
        def _backup_periodico():
            fazer_backup_async()
            app.after(14400000, _backup_periodico)
        app.after(14400000, _backup_periodico)
    except Exception:
        pass

    # ── 8. Backup na nuvem em background ──────────────────────────────────────
    try:
        from utils.backup_nuvem import backup_nuvem_async, verificar_e_processar_fila
        app.after(300000, lambda: backup_nuvem_async())
        app.after(10000,  lambda: verificar_e_processar_fila())
    except Exception:
        pass

    # ── 8. Monitoramento USB ───────────────────────────────────────────────────
    try:
        from utils.firewall import iniciar_monitoramento_usb
        def alerta_usb(dispositivo):
            from tkinter import messagebox
            app.after(0, lambda: messagebox.showwarning(
                "⚠️ Dispositivo USB",
                f"Dispositivo não autorizado conectado:\n{dispositivo}\n\n"
                "Autorize em Configurações → Segurança."))
        iniciar_monitoramento_usb(alerta_usb)
    except Exception:
        pass

    app.mainloop()
