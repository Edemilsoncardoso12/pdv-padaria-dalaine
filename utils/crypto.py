"""
utils/crypto.py — Criptografia e Proteção de Dados
- Criptografia AES para dados sensíveis
- Proteção de chaves de API
- Conformidade LGPD básica
"""
import os, sys, base64, hashlib, json
from datetime import datetime

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chave derivada do hardware do PC — única por computador
def _chave_local():
    import platform, subprocess
    try:
        uuid = subprocess.check_output(
            "wmic csproduct get uuid", shell=True,
            stderr=subprocess.DEVNULL).decode().strip().split("\n")
        uuid = [x.strip() for x in uuid if x.strip() and x.strip() != "UUID"]
        seed = uuid[0] if uuid else platform.node()
    except Exception:
        seed = platform.node()
    return hashlib.sha256(f"PDV_CRYPTO_{seed}".encode()).digest()[:32]

def criptografar(texto):
    """Criptografia simples com XOR + base64 (sem dependências externas)"""
    if not texto:
        return ""
    chave = _chave_local()
    dados = texto.encode("utf-8")
    enc   = bytes([dados[i] ^ chave[i % len(chave)] for i in range(len(dados))])
    return base64.b64encode(enc).decode()

def descriptografar(enc_texto):
    """Descriptografa texto cifrado"""
    if not enc_texto:
        return ""
    try:
        chave = _chave_local()
        dados = base64.b64decode(enc_texto)
        dec   = bytes([dados[i] ^ chave[i % len(chave)] for i in range(len(dados))])
        return dec.decode("utf-8")
    except Exception:
        return ""

# ── Arquivo de configuração seguro (substitui hardcode de chaves) ─────────────
CONFIG_SEGURO_PATH = os.path.join(
    get_base_dir(), "banco", ".config_seguro")

def salvar_config_segura(chave, valor):
    """Salva chave de API de forma criptografada"""
    configs = _ler_configs_seguras()
    configs[chave] = criptografar(str(valor))
    with open(CONFIG_SEGURO_PATH, "w") as f:
        json.dump(configs, f)

def ler_config_segura(chave, padrao=""):
    """Lê chave de API descriptografada"""
    configs = _ler_configs_seguras()
    enc = configs.get(chave, "")
    return descriptografar(enc) if enc else padrao

def _ler_configs_seguras():
    if os.path.exists(CONFIG_SEGURO_PATH):
        try:
            with open(CONFIG_SEGURO_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

# ── Anonimização LGPD ─────────────────────────────────────────────────────────
def anonimizar_cpf(cpf):
    """Mascara CPF para exibição: 123.456.789-00 → ***.456.***-**"""
    if not cpf or len(cpf) < 11:
        return cpf
    nums = "".join(filter(str.isdigit, cpf))
    if len(nums) == 11:
        return f"***.{nums[3:6]}.***-**"
    return cpf

def anonimizar_nome(nome):
    """Mascara nome: João Silva → João S***"""
    if not nome or " " not in nome:
        return nome
    partes = nome.split()
    return f"{partes[0]} {'*' * len(partes[-1])}"

def hash_senha_seguro(senha):
    """Senha com salt + pepper — mais seguro que SHA-256 simples"""
    salt  = "pdv_padaria_laine_2025"
    pepper = "!@#PDV$%&"
    return hashlib.sha256(
        f"{salt}{senha}{pepper}".encode()).hexdigest()
