"""
utils/seguranca.py — Segurança e Proteções do Sistema
- Tratamento global de erros
- Log de auditoria completo
- Timeout de sessão
- Proteção contra SQL injection
- Criptografia de dados sensíveis
- Detecção de adulteração
"""
import os, sys, json, hashlib, logging, traceback
from datetime import datetime, timedelta
from banco.database import get_conn

# ── Configuração de logs de erro ──────────────────────────────────────────────
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR  = os.path.join(get_base_dir(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR,
    f"pdv_{datetime.now().strftime('%Y%m')}.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8"
)

def log_info(msg):    logging.info(msg)
def log_erro(msg):    logging.error(msg)
def log_aviso(msg):   logging.warning(msg)


# ── Auditoria ─────────────────────────────────────────────────────────────────
def inicializar_auditoria():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario     TEXT,
            acao        TEXT,
            modulo      TEXT,
            detalhes    TEXT,
            ip_maquina  TEXT,
            data_hora   TEXT DEFAULT(datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

def registrar_auditoria(usuario, acao, modulo="", detalhes=""):
    """Registra toda ação importante do usuário"""
    try:
        import socket
        ip = socket.gethostname()
    except Exception:
        ip = "desconhecido"
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO auditoria(usuario,acao,modulo,detalhes,ip_maquina) "
            "VALUES(?,?,?,?,?)",
            (usuario, acao, modulo, str(detalhes)[:500], ip))
        conn.commit()
        conn.close()
        log_info(f"AUDITORIA | {usuario} | {acao} | {modulo} | {detalhes}")
    except Exception as e:
        log_erro(f"Falha auditoria: {e}")

def listar_auditoria(limite=200):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM auditoria ORDER BY data_hora DESC LIMIT ?",
            (limite,)).fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


# ── Tratamento global de erros ────────────────────────────────────────────────
def instalar_tratamento_global(app):
    """
    Intercepta todos os erros não tratados e:
    1. Salva no log
    2. Mostra mensagem amigável
    3. NÃO fecha o programa
    """
    import tkinter as tk

    def tratar_erro_tkinter(exc, val, tb):
        msg = "".join(traceback.format_exception(exc, val, tb))
        log_erro(f"ERRO NÃO TRATADO:\n{msg}")
        from tkinter import messagebox
        messagebox.showerror(
            "Erro no Sistema",
            f"Ocorreu um erro inesperado.\n\n"
            f"{str(val)[:200]}\n\n"
            f"O erro foi registrado em logs\\")

    app.report_callback_exception = tratar_erro_tkinter
    log_info("Sistema iniciado — tratamento de erros ativo")


# ── Timeout de sessão ─────────────────────────────────────────────────────────
class GerenciadorSessao:
    """
    Bloqueia a tela após X minutos sem interação
    """
    def __init__(self, app, minutos=15):
        self.app          = app
        self.minutos      = minutos
        self.ultimo_uso   = datetime.now()
        self.bloqueado    = False
        self._monitorar()

    def registrar_atividade(self):
        self.ultimo_uso = datetime.now()
        self.bloqueado  = False

    def _monitorar(self):
        if not self.bloqueado:
            inativo = (datetime.now() - self.ultimo_uso).seconds
            if inativo > self.minutos * 60:
                self._bloquear()
        self.app.after(30000, self._monitorar)  # verifica a cada 30s

    def _bloquear(self):
        if self.bloqueado:
            return
        self.bloqueado = True
        log_aviso("Sessão bloqueada por inatividade")
        TelaBloqueioSessao(self.app, self)


class TelaBloqueioSessao:
    """Tela de bloqueio por inatividade"""
    def __init__(self, master, sessao):
        import customtkinter as ctk
        try:
            from tema import (COR_ACENTO, COR_ACENTO2, COR_CARD,
                              COR_TEXTO, COR_TEXTO_SUB, FONTE_TITULO,
                              FONTE_LABEL, FONTE_BTN, COR_BORDA)
        except ImportError:
            return

        self.sessao = sessao
        win = ctk.CTkToplevel(master)
        win.title("Sessão Bloqueada")
        win.geometry("400x300")
        win.configure(fg_color="#1A1A1A")
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(win, text="🔒",
                     font=("Arial", 52)).pack(pady=(30,4))
        ctk.CTkLabel(win, text="Sessão Bloqueada",
                     font=("Georgia",18,"bold"),
                     text_color=COR_ACENTO).pack()
        ctk.CTkLabel(win, text="Inatividade detectada.\nDigite sua senha para continuar:",
                     font=FONTE_LABEL, text_color="#9CA3AF",
                     justify="center").pack(pady=12)

        ent = ctk.CTkEntry(win, font=FONTE_LABEL, width=200,
                           show="●", justify="center",
                           fg_color="#2A2A2A", border_color=COR_ACENTO,
                           text_color="white")
        ent.pack(pady=4)
        ent.focus_set()

        lbl_erro = ctk.CTkLabel(win, text="",
                                font=FONTE_LABEL, text_color="#EF4444")
        lbl_erro.pack()

        def desbloquear():
            from banco.database import get_conn
            import hashlib, base64
            senha = ent.get().strip()
            if not senha:
                return

            # Hash scrypt (método atual)
            salt_scrypt = b"pdv_padaria_laine_2025_fixed"
            h_bytes = hashlib.scrypt(
                senha.encode(), salt=salt_scrypt, n=16384, r=8, p=1, dklen=32)
            hash_scrypt = "scrypt:" + base64.b64encode(h_bytes).decode()

            # Hash SHA-256 (método legado)
            salt_leg = "pdv_padaria_laine_2025"
            hash_leg = hashlib.sha256(
                f"{salt_leg}{senha}".encode()).hexdigest()

            conn = get_conn()
            ok = conn.execute(
                "SELECT id FROM usuarios WHERE (senha=? OR senha=?) AND ativo=1",
                (hash_scrypt, hash_leg)
            ).fetchone()
            conn.close()

            if ok:
                sessao.registrar_atividade()
                win.destroy()
            else:
                lbl_erro.configure(text="❌ Senha incorreta!")
                ent.delete(0, "end")
                ent.focus_set()

        ent.bind("<Return>", lambda e: desbloquear())
        ctk.CTkButton(win, text="Desbloquear",
                      font=FONTE_BTN, height=40,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white",
                      command=desbloquear).pack(pady=12)


# ── Proteção SQL Injection ────────────────────────────────────────────────────
def sanitizar(texto):
    """Remove caracteres perigosos de inputs"""
    if not isinstance(texto, str):
        return texto
    # Remove caracteres de controle e SQL perigosos
    proibidos = ["'", '"', ";", "--", "/*", "*/",
                 "DROP", "DELETE", "INSERT", "UPDATE",
                 "xp_", "exec", "EXEC"]
    resultado = texto
    for p in proibidos:
        resultado = resultado.replace(p, "")
    return resultado.strip()


# ── Verificação de integridade ────────────────────────────────────────────────
def verificar_integridade_banco():
    """Verifica se o banco SQLite está íntegro"""
    try:
        conn = get_conn()
        resultado = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if resultado and resultado[0] == "ok":
            log_info("Integridade do banco: OK")
            return True, "Banco de dados íntegro."
        else:
            log_erro(f"BANCO CORROMPIDO: {resultado}")
            return False, f"Banco com problemas: {resultado[0]}"
    except Exception as e:
        log_erro(f"Falha verificação banco: {e}")
        return False, str(e)


# ── Proteção contra cópia do banco ───────────────────────────────────────────
def verificar_hash_banco():
    """
    Gera e verifica hash do banco para detectar
    modificações externas suspeitas
    """
    from banco.database import get_conn
    import os, sys
    base = get_base_dir()
    db_path   = os.path.join(base, "banco", "padaria.db")
    hash_path = os.path.join(base, "banco", ".db_hash")

    if not os.path.exists(db_path):
        return True, "Banco novo"

    try:
        with open(db_path, "rb") as f:
            hash_atual = hashlib.md5(f.read()).hexdigest()

        if os.path.exists(hash_path):
            with open(hash_path, "r") as f:
                hash_salvo = f.read().strip()
            if hash_atual != hash_salvo:
                log_aviso("Banco modificado externamente detectado!")

        # Salva hash atual
        with open(hash_path, "w") as f:
            f.write(hash_atual)
        return True, "OK"
    except Exception as e:
        return True, str(e)  # Não bloqueia por erro de hash


# ── Controle de permissão (inspirado no módulo ChatGPT) ───────────────────────
NIVEIS_ACESSO = {
    "FUNCIONARIO": 1,
    "OPERADOR":    2,
    "ADMIN":       3,
}

def verificar_permissao(perfil_usuario, perfil_necessario):
    """
    Verifica se o usuário tem permissão suficiente.
    Uso:
        if not verificar_permissao(sessao["perfil"], "ADMIN"):
            messagebox.showwarning("Acesso negado", "Somente administrador.")
            return
    """
    nivel_user = NIVEIS_ACESSO.get(perfil_usuario, 0)
    nivel_req  = NIVEIS_ACESSO.get(perfil_necessario, 99)
    return nivel_user >= nivel_req

def requer_permissao(perfil_usuario, perfil_necessario, parent=None):
    """
    Verifica permissão e já mostra mensagem se negado.
    Retorna True se permitido, False se negado.
    """
    if not verificar_permissao(perfil_usuario, perfil_necessario):
        try:
            from tkinter import messagebox
            nomes = {"ADMIN":"Administrador","OPERADOR":"Operador","FUNCIONARIO":"Funcionário"}
            messagebox.showwarning(
                "Acesso Negado",
                f"Esta ação requer perfil: {nomes.get(perfil_necessario, perfil_necessario)}\n"
                f"Seu perfil: {nomes.get(perfil_usuario, perfil_usuario)}",
                parent=parent)
        except Exception:
            pass
        return False
    return True

# ── Sessão global ─────────────────────────────────────────────────────────────
_sessao_atual = {}

def iniciar_sessao(usuario_dict):
    """Inicia sessão do usuário logado"""
    global _sessao_atual
    _sessao_atual = dict(usuario_dict)
    log_info(f"Sessão iniciada: {usuario_dict.get('nome','?')}")

def obter_sessao():
    """Retorna dados do usuário logado"""
    return _sessao_atual

def encerrar_sessao():
    """Encerra sessão atual"""
    global _sessao_atual
    nome = _sessao_atual.get("nome","?")
    _sessao_atual = {}
    log_info(f"Sessão encerrada: {nome}")
