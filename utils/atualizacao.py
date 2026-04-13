"""
utils/atualizacao.py — Atualização automática silenciosa via GitHub
O PDV verifica e instala atualizações automaticamente ao abrir
"""
import os, sys, json, threading, urllib.request, zipfile, shutil
from datetime import datetime

GITHUB_USUARIO  = "edemilsonrussin12"
GITHUB_REPO     = "pdv-padaria-dalaine"

URL_VERSAO = f"https://raw.githubusercontent.com/{GITHUB_USUARIO}/{GITHUB_REPO}/main/versao.json"
URL_ZIP    = f"https://github.com/{GITHUB_USUARIO}/{GITHUB_REPO}/archive/refs/heads/main.zip"

def get_versao_atual():
    """Lê a versão instalada do versao.json local — nunca fica travada"""
    try:
        base = get_base_dir()
        path = os.path.join(base, "versao.json")
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get("versao", "0.0.0")
    except Exception:
        return "0.0.0"

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def verificar_versao_online():
    try:
        import ssl
        ctx = ssl.create_default_context()
        req = urllib.request.Request(URL_VERSAO,
            headers={"User-Agent": "PDV-PadariaLaine/2.0"})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            dados = json.loads(r.read().decode())
        return dados.get("versao"), dados.get("notas",""), dados.get("obrigatorio", False)
    except Exception:
        return None, "", False

def baixar_e_instalar(versao_nova=""):
    """Baixa e instala atualização silenciosamente"""
    try:
        base     = get_base_dir()
        zip_path = os.path.join(base, "_update.zip")

        import ssl
        ctx = ssl.create_default_context()
        req = urllib.request.Request(URL_ZIP,
            headers={"User-Agent": "PDV-PadariaLaine/2.0"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            with open(zip_path, "wb") as f:
                f.write(r.read())

        # Extrair apenas arquivos .py — nunca sobrescreve banco ou licença
        with zipfile.ZipFile(zip_path, "r") as z:
            for item in z.namelist():
                if not item.endswith(".py"):
                    continue
                if any(x in item for x in ["padaria.db","licenca","__pycache__"]):
                    continue
                partes = item.split("/", 1)
                if len(partes) < 2 or not partes[1]:
                    continue
                destino = os.path.join(base, partes[1])
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with z.open(item) as src, open(destino, "wb") as dst:
                    dst.write(src.read())

        os.remove(zip_path)

        # ✅ Atualiza versao.json local para evitar loop de atualização
        if versao_nova:
            versao_path = os.path.join(base, "versao.json")
            try:
                dados_versao = {"versao": versao_nova,
                                "data": datetime.now().strftime("%Y-%m-%d"),
                                "notas": "Atualização automática",
                                "obrigatorio": False}
                with open(versao_path, "w", encoding="utf-8") as f:
                    json.dump(dados_versao, f, ensure_ascii=False, indent=4)
                print(f"[PDV] versao.json atualizado para {versao_nova}")
            except Exception as e:
                print(f"[PDV] Aviso: não foi possível atualizar versao.json: {e}")

        # Salvar timestamp da instalação
        ver_path = os.path.join(base, "versao_instalada.txt")
        with open(ver_path, "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M"))

        return True, "OK"
    except Exception as e:
        return False, str(e)

def verificar_atualizacao_async(callback=None):
    """
    Verifica e instala atualização em background.
    SILENCIOSO — usuário não precisa fazer nada!
    Só reinicia o sistema se tiver atualização.
    """
    def _verificar():
        try:
            versao_nova, notas, obrigatorio = verificar_versao_online()
            versao_atual = get_versao_atual()

            print(f"[PDV] Versão local: {versao_atual} | GitHub: {versao_nova}")

            if not versao_nova or versao_nova == versao_atual:
                print(f"[PDV] Sistema atualizado. Nenhuma ação necessária.")
                return

            # TEM ATUALIZAÇÃO — instala silenciosamente em background
            print(f"[PDV] Atualização {versao_nova} disponível. Instalando...")
            ok, msg = baixar_e_instalar(versao_nova)

            if ok:
                print(f"[PDV] Atualização instalada com sucesso!")
                # Avisar usuário para reiniciar (só um aviso simples)
                if callback:
                    callback(True, versao_nova, notas, obrigatorio)
            else:
                print(f"[PDV] Erro na atualização: {msg}")

        except Exception as e:
            print(f"[PDV] Verificação de atualização falhou: {e}")

    threading.Thread(target=_verificar, daemon=True).start()

def mostrar_dialogo_atualizacao(parent, versao, notas, obrigatorio=False):
    """
    Aviso SIMPLES — só informa que foi atualizado
    Pede para reiniciar o sistema
    """
    try:
        import customtkinter as ctk
        from tema import (COR_CARD, COR_ACENTO, COR_ACENTO2,
                         COR_SUCESSO, COR_SUCESSO2, COR_TEXTO,
                         COR_TEXTO_SUB, FONTE_TITULO, FONTE_LABEL,
                         FONTE_SMALL, FONTE_BTN)

        win = ctk.CTkToplevel(parent)
        win.title("Sistema Atualizado!")
        win.geometry("400x250")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.lift()
        win.focus_force()

        ctk.CTkLabel(win, text="✅  Sistema Atualizado!",
                     font=FONTE_TITULO, text_color=COR_SUCESSO).pack(pady=(24,8))
        ctk.CTkLabel(win, text=f"Versão {versao} instalada com sucesso!",
                     font=FONTE_LABEL, text_color=COR_TEXTO).pack()
        if notas:
            ctk.CTkLabel(win, text=notas,
                         font=FONTE_SMALL, text_color=COR_TEXTO_SUB,
                         wraplength=340).pack(pady=8)

        ctk.CTkLabel(win,
                     text="Feche e abra o sistema para aplicar.",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=4)

        ctk.CTkButton(win, text="OK — Entendido",
                      font=FONTE_BTN, height=44,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=win.destroy).pack(pady=16, padx=40, fill="x")

    except Exception as e:
        print(f"Dialogo: {e}")
