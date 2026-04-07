"""
utils/balanca.py — Integração com Balança Serial
Suporte: Toledo, Filizola, Urano (protocolos brasileiros)
"""
import threading
import time

try:
    import serial
    import serial.tools.list_ports
    SERIAL_OK = True
except ImportError:
    SERIAL_OK = False


class Balanca:
    """
    Integração com balança via porta serial.
    Protocolos: Toledo Prix / Filizola / Urano
    """
    def __init__(self):
        self.porta      = None
        self.ser        = None
        self.conectada  = False
        self.peso_atual = 0.0
        self._thread    = None
        self._rodando   = False

    def listar_portas(self):
        """Lista portas COM disponíveis"""
        if not SERIAL_OK:
            return []
        return [p.device for p in serial.tools.list_ports.comports()]

    def conectar(self, porta="COM1", baudrate=9600):
        """Conecta à balança"""
        if not SERIAL_OK:
            return False, "❌ Instale pyserial: pip install pyserial"
        try:
            self.ser = serial.Serial(
                port=porta, baudrate=baudrate,
                bytesize=8, parity='N', stopbits=1,
                timeout=1
            )
            self.porta     = porta
            self.conectada = True
            self._iniciar_leitura()
            return True, f"✅ Balança conectada em {porta}"
        except Exception as e:
            return False, f"❌ Erro ao conectar: {e}"

    def desconectar(self):
        self._rodando = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.conectada = False

    def _iniciar_leitura(self):
        """Thread de leitura contínua da balança"""
        self._rodando = True
        self._thread  = threading.Thread(
            target=self._ler_peso, daemon=True)
        self._thread.start()

    def _ler_peso(self):
        """Loop de leitura do peso"""
        while self._rodando and self.ser and self.ser.is_open:
            try:
                # Envia comando de leitura (protocolo Toledo)
                self.ser.write(b'\x05')
                time.sleep(0.1)
                linha = self.ser.readline().decode("ascii", errors="ignore").strip()
                peso  = self._parsear_peso(linha)
                if peso is not None:
                    self.peso_atual = peso
            except Exception:
                pass
            time.sleep(0.3)

    def _parsear_peso(self, linha):
        """
        Tenta extrair peso de diferentes formatos:
        Toledo:   '0001500' → 1.500 kg
        Filizola: 'P+001500' → 1.500 kg
        Urano:    '001.500' → 1.500 kg
        """
        if not linha:
            return None
        try:
            # Remove caracteres não numéricos exceto ponto
            numeros = ''.join(c for c in linha if c.isdigit() or c == '.')
            if numeros:
                peso = float(numeros)
                # Toledo envia em gramas (dividir por 1000)
                if peso > 100 and '.' not in linha:
                    peso = peso / 1000
                return round(peso, 3)
        except ValueError:
            pass
        return None

    def ler_peso(self):
        """Retorna o peso atual"""
        if not self.conectada:
            return None
        return self.peso_atual

    def ler_peso_unico(self, porta="COM1", baudrate=9600):
        """
        Lê peso uma única vez (sem thread contínua).
        Útil para leitura pontual no PDV.
        """
        if not SERIAL_OK:
            return None, "❌ pyserial não instalado"
        try:
            with serial.Serial(porta, baudrate, timeout=2) as ser:
                ser.write(b'\x05')
                time.sleep(0.2)
                linha = ser.readline().decode("ascii", errors="ignore").strip()
                peso  = self._parsear_peso(linha)
                if peso is not None:
                    return peso, f"✅ {peso:.3f} kg"
                return None, "⚠️ Não foi possível ler o peso"
        except Exception as e:
            return None, f"❌ Erro: {e}"


# Instância global
balanca = Balanca()


def get_peso_balanca(porta=None):
    """
    Função de conveniência para ler o peso.
    Retorna (peso_float, mensagem_str)
    """
    from banco.database import get_config
    porta = porta or get_config("balanca_porta") or "COM1"
    baudrate = int(get_config("balanca_baudrate") or "9600")

    if not SERIAL_OK:
        return None, "❌ Instale: pip install pyserial"

    peso, msg = balanca.ler_peso_unico(porta, baudrate)
    return peso, msg
