"""
telas/fechamento.py — Fechamento de Caixa com Relatório
"""
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
from tema import *
from banco.database import get_conn, caixa_aberto, fechar_caixa

def get_resumo_caixa(caixa_id):
    """Retorna resumo completo do caixa para fechamento"""
    conn = get_conn()

    # Dados do caixa
    cx = conn.execute(
        "SELECT * FROM caixa WHERE id=?", (caixa_id,)).fetchone()

    # Total de vendas por forma de pagamento
    vendas = conn.execute("""
        SELECT forma_pagamento, COUNT(*) as qtde,
               SUM(total) as total, SUM(troco) as troco
        FROM vendas
        WHERE caixa_id=? AND status='CONCLUIDA'
        GROUP BY forma_pagamento
    """, (caixa_id,)).fetchall()

    # Total geral de vendas
    total_vendas = conn.execute("""
        SELECT COALESCE(SUM(total),0), COUNT(*)
        FROM vendas WHERE caixa_id=? AND status='CONCLUIDA'
    """, (caixa_id,)).fetchone()

    # Sangrias e suprimentos
    try:
        sangria = conn.execute("""
            SELECT COALESCE(SUM(valor),0) FROM sangria_suprimento
            WHERE caixa_id=? AND tipo='SANGRIA'
        """, (caixa_id,)).fetchone()[0]
        suprimento = conn.execute("""
            SELECT COALESCE(SUM(valor),0) FROM sangria_suprimento
            WHERE caixa_id=? AND tipo='SUPRIMENTO'
        """, (caixa_id,)).fetchone()[0]
    except Exception:
        sangria = 0; suprimento = 0

    conn.close()
    return {
        "caixa":       dict(cx) if cx else {},
        "vendas":      [dict(v) for v in vendas],
        "total_vendas":total_vendas[0],
        "qtde_vendas": total_vendas[1],
        "sangria":     sangria,
        "suprimento":  suprimento,
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

        self._build_header()
        if self.caixa_id:
            self._build_resumo()
        else:
            self._build_sem_caixa()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="🔒  Fechamento de Caixa",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        if self.caixa_id:
            abertura = self.cx_dados.get("data_abertura","")[:16]
            ctk.CTkLabel(hdr,
                         text=f"Caixa #{self.caixa_id} — Aberto em {abertura}",
                         font=FONTE_LABEL,
                         text_color=COR_TEXTO_SUB).grid(
                row=0, column=1, padx=24, sticky="e")

    def _build_sem_caixa(self):
        f = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12)
        f.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        ctk.CTkLabel(f, text="⚠️  Nenhum caixa aberto!",
                     font=FONTE_TITULO, text_color=COR_PERIGO).pack(pady=60)

    def _build_resumo(self):
        res = get_resumo_caixa(self.caixa_id)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # ── Cards de resumo ───────────────────────────────────────────────────
        cards = ctk.CTkFrame(scroll, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(0,12))
        cards.grid_columnconfigure((0,1,2,3), weight=1)

        val_ini = self.cx_dados.get("valor_inicial", 0)
        total_v = res["total_vendas"]
        sangria = res["sangria"]
        suprim  = res["suprimento"]
        saldo_esp = val_ini + total_v + suprim - sangria

        self._card(cards, 0, "💰 Valor Inicial",    f"R$ {val_ini:.2f}", COR_TEXTO)
        self._card(cards, 1, "🛒 Total Vendas",      f"R$ {total_v:.2f}", COR_SUCESSO)
        self._card(cards, 2, "📤 Sangrias",          f"R$ {sangria:.2f}", COR_PERIGO)
        self._card(cards, 3, "💵 Saldo Esperado",    f"R$ {saldo_esp:.2f}", COR_ACENTO)

        # ── Vendas por forma de pagamento ─────────────────────────────────────
        sec1 = self._secao(scroll, 1, "📊  Vendas por Forma de Pagamento")
        sec1.grid_columnconfigure((0,1,2,3), weight=1)

        cols  = ["Forma de Pagamento", "Qtde Vendas", "Total", "Troco"]
        pesos = [4, 2, 2, 2]
        cab = ctk.CTkFrame(sec1, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=34)
        cab.grid(row=0, column=0, columnspan=4, sticky="ew",
                 padx=0, pady=(0,4))
        cab.grid_propagate(False)
        for i, (c, p) in enumerate(zip(cols, pesos)):
            cab.grid_columnconfigure(i, weight=p)
            ctk.CTkLabel(cab, text=c,
                         font=("Courier New",10,"bold"),
                         text_color=COR_ACENTO).grid(
                row=0, column=i, padx=6, pady=6, sticky="w")

        if res["vendas"]:
            for idx, v in enumerate(res["vendas"]):
                cor_bg = COR_LINHA_PAR if idx % 2 == 0 else COR_CARD
                row_f = ctk.CTkFrame(sec1, fg_color=cor_bg,
                                     corner_radius=6, height=34)
                row_f.grid(row=idx+1, column=0, columnspan=4,
                           sticky="ew", pady=1)
                row_f.grid_propagate(False)
                for i, p in enumerate(pesos):
                    row_f.grid_columnconfigure(i, weight=p)
                vals  = [v["forma_pagamento"], str(v["qtde"]),
                         f'R$ {v["total"]:.2f}', f'R$ {v["troco"]:.2f}']
                cores = [COR_TEXTO, COR_TEXTO_SUB, COR_SUCESSO, COR_TEXTO_SUB]
                for i, (val, cor) in enumerate(zip(vals, cores)):
                    ctk.CTkLabel(row_f, text=val, font=FONTE_SMALL,
                                 text_color=cor).grid(
                        row=0, column=i, padx=6, sticky="w")
        else:
            ctk.CTkLabel(sec1, text="Nenhuma venda neste caixa.",
                         font=FONTE_LABEL,
                         text_color=COR_TEXTO_SUB).grid(
                row=1, column=0, columnspan=4, pady=20)

        # Total linha
        tot_f = ctk.CTkFrame(sec1, fg_color=COR_ACENTO_LIGHT,
                             corner_radius=6, height=34)
        tot_f.grid(row=len(res["vendas"])+1, column=0, columnspan=4,
                   sticky="ew", pady=(4,0))
        tot_f.grid_propagate(False)
        tot_f.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tot_f, text=f"TOTAL GERAL",
                     font=("Courier New",11,"bold"),
                     text_color=COR_ACENTO).grid(
            row=0, column=0, padx=12, pady=6, sticky="w")
        ctk.CTkLabel(tot_f,
                     text=f"{res['qtde_vendas']} vendas  —  R$ {total_v:.2f}",
                     font=("Courier New",11,"bold"),
                     text_color=COR_ACENTO).grid(
            row=0, column=1, padx=12, pady=6, sticky="e")

        # ── Conferência de caixa ──────────────────────────────────────────────
        sec2 = self._secao(scroll, 2, "🔍  Conferência — Valor em Caixa")
        sec2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sec2, text="Valor contado (R$):",
                     font=FONTE_LABEL,
                     text_color=COR_TEXTO_SUB).grid(
            row=0, column=0, pady=8, sticky="w")

        self.ent_valor_final = ctk.CTkEntry(
            sec2, font=("Georgia",18), width=200,
            justify="center",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_valor_final.insert(0, f"{saldo_esp:.2f}")
        self.ent_valor_final.grid(row=0, column=1, pady=8,
                                   padx=(12,0), sticky="w")
        self.ent_valor_final.bind("<KeyRelease>", self._calcular_diferenca)

        ctk.CTkLabel(sec2, text="Diferença:",
                     font=FONTE_LABEL,
                     text_color=COR_TEXTO_SUB).grid(
            row=1, column=0, pady=4, sticky="w")
        self.lbl_diferenca = ctk.CTkLabel(
            sec2, text="R$ 0,00",
            font=("Georgia",14,"bold"),
            text_color=COR_SUCESSO)
        self.lbl_diferenca.grid(row=1, column=1, pady=4,
                                 padx=(12,0), sticky="w")

        self.saldo_esperado = saldo_esp

        # ── Botão fechar ──────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=16, sticky="ew")
        btn_frame.grid_columnconfigure((0,1), weight=1)

        ctk.CTkButton(btn_frame,
                      text="🖨️  Imprimir Relatório",
                      font=FONTE_BTN, height=48,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white",
                      command=lambda: self._imprimir_relatorio(res)
                      ).grid(row=0, column=0, padx=8, sticky="ew")

        ctk.CTkButton(btn_frame,
                      text="🔒  FECHAR CAIXA",
                      font=("Georgia",14,"bold"), height=48,
                      fg_color=COR_PERIGO, hover_color=COR_PERIGO2,
                      text_color="white",
                      command=lambda: self._fechar(res)
                      ).grid(row=0, column=1, padx=8, sticky="ew")

    def _card(self, parent, col, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=12,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=0, column=col, padx=6, sticky="ew")
        ctk.CTkLabel(card, text=titulo, font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(14,2))
        ctk.CTkLabel(card, text=valor,
                     font=("Georgia",18,"bold"),
                     text_color=cor).pack(pady=(0,14))

    def _secao(self, parent, row, titulo):
        frame = ctk.CTkFrame(parent, fg_color=COR_CARD,
                             corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=titulo,
                     font=FONTE_SUBTITULO,
                     text_color=COR_ACENTO).grid(
            row=0, column=0, padx=16, pady=(12,4), sticky="w")
        ctk.CTkFrame(frame, height=1, fg_color=COR_BORDA).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(0,8))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.grid(row=2, column=0, sticky="ew", padx=16, pady=(0,14))
        return inner

    def _calcular_diferenca(self, event=None):
        try:
            contado = float(
                self.ent_valor_final.get().replace(",","."))
            diff = contado - self.saldo_esperado
            cor  = COR_SUCESSO if abs(diff) < 0.01 else COR_PERIGO
            sinal = "+" if diff >= 0 else ""
            self.lbl_diferenca.configure(
                text=f"{sinal}R$ {diff:.2f}",
                text_color=cor)
        except Exception:
            pass

    def _fechar(self, res):
        try:
            valor_final = float(
                self.ent_valor_final.get().replace(",","."))
        except ValueError:
            messagebox.showerror("Erro","Valor inválido.")
            return

        if not messagebox.askyesno(
            "Fechar Caixa",
            f"Confirma o fechamento do caixa?\n\n"
            f"Total vendas: R$ {res['total_vendas']:.2f}\n"
            f"Valor contado: R$ {valor_final:.2f}\n\n"
            f"Esta ação não pode ser desfeita!"
        ):
            return

        fechar_caixa(self.caixa_id, valor_final)
        self._imprimir_relatorio(res, valor_final)
        messagebox.showinfo("Caixa Fechado",
                            "✅ Caixa fechado com sucesso!\n"
                            "Relatório salvo em cupons\\")
        # Atualiza tela
        self.caixa_id = None
        for w in self.winfo_children():
            w.destroy()
        self._build_header()
        self._build_sem_caixa()

    def _imprimir_relatorio(self, res, valor_final=None):
        """Salva relatório de fechamento em txt"""
        try:
            import os, sys
            if getattr(sys,"frozen",False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))

            pasta = os.path.join(base, "cupons")
            os.makedirs(pasta, exist_ok=True)
            agora = datetime.now().strftime("%Y%m%d_%H%M%S")
            path  = os.path.join(pasta, f"fechamento_{agora}.txt")

            from banco.database import get_config
            empresa = get_config("empresa_nome") or "Padaria Da Laine"

            with open(path, "w", encoding="utf-8") as f:
                f.write("=" * 48 + "\n")
                f.write(f"{empresa:^48}\n")
                f.write("=" * 48 + "\n")
                f.write(f"{'RELATÓRIO DE FECHAMENTO DE CAIXA':^48}\n")
                f.write("-" * 48 + "\n")
                f.write(f"Caixa #:      {self.caixa_id}\n")
                ab = self.cx_dados.get("data_abertura","")[:16]
                f.write(f"Abertura:     {ab}\n")
                f.write(f"Fechamento:   {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                f.write(f"Operador:     {self.usuario}\n")
                f.write("-" * 48 + "\n")
                f.write(f"Valor inicial: R$ {self.cx_dados.get('valor_inicial',0):.2f}\n")
                f.write(f"Total vendas:  R$ {res['total_vendas']:.2f}\n")
                f.write(f"Qtde vendas:   {res['qtde_vendas']}\n")
                f.write(f"Sangrias:      R$ {res['sangria']:.2f}\n")
                f.write(f"Suprimentos:   R$ {res['suprimento']:.2f}\n")
                f.write("-" * 48 + "\n")
                f.write("VENDAS POR FORMA DE PAGAMENTO:\n")
                for v in res["vendas"]:
                    f.write(f"  {v['forma_pagamento']:<20} R$ {v['total']:.2f}\n")
                f.write("-" * 48 + "\n")
                if valor_final is not None:
                    saldo_esp = (self.cx_dados.get("valor_inicial",0) +
                                 res["total_vendas"] + res["suprimento"] -
                                 res["sangria"])
                    diff = valor_final - saldo_esp
                    f.write(f"Saldo esperado: R$ {saldo_esp:.2f}\n")
                    f.write(f"Valor contado:  R$ {valor_final:.2f}\n")
                    f.write(f"Diferença:      R$ {diff:+.2f}\n")
                f.write("=" * 48 + "\n")

            messagebox.showinfo("Relatório",
                f"Relatório salvo em:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")
