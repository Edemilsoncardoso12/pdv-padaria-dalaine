"""
utils/backup_nuvem.py — Backup Automático Google Drive + OneDrive
Modo offline com fila de NFe
"""
import os, sys, json, shutil, threading
from datetime import datetime

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Backup Google Drive (pasta local sincronizada) ────────────────────────────
def backup_google_drive():
    """
    Copia backup para pasta do Google Drive local.
    O Google Drive sincroniza automaticamente para nuvem.
    Não precisa de API — usa a pasta local do app.
    """
    base     = get_base_dir()
    db_path  = os.path.join(base, "banco", "padaria.db")
    if not os.path.exists(db_path):
        return False, "Banco não encontrado."

    # Pastas candidatas do Google Drive
    possiveis = [
        os.path.join(os.path.expanduser("~"), "Google Drive"),
        os.path.join(os.path.expanduser("~"), "Google Drive", "Meu Drive"),
        os.path.join(os.path.expanduser("~"), "OneDrive"),
        os.path.join(os.path.expanduser("~"), "OneDrive - Personal"),
        os.path.join(os.path.expanduser("~"), "Dropbox"),
        "D:\\Google Drive",
        "D:\\OneDrive",
    ]

    pasta_nuvem = None
    for p in possiveis:
        if os.path.exists(p):
            pasta_nuvem = p
            break

    if not pasta_nuvem:
        return False, ("Google Drive/OneDrive/Dropbox não encontrado.\n"
                       "Instale o app de sincronização no computador.")

    pasta_pdv = os.path.join(pasta_nuvem, "PDV_Padaria_Backup")
    os.makedirs(pasta_pdv, exist_ok=True)

    agora    = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino  = os.path.join(pasta_pdv, f"padaria_{agora}.db")
    shutil.copy2(db_path, destino)

    # Manter apenas os últimos 30 backups na nuvem
    backups = sorted([
        os.path.join(pasta_pdv, f)
        for f in os.listdir(pasta_pdv)
        if f.endswith(".db")
    ])
    while len(backups) > 30:
        os.remove(backups.pop(0))

    return True, f"Backup na nuvem: {pasta_nuvem}\nArquivo: {os.path.basename(destino)}"


def backup_nuvem_async(callback=None):
    """Faz backup em background — não trava o sistema"""
    def _fazer():
        ok, msg = backup_google_drive()
        if callback:
            callback(ok, msg)
    threading.Thread(target=_fazer, daemon=True).start()


# ── Fila offline de NFe ───────────────────────────────────────────────────────
FILA_PATH = os.path.join(get_base_dir(), "banco", "fila_nfce.json")

def adicionar_fila_nfce(venda_id, dados_nfce):
    """Adiciona NFe na fila quando sem internet"""
    fila = _ler_fila()
    fila.append({
        "venda_id":  venda_id,
        "dados":     dados_nfce,
        "tentativas":0,
        "adicionado":datetime.now().isoformat(),
        "status":    "PENDENTE",
    })
    _salvar_fila(fila)
    return len(fila)

def processar_fila_nfce():
    """
    Tenta emitir NFes pendentes da fila.
    Chamar ao iniciar o sistema ou quando internet voltar.
    """
    fila     = _ler_fila()
    pendentes= [i for i in fila if i["status"] == "PENDENTE"]
    if not pendentes:
        return 0, "Nenhuma NFe pendente."

    processadas = 0
    for item in pendentes:
        try:
            from fiscal.nfce import emitir_nfce_dados
            ok, msg, _ = emitir_nfce_dados(item["dados"])
            if ok:
                item["status"] = "EMITIDA"
                processadas += 1
            else:
                item["tentativas"] += 1
                if item["tentativas"] >= 5:
                    item["status"] = "FALHOU"
        except Exception as e:
            item["tentativas"] += 1

    _salvar_fila(fila)
    return processadas, f"{processadas} NFe(s) emitida(s)."

def qtde_fila_nfce():
    """Retorna quantas NFes estão pendentes"""
    return sum(1 for i in _ler_fila() if i["status"] == "PENDENTE")

def _ler_fila():
    if os.path.exists(FILA_PATH):
        try:
            with open(FILA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _salvar_fila(fila):
    with open(FILA_PATH, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)


# ── Verificar conectividade ───────────────────────────────────────────────────
def tem_internet(timeout=3):
    """Verifica se tem conexão com internet"""
    try:
        import urllib.request
        urllib.request.urlopen(
            "https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False

def verificar_e_processar_fila():
    """
    Verifica internet e processa fila se tiver conexão.
    Chamar periodicamente ou ao iniciar.
    """
    if tem_internet():
        qtde = qtde_fila_nfce()
        if qtde > 0:
            return processar_fila_nfce()
    return 0, "Sem internet."
