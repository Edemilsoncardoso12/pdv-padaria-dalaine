"""
fiscal/nfce.py — Emissão de NFC-e via API Focus NFe
Homologação: gratuito para testes
Produção: requer CNPJ, IE e certificado digital A1
"""
import json
import datetime
try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

from banco.database import get_config, get_conn

# ── URLs da API ───────────────────────────────────────────────────────────────
URLS = {
    "homologacao": "https://homologacao.focusnfe.com.br/v2/nfce",
    "producao":    "https://api.focusnfe.com.br/v2/nfce",
}

# Mapa forma de pagamento → código NFC-e
FORMA_PAGAMENTO = {
    "DINHEIRO": "01",
    "CREDITO":  "03",
    "DEBITO":   "04",
    "PIX":      "17",
    "FIADO":    "99",
}


def _get_configs():
    return {
        "token":   get_config("focusnfe_token") or "",
        "amb":     get_config("focusnfe_amb")   or "homologacao",
        "cnpj":    get_config("empresa_cnpj")   or "",
        "nome":    get_config("empresa_nome")   or "Padaria Da Laine",
        "ie":      get_config("empresa_ie")     or "",
        "end":     get_config("empresa_end")    or "",
    }


def _montar_payload(venda_id, itens, total, desconto,
                    forma_pagamento, cpf=""):
    """Monta o JSON da NFC-e no formato Focus NFe"""
    cfg = _get_configs()
    agora = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    ref   = f"pdv{venda_id:08d}"

    # Itens da nota
    items_nfe = []
    for i, item in enumerate(itens, 1):
        items_nfe.append({
            "numero_item":                    str(i),
            "codigo_ncm":                     item.get("ncm") or "21069090",
            "descricao":                      item["nome_produto"][:120],
            "cfop":                           "5102",
            "unidade_comercial":              item.get("unidade") or "UN",
            "quantidade_comercial":           str(item["quantidade"]),
            "valor_unitario_comercial":       str(round(item["preco_unitario"], 4)),
            "valor_bruto":                    str(round(item["total_item"], 2)),
            "unidade_tributavel":             item.get("unidade") or "UN",
            "quantidade_tributavel":          str(item["quantidade"]),
            "valor_unitario_tributavel":      str(round(item["preco_unitario"], 4)),
            "icms_situacao_tributaria":       "400",
            "icms_origem":                    "0",
            "pis_situacao_tributaria":        "07",
            "cofins_situacao_tributaria":     "07",
            "valor_desconto":                 "0.00",
            "valor_total_tributos":           "0.00",
        })

    # Forma de pagamento
    cod_pagto = FORMA_PAGAMENTO.get(forma_pagamento.upper(), "01")

    payload = {
        "natureza_operacao":        "VENDA AO CONSUMIDOR",
        "data_emissao":             agora,
        "tipo_documento":           "1",
        "finalidade_emissao":       "1",
        "consumidor_final":         "1",
        "presenca_comprador":       "1",
        "modalidade_frete":         "9",
        "items":                    items_nfe,
        "formas_pagamento": [{
            "forma_pagamento":      cod_pagto,
            "valor_pagamento":      str(round(total, 2)),
        }],
        "valor_produtos":           str(round(sum(i["total_item"] for i in itens), 2)),
        "valor_desconto":           str(round(desconto, 2)),
        "valor_total":              str(round(total, 2)),
    }

    # CPF do consumidor (opcional)
    if cpf and len(cpf.replace(".", "").replace("-", "")) == 11:
        payload["cpf_destinatario"] = cpf.replace(".", "").replace("-", "")

    return ref, payload


def emitir_nfce(venda_id, itens, total, desconto,
                forma_pagamento, cpf=""):
    """
    Emite NFC-e via Focus NFe.
    Retorna (sucesso: bool, mensagem: str, numero_nota: str)
    """
    if not REQUESTS_OK:
        return False, "❌ Instale requests: pip install requests", ""

    cfg = _get_configs()

    if not cfg["token"]:
        return False, "❌ Token Focus NFe não configurado.\nVá em Configurações → NFC-e", ""

    if not cfg["cnpj"] and cfg["amb"] == "producao":
        return False, "❌ CNPJ não configurado para produção.", ""

    try:
        ref, payload = _montar_payload(
            venda_id, itens, total, desconto, forma_pagamento, cpf)

        url = URLS[cfg["amb"]]
        resp = requests.post(
            f"{url}?ref={ref}",
            json=payload,
            auth=(cfg["token"], ""),
            timeout=30
        )

        if resp.status_code in (200, 201):
            dados = resp.json()
            numero = dados.get("numero", "")
            chave  = dados.get("chave_nfe", "")
            danfe  = dados.get("caminho_danfe", "")

            # Salva na venda
            _atualizar_venda_nfce(venda_id, numero, chave, "EMITIDA")

            msg = (f"✅ NFC-e emitida com sucesso!\n\n"
                   f"Número: {numero}\n"
                   f"Chave: {chave[:20]}...\n")
            if danfe:
                msg += f"DANFE: {danfe}"

            return True, msg, numero

        elif resp.status_code == 422:
            erros = resp.json().get("erros", [])
            msg_erro = "\n".join(
                [e.get("mensagem", str(e)) for e in erros]
            ) if erros else resp.text
            _atualizar_venda_nfce(venda_id, "", "", "ERRO")
            return False, f"⚠️ Erro de validação:\n{msg_erro}", ""

        else:
            _atualizar_venda_nfce(venda_id, "", "", "PENDENTE")
            return False, f"⚠️ Erro {resp.status_code}:\n{resp.text[:200]}", ""

    except Exception as e:
        _atualizar_venda_nfce(venda_id, "", "", "PENDENTE")
        return False, f"⚠️ Erro de conexão:\n{str(e)}\n\nVenda salva como PENDENTE.", ""


def cancelar_nfce(venda_id, justificativa="Cancelamento solicitado pelo emitente"):
    """Cancela uma NFC-e emitida (prazo de 30 minutos)"""
    if not REQUESTS_OK:
        return False, "❌ requests não instalado"

    cfg = _get_configs()
    conn = get_conn()
    venda = conn.execute(
        "SELECT nfce_numero FROM vendas WHERE id=?", (venda_id,)
    ).fetchone()
    conn.close()

    if not venda or not venda["nfce_numero"]:
        return False, "❌ Nota não encontrada."

    ref = f"pdv{venda_id:08d}"
    url = URLS[cfg["amb"]]

    try:
        resp = requests.delete(
            f"{url}/{ref}",
            json={"justificativa": justificativa},
            auth=(cfg["token"], ""),
            timeout=30
        )
        if resp.status_code == 200:
            _atualizar_venda_nfce(venda_id, "", "", "CANCELADA")
            return True, "✅ NFC-e cancelada com sucesso!"
        else:
            return False, f"⚠️ Erro ao cancelar: {resp.text[:200]}"
    except Exception as e:
        return False, f"⚠️ Erro: {str(e)}"


def consultar_nfce(venda_id):
    """Consulta status de uma NFC-e"""
    if not REQUESTS_OK:
        return False, "❌ requests não instalado"

    cfg = _get_configs()
    ref = f"pdv{venda_id:08d}"
    url = URLS[cfg["amb"]]

    try:
        resp = requests.get(
            f"{url}/{ref}",
            auth=(cfg["token"], ""),
            timeout=30
        )
        if resp.status_code == 200:
            dados = resp.json()
            status = dados.get("status", "")
            return True, f"Status: {status}"
        return False, f"Erro {resp.status_code}"
    except Exception as e:
        return False, str(e)


def _atualizar_venda_nfce(venda_id, numero, chave, status):
    conn = get_conn()
    conn.execute("""
        UPDATE vendas SET
            nfce_numero=?,
            nfce_chave=?,
            nfce_status=?
        WHERE id=?
    """, (numero, chave, status, venda_id))
    conn.commit()
    conn.close()


def listar_notas(data_ini=None, data_fim=None):
    """Lista notas fiscais emitidas"""
    conn = get_conn()
    query = """
        SELECT id, data_hora, total, nfce_numero,
               nfce_status, forma_pagamento
        FROM vendas
        WHERE nfce_status IS NOT NULL
    """
    params = []
    if data_ini:
        query += " AND date(data_hora) >= ?"
        params.append(data_ini)
    if data_fim:
        query += " AND date(data_hora) <= ?"
        params.append(data_fim)
    query += " ORDER BY data_hora DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows
