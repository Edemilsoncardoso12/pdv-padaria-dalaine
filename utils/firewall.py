"""
utils/firewall.py — Proteção de Rede e Dispositivos
- Verificação de HTTPS nas APIs
- Proteção contra dispositivos USB não autorizados
- Monitoramento de rede
- Rate limiting de requisições
"""
import os, sys, json, time, threading, hashlib
from datetime import datetime, timedelta
from collections import defaultdict

# ── HTTPS forçado para todas as APIs ─────────────────────────────────────────
def requisicao_segura(url, dados=None, headers=None, token=None, timeout=10):
    """
    Faz requisição HTTPS segura com:
    - Verificação de certificado SSL
    - Timeout definido
    - Headers de segurança
    - Rate limiting
    """
    import urllib.request, urllib.error, ssl

    # NUNCA aceita HTTP — somente HTTPS
    if not url.startswith("https://"):
        raise ValueError(f"URL insegura bloqueada: {url}")

    # Verifica rate limit
    if not _rate_limit_ok(url):
        raise Exception("Rate limit atingido. Aguarde.")

    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode    = ssl.CERT_REQUIRED

    req_headers = {
        "User-Agent":    "PDV-PadariaLaine/2.0",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
        "X-App-Version": "2.0.0",
    }
    if token:
        req_headers["Authorization"] = f"Bearer {token}"
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(
        url,
        data=json.dumps(dados).encode() if dados else None,
        headers=req_headers,
        method="POST" if dados else "GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Erro de rede: {e.reason}")

# ── Rate Limiting ─────────────────────────────────────────────────────────────
_contadores = defaultdict(list)
_LIMITE_REQ = 30   # máximo por janela
_JANELA_SEG = 60   # janela de 60 segundos

def _rate_limit_ok(url):
    """Permite no máximo 30 requisições por minuto por URL"""
    agora  = time.time()
    dominio = url.split("/")[2]
    _contadores[dominio] = [
        t for t in _contadores[dominio]
        if agora - t < _JANELA_SEG]
    if len(_contadores[dominio]) >= _LIMITE_REQ:
        return False
    _contadores[dominio].append(agora)
    return True

# ── Proteção USB ──────────────────────────────────────────────────────────────
_dispositivos_autorizados = set()
_monitorando_usb          = False

def autorizar_dispositivo(device_id):
    """Adiciona dispositivo à lista branca"""
    _dispositivos_autorizados.add(device_id)
    _salvar_dispositivos()

def _salvar_dispositivos():
    try:
        import sys
        base = (os.path.dirname(sys.executable)
                if getattr(sys,"frozen",False)
                else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "banco", ".dispositivos")
        with open(path, "w") as f:
            json.dump(list(_dispositivos_autorizados), f)
    except Exception:
        pass

def _carregar_dispositivos():
    try:
        import sys
        base = (os.path.dirname(sys.executable)
                if getattr(sys,"frozen",False)
                else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "banco", ".dispositivos")
        if os.path.exists(path):
            with open(path) as f:
                for d in json.load(f):
                    _dispositivos_autorizados.add(d)
    except Exception:
        pass

def iniciar_monitoramento_usb(callback_alerta=None):
    """
    Monitora novos dispositivos USB em thread separada.
    callback_alerta(nome_dispositivo) chamado quando USB desconhecido conectado.
    """
    global _monitorando_usb
    if _monitorando_usb:
        return
    _monitorando_usb = True
    _carregar_dispositivos()

    def _monitorar():
        dispositivos_anteriores = _listar_usb()
        while _monitorando_usb:
            time.sleep(5)
            try:
                atuais = _listar_usb()
                novos  = atuais - dispositivos_anteriores
                for dev in novos:
                    dev_id = hashlib.md5(dev.encode()).hexdigest()[:8]
                    if dev_id not in _dispositivos_autorizados:
                        from utils.seguranca import log_aviso
                        log_aviso(f"USB NÃO AUTORIZADO: {dev}")
                        if callback_alerta:
                            callback_alerta(dev)
                dispositivos_anteriores = atuais
            except Exception:
                pass

    threading.Thread(target=_monitorar, daemon=True).start()

def _listar_usb():
    """Lista dispositivos USB conectados no Windows"""
    try:
        import subprocess
        saida = subprocess.check_output(
            "wmic logicaldisk get caption,description,drivetype",
            shell=True, stderr=subprocess.DEVNULL).decode()
        return {linha.strip() for linha in saida.split("\n")
                if "2" in linha and linha.strip()}
    except Exception:
        return set()

# ── Verificação de rede segura ────────────────────────────────────────────────
def verificar_rede():
    """
    Retorna informações da rede atual.
    Alerta se estiver em rede pública.
    """
    try:
        import socket
        hostname = socket.gethostname()
        ip_local = socket.gethostbyname(hostname)
        # IPs de rede interna (seguros)
        redes_seguras = ("192.168.", "10.", "172.16.", "172.17.",
                         "172.18.", "172.19.", "172.2", "127.")
        eh_segura = any(ip_local.startswith(r) for r in redes_seguras)
        return {
            "hostname":  hostname,
            "ip":        ip_local,
            "eh_segura": eh_segura,
            "mensagem":  "Rede interna (segura)" if eh_segura
                         else "⚠️ Possível rede pública!",
        }
    except Exception:
        return {"ip": "desconhecido", "eh_segura": True}
