"""
telas/fechamento.py — Fechamento de Caixa modelo Eccus
Secoes: Anterior-Caixa / Mov.Caixa-Retirada / Recolhimento / Vendas / Resumo / Diferenca
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn, caixa_aberto, fechar_caixa, get_config
try:
    from sangria import DialogoMovimentacao as _DlgMov, registrar_movimentacao as _RegMov
except Exception:
    try:
        from telas.sangria import DialogoMovimentacao as _DlgMov, registrar_movimentacao as _RegMov
    except Exception:
        _DlgMov = None
        _RegMov = None


import re as _re

def _grupo_forma(forma):
    f = forma.upper()
    if "DINHEIRO" in f:                    return "DINHEIRO"
    if "PIX"      in f:                    return "PIX"
    if "VALE"     in f:                    return "VALE ALIMENTACAO"
    if "CREDITO"  in f or "CRÉDITO" in f: return "CREDITO"
    if "DEBITO"   in f or "DÉBITO"  in f: return "DEBITO"
    return "OUTROS"

def _extrair_grupos(forma, total):
    """
    Extrai grupos e valores de formas simples ou mistas.
    Ex: 'DINHEIRO(R$150.0) + CARTAO - CREDITO(R$338.0)' -> {'DINHEIRO':150, 'CREDITO':338}
    Ex: 'PIX' -> {'PIX': total}
    """
    resultado = {}
    partes = _re.findall(r'([A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀ\s\-]+)\(R\$([\d.,]+)\)', forma)
    if partes:
        for nome, val_str in partes:
            try:
                valor = float(val_str.replace(",","."))
            except Exception:
                valor = 0.0
            g = _grupo_forma(nome.strip())
            resultado[g] = resultado.get(g, 0.0) + valor
    else:
        resultado[_grupo_forma(forma)] = total
    return resultado


def get_resumo_caixa(caixa_id):
    conn = get_conn()
    cx = conn.execute("SELECT * FROM caixa WHERE id=?", (caixa_id,)).fetchone()

    vendas = conn.execute("""
        SELECT forma_pagamento, COUNT(*) as qtde,
               SUM(total) as total, SUM(troco) as troco
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
        GROUP BY forma_pagamento ORDER BY total DESC
    """, (caixa_id,)).fetchall()

    total_geral = conn.execute("""
        SELECT COALESCE(SUM(total),0), COUNT(*)
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
    """, (caixa_id,)).fetchone()

    produtos_top = conn.execute("""
        SELECT iv.nome_produto, SUM(iv.quantidade) as qtde,
               SUM(iv.total_item) as total
        FROM itens_venda iv JOIN vendas v ON v.id=iv.venda_id
        WHERE v.caixa_id=? AND v.status='CONCLUIDA'
        GROUP BY iv.nome_produto ORDER BY total DESC LIMIT 10
    """, (caixa_id,)).fetchall()

    movs = []
    try:
        movs = conn.execute("""
            SELECT id, caixa_id, tipo, valor, motivo, usuario, data_hora
            FROM sangria_suprimento WHERE caixa_id=? ORDER BY data_hora
        """, (caixa_id,)).fetchall()
    except Exception:
        pass
    if not movs:
        try:
            movs = conn.execute("""
                SELECT id, caixa_id, tipo, valor,
                       descricao as motivo, operador as usuario, data_hora
                FROM movimentacao_caixa WHERE caixa_id=? ORDER BY data_hora
            """, (caixa_id,)).fetchall()
        except Exception:
            pass

    conn.close()
    movs   = [dict(m) for m in movs]
    vendas = [dict(v) for v in vendas]

    retiradas    = sum(m["valor"] for m in movs if m["tipo"] in ("RETIRADA","SANGRIA","DESPESA"))
    recolhimento = sum(m["valor"] for m in movs if m["tipo"] == "RECOLHIMENTO")
    suprimento   = sum(m["valor"] for m in movs if m["tipo"] == "SUPRIMENTO")
    total_dinheiro = sum(
        _extrair_grupos(v["forma_pagamento"], v["total"]).get("DINHEIRO", 0.0)
        for v in vendas
    )

    grupos_venda = {}
    for v in vendas:
        partes = _extrair_grupos(v["forma_pagamento"], v["total"])
        for g, val in partes.items():
            grupos_venda[g] = grupos_venda.get(g, 0.0) + val

    return {
        "caixa":          dict(cx) if cx else {},
        "vendas":         vendas,
        "total_vendas":   total_geral[0],
        "total_dinheiro": total_dinheiro,
        "qtde_vendas":    total_geral[1],
        "retiradas":      retiradas,
        "recolhimento":   recolhimento,
        "suprimento":     suprimento,
        "sangria":        retiradas + recolhimento,
        "produtos_top":   [dict(p) for p in produtos_top],
        "movimentacoes":  movs,
        "grupos_venda":   grupos_venda,
    }


class TelaFechamentoCaixa(ctk.CTkFrame):
    def __init__(self, master, usuario="Sistema"):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cx = caixa_aberto()
        self.caixa_id = cx["id"]   if cx else None
        self.cx_dados = dict(cx)   if cx else {}
        self._ent_dinheiro  = None
        self._lbl_diferenca = None
        self._checks_baixa  = {}
        self._build_header()
        if self.caixa_id:
            self._build_corpo()
        else:
            self._build_sem_caixa()

    # ─────────────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_columnconfigure(2, weight=0)
        ctk.CTkLabel(hdr, text="🔒  Fechamento",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=16, pady=18, sticky="w")
        if self.caixa_id:
            ab = self.cx_dados.get("data_abertura","")[:16]
            ctk.CTkLabel(hdr, text=f"Cx#{self.caixa_id} — {ab}",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(
                row=0, column=1, padx=8, sticky="w")
            bf = ctk.CTkFrame(hdr, fg_color="transparent")
            bf.grid(row=0, column=2, padx=16, sticky="e")
            ctk.CTkButton(bf, text="📤 Retirada", font=FONTE_BTN, height=36,
                         fg_color=COR_PERIGO, hover_color=COR_PERIGO2, text_color="white",
                         command=self._mov_retirada).pack(side="left", padx=3)
            ctk.CTkButton(bf, text="📥 Suprimento", font=FONTE_BTN, height=36,
                         fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2, text_color="white",
                         command=self._mov_suprimento).pack(side="left", padx=3)
            ctk.CTkButton(bf, text="💰 Recolhimento", font=FONTE_BTN, height=36,
                         fg_color="#6B7280", hover_color="#4B5563", text_color="white",
                         command=self._mov_recolhimento).pack(side="left", padx=3)
            ctk.CTkButton(bf, text="🧾 Despesa", font=FONTE_BTN, height=36,
                         fg_color="#B45309", hover_color="#92400E", text_color="white",
                         command=self._mov_despesa).pack(side="left", padx=3)

    def _build_sem_caixa(self):
        f = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12)
        f.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        ctk.CTkLabel(f, text="⚠️  Nenhum caixa aberto!",
                     font=FONTE_TITULO, text_color=COR_PERIGO).pack(pady=60)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_corpo(self):
        res     = get_resumo_caixa(self.caixa_id)
        val_ini = self.cx_dados.get("valor_inicial", 0)
        movs    = res["movimentacoes"]

        # Só afetam o dinheiro físico: retiradas/despesas e recolhimentos NÃO eletrônicos
        FORMAS_ELETR = {"PIX","CREDITO","DEBITO","VALE ALIMENTACAO","OUTROS"}
        saidas_dinheiro = sum(
            m["valor"] for m in movs
            if m["tipo"] in ("RETIRADA","SANGRIA","DESPESA")
        ) + sum(
            m["valor"] for m in movs
            if m["tipo"] == "RECOLHIMENTO"
            and (m.get("motivo","") or "").upper() not in FORMAS_ELETR
        )
        self.saldo_esperado = val_ini + res["total_dinheiro"] + res["suprimento"] - saidas_dinheiro
        self._res_atual = res

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)
        r = 0

        # ── ANTERIOR - CAIXA
        r = self._secao(scroll, r, "ANTERIOR - CAIXA")
        r = self._linha(scroll, r,
            self.cx_dados.get("data_abertura","")[:16],
            "VALOR INICIADO CAIXA", self.usuario,
            f"R$ {val_ini:.2f}", COR_TEXTO)
        r = self._subtotal(scroll, r, val_ini)

        # ── MOV. CAIXA - RETIRADA
        movs     = res["movimentacoes"]
        movs_ret = [m for m in movs if m["tipo"] in ("RETIRADA","SANGRIA","DESPESA")]
        FORMAS_ELETR = {"PIX","CREDITO","DEBITO","VALE ALIMENTACAO","OUTROS"}
        movs_rec_din = [m for m in movs
                        if m["tipo"] == "RECOLHIMENTO"
                        and (m.get("motivo","") or "").upper() not in FORMAS_ELETR]
        movs_rec_form = [m for m in movs
                         if m["tipo"] == "RECOLHIMENTO"
                         and (m.get("motivo","") or "").upper() in FORMAS_ELETR]
        movs_sup = [m for m in movs if m["tipo"] == "SUPRIMENTO"]

        if movs_ret or movs_rec_din:
            r = self._secao(scroll, r, "MOV. CAIXA - RETIRADA")
            total_ret = 0.0
            for m in movs_ret:
                r = self._linha(scroll, r, m["data_hora"][:16],
                    m.get("motivo","") or m["tipo"],
                    m.get("usuario","") or "—",
                    f"-R$ {m['valor']:.2f}", COR_PERIGO)
                total_ret -= m["valor"]
            for m in movs_rec_din:
                r = self._linha(scroll, r, m["data_hora"][:16],
                    m.get("motivo","") or "RECOLHIMENTO",
                    m.get("usuario","") or "—",
                    f"-R$ {m['valor']:.2f}", "#6B7280")
                total_ret -= m["valor"]
            r = self._subtotal(scroll, r, total_ret)

        # Recolhimentos de outras formas (cartão, pix, etc) ficam separados
        if movs_rec_form:
            r = self._secao(scroll, r, "RECOLHIMENTO - FORMAS DE PAGAMENTO")
            total_rec_form = 0.0
            for m in movs_rec_form:
                r = self._linha(scroll, r, m["data_hora"][:16],
                    m.get("motivo","") or "RECOLHIMENTO",
                    m.get("usuario","") or "—",
                    f"-R$ {m['valor']:.2f}", "#1D4ED8")
                total_rec_form -= m["valor"]
            r = self._subtotal(scroll, r, total_rec_form)

        if movs_sup:
            r = self._secao(scroll, r, "SUPRIMENTO")
            total_sup = 0.0
            for m in movs_sup:
                r = self._linha(scroll, r, m["data_hora"][:16],
                    m.get("motivo","") or "SUPRIMENTO",
                    m.get("usuario","") or "—",
                    f"+R$ {m['valor']:.2f}", COR_SUCESSO)
                total_sup += m["valor"]
            r = self._subtotal(scroll, r, total_sup)

        # ── VENDAS
        r = self._secao(scroll, r, "VENDAS")
        total_vend = 0.0
        for v in res["vendas"]:
            r = self._linha(scroll, r, "",
                v["forma_pagamento"], f"{v['qtde']} vendas",
                f"R$ {v['total']:.2f}", COR_SUCESSO)
            total_vend += v["total"]
        r = self._subtotal(scroll, r, total_vend)

        # ── RESUMO
        r = self._secao(scroll, r, "RESUMO")
        r = self._tabela_resumo(scroll, r, res, val_ini)

        # ── DAR BAIXA
        movs_rec = movs_rec_din + movs_rec_form
        ja_recolhidos = {(m.get("motivo","") or "").upper() for m in movs_rec}
        formas_pendentes = {
            g: v for g, v in res["grupos_venda"].items()
            if g != "DINHEIRO" and v > 0 and g not in ja_recolhidos
        }
        if formas_pendentes:
            r = self._build_dar_baixa(scroll, r, formas_pendentes)

        # ── CONFERÊNCIA DINHEIRO
        r = self._build_conferencia(scroll, r)

        # ── BOTÕES
        fb = ctk.CTkFrame(scroll, fg_color="transparent")
        fb.grid(row=r, column=0, sticky="ew", pady=(8,0)); r+=1
        fb.grid_columnconfigure((0,1), weight=1)
        ctk.CTkButton(fb, text="🖨️  Imprimir Relatório",
                      font=FONTE_BTN, height=44,
                      fg_color="#6B7280", hover_color="#4B5563", text_color="white",
                      command=lambda: self._gerar_pdf(res, self.saldo_esperado)
                      ).grid(row=0, column=0, padx=(0,4), sticky="ew")
        ctk.CTkButton(fb, text="🔒  FECHAR CAIXA",
                      font=("Georgia",16,"bold"), height=44,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2, text_color="white",
                      command=lambda: self._fechar(res)
                      ).grid(row=0, column=1, padx=(4,0), sticky="ew")

    # ── WIDGETS ──────────────────────────────────────────────────────────────
    def _secao(self, parent, row, titulo):
        f = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=6, height=30)
        f.grid(row=row, column=0, sticky="ew", pady=(6,0))
        f.grid_propagate(False)
        ctk.CTkLabel(f, text=titulo, font=("Courier New",12,"bold"),
                     text_color=COR_ACENTO).pack(side="left", padx=12, pady=4)
        return row + 1

    def _linha(self, parent, row, data, descricao, usuario, valor, cor_val):
        cor_bg = COR_LINHA_PAR if row % 2 == 0 else COR_CARD
        f = ctk.CTkFrame(parent, fg_color=cor_bg, corner_radius=0, height=28)
        f.grid(row=row, column=0, sticky="ew")
        f.grid_propagate(False)
        f.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text=data, font=("Courier New",11),
                     text_color=COR_TEXTO_SUB, width=130, anchor="w").grid(
            row=0, column=0, padx=8, pady=3, sticky="w")
        ctk.CTkLabel(f, text=descricao, font=("Courier New",11),
                     text_color=COR_TEXTO, anchor="w").grid(
            row=0, column=1, padx=4, pady=3, sticky="w")
        ctk.CTkLabel(f, text=usuario, font=("Courier New",11),
                     text_color=COR_TEXTO_SUB, width=80, anchor="w").grid(
            row=0, column=2, padx=4, pady=3, sticky="w")
        ctk.CTkLabel(f, text=valor, font=("Courier New",11,"bold"),
                     text_color=cor_val, width=110, anchor="e").grid(
            row=0, column=3, padx=8, pady=3, sticky="e")
        return row + 1

    def _subtotal(self, parent, row, valor):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        cor = COR_SUCESSO if valor >= 0 else COR_PERIGO
        ctk.CTkLabel(f, text=f"Sub-Total:   R$ {valor:.2f}",
                     font=("Courier New",11,"bold"), text_color=cor,
                     anchor="e").grid(row=0, column=0, padx=12, pady=2, sticky="e")
        ctk.CTkFrame(f, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=8, pady=(0,4))
        return row + 1

    def _tabela_resumo(self, parent, row, res, val_ini):
        frame = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=8,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=row, column=0, sticky="ew", pady=4)

        # Cabeçalho
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO, corner_radius=0, height=28)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        ctk.CTkLabel(cab, text="", width=200, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(cab, text="Entradas", font=("Courier New",12,"bold"),
                     text_color="white", width=120, anchor="e").pack(side="left", padx=4, pady=4, expand=True)
        ctk.CTkLabel(cab, text="Saídas", font=("Courier New",12,"bold"),
                     text_color="white", width=120, anchor="e").pack(side="right", padx=8, pady=4)

        # Saídas por grupo
        movs = res["movimentacoes"]
        FORMAS_ELETR_R = {"PIX","CREDITO","DEBITO","VALE ALIMENTACAO","OUTROS"}
        saidas_grupo = {}
        for m in movs:
            if m["tipo"] == "RECOLHIMENTO":
                motivo = (m.get("motivo","") or "").upper()
                # recolhimento eletrônico vai para sua forma, senão vai para DINHEIRO
                g = motivo if motivo in FORMAS_ELETR_R else "DINHEIRO"
                saidas_grupo[g] = saidas_grupo.get(g, 0) + m["valor"]
            elif m["tipo"] in ("RETIRADA","SANGRIA","DESPESA"):
                saidas_grupo["DINHEIRO"] = saidas_grupo.get("DINHEIRO", 0) + m["valor"]

        linhas = [("INICIO", val_ini, 0.0)]
        for g, ent in res["grupos_venda"].items():
            linhas.append((g, ent, saidas_grupo.get(g, 0.0)))

        total_ent = val_ini
        total_sai = 0.0

        for idx, (nome, ent, sai) in enumerate(linhas):
            cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
            lf = ctk.CTkFrame(frame, fg_color=cor_bg, corner_radius=0, height=26)
            lf.pack(fill="x")
            lf.pack_propagate(False)
            ctk.CTkLabel(lf, text=nome, font=("Courier New",11),
                         text_color=COR_TEXTO, width=200, anchor="w").pack(
                side="left", padx=12, pady=3)
            ctk.CTkLabel(lf, text=f"{ent:.2f}",
                         font=("Courier New",11), text_color=COR_SUCESSO,
                         width=120, anchor="e").pack(side="left", padx=4, pady=3, expand=True)
            ctk.CTkLabel(lf, text=f"{sai:.2f}",
                         font=("Courier New",11),
                         text_color=COR_PERIGO if sai > 0 else COR_TEXTO_SUB,
                         width=120, anchor="e").pack(side="right", padx=8, pady=3)
            if nome != "INICIO":
                total_ent += ent
                total_sai += sai

        # Totais
        tf = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT, corner_radius=0, height=28)
        tf.pack(fill="x")
        tf.pack_propagate(False)
        ctk.CTkLabel(tf, text="Totais", font=("Courier New",12,"bold"),
                     text_color=COR_ACENTO, width=200, anchor="w").pack(
            side="left", padx=12, pady=4)
        ctk.CTkLabel(tf, text=f"{total_ent:.2f}",
                     font=("Courier New",12,"bold"), text_color=COR_SUCESSO,
                     width=120, anchor="e").pack(side="left", padx=4, pady=4, expand=True)
        ctk.CTkLabel(tf, text=f"{total_sai:.2f}",
                     font=("Courier New",12,"bold"),
                     text_color=COR_PERIGO if total_sai > 0 else COR_TEXTO_SUB,
                     width=120, anchor="e").pack(side="right", padx=8, pady=4)

        return row + 1

    def _build_dar_baixa(self, parent, row, formas_pendentes):
        frame = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                             border_width=2, border_color="#1D4ED8")
        frame.grid(row=row, column=0, sticky="ew", pady=(8,4))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="💳  DAR BAIXA NAS FORMAS DE PAGAMENTO",
                     font=("Georgia",13,"bold"), text_color="#1D4ED8").pack(
            anchor="w", padx=16, pady=(10,2))
        ctk.CTkLabel(frame,
                     text="Marque as formas já conferidas na maquininha/app e clique em Dar Baixa",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(
            anchor="w", padx=16, pady=(0,6))

        self._checks_baixa = {}
        for g, valor in formas_pendentes.items():
            lf = ctk.CTkFrame(frame, fg_color=COR_LINHA_PAR, corner_radius=6, height=36)
            lf.pack(fill="x", padx=12, pady=2)
            lf.pack_propagate(False)
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(lf, text=f"  {g}", variable=var,
                           font=("Courier New",12,"bold"), text_color=COR_TEXTO,
                           fg_color="#1D4ED8", hover_color="#1E40AF").pack(
                side="left", padx=12, pady=6)
            ctk.CTkLabel(lf, text=f"R$ {valor:.2f}",
                         font=("Courier New",12,"bold"),
                         text_color=COR_SUCESSO).pack(side="right", padx=16, pady=6)
            self._checks_baixa[g] = (var, valor)

        ctk.CTkButton(frame, text="✅  Dar Baixa nas Selecionadas",
                      font=FONTE_BTN, height=38, corner_radius=8,
                      fg_color="#1D4ED8", hover_color="#1E40AF", text_color="white",
                      command=self._confirmar_baixa).pack(
            fill="x", padx=12, pady=(4,10))

        return row + 1

    def _confirmar_baixa(self):
        import importlib.util, os, sys
        registrar = _RegMov
        if registrar is None:
            try:
                base     = os.path.dirname(os.path.abspath(__file__))
                caminho  = os.path.join(base, "sangria.py")
                spec     = importlib.util.spec_from_file_location("sangria", caminho)
                mod      = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                registrar = mod.registrar_movimentacao
            except Exception as e:
                messagebox.showerror("Erro", f"Nao foi possivel registrar:\n{e}")
                return

        selecionadas = [(g, v) for g, (var, v) in self._checks_baixa.items() if var.get()]
        if not selecionadas:
            messagebox.showwarning("Atencao", "Marque pelo menos uma forma!")
            return

        for g, valor in selecionadas:
            registrar(self.caixa_id, "RECOLHIMENTO", valor, g, self.usuario)

        nomes = ", ".join(g for g, _ in selecionadas)
        messagebox.showinfo("Baixa Registrada", f"Recolhimento registrado:\n{nomes}")
        self._recarregar()

    def _build_conferencia(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_SUCESSO)
        frame.grid(row=row, column=0, sticky="ew", pady=(8,4))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="💵  DINHEIRO NA GAVETA",
                     font=("Georgia",13,"bold"), text_color=COR_SUCESSO).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(10,2), sticky="w")
        ctk.CTkLabel(frame,
                     text=f"Esperado: R$ {self.saldo_esperado:.2f}  "
                          f"(Fundo + Vendas Dinheiro + Suprimentos - Retiradas - Recolhimentos)",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).grid(
            row=1, column=0, columnspan=2, padx=16, pady=(0,6), sticky="w")

        ctk.CTkLabel(frame, text="Você contou (R$):",
                     font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(
            row=2, column=0, padx=16, pady=8, sticky="w")

        self._ent_dinheiro = ctk.CTkEntry(frame, font=("Georgia",20), width=160,
                                          justify="center", placeholder_text="0,00",
                                          fg_color=COR_CARD2, border_color=COR_SUCESSO,
                                          border_width=2, text_color=COR_TEXTO)
        self._ent_dinheiro.grid(row=2, column=1, padx=16, pady=8, sticky="e")
        self._ent_dinheiro.bind("<KeyRelease>", self._calcular_diferenca)

        self._lbl_diferenca = ctk.CTkLabel(frame, text="",
                                           font=("Georgia",13,"bold"),
                                           text_color=COR_TEXTO_SUB)
        self._lbl_diferenca.grid(row=3, column=0, columnspan=2,
                                 padx=16, pady=(0,10), sticky="e")
        return row + 1

    def _calcular_diferenca(self, event=None):
        try:
            val_txt = self._ent_dinheiro.get().strip().replace(",",".")
            if not val_txt:
                self._lbl_diferenca.configure(text="")
                return
            contado = float(val_txt)
            diff    = contado - self.saldo_esperado
            cor     = COR_SUCESSO if abs(diff) < 0.01 else COR_PERIGO
            if abs(diff) < 0.01:
                texto = "✅  Caixa conferido! Valores batem."
            elif diff > 0:
                texto = f"⚠️  Sobrou R$ {abs(diff):.2f} no caixa."
            else:
                texto = f"❌  Faltam R$ {abs(diff):.2f} no caixa!"
            self._lbl_diferenca.configure(text=texto, text_color=cor)
        except Exception:
            pass

    # ── FECHAR ───────────────────────────────────────────────────────────────
    def _fechar(self, res):
        val_txt     = self._ent_dinheiro.get().strip().replace(",",".") if self._ent_dinheiro else ""
        val_contado = float(val_txt) if val_txt else self.saldo_esperado
        diff        = val_contado - self.saldo_esperado
        sinal       = "+" if diff >= 0 else ""
        msg_diff    = "Gaveta OK!" if abs(diff) < 0.01 else f"Diferenca: {sinal}R$ {diff:.2f}"

        if not messagebox.askyesno("Fechar Caixa",
            f"Confirma o fechamento?\n\n"
            f"Total vendas:       R$ {res['total_vendas']:.2f}\n"
            f"Vendas dinheiro:    R$ {res['total_dinheiro']:.2f}\n"
            f"Esperado na gaveta: R$ {self.saldo_esperado:.2f}\n"
            f"Voce contou:        R$ {val_contado:.2f}\n"
            f"{msg_diff}\n\n"
            f"Esta acao nao pode ser desfeita!"):
            return

        fechar_caixa(self.caixa_id, val_contado)
        self._gerar_pdf(res, val_contado, fechando=True)
        messagebox.showinfo("Caixa Fechado",
                            "Caixa fechado com sucesso!\nRelatorio salvo em cupons\\")
        self.caixa_id = None
        try:
            toplevel = self.winfo_toplevel()
            if str(toplevel) != str(self):
                toplevel.destroy()
            else:
                for w in self.winfo_children():
                    try: w.destroy()
                    except Exception: pass
                self._build_header()
                self._build_sem_caixa()
        except Exception:
            pass

    # ── RECARREGAR ────────────────────────────────────────────────────────────
    def _recarregar(self):
        for w in self.winfo_children():
            try: w.destroy()
            except Exception: pass
        self._ent_dinheiro  = None
        self._lbl_diferenca = None
        self._checks_baixa  = {}
        cx = caixa_aberto()
        self.caixa_id = cx["id"]   if cx else None
        self.cx_dados = dict(cx)   if cx else {}
        self._build_header()
        if self.caixa_id:
            self._build_corpo()
        else:
            self._build_sem_caixa()

    # ── MOVIMENTAÇÃO RÁPIDA ───────────────────────────────────────────────────
    def _mov_retirada(self):    self._nova_movimentacao("RETIRADA")
    def _mov_suprimento(self):  self._nova_movimentacao("SUPRIMENTO")
    def _mov_recolhimento(self): self._nova_movimentacao("RECOLHIMENTO")
    def _mov_despesa(self):     self._nova_movimentacao("DESPESA")

    def _nova_movimentacao(self, tipo):
        import importlib.util, os, sys
        DlgMov = _DlgMov
        if DlgMov is None:
            try:
                base    = os.path.dirname(os.path.abspath(__file__))
                caminho = os.path.join(base, "sangria.py")
                spec    = importlib.util.spec_from_file_location("sangria", caminho)
                mod     = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                DlgMov  = mod.DialogoMovimentacao
            except Exception as e:
                messagebox.showerror("Erro", f"Nao foi possivel abrir movimentacao:\n{e}")
                return
        DlgMov(self, tipo, self.caixa_id, self.usuario, self._recarregar)

    # ── PDF MODELO ECCUS ──────────────────────────────────────────────────────
    def _gerar_pdf(self, res, valor_final, fechando=False):
        import os, sys, base64
        try:
            base  = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
                    else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            path  = os.path.join(pasta, f"fechamento_caixa_{agora}.pdf")

            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable, Image)
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.pdfgen import canvas as pdfcanvas

            COR_PDF   = colors.HexColor("#8B1A1A")
            COR_CINZA = colors.HexColor("#F5F0E8")
            COR_VERDE = colors.HexColor("#059669")
            COR_VERM  = colors.HexColor("#DC2626")
            COR_SEC   = colors.HexColor("#B45309")
            COR_SEC_BG= colors.HexColor("#FEF3C7")

            empresa  = get_config("empresa_nome")     or "Padaria Da Laine"
            endereco = get_config("empresa_endereco") or ""
            cnpj     = get_config("empresa_cnpj")     or ""
            fone     = get_config("empresa_fone")     or ""
            val_ini  = self.cx_dados.get("valor_inicial", 0)

            # Caminho do logo
            base_dir = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
                       else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(base_dir, "logo.png")
            if not os.path.exists(logo_path):
                logo_path = os.path.join(base_dir, "assets", "logo.png")
            tem_logo = os.path.exists(logo_path)

            # Marca dagua — callback para cada pagina
            def marca_dagua(canvas_obj, doc_obj):
                if not tem_logo: return
                canvas_obj.saveState()
                try:
                    from PIL import Image as PILImage
                    pw, ph = A4
                    canvas_obj.setFillAlpha(0.06)
                    canvas_obj.drawImage(logo_path,
                        pw/2 - 6*cm, ph/2 - 6*cm,
                        width=12*cm, height=12*cm,
                        preserveAspectRatio=True, mask="auto")
                except Exception:
                    pass
                canvas_obj.restoreState()

            doc = SimpleDocTemplate(path, pagesize=A4,
                                    topMargin=1.8*cm, bottomMargin=1.8*cm,
                                    leftMargin=2*cm,  rightMargin=2*cm)
            story = []

            T = lambda txt, size=10, bold=False, cor=colors.black, align=TA_LEFT: \
                Paragraph(txt, ParagraphStyle("x", fontSize=size,
                          fontName="Helvetica-Bold" if bold else "Helvetica",
                          textColor=cor, alignment=align, spaceAfter=2,
                          leading=size*1.4))

            COL_W = [3.5*cm, 7*cm, 2.5*cm, 4*cm]

            def secao(titulo, cor_bg="#B45309", cor_txt="white"):
                story.append(Spacer(1, 0.25*cm))
                story.append(Table([[titulo]], colWidths=[17*cm],
                    style=TableStyle([
                        ("BACKGROUND",(0,0),(-1,-1), colors.HexColor(cor_bg)),
                        ("TEXTCOLOR",(0,0),(-1,-1), colors.HexColor(cor_txt) if cor_txt != "white" else colors.white),
                        ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                        ("FONTSIZE",(0,0),(-1,-1),10),
                        ("TOPPADDING",(0,0),(-1,-1),5),
                        ("BOTTOMPADDING",(0,0),(-1,-1),5),
                        ("LEFTPADDING",(0,0),(-1,-1),10),
                        ("ROUNDEDCORNERS",(0,0),(-1,-1),2),
                    ])))

            def cab_tab():
                story.append(Table([["Data/Hora","Descrição","Usuário","Valor"]],
                    colWidths=COL_W,
                    style=TableStyle([
                        ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                        ("FONTSIZE",(0,0),(-1,-1),8),
                        ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#FEF3C7")),
                        ("TEXTCOLOR",(0,0),(-1,-1), colors.HexColor("#92400E")),
                        ("ALIGN",(3,0),(3,-1),"RIGHT"),
                        ("TOPPADDING",(0,0),(-1,-1),4),
                        ("BOTTOMPADDING",(0,0),(-1,-1),4),
                        ("LEFTPADDING",(0,0),(-1,-1),6),
                        ("LINEBELOW",(0,0),(-1,-1),1, colors.HexColor("#B45309")),
                    ])))

            def linhas_tab(linhas, cor_valor=None):
                if not linhas: return
                t = Table(linhas, colWidths=COL_W)
                style = [
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                    ("FONTSIZE",(0,0),(-1,-1),9),
                    ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, COR_CINZA]),
                    ("ALIGN",(3,0),(3,-1),"RIGHT"),
                    ("TOPPADDING",(0,0),(-1,-1),5),
                    ("BOTTOMPADDING",(0,0),(-1,-1),5),
                    ("LEFTPADDING",(0,0),(-1,-1),6),
                    ("LINEBELOW",(0,-1),(-1,-1),0.5, colors.HexColor("#E5E7EB")),
                ]
                if cor_valor:
                    for i in range(len(linhas)):
                        style.append(("TEXTCOLOR",(3,i),(3,i), cor_valor))
                        style.append(("FONTNAME",(3,i),(3,i),"Helvetica-Bold"))
                t.setStyle(TableStyle(style))
                story.append(t)

            def subtotal(valor):
                cor_s = COR_VERDE if valor >= 0 else COR_VERM
                sinal = "+" if valor >= 0 else ""
                story.append(Table([[f"Sub-Total: {sinal}R$ {valor:.2f}"]], colWidths=[17*cm],
                    style=TableStyle([
                        ("ALIGN",(0,0),(-1,-1),"RIGHT"),
                        ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                        ("FONTSIZE",(0,0),(-1,-1),10),
                        ("TEXTCOLOR",(0,0),(-1,-1), cor_s),
                        ("TOPPADDING",(0,0),(-1,-1),4),
                        ("BOTTOMPADDING",(0,0),(-1,-1),4),
                        ("RIGHTPADDING",(0,0),(-1,-1),10),
                        ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#F9FAFB")),
                        ("LINEABOVE",(0,0),(-1,-1),1, colors.HexColor("#E5E7EB")),
                    ])))
                story.append(Spacer(1, 0.1*cm))

            # Cabeçalho PDF com logo
            ab = self.cx_dados.get("data_abertura","")[:16]

            if tem_logo:
                try:
                    logo_img = Image(logo_path, width=3.5*cm, height=3.5*cm)
                    info_txt = f"""<b><font size=16 color="#8B1A1A">{empresa.upper()}</font></b><br/>
<font size=9 color="#6B7280">{endereco}</font><br/>
<font size=9 color="#6B7280">CNPJ: {cnpj}   Fone: {fone}</font>"""
                    cab_data = [[logo_img,
                                 Paragraph(info_txt, ParagraphStyle("cab",
                                     alignment=TA_LEFT, leading=14, spaceAfter=0))]]
                    logo_tab = Table(cab_data, colWidths=[4*cm, 13*cm])
                    logo_tab.setStyle(TableStyle([
                        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                        ("LEFTPADDING",(0,0),(-1,-1),0),
                        ("RIGHTPADDING",(0,0),(-1,-1),0),
                        ("TOPPADDING",(0,0),(-1,-1),0),
                        ("BOTTOMPADDING",(0,0),(-1,-1),0),
                    ]))
                    story.append(logo_tab)
                except Exception:
                    story.append(T(empresa.upper(), 16, True, COR_PDF, TA_CENTER))
            else:
                story.append(T(empresa.upper(), 16, True, COR_PDF, TA_CENTER))
                if endereco: story.append(T(endereco, 9, align=TA_CENTER))
                if cnpj:     story.append(T(f"CNPJ: {cnpj}   Fone: {fone}", 9, align=TA_CENTER))

            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=2, color=COR_PDF))
            story.append(Spacer(1, 0.15*cm))

            # Titulo
            titulo_data = [["PRÉ FECHAMENTO DE CAIXA"]]
            titulo_tab  = Table(titulo_data, colWidths=[17*cm])
            titulo_tab.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#8B1A1A")),
                ("TEXTCOLOR",(0,0),(-1,-1), colors.white),
                ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),13),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("TOPPADDING",(0,0),(-1,-1),7),
                ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ]))
            story.append(titulo_tab)
            story.append(T(f"Caixa #{self.caixa_id}    Aberto: {ab}    Operador: {self.usuario}",
                           9, align=TA_CENTER))
            story.append(Spacer(1, 0.3*cm))

            # ANTERIOR - CAIXA
            secao("ANTERIOR - CAIXA", "#92400E")
            cab_tab()
            linhas_tab([[ab, "VALOR INICIADO CAIXA", self.usuario, f"R$ {val_ini:.2f}"]])
            subtotal(val_ini)

            # MOV. CAIXA - RETIRADA
            movs     = res["movimentacoes"]
            movs_ret = [m for m in movs if m["tipo"] in ("RETIRADA","SANGRIA","DESPESA")]
            movs_rec = [m for m in movs if m["tipo"] == "RECOLHIMENTO"]
            movs_sup = [m for m in movs if m["tipo"] == "SUPRIMENTO"]

            if movs_ret or movs_rec:
                secao("MOV. CAIXA - RETIRADA", "#DC2626")
                cab_tab()
                rows_ret = []
                total_ret = 0.0
                for m in movs_ret:
                    rows_ret.append([m["data_hora"][:16],
                        m.get("motivo","") or m["tipo"],
                        m.get("usuario","") or "—",
                        f"-R$ {m['valor']:.2f}"])
                    total_ret -= m["valor"]
                for m in movs_rec:
                    rows_ret.append([m["data_hora"][:16],
                        m.get("motivo","") or "RECOLHIMENTO",
                        m.get("usuario","") or "—",
                        f"-R$ {m['valor']:.2f}"])
                    total_ret -= m["valor"]
                linhas_tab(rows_ret)
                subtotal(total_ret)

            if movs_sup:
                secao("SUPRIMENTO", "#059669")
                cab_tab()
                rows_sup = []
                total_sup = 0.0
                for m in movs_sup:
                    rows_sup.append([m["data_hora"][:16],
                        m.get("motivo","") or "SUPRIMENTO",
                        m.get("usuario","") or "—",
                        f"+R$ {m['valor']:.2f}"])
                    total_sup += m["valor"]
                linhas_tab(rows_sup)
                subtotal(total_sup)

            # VENDAS
            secao("VENDAS", "#1D4ED8")
            cab_tab()
            rows_vend = []
            total_vend = 0.0
            for v in res["vendas"]:
                rows_vend.append(["", v["forma_pagamento"],
                                  f"{v['qtde']} vendas", f"R$ {v['total']:.2f}"])
                total_vend += v["total"]
            linhas_tab(rows_vend)
            subtotal(total_vend)

            # RESUMO
            secao("RESUMO", "#374151")
            FORMAS_ELETR_P = {"PIX","CREDITO","DEBITO","VALE ALIMENTACAO","OUTROS"}
            saidas_grupo = {}
            for m in movs_rec:
                motivo = (m.get("motivo","") or "").upper()
                g = motivo if motivo in FORMAS_ELETR_P else "DINHEIRO"
                saidas_grupo[g] = saidas_grupo.get(g, 0) + m["valor"]
            for m in movs_ret:
                saidas_grupo["DINHEIRO"] = saidas_grupo.get("DINHEIRO", 0) + m["valor"]

            res_rows = [["", "Entradas", "Saidas"]]
            total_ent = val_ini
            total_sai = 0.0
            res_rows.append(["INICIO", f"{val_ini:.2f}", "0,00"])
            for g, ent in res["grupos_venda"].items():
                sai = saidas_grupo.get(g, 0.0)
                res_rows.append([g, f"{ent:.2f}", f"{sai:.2f}"])
                total_ent += ent
                total_sai += sai
            res_rows.append(["Totais", f"{total_ent:.2f}", f"{total_sai:.2f}"])

            t_res = Table(res_rows, colWidths=[7*cm, 5*cm, 5*cm])
            n = len(res_rows)
            t_res.setStyle(TableStyle([
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
                ("FONTNAME",(0,1),(-1,-2),"Helvetica"),
                ("FONTSIZE",(0,0),(-1,-1),9),
                ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#E5E7EB")),
                ("BACKGROUND",(0,-1),(-1,-1), colors.HexColor("#E5E7EB")),
                ("ROWBACKGROUNDS",(0,1),(-1,-2),[colors.white, COR_CINZA]),
                ("ALIGN",(1,0),(-1,-1),"RIGHT"),
                ("TOPPADDING",(0,0),(-1,-1),4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),8),
                ("TEXTCOLOR",(1,1),(1,-2), COR_VERDE),
                ("TEXTCOLOR",(2,1),(2,-2), COR_VERM),
            ]))
            story.append(t_res)

            # DIFERENÇA FINAL
            story.append(Spacer(1, 0.3*cm))
            diff     = valor_final - self.saldo_esperado
            cor_diff = COR_VERDE if abs(diff) < 0.01 else COR_VERM
            status   = "CAIXA OK" if abs(diff) < 0.01 else \
                       ("SOBRA NO CAIXA" if diff > 0 else "FALTA NO CAIXA")

            t_diff = Table([
                ["Saldo a Transferir p/ proximo Caixa:", f"R$ {valor_final:.2f}"],
                ["Diferenca:", f"R$ {diff:.2f}"],
                [status, ""],
            ], colWidths=[12*cm, 5*cm])
            t_diff.setStyle(TableStyle([
                ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1),10),
                ("ALIGN",(1,0),(1,-1),"RIGHT"),
                ("TOPPADDING",(0,0),(-1,-1),5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1),8),
                ("TEXTCOLOR",(0,1),(-1,-1), cor_diff),
                ("LINEABOVE",(0,0),(-1,0), 1, colors.grey),
            ]))
            story.append(t_diff)

            # Assinatura
            story.append(Spacer(1, 1*cm))
            story.append(Table(
                [[f"Data: ____/____/______",
                  f"Caixa Responsavel: {self.usuario}"]],
                colWidths=[8*cm, 9*cm],
                style=TableStyle([
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                    ("FONTSIZE",(0,0),(-1,-1),9),
                    ("LINEBELOW",(0,0),(-1,-1), 0.5, colors.grey),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                ])))

            # Rodapé
            story.append(Spacer(1, 0.3*cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(T(
                f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}  —  {empresa}",
                8, align=TA_CENTER))

            doc.build(story)

            try:
                import subprocess
                subprocess.Popen(["start","",path], shell=True)
            except Exception:
                pass

        except Exception as e:
            messagebox.showwarning("PDF", f"Erro ao gerar PDF: {e}\nVerifique a pasta cupons\\")

    def _imprimir_relatorio(self, res, valor_final):
        pass
