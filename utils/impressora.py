"""
utils/impressora.py — Impressão de cupom térmico
Suporte: USB (Windows), Rede (IP:porta), Fallback .txt
"""
import os
import datetime
from banco.database import get_config

# Tenta importar escpos (opcional)
try:
    from escpos.printer import Usb, Network, Win32Raw
    ESCPOS_OK = True
except ImportError:
    ESCPOS_OK = False


# ── Configurações ESC/POS ─────────────────────────────────────────────────────
ESC  = b'\x1b'
GS   = b'\x1d'
INIT       = ESC + b'@'
BOLD_ON    = ESC + b'\x45\x01'
BOLD_OFF   = ESC + b'\x45\x00'
CENTER     = ESC + b'\x61\x01'
LEFT       = ESC + b'\x61\x00'
RIGHT      = ESC + b'\x61\x02'
FONT_LARGE = GS  + b'\x21\x11'
FONT_NORM  = GS  + b'\x21\x00'
CUT        = GS  + b'V\x41\x03'
FEED       = b'\n'


def _linha(char="-", largura=42):
    return char * largura + "\n"


def _formatar_cupom(venda_id, itens, subtotal, desconto,
                    total, forma_pagamento, valor_pago, troco, cpf=""):
    """Monta o texto do cupom"""
    empresa_nome = get_config("empresa_nome") or "Padaria Da Laine"
    empresa_cnpj = get_config("empresa_cnpj") or ""
    empresa_end  = get_config("empresa_end")  or ""
    agora        = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    linhas = []
    linhas.append(_linha("="))
    linhas.append(f"{empresa_nome:^42}\n")
    if empresa_cnpj:
        linhas.append(f"CNPJ: {empresa_cnpj:^36}\n")
    if empresa_end:
        # Quebra endereço longo
        for i in range(0, len(empresa_end), 42):
            linhas.append(f"{empresa_end[i:i+42]}\n")
    linhas.append(_linha("="))
    linhas.append(f"{'CUPOM NAO FISCAL':^42}\n")
    linhas.append(_linha("-"))
    linhas.append(f"Venda #: {venda_id:<10}  Data: {agora[:10]}\n")
    linhas.append(f"Hora: {agora[11:]}\n")
    if cpf:
        linhas.append(f"CPF: {cpf}\n")
    linhas.append(_linha("-"))
    linhas.append(f"{'ITEM':<22}{'QTD':>5}{'UNIT':>7}{'TOTAL':>8}\n")
    linhas.append(_linha("-"))

    for item in itens:
        nome = item["nome_produto"][:21]
        qtd  = f'{item["quantidade"]:.2f}'.rstrip("0").rstrip(".")
        unit = f'R${item["preco_unitario"]:.2f}'
        tot  = f'R${item["total_item"]:.2f}'
        linhas.append(f'{nome:<22}{qtd:>5}{unit:>7}{tot:>8}\n')

    linhas.append(_linha("-"))
    linhas.append(f'{"Subtotal:":>32} R${subtotal:>7.2f}\n')
    if desconto > 0:
        linhas.append(f'{"Desconto:":>32} R${desconto:>7.2f}\n')
    linhas.append(_linha("-"))
    linhas.append(f'{"TOTAL:":>28} R${total:>11.2f}\n')
    linhas.append(_linha("-"))
    linhas.append(f'Pagamento: {forma_pagamento}\n')
    linhas.append(f'Valor pago: R$ {valor_pago:.2f}\n')
    if troco > 0:
        linhas.append(f'Troco: R$ {troco:.2f}\n')
    linhas.append(_linha("="))
    linhas.append(f"{'Obrigado pela preferencia!':^42}\n")
    linhas.append(f"{'Volte sempre!':^42}\n")
    linhas.append(_linha("="))
    linhas.append(f"{'Este nao e um documento fiscal':^42}\n")
    linhas.append("\n\n\n")

    return "".join(linhas)


def _salvar_txt(texto, venda_id):
    """Salva cupom como .txt como fallback"""
    pasta = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "cupons"
    )
    os.makedirs(pasta, exist_ok=True)
    nome = f"cupom_{venda_id:04d}.txt"
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


def imprimir_cupom(venda_id, itens, subtotal, desconto,
                   total, forma_pagamento, valor_pago, troco, cpf=""):
    """
    Imprime cupom na impressora configurada.
    Retorna (sucesso: bool, mensagem: str)
    """
    texto = _formatar_cupom(
        venda_id, itens, subtotal, desconto,
        total, forma_pagamento, valor_pago, troco, cpf
    )

    tipo_impressora = get_config("impressora_tipo") or "txt"
    resultado = False
    mensagem  = ""

    # ── Impressora USB Windows ────────────────────────────────────────────────
    if tipo_impressora == "usb_windows" and ESCPOS_OK:
        try:
            nome_imp = get_config("impressora_nome") or ""
            p = Win32Raw(nome_imp)
            p.set(align="center", bold=True, double_height=True)
            p.text(get_config("empresa_nome") or "Padaria Da Laine")
            p.set(align="left", bold=False, double_height=False)
            p.text("\n")
            for item in itens:
                nome = item["nome_produto"][:21]
                qtd  = f'{item["quantidade"]:.2f}'.rstrip("0").rstrip(".")
                tot  = f'R${item["total_item"]:.2f}'
                p.text(f'{nome:<22}{qtd:>5} {tot:>8}\n')
            p.set(align="right", bold=True)
            p.text(f'\nTOTAL: R$ {total:.2f}\n')
            p.set(align="left", bold=False)
            p.text(f'Pagamento: {forma_pagamento}\n')
            if troco > 0:
                p.text(f'Troco: R$ {troco:.2f}\n')
            p.text('\nObrigado pela preferencia!\n')
            p.text('Este nao e um documento fiscal\n\n\n')
            p.cut()
            resultado = True
            mensagem  = "✅ Cupom impresso com sucesso!"
        except Exception as e:
            mensagem = f"⚠️ Erro USB: {e}"

    # ── Impressora em rede (IP) ───────────────────────────────────────────────
    elif tipo_impressora == "rede" and ESCPOS_OK:
        try:
            ip   = get_config("impressora_ip")   or "192.168.1.100"
            port = int(get_config("impressora_porta") or "9100")
            p = Network(ip, port)
            p.text(texto.encode("cp850", errors="replace"))
            p.cut()
            resultado = True
            mensagem  = "✅ Cupom impresso via rede!"
        except Exception as e:
            mensagem = f"⚠️ Erro rede: {e}"

    # ── Impressora Windows pelo nome (win32print) ─────────────────────────────
    elif tipo_impressora == "win32":
        try:
            import win32print
            import win32ui
            nome_imp = get_config("impressora_nome") or ""
            hprinter = win32print.OpenPrinter(nome_imp)
            try:
                hjob = win32print.StartDocPrinter(
                    hprinter, 1, ("Cupom PDV", None, "RAW"))
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(
                    hprinter, texto.encode("cp850", errors="replace"))
                win32print.EndPagePrinter(hprinter)
                win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)
            resultado = True
            mensagem  = "✅ Cupom impresso!"
        except Exception as e:
            mensagem = f"⚠️ Erro win32: {e}"

    # ── Fallback: salvar como .txt ────────────────────────────────────────────
    if not resultado:
        caminho = _salvar_txt(texto, venda_id)
        resultado = True
        mensagem  = f"📄 Cupom salvo em:\n{caminho}"

    return resultado, mensagem


def testar_impressora():
    """Imprime cupom de teste"""
    itens_teste = [{
        "nome_produto":   "PRODUTO TESTE",
        "quantidade":     1,
        "preco_unitario": 9.99,
        "total_item":     9.99,
    }]
    ok, msg = imprimir_cupom(
        venda_id=0,
        itens=itens_teste,
        subtotal=9.99, desconto=0,
        total=9.99, forma_pagamento="TESTE",
        valor_pago=10.00, troco=0.01
    )
    return ok, msg
