"""
utils/licenca.py — Sistema de Licença por Computador
PDV Padaria Da Laine — Uso Comercial
"""
import hashlib
import os, sys, json, platform, subprocess
from datetime import datetime

CHAVE_MESTRA = "PadariaDaLaine@2025#PDV$Comercial"

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LICENCA_PATH = os.path.join(get_base_dir(), "licenca.key")


def _hash(texto):
    return hashlib.sha256(
        f"{CHAVE_MESTRA}#{texto}".encode()
    ).hexdigest()


def get_id_computador():
    """
    Gera ID único do computador baseado no hardware.
    Funciona no Windows.
    """
    try:
        # Pega UUID do Windows (único por instalação)
        resultado = subprocess.check_output(
            "wmic csproduct get uuid",
            shell=True, stderr=subprocess.DEVNULL
        ).decode().strip().split("\n")
        uuid = [x.strip() for x in resultado if x.strip() and x.strip() != "UUID"]
        if uuid:
            return _hash(uuid[0])[:16].upper()
    except Exception:
        pass

    # Fallback: nome do computador + usuário
    try:
        pc   = platform.node()
        user = os.environ.get("USERNAME", os.environ.get("USER", "user"))
        return _hash(f"{pc}_{user}")[:16].upper()
    except Exception:
        return "0000000000000000"


def get_info_computador():
    """Retorna informações legíveis do computador"""
    try:
        pc   = platform.node()
        user = os.environ.get("USERNAME", os.environ.get("USER", ""))
        sistema = platform.system() + " " + platform.release()
        id_pc = get_id_computador()
        return {
            "nome_pc":  pc,
            "usuario":  user,
            "sistema":  sistema,
            "id_pc":    id_pc,
        }
    except Exception:
        return {"id_pc": "DESCONHECIDO"}


def gerar_chave_licenca(cnpj, nome_empresa, id_computador, validade_dias=36500):
    """
    Gera chave de licença vinculada ao CNPJ + computador específico.
    """
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    data_expira = ""
    if validade_dias < 36500:
        from datetime import timedelta
        expira = datetime.now() + timedelta(days=validade_dias)
        data_expira = expira.strftime("%Y%m%d")

    payload = f"{cnpj_limpo}|{nome_empresa}|{id_computador}|{data_expira}"
    chave   = _hash(payload)

    return {
        "cnpj":          cnpj_limpo,
        "nome_empresa":  nome_empresa,
        "id_computador": id_computador,
        "data_emissao":  datetime.now().strftime("%Y-%m-%d"),
        "data_expira":   data_expira or "PERMANENTE",
        "chave":         chave,
        "versao":        "2.0",
    }


def salvar_licenca(dados, caminho=None):
    import base64
    path     = caminho or LICENCA_PATH
    conteudo = json.dumps(dados, ensure_ascii=False)
    encoded  = base64.b64encode(conteudo.encode()).decode()
    with open(path, "w") as f:
        f.write(encoded)
    return path


def verificar_licenca():
    """
    Verifica se a licença é válida para este computador.
    Retorna (valido: bool, mensagem: str, dados: dict)
    """
    if not os.path.exists(LICENCA_PATH):
        id_pc = get_id_computador()
        return False, (
            f"Licença não encontrada.\n\n"
            f"ID deste computador:\n{id_pc}\n\n"
            f"Informe este código ao desenvolvedor."
        ), {}

    try:
        import base64
        with open(LICENCA_PATH, "r") as f:
            encoded = f.read().strip()
        conteudo = base64.b64decode(encoded).decode()
        dados    = json.loads(conteudo)
    except Exception:
        return False, "Arquivo de licença corrompido.\nContate o desenvolvedor.", {}

    # Verifica se é para este computador
    id_pc_atual   = get_id_computador()
    id_pc_licenca = dados.get("id_computador", "")

    if id_pc_licenca != id_pc_atual:
        return False, (
            f"Licença inválida para este computador.\n\n"
            f"ID deste PC: {id_pc_atual}\n"
            f"ID na licença: {id_pc_licenca}\n\n"
            f"Contate o desenvolvedor."
        ), {}

    # Verifica chave
    cnpj        = dados.get("cnpj", "")
    nome        = dados.get("nome_empresa", "")
    data_expira = dados.get("data_expira", "")
    chave_salva = dados.get("chave", "")

    data_payload = "" if data_expira == "PERMANENTE" else data_expira
    payload      = f"{cnpj}|{nome}|{id_pc_licenca}|{data_payload}"
    chave_valida = _hash(payload)

    if chave_salva != chave_valida:
        return False, "Licença adulterada.\nContate o desenvolvedor.", {}

    # Verifica validade
    if data_expira != "PERMANENTE":
        try:
            from datetime import timedelta
            expira = datetime.strptime(data_expira, "%Y%m%d")
            if datetime.now() > expira:
                dias = (datetime.now() - expira).days
                return False, (
                    f"Licença expirada há {dias} dias.\n"
                    f"Contate o desenvolvedor para renovar."
                ), dados
            # Aviso 30 dias antes
            restam = (expira - datetime.now()).days
            if restam <= 30:
                dados["aviso"] = f"Licença vence em {restam} dias!"
        except Exception:
            pass

    return True, "Licença válida.", dados
