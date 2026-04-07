"""
utils/atualizacao.py — Atualização automática via GitHub
O PDV verifica se tem versão nova e baixa automaticamente
"""
import os, sys, json, threading, urllib.request, zipfile, shutil
from datetime import datetime

# ── URL do seu repositório GitHub ────────────────────────────────────────────
# SUBSTITUA pelo link do seu repositório após criar no GitHub!
GITHUB_USUARIO  = "SEU_USUARIO_GITHUB"
GITHUB_REPO     = "pdv-padaria-dalaine"
VERSAO_ATUAL    = "2.0.0"

URL_VERSAO = f"https://raw.githubusercontent.com/{GITHUB_USUARIO}/{GITHUB_REPO}/main/versao.json"
URL_ZIP    = f"https://github.com/{GITHUB_USUARIO}/{GITHUB_REPO}/archive/refs/heads/main.zip"

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def verificar_versao_online():
    """Verifica se tem versão nova no GitHub"""
    try:
        ctx = __import__("ssl").create_default_context()
        req = urllib.request.Request(URL_VERSAO,
            headers={"User-Agent": "PDV-PadariaLaine/2.0"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            dados = json.loads(r.read().decode())
        return dados.get("versao"), dados.get("notas", "")
    except Exception:
        return None, ""

def verificar_atualizacao_async(callback):
    """Verifica atualização em background sem travar o sistema"""
    def _verificar():
        try:
            versao_nova, notas = verificar_versao_online()
            if versao_nova and versao_nova != VERSAO_ATUAL:
                callback(True, versao_nova, notas)
            else:
                callback(False, VERSAO_ATUAL, "")
        except Exception:
            callback(False, VERSAO_ATUAL, "")
    threading.Thread(target=_verificar, daemon=True).start()

def mostrar_dialogo_atualizacao(parent, versao, notas, obrigatorio=False):
    """Mostra diálogo de atualização disponível"""
    try:
        import customtkinter as ctk
        from tema import (COR_CARD, COR_ACENTO, COR_ACENTO2,
                         COR_SUCESSO, COR_SUCESSO2, COR_TEXTO,
                         COR_TEXTO_SUB, COR_BORDA, FONTE_TITULO,
                         FONTE_LABEL, FONTE_SMALL, FONTE_BTN)

        win = ctk.CTkToplevel(parent)
        win.title("Atualização Disponível")
        win.geometry("420x300")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text="🔄  Atualização Disponível!",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20,8))
        ctk.CTkLabel(win, text=f"Versão {versao} disponível",
                     font=FONTE_LABEL, text_color=COR_TEXTO).pack()
        if notas:
            ctk.CTkLabel(win, text=notas,
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB,
                         wraplength=360).pack(pady=8)

        ctk.CTkLabel(win, text="Deseja atualizar agora?",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=(8,4))

        lbl_prog = ctk.CTkLabel(win, text="",
                                font=FONTE_SMALL, text_color=COR_ACENTO)
        lbl_prog.pack()

        def atualizar():
            lbl_prog.configure(text="Baixando atualização...")
            win.update()
            ok, msg = baixar_e_instalar()
            if ok:
                lbl_prog.configure(text="✅ Atualizado! Reinicie o sistema.")
            else:
                lbl_prog.configure(text=f"❌ Erro: {msg}")

        f = ctk.CTkFrame(win, fg_color="transparent")
        f.pack(pady=12)
        ctk.CTkButton(f, text="✅ Atualizar Agora",
                      font=FONTE_BTN, height=42, width=180,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=atualizar).pack(side="left", padx=8)
        if not obrigatorio:
            ctk.CTkButton(f, text="Depois",
                          font=FONTE_BTN, height=42, width=100,
                          fg_color="#6B7280", hover_color="#4B5563",
                          text_color="white",
                          command=win.destroy).pack(side="left", padx=8)
    except Exception as e:
        print(f"Dialogo atualizacao: {e}")

def baixar_e_instalar():
    """Baixa o ZIP do GitHub e instala"""
    try:
        base     = get_base_dir()
        zip_path = os.path.join(base, "_update.zip")
        ctx = __import__("ssl").create_default_context()
        urllib.request.urlretrieve(URL_ZIP, zip_path)

        # Extrair apenas arquivos .py (não sobrescreve banco ou licença)
        with zipfile.ZipFile(zip_path, "r") as z:
            for item in z.namelist():
                if item.endswith(".py") and "banco/padaria.db" not in item:
                    # Remove prefixo do repositório GitHub
                    partes = item.split("/", 1)
                    if len(partes) > 1:
                        destino = os.path.join(base, partes[1])
                        os.makedirs(os.path.dirname(destino), exist_ok=True)
                        with z.open(item) as src, open(destino, "wb") as dst:
                            dst.write(src.read())

        os.remove(zip_path)
        return True, "OK"
    except Exception as e:
        return False, str(e)
