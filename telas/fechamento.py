"""
telas/fechamento.py — Fechamento de Caixa completo
Modelo Eccus: relatório com movimentações, vendas por horário, resumo e conferência
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn, caixa_aberto, fechar_caixa, get_config
# sangria importado dinamicamente em _nova_movimentacao


def get_resumo_caixa(caixa_id):
    conn = get_conn()
    cx = conn.execute("SELECT * FROM caixa WHERE id=?", (caixa_id,)).fetchone()

    # Vendas agrupadas por forma
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

    # Movimentações — tenta sangria_suprimento primeiro, depois movimentacao_caixa
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
                SELECT * FROM movimentacao_caixa WHERE caixa_id=? ORDER BY data_hora
            """, (caixa_id,)).fetchall()
        except Exception:
            pass

    # Vendas detalhadas por forma
    vendas_detalhe = conn.execute("""
        SELECT id, data_hora, forma_pagamento, total, troco, desconto
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
        ORDER BY data_hora ASC
    """, (caixa_id,)).fetchall()

    conn.close()

    # Totais de movimentações
    sangria    = sum(m["valor"] for m in movs if m["tipo"] in ("SANGRIA","RETIRADA","DESPESA"))
    recolhimento = sum(m["valor"] for m in movs if m["tipo"] == "RECOLHIMENTO")
    suprimento = sum(m["valor"] for m in movs if m["tipo"] == "SUPRIMENTO")

    # Agrupa vendas por forma para conferência
    detalhe_por_forma = {}
    for v in vendas_detalhe:
        forma = v["forma_pagamento"]
        if forma not in detalhe_por_forma:
            detalhe_por_forma[forma] = []
        detalhe_por_forma[forma].append(dict(v))

    return {
        "caixa":            dict(cx) if cx else {},
        "vendas":           [dict(v) for v in vendas],
        "total_vendas":     total_geral[0],
        "qtde_vendas":      total_geral[1],
        "sangria":          sangria + recolhimento,
        "recolhimento":     recolhimento,
        "retiradas":        sangria,
        "suprimento":       suprimento,
        "produtos_top":     [dict(p) for p in produtos_top],
        "movimentacoes":    [dict(m) for m in movs],
        "vendas_detalhe":   [dict(v) for v in vendas_detalhe],
        "detalhe_por_forma": detalhe_por_forma,
        "aberto_em":        dict(cx)["data_abertura"] if cx else "",
    }


class TelaFechamentoCaixa(ctk.CTkFrame):
    def __init__(self, master, usuario="Sistema"):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.usuario = usuario
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        cx = caixa_aberto()
        self.caixa_id = cx["id"] if cx else None
        self.cx_dados = dict(cx) if cx else {}
        self._ent_conferencia = {}
        self._lbl_conf_diff   = {}
        self._build_header()
        if self.caixa_id:
            self._build_corpo()
        else:
            self._build_sem_caixa()

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
            # Botões de movimentação rápida
            bf = ctk.CTkFrame(hdr, fg_color="transparent")
            bf.grid(row=0, column=2, padx=24, sticky="e")
            for txt, cor, hover, tipo in [
                ("📤 Retirada",     COR_PERIGO,  COR_PERIGO2,  "RETIRADA"),
                ("📥 Suprimento",   COR_SUCESSO, COR_SUCESSO2, "SUPRIMENTO"),
                ("💰 Recolhimento", "#6B7280",   "#4B5563",    "RECOLHIMENTO"),
                ("🧾 Despesa",      "#B45309",   "#92400E",    "DESPESA"),
            ]:
                ctk.CTkButton(bf, text=txt, font=FONTE_BTN, height=36,
                             fg_color=cor, hover_color=hover, text_color="white",
                             command=lambda t=tipo: self._nova_movimentacao(t)
                             ).pack(side="left", padx=3)

    def _build_sem_caixa(self):
        f = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12)
        f.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        ctk.CTkLabel(f, text="⚠️  Nenhum caixa aberto!",
                     font=FONTE_TITULO, text_color=COR_PERIGO).pack(pady=60)

    def _build_corpo(self):
        res       = get_resumo_caixa(self.caixa_id)
        val_ini   = self.cx_dados.get("valor_inicial", 0)
        total_v   = res["total_vendas"]
        sangria   = res["sangria"]
        suprim    = res["suprimento"]
        saldo_esp = val_ini + total_v + suprim - sangria
        self.saldo_esperado = saldo_esp
        self._res_atual     = res

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # ── KPI Cards ────────────────────────────────────────────────────
        cards = ctk.CTkFrame(scroll, fg_color="transparent")
        cards.grid(row=row, column=0, sticky="ew", pady=(0,12)); row+=1
        for i in range(4): cards.grid_columnconfigure(i, weight=1)
        # Saldo esperado em caixa = só dinheiro físico (fundo + vendas dinheiro - retiradas + suprimentos)
        vd_kpi = get_conn()
        vd_val = vd_kpi.execute("""
            SELECT COALESCE(SUM(total),0) FROM vendas
            WHERE caixa_id=? AND status='CONCLUIDA' AND forma_pagamento LIKE '%DINHEIRO%'
        """, (self.caixa_id,)).fetchone()[0]
        vd_kpi.close()
        saidas_kpi   = res["retiradas"] + res["recolhimento"]
        entradas_kpi = res["suprimento"]
        saldo_caixa  = val_ini + vd_val + entradas_kpi - saidas_kpi
        self._card(cards, 0, "💰 Fundo Inicial",   f"R$ {val_ini:.2f}",    COR_TEXTO)
        self._card(cards, 1, "🛒 Total Vendas",    f"R$ {total_v:.2f}",    COR_SUCESSO)
        self._card(cards, 2, "📤 Sangrias/Retir",  f"R$ {sangria:.2f}",    COR_PERIGO)
        self._card(cards, 3, "💵 Saldo em Caixa",  f"R$ {saldo_caixa:.2f}",COR_ACENTO)

        # ── Movimentações de caixa ────────────────────────────────────────
        if res["movimentacoes"]:
            sec_mov = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=12,
                                   border_width=1, border_color=COR_BORDA)
            sec_mov.grid(row=row, column=0, sticky="ew", pady=(0,8)); row+=1
            sec_mov.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(sec_mov, text="📋  Movimentação de Caixa",
                         font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
                anchor="w", padx=16, pady=(12,4))

            TIPOS_COR = {"RETIRADA":COR_PERIGO,"DESPESA":COR_PERIGO,
                         "RECOLHIMENTO":"#6B7280","SUPRIMENTO":COR_SUCESSO,
                         "SANGRIA":COR_PERIGO}

            # saldo progressivo começa em fundo + vendas dinheiro
            conn2 = get_conn()
            vd_mov = conn2.execute("""
                SELECT COALESCE(SUM(total),0) FROM vendas
                WHERE caixa_id=? AND status='CONCLUIDA' AND forma_pagamento LIKE '%DINHEIRO%'
            """, (self.caixa_id,)).fetchone()[0]
            conn2.close()
            saldo_prog = val_ini + vd_mov

            # Linha de origem do saldo inicial
            origem_f = ctk.CTkFrame(sec_mov, fg_color=COR_LINHA_PAR, corner_radius=4, height=28)
            origem_f.pack(fill="x", padx=16, pady=(0,2))
            origem_f.pack_propagate(False)
            origem_i = ctk.CTkFrame(origem_f, fg_color="transparent")
            origem_i.pack(fill="x", padx=8, pady=4)
            hora_ab = self.cx_dados.get("data_abertura","")[11:16]
            ctk.CTkLabel(origem_i, text=hora_ab,
                         font=("Courier New",12), text_color=COR_TEXTO_SUB,
                         width=130, anchor="w").pack(side="left")
            ctk.CTkLabel(origem_i, text="INÍCIO",
                         font=("Courier New",12,"bold"), text_color=COR_SUCESSO,
                         width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(origem_i,
                         text=f"Fundo R$ {val_ini:.2f}  +  Vendas Dinheiro R$ {vd_mov:.2f}",
                         font=("Courier New",12), text_color=COR_TEXTO_SUB,
                         anchor="w").pack(side="left", padx=4, fill="x", expand=True)
            ctk.CTkLabel(origem_i, text=f"R$ {saldo_prog:.2f}",
                         font=("Courier New",12,"bold"), text_color=COR_SUCESSO,
                         width=110, anchor="e").pack(side="right")

            for m in res["movimentacoes"]:
                cor_t = TIPOS_COR.get(m["tipo"], COR_TEXTO)
                if m["tipo"] == "SUPRIMENTO":
                    sinal = "+"
                    saldo_prog += m["valor"]
                else:
                    sinal = "-"
                    saldo_prog -= m["valor"]
                cor_saldo = COR_SUCESSO if saldo_prog >= 0 else COR_PERIGO
                f = ctk.CTkFrame(sec_mov, fg_color="transparent")
                f.pack(fill="x", padx=16, pady=2)
                f.grid_columnconfigure(2, weight=1)
                ctk.CTkLabel(f, text=m["data_hora"][:16],
                             font=("Courier New",13), text_color=COR_TEXTO_SUB,
                             width=130, anchor="w").grid(row=0, column=0, sticky="w")
                ctk.CTkLabel(f, text=m["tipo"],
                             font=("Courier New",13,"bold"), text_color=cor_t,
                             width=120, anchor="w").grid(row=0, column=1, sticky="w")
                ctk.CTkLabel(f, text=m.get("motivo","") or "—",
                             font=("Courier New",13), text_color=COR_TEXTO_SUB,
                             width=180, anchor="w").grid(row=0, column=2, sticky="w")
                ctk.CTkLabel(f, text=f"{sinal}R$ {m['valor']:.2f}",
                             font=("Courier New",13,"bold"), text_color=cor_t,
                             width=100, anchor="e").grid(row=0, column=3, sticky="e", padx=(4,0))
                ctk.CTkLabel(f, text=f"R$ {saldo_prog:.2f}",
                             font=("Courier New",13,"bold"), text_color=cor_saldo,
                             width=110, anchor="e").grid(row=0, column=4, sticky="e", padx=(4,0))

            # Subtotal movimentações
            ctk.CTkFrame(sec_mov, height=1, fg_color=COR_BORDA).pack(
                fill="x", padx=16, pady=4)
            fsub = ctk.CTkFrame(sec_mov, fg_color="transparent")
            fsub.pack(fill="x", padx=16, pady=(0,12))
            ctk.CTkLabel(fsub, text="Sub-Total Movimentações:",
                         font=("Courier New",13,"bold"),
                         text_color=COR_TEXTO_SUB).pack(side="left")
            saldo_mov = suprim - sangria
            cor_mov = COR_SUCESSO if saldo_mov >= 0 else COR_PERIGO
            sinal_mov = "+" if saldo_mov >= 0 else ""
            ctk.CTkLabel(fsub, text=f"{sinal_mov}R$ {saldo_mov:.2f}",
                         font=("Courier New",13,"bold"),
                         text_color=cor_mov).pack(side="right")

        # ── Vendas por forma de pagamento ─────────────────────────────────
        sec_vend = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=12,
                                border_width=1, border_color=COR_BORDA)
        sec_vend.grid(row=row, column=0, sticky="ew", pady=(0,8)); row+=1
        sec_vend.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sec_vend, text="💳  Vendas por Forma de Pagamento",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
            anchor="w", padx=16, pady=(12,4))
        self._build_tabela_vendas(sec_vend, res, total_v)

        # ── Produtos mais vendidos ────────────────────────────────────────
        if res["produtos_top"]:
            sec_prod = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=12,
                                    border_width=1, border_color=COR_BORDA)
            sec_prod.grid(row=row, column=0, sticky="ew", pady=(0,8)); row+=1
            sec_prod.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(sec_prod, text="🏆  Produtos Mais Vendidos",
                         font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
                anchor="w", padx=16, pady=(12,4))
            self._build_produtos_top(sec_prod, res)

        # ── Conferência por grupo ─────────────────────────────────────────
        sec_conf = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=12,
                                border_width=1, border_color=COR_BORDA)
        sec_conf.grid(row=row, column=0, sticky="ew", pady=(0,8)); row+=1
        sec_conf.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sec_conf, text="🔍  Conferência — Valor em Caixa",
                     font=FONTE_SUBTITULO, text_color=COR_ACENTO).pack(
            anchor="w", padx=16, pady=(12,4))
        f_conf = ctk.CTkFrame(sec_conf, fg_color="transparent")
        f_conf.pack(fill="x", padx=16, pady=(0,16))
        f_conf.grid_columnconfigure(0, weight=1)
        self._build_conferencia(f_conf, saldo_esp)

        # ── Botões de ação ────────────────────────────────────────────────
        f_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        f_btn.grid(row=row, column=0, sticky="ew", pady=(4,0)); row+=1
        f_btn.grid_columnconfigure((0,1), weight=1)

        ctk.CTkButton(f_btn, text="🖨️  Imprimir Relatório",
                      font=FONTE_BTN, height=44,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white",
                      command=lambda: self._gerar_pdf(res, self.saldo_esperado)
                      ).grid(row=0, column=0, padx=(0,4), sticky="ew")

        ctk.CTkButton(f_btn, text="🔒  FECHAR CAIXA",
                      font=("Georgia",16,"bold"), height=44,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                      text_color="white",
                      command=lambda: self._fechar(res)
                      ).grid(row=0, column=1, padx=(4,0), sticky="ew")

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=4, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(12,2))
        ctk.CTkLabel(card, text=valor,
                     font=("Georgia",20,"bold"), text_color=cor).pack(pady=(0,12))

    def _build_tabela_vendas(self, parent, res, total_v):
        COLS = ["Forma de Pagamento","Qtde","Total","Troco"]
        WIDS = [280, 60, 120, 100]
        cab = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.pack(fill="x", padx=16, pady=(0,2))
        cab.pack_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=4)
        for c, w in zip(COLS, WIDS):
            ctk.CTkLabel(hdr, text=c, font=("Courier New",13,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)
        if res["vendas"]:
            for idx, v in enumerate(res["vendas"]):
                cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
                row_f = ctk.CTkFrame(parent, fg_color=cor_bg, corner_radius=4, height=34)
                row_f.pack(fill="x", padx=16, pady=1)
                row_f.pack_propagate(False)
                row_i = ctk.CTkFrame(row_f, fg_color="transparent")
                row_i.pack(fill="x", padx=8, pady=4)
                vals  = [v["forma_pagamento"], str(v["qtde"]),
                         f"R$ {v['total']:.2f}", f"R$ {v['troco']:.2f}"]
                cores = [COR_TEXTO, COR_TEXTO_SUB, COR_SUCESSO, COR_TEXTO_SUB]
                for val, cor, w in zip(vals, cores, WIDS):
                    ctk.CTkLabel(row_i, text=val, font=FONTE_SMALL,
                                 text_color=cor, width=w, anchor="w").pack(side="left", padx=2)
        else:
            ctk.CTkLabel(parent, text="Nenhuma venda neste caixa.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=20)
        # Total geral
        tot_f = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=6, height=36)
        tot_f.pack(fill="x", padx=16, pady=(4,12))
        tot_f.pack_propagate(False)
        fi = ctk.CTkFrame(tot_f, fg_color="transparent")
        fi.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(fi, text="TOTAL GERAL",
                     font=("Courier New",14,"bold"), text_color=COR_ACENTO).pack(side="left")
        ctk.CTkLabel(fi, text=f"{res['qtde_vendas']} vendas  —  R$ {total_v:.2f}",
                     font=("Courier New",14,"bold"), text_color=COR_ACENTO).pack(side="right")

    def _build_produtos_top(self, parent, res):
        COLS = ["Produto","Qtde","Total"]
        WIDS = [300, 80, 120]
        cab = ctk.CTkFrame(parent, fg_color=COR_ACENTO_LIGHT, corner_radius=8, height=36)
        cab.pack(fill="x", padx=16, pady=(0,2))
        cab.pack_propagate(False)
        hdr = ctk.CTkFrame(cab, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=4)
        for c, w in zip(COLS, WIDS):
            ctk.CTkLabel(hdr, text=c, font=("Courier New",13,"bold"),
                         text_color=COR_ACENTO, width=w, anchor="w").pack(side="left", padx=2)
        if res["produtos_top"]:
            for idx, p in enumerate(res["produtos_top"]):
                cor_bg = COR_LINHA_PAR if idx%2==0 else COR_CARD
                row_f = ctk.CTkFrame(parent, fg_color=cor_bg, corner_radius=4, height=32)
                row_f.pack(fill="x", padx=16, pady=1)
                row_f.pack_propagate(False)
                row_i = ctk.CTkFrame(row_f, fg_color="transparent")
                row_i.pack(fill="x", padx=8, pady=4)
                vals  = [p["nome_produto"][:35],
                         f'{p["qtde"]:.1f}'.rstrip("0").rstrip("."),
                         f'R$ {p["total"]:.2f}']
                cores = [COR_TEXTO, COR_TEXTO_SUB, COR_SUCESSO]
                for val, cor, w in zip(vals, cores, WIDS):
                    ctk.CTkLabel(row_i, text=val, font=FONTE_SMALL,
                                 text_color=cor, width=w, anchor="w").pack(side="left", padx=2)
        else:
            ctk.CTkLabel(parent, text="Nenhum item vendido.",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).pack(pady=12)

    def _build_conferencia(self, parent, saldo_esp):
        """Conferência por grupo: Dinheiro, Cartões, PIX com vendas por horário"""
        parent.grid_columnconfigure(0, weight=1)
        res    = self._res_atual if hasattr(self,"_res_atual") else {}
        val_ini = self.cx_dados.get("valor_inicial", 0)

        # Agrupa vendas por grupo
        grupos = {
            "DINHEIRO": {"label":"💵  Dinheiro", "cor":COR_SUCESSO,  "vendas":[], "total":0.0},
            "CARTAO":   {"label":"💳  Cartões",  "cor":"#1D4ED8",    "vendas":[], "total":0.0},
            "PIX":      {"label":"📱  PIX",       "cor":"#0891B2",    "vendas":[], "total":0.0},
        }
        for v in res.get("vendas_detalhe", []):
            forma = v["forma_pagamento"].upper()
            if "DINHEIRO" in forma:
                grupos["DINHEIRO"]["vendas"].append(v)
                grupos["DINHEIRO"]["total"] += v["total"]
            elif "PIX" in forma:
                grupos["PIX"]["vendas"].append(v)
                grupos["PIX"]["total"] += v["total"]
            else:
                grupos["CARTAO"]["vendas"].append(v)
                grupos["CARTAO"]["total"] += v["total"]

        # Retiradas/sangrias/despesas/recolhimento saem do dinheiro fisico
        saidas_dinheiro = sum(
            m["valor"] for m in res.get("movimentacoes", [])
            if m["tipo"] in ("RETIRADA", "SANGRIA", "DESPESA", "RECOLHIMENTO")
        )
        entradas_dinheiro = sum(
            m["valor"] for m in res.get("movimentacoes", [])
            if m["tipo"] == "SUPRIMENTO"
        )
        grupos["DINHEIRO"]["total_esperado"] = (
            grupos["DINHEIRO"]["total"] + val_ini + entradas_dinheiro - saidas_dinheiro
        )
        grupos["CARTAO"]["total_esperado"]   = grupos["CARTAO"]["total"]
        grupos["PIX"]["total_esperado"]      = grupos["PIX"]["total"]

        self._ent_conferencia = {}
        self._lbl_conf_diff   = {}

        row = 0
        for key, grupo in grupos.items():
            esperado  = grupo["total_esperado"]
            cor_grupo = grupo["cor"]

            # Cabeçalho do grupo
            cab = ctk.CTkFrame(parent, fg_color=cor_grupo, corner_radius=8, height=38)
            cab.grid(row=row, column=0, sticky="ew", pady=(8,0))
            cab.grid_propagate(False)
            cab.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(cab, text=grupo["label"],
                         font=("Georgia",14,"bold"), text_color="white").grid(
                row=0, column=0, padx=12, pady=8, sticky="w")
            ctk.CTkLabel(cab, text=f"Sistema: R$ {esperado:.2f}",
                         font=("Georgia",14,"bold"), text_color="white").grid(
                row=0, column=1, padx=12, pady=8, sticky="e")
            row += 1

            # Linhas detalhadas: fundo + movimentações + vendas (só para Dinheiro)
            f_vendas = ctk.CTkFrame(parent, fg_color=COR_CARD2, corner_radius=0)
            f_vendas.grid(row=row, column=0, sticky="ew")
            linha_idx = 0

            def _linha(parent_f, idx, hora, descricao, valor, cor_val, cor_bg_par):
                cor_bg = cor_bg_par if idx%2==0 else COR_CARD
                lv = ctk.CTkFrame(parent_f, fg_color=cor_bg, corner_radius=0, height=28)
                lv.pack(fill="x")
                lv.pack_propagate(False)
                li = ctk.CTkFrame(lv, fg_color="transparent")
                li.pack(fill="x", padx=8, pady=4)
                ctk.CTkLabel(li, text=f"🕐 {hora}",
                             font=("Courier New",12), text_color=COR_TEXTO_SUB,
                             width=60, anchor="w").pack(side="left")
                ctk.CTkLabel(li, text=descricao,
                             font=("Courier New",12), text_color=COR_TEXTO_SUB,
                             anchor="w").pack(side="left", padx=8, fill="x", expand=True)
                ctk.CTkLabel(li, text=valor,
                             font=("Courier New",12,"bold"), text_color=cor_val).pack(side="right")

            if key == "DINHEIRO":
                # Linha de abertura
                ab_hora = self.cx_dados.get("data_abertura","")[11:16]
                _linha(f_vendas, linha_idx, ab_hora,
                       "Abertura (Fundo Inicial)",
                       f"+R$ {val_ini:.2f}", COR_SUCESSO, COR_LINHA_PAR)
                linha_idx += 1

            # Vendas do grupo
            for v in grupo["vendas"]:
                hora = v["data_hora"][11:16] if len(v["data_hora"]) > 10 else ""
                forma_curta = v["forma_pagamento"].replace("CARTAO - ","").replace("CARTAO","CARTÃO")
                _linha(f_vendas, linha_idx, hora,
                       f"Venda — {forma_curta[:25]}",
                       f"+R$ {v['total']:.2f}", cor_grupo, COR_LINHA_PAR)
                linha_idx += 1

            # Movimentações (só afetam o Dinheiro)
            if key == "DINHEIRO":
                TIPOS_COR_MOV = {
                    "RETIRADA": COR_PERIGO, "SANGRIA": COR_PERIGO,
                    "DESPESA": COR_PERIGO, "RECOLHIMENTO": "#6B7280",
                    "SUPRIMENTO": COR_SUCESSO,
                }
                for m in res.get("movimentacoes", []):
                    hora_m = m["data_hora"][11:16] if len(m["data_hora"]) > 10 else ""
                    motivo = m.get("motivo","") or ""
                    desc   = f"{m['tipo']}" + (f" — {motivo}" if motivo else "")
                    sinal  = "+" if m["tipo"] == "SUPRIMENTO" else "-"
                    cor_m  = TIPOS_COR_MOV.get(m["tipo"], COR_TEXTO)
                    _linha(f_vendas, linha_idx, hora_m, desc,
                           f"{sinal}R$ {m['valor']:.2f}", cor_m, COR_LINHA_PAR)
                    linha_idx += 1

            if linha_idx == 0:
                ctk.CTkLabel(f_vendas, text="  Nenhum movimento nesta forma.",
                             font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack(pady=6)
            row += 1

            # Campo para digitar valor contado
            f_conf = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=0,
                                  border_width=1, border_color=COR_BORDA)
            f_conf.grid(row=row, column=0, sticky="ew", pady=(0,4))
            f_conf.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(f_conf, text="Valor conferido (R$):",
                         font=FONTE_LABEL, text_color=COR_TEXTO_SUB).grid(
                row=0, column=0, padx=12, pady=8, sticky="w")
            ent = ctk.CTkEntry(f_conf, font=("Georgia",18), width=140,
                               justify="center", placeholder_text="0,00",
                               fg_color=COR_CARD2, border_color=cor_grupo,
                               border_width=2, text_color=COR_TEXTO)
            ent.grid(row=0, column=1, padx=8, pady=8, sticky="e")
            lbl_diff = ctk.CTkLabel(f_conf, text="",
                                    font=("Georgia",13,"bold"), text_color=COR_TEXTO_SUB)
            lbl_diff.grid(row=1, column=0, columnspan=2, padx=12, pady=(0,8), sticky="e")
            self._ent_conferencia[key] = (ent, esperado)
            self._lbl_conf_diff[key]   = lbl_diff
            ent.bind("<KeyRelease>", self._calcular_diferenca)
            row += 1

        # Diferença total
        ctk.CTkFrame(parent, height=2, fg_color=COR_BORDA).grid(
            row=row, column=0, sticky="ew", pady=8); row+=1

        self.frame_diferenca = ctk.CTkFrame(parent, fg_color=COR_CARD2,
                                            corner_radius=8, border_width=2,
                                            border_color=COR_BORDA)
        self.frame_diferenca.grid(row=row, column=0, sticky="ew", pady=4); row+=1
        fd = ctk.CTkFrame(self.frame_diferenca, fg_color="transparent")
        fd.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(fd, text="💰  Diferença total do caixa:",
                     font=("Georgia",15,"bold"), text_color=COR_TEXTO_SUB).pack(side="left")
        self.lbl_diferenca = ctk.CTkLabel(fd, text="—",
                                          font=("Georgia",22,"bold"), text_color=COR_TEXTO_SUB)
        self.lbl_diferenca.pack(side="right")

        self.lbl_status = ctk.CTkLabel(parent,
                                       text="Preencha os campos para conferir",
                                       font=FONTE_LABEL, text_color=COR_TEXTO_SUB)
        self.lbl_status.grid(row=row, column=0, pady=4)

    def _calcular_diferenca(self, event=None):
        try:
            total_contado    = 0.0
            algum_preenchido = False
            for key, (ent, esperado) in self._ent_conferencia.items():
                val_txt = ent.get().strip().replace(",",".")
                if val_txt:
                    algum_preenchido = True
                    contado = float(val_txt)
                    total_contado += contado
                    diff_forma = contado - esperado
                    cor   = COR_SUCESSO if abs(diff_forma) < 0.01 else COR_PERIGO
                    sinal = "+" if diff_forma >= 0 else ""
                    self._lbl_conf_diff[key].configure(
                        text=f"Diferença: {sinal}R$ {diff_forma:.2f}", text_color=cor)
                else:
                    self._lbl_conf_diff[key].configure(text="")
            if not algum_preenchido:
                self.lbl_diferenca.configure(text="—", text_color=COR_TEXTO_SUB)
                self.lbl_status.configure(text="Preencha os campos para conferir",
                                          text_color=COR_TEXTO_SUB)
                return
            diff  = total_contado - self.saldo_esperado
            cor   = COR_SUCESSO if abs(diff) < 0.01 else COR_PERIGO
            sinal = "+" if diff >= 0 else ""
            self.lbl_diferenca.configure(text=f"{sinal}R$ {diff:.2f}", text_color=cor)
            self.frame_diferenca.configure(border_color=cor)
            if abs(diff) < 0.01:
                self.lbl_status.configure(text="✅  Caixa conferido! Valores batem.",
                                          text_color=COR_SUCESSO)
            elif diff > 0:
                self.lbl_status.configure(text=f"⚠️  Sobrou R$ {abs(diff):.2f} no caixa.",
                                          text_color=COR_AVISO)
            else:
                self.lbl_status.configure(text=f"❌  Faltam R$ {abs(diff):.2f} no caixa!",
                                          text_color=COR_PERIGO)
        except Exception:
            pass

    def _fechar(self, res):
        valor_final = 0.0
        algum_preenchido = False
        if hasattr(self,"_ent_conferencia") and self._ent_conferencia:
            for key, (ent, esperado) in self._ent_conferencia.items():
                val_txt = ent.get().strip().replace(",",".")
                if val_txt:
                    try:
                        valor_final += float(val_txt)
                        algum_preenchido = True
                    except ValueError:
                        pass
        if not algum_preenchido:
            valor_final = self.saldo_esperado

        diff  = valor_final - self.saldo_esperado
        sinal = "+" if diff >= 0 else ""
        msg_diff = "✅ Caixa OK!" if abs(diff) < 0.01 else f"⚠️ Diferença: {sinal}R$ {diff:.2f}"

        if not messagebox.askyesno("Fechar Caixa",
            f"Confirma o fechamento?\n\n"
            f"Total vendas:   R$ {res['total_vendas']:.2f}\n"
            f"Saldo esperado: R$ {self.saldo_esperado:.2f}\n"
            f"Valor contado:  R$ {valor_final:.2f}\n"
            f"{msg_diff}\n\n"
            f"Esta ação não pode ser desfeita!"):
            return

        fechar_caixa(self.caixa_id, valor_final)
        self._gerar_pdf(res, valor_final, fechando=True)
        messagebox.showinfo("✅ Caixa Fechado",
                            "Caixa fechado com sucesso!\nRelatório salvo em cupons\\")
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

    def _gerar_pdf(self, res, valor_final, fechando=False):
        """Gera PDF do fechamento no modelo Eccus"""
        import os, sys
        try:
            base = os.path.dirname(sys.executable) if getattr(sys,"frozen",False) \
                   else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            path  = os.path.join(pasta, f"fechamento_caixa_{agora}.pdf")

            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

            doc    = SimpleDocTemplate(path, pagesize=A4,
                                       topMargin=1.5*cm, bottomMargin=1.5*cm,
                                       leftMargin=2*cm, rightMargin=2*cm)
            styles = getSampleStyleSheet()
            story  = []

            COR_PDF    = colors.HexColor("#B45309")
            COR_CINZA  = colors.HexColor("#F3F4F6")
            COR_VERDE  = colors.HexColor("#059669")
            COR_VERM   = colors.HexColor("#DC2626")

            empresa  = get_config("empresa_nome") or "Padaria"
            endereco = get_config("empresa_endereco") or ""
            cnpj     = get_config("empresa_cnpj") or ""
            fone     = get_config("empresa_fone") or ""
            val_ini  = self.cx_dados.get("valor_inicial",0)

            T = lambda txt, size=10, bold=False, cor=colors.black, align=TA_LEFT: \
                Paragraph(txt, ParagraphStyle("x", fontSize=size,
                          fontName="Helvetica-Bold" if bold else "Helvetica",
                          textColor=cor, alignment=align, spaceAfter=2))

            # Cabeçalho
            story.append(T(empresa.upper(), 14, True, COR_PDF, TA_CENTER))
            if endereco: story.append(T(endereco, 9, align=TA_CENTER))
            if cnpj:     story.append(T(f"CNPJ: {cnpj}    Fone: {fone}", 9, align=TA_CENTER))
            story.append(Spacer(1,0.2*cm))
            story.append(T("PRÉ FECHAMENTO DE CAIXA", 12, True, align=TA_CENTER))
            ab = self.cx_dados.get("data_abertura","")[:16]
            story.append(T(f"Caixa #{self.caixa_id}    Aberto: {ab}    Operador: {self.usuario}", 9, align=TA_CENTER))
            story.append(HRFlowable(width="100%", thickness=2, color=COR_PDF))
            story.append(Spacer(1,0.3*cm))

            # Início do caixa
            story.append(T("INÍCIO DO CAIXA", 10, True))
            story.append(T(f"{ab}    Fundo Inicial: R$ {val_ini:.2f}", 9))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(Spacer(1,0.2*cm))

            # Movimentações
            movs = res.get("movimentacoes",[])
            if movs:
                story.append(T("MOV. CAIXA", 10, True))
                # cabeçalho
                cab_mov = [["Tipo","Data/Hora","Motivo","Usuário","Valor","Saldo"]]
                dados_mov = []
                saldo_prog_pdf = val_ini + sum(
                    v["total"] for v in res.get("vendas_detalhe",[])
                    if "DINHEIRO" in v["forma_pagamento"].upper()
                )
                for m in movs:
                    sinal = "+" if m["tipo"]=="SUPRIMENTO" else "-"
                    if m["tipo"] == "SUPRIMENTO":
                        saldo_prog_pdf += m["valor"]
                    else:
                        saldo_prog_pdf -= m["valor"]
                    dados_mov.append([
                        m["tipo"], m["data_hora"][:16],
                        m.get("motivo","") or "—",
                        m.get("usuario","") or "—",
                        f"{sinal}R$ {m['valor']:.2f}",
                        f"R$ {saldo_prog_pdf:.2f}"
                    ])
                t_mov = Table(cab_mov + dados_mov,
                              colWidths=[2.8*cm,3.2*cm,4*cm,2*cm,2.2*cm,2.3*cm])
                n = len(dados_mov)
                t_mov.setStyle(TableStyle([
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("FONTSIZE",(0,0),(-1,-1),8),
                    ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E5E7EB")),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,COR_CINZA]),
                    ("ALIGN",(4,0),(-1,-1),"RIGHT"),
                    ("TOPPADDING",(0,0),(-1,-1),3),
                    ("BOTTOMPADDING",(0,0),(-1,-1),3),
                    ("LEFTPADDING",(0,0),(-1,-1),4),
                ]))
                # colorir coluna saldo: verde/vermelho
                for i, m in enumerate(movs):
                    saldo_val = float(dados_mov[i][5].replace("R$ ",""))
                    cor_s = COR_VERDE if saldo_val >= 0 else COR_VERM
                    t_mov.setStyle(TableStyle([
                        ("TEXTCOLOR",(5,i+1),(5,i+1), cor_s),
                        ("FONTNAME",(5,i+1),(5,i+1),"Helvetica-Bold"),
                    ]))
                story.append(t_mov)
                story.append(Spacer(1,0.2*cm))

            # Vendas por forma com horário
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(T("VENDAS", 10, True))

            grupos_pdf = {
                "DINHEIRO": {"label":"DINHEIRO","vendas":[],"total":0},
                "PIX":      {"label":"PIX","vendas":[],"total":0},
                "CARTAO":   {"label":"CARTÕES","vendas":[],"total":0},
            }
            for v in res.get("vendas_detalhe",[]):
                forma = v["forma_pagamento"].upper()
                if "DINHEIRO" in forma:
                    grupos_pdf["DINHEIRO"]["vendas"].append(v)
                    grupos_pdf["DINHEIRO"]["total"] += v["total"]
                elif "PIX" in forma:
                    grupos_pdf["PIX"]["vendas"].append(v)
                    grupos_pdf["PIX"]["total"] += v["total"]
                else:
                    grupos_pdf["CARTAO"]["vendas"].append(v)
                    grupos_pdf["CARTAO"]["total"] += v["total"]

            for key, g in grupos_pdf.items():
                story.append(T(g["label"], 9, True))
                dados_v = []

                # Dinheiro: começa com fundo inicial
                if key == "DINHEIRO":
                    ab_hora = self.cx_dados.get("data_abertura","")[11:16]
                    dados_v.append([ab_hora, "Abertura (Fundo Inicial)", f"+R$ {val_ini:.2f}"])

                # Vendas do grupo
                for v in g["vendas"]:
                    hora  = v["data_hora"][11:16] if len(v["data_hora"])>10 else ""
                    forma = v["forma_pagamento"].replace("CARTAO - ","")
                    dados_v.append([hora, f"Venda — {forma[:22]}", f"+R$ {v['total']:.2f}"])

                # Movimentações (somente no grupo Dinheiro)
                if key == "DINHEIRO":
                    for m in res.get("movimentacoes",[]):
                        hora_m = m["data_hora"][11:16] if len(m["data_hora"])>10 else ""
                        motivo = m.get("motivo","") or ""
                        desc   = m["tipo"] + (f" — {motivo}" if motivo else "")
                        sinal  = "+" if m["tipo"] == "SUPRIMENTO" else "-"
                        dados_v.append([hora_m, desc, f"{sinal}R$ {m['valor']:.2f}"])

                if not dados_v:
                    story.append(T("  Nenhum movimento.", 8, cor=colors.grey))
                    story.append(Spacer(1,0.1*cm))
                    continue

                t_v = Table(dados_v, colWidths=[1.8*cm,11*cm,4.2*cm])
                # colorir coluna valor: verde para +, vermelho para -
                style_v = [
                    ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                    ("FONTSIZE",(0,0),(-1,-1),8),
                    ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,COR_CINZA]),
                    ("ALIGN",(2,0),(-1,-1),"RIGHT"),
                    ("TOPPADDING",(0,0),(-1,-1),2),
                    ("BOTTOMPADDING",(0,0),(-1,-1),2),
                ]
                for i, row_d in enumerate(dados_v):
                    cor_v = COR_VERDE if row_d[2].startswith("+") else COR_VERM
                    style_v.append(("TEXTCOLOR",(2,i),(2,i), cor_v))
                    style_v.append(("FONTNAME",(2,i),(2,i), "Helvetica-Bold"))
                t_v.setStyle(TableStyle(style_v))
                story.append(t_v)

                # Sub-total do grupo
                if key == "DINHEIRO":
                    saidas = sum(m["valor"] for m in res.get("movimentacoes",[])
                                 if m["tipo"] in ("RETIRADA","SANGRIA","DESPESA","RECOLHIMENTO"))
                    entradas = sum(m["valor"] for m in res.get("movimentacoes",[])
                                   if m["tipo"] == "SUPRIMENTO")
                    total_din = val_ini + g["total"] + entradas - saidas
                    story.append(T(f"Sub-Total DINHEIRO (esperado em caixa): R$ {total_din:.2f}", 9, True))
                else:
                    story.append(T(f"Sub-Total {g['label']}: R$ {g['total']:.2f}", 9, True))
                story.append(Spacer(1,0.15*cm))

            # Resumo final
            story.append(HRFlowable(width="100%", thickness=1, color=COR_PDF))
            story.append(T("RESUMO FINAL", 11, True, COR_PDF))
            total_v = res["total_vendas"]
            sangria = res["sangria"]
            saldo_esp = val_ini + total_v + res["suprimento"] - sangria
            diff = valor_final - saldo_esp

            dados_res = [
                ["Fundo Inicial:",    f"R$ {val_ini:.2f}"],
                ["Total Vendas:",     f"R$ {total_v:.2f}"],
                ["Total Retiradas:",  f"-R$ {sangria:.2f}"],
                ["Suprimentos:",      f"+R$ {res['suprimento']:.2f}"],
                ["Saldo Esperado:",   f"R$ {saldo_esp:.2f}"],
                ["Valor Contado:",    f"R$ {valor_final:.2f}"],
                ["Diferença:",        f"{'+'if diff>=0 else ''}R$ {diff:.2f}"],
            ]
            t_res = Table(dados_res, colWidths=[8*cm,9*cm])
            t_res.setStyle(TableStyle([
                ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
                ("FONTNAME",(1,0),(-1,-1),"Helvetica"),
                ("FONTSIZE",(0,0),(-1,-1),10),
                ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,COR_CINZA]),
                ("TOPPADDING",(0,0),(-1,-1),5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1),8),
                ("TEXTCOLOR",(0,-1),(-1,-1),COR_VERDE if abs(diff)<0.01 else COR_VERM),
                ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
            ]))
            story.append(t_res)

            status = "✅ CAIXA OK" if abs(diff)<0.01 else (f"⚠️ SOBROU R$ {abs(diff):.2f}" if diff>0 else f"❌ FALTA R$ {abs(diff):.2f}")
            story.append(Spacer(1,0.3*cm))
            story.append(T(status, 13, True,
                           COR_VERDE if abs(diff)<0.01 else COR_VERM, TA_CENTER))

            # Rodapé
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(T(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}  —  {empresa}", 8, align=TA_CENTER))

            doc.build(story)

            # Abre o PDF
            try:
                import subprocess
                subprocess.Popen(["start","",path], shell=True)
            except Exception:
                pass

        except Exception as e:
            messagebox.showwarning("PDF", f"Erro ao gerar PDF: {e}\nVerifique a pasta cupons\\")

    def _imprimir_relatorio(self, res, valor_final):
        pass

    def _nova_movimentacao(self, tipo):
        """Abre dialogo de movimentacao direto do fechamento e recarrega a tela"""
        import importlib.util, os, sys
        try:
            # Tenta achar sangria.py na mesma pasta do fechamento.py
            base = os.path.dirname(os.path.abspath(__file__))
            caminho = os.path.join(base, "sangria.py")
            spec = importlib.util.spec_from_file_location("sangria", caminho)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            DialogoMovimentacao = mod.DialogoMovimentacao
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro", f"Nao foi possivel abrir movimentacao:\n{e}")
            return
        def _recarregar():
            # destrói o corpo atual e reconstrói
            for w in self.winfo_children():
                if str(w) != str(self.winfo_children()[0]):  # mantém header
                    try: w.destroy()
                    except Exception: pass
            # reconstrói tudo
            for w in self.winfo_children():
                try: w.destroy()
                except Exception: pass
            self._ent_conferencia = {}
            self._lbl_conf_diff   = {}
            self._build_header()
            if self.caixa_id:
                self._build_corpo()
        DialogoMovimentacao(self, tipo, self.caixa_id, self.usuario, _recarregar)
