"""
telas/auditoria.py — Tela de Auditoria Visual
Histórico completo de ações do sistema — acesso somente admin
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date, timedelta
from tema import *
from banco.database import get_conn


def registrar_auditoria(usuario, acao, modulo="", detalhe=""):
    """Registra uma ação no log de auditoria"""
    try:
        conn = get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auditoria (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT DEFAULT (datetime('now','localtime')),
                usuario   TEXT,
                acao      TEXT,
                modulo    TEXT,
                detalhe   TEXT
            )
        """)
        conn.execute("""
            INSERT INTO auditoria (usuario, acao, modulo, detalhe)
            VALUES (?, ?, ?, ?)
        """, (usuario, acao, modulo, str(detalhe)[:500]))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Auditoria] Erro: {e}")


def listar_auditoria(data_ini=None, data_fim=None, usuario=None,
                      acao=None, limite=500):
    """Lista registros de auditoria com filtros"""
    conn = get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auditoria (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT DEFAULT (datetime('now','localtime')),
                usuario   TEXT,
                acao      TEXT,
                modulo    TEXT,
                detalhe   TEXT
            )
        """)
        conn.commit()

        query  = "SELECT * FROM auditoria WHERE 1=1"
        params = []

        if data_ini:
            query += " AND date(data_hora) >= ?"
            params.append(data_ini)
        if data_fim:
            query += " AND date(data_hora) <= ?"
            params.append(data_fim)
        if usuario:
            query += " AND usuario LIKE ?"
            params.append(f"%{usuario}%")
        if acao:
            query += " AND acao LIKE ?"
            params.append(f"%{acao}%")

        query += f" ORDER BY data_hora DESC LIMIT {limite}"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        conn.close()
        return []


class TelaAuditoria(ctk.CTkFrame):
    """Tela de auditoria visual — somente admin"""

    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_filtros()
        self._build_tabela()
        self._carregar()

    # ── Header ──────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="🔍  Auditoria do Sistema",
                     font=FONTE_TITULO, text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")

        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")

        ctk.CTkButton(bf, text="🔄  Atualizar",
                      font=FONTE_BTN, width=120,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white", command=self._carregar
                      ).pack(side="left", padx=4)

        ctk.CTkButton(bf, text="📄  Exportar TXT",
                      font=FONTE_BTN, width=130,
                      fg_color="#6B7280", hover_color="#4B5563",
                      text_color="white", command=self._exportar
                      ).pack(side="left", padx=4)

    # ── Filtros ──────────────────────────────────────────────────
    def _build_filtros(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=(8, 0), sticky="ew")

        f = ctk.CTkFrame(frame, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=12)

        # Data início
        ctk.CTkLabel(f, text="De:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.ent_data_ini = ctk.CTkEntry(
            f, width=110, font=FONTE_LABEL,
            placeholder_text="DD/MM/AAAA",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_data_ini.pack(side="left", padx=(0, 12))
        self.ent_data_ini.insert(0, date.today().strftime("%d/%m/%Y"))

        # Data fim
        ctk.CTkLabel(f, text="Até:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.ent_data_fim = ctk.CTkEntry(
            f, width=110, font=FONTE_LABEL,
            placeholder_text="DD/MM/AAAA",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_data_fim.pack(side="left", padx=(0, 12))
        self.ent_data_fim.insert(0, date.today().strftime("%d/%m/%Y"))

        # Usuário
        ctk.CTkLabel(f, text="Usuário:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.ent_usuario = ctk.CTkEntry(
            f, width=120, font=FONTE_LABEL,
            placeholder_text="Todos",
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_usuario.pack(side="left", padx=(0, 12))

        # Ação
        ctk.CTkLabel(f, text="Ação:", font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(side="left", padx=(0, 4))
        self.cmb_acao = ctk.CTkComboBox(
            f, width=150, font=FONTE_LABEL,
            values=["Todas", "LOGIN", "LOGOUT", "VENDA", "CANCELAMENTO",
                    "SANGRIA", "SUPRIMENTO", "FECHAMENTO", "PRODUTO",
                    "CLIENTE", "CONFIGURACAO"],
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.cmb_acao.set("Todas")
        self.cmb_acao.pack(side="left", padx=(0, 12))

        # Botões rápidos de período
        for label, dias in [("Hoje", 0), ("7 dias", 7), ("30 dias", 30)]:
            ctk.CTkButton(
                f, text=label, font=FONTE_SMALL, width=70,
                fg_color=COR_ACENTO_LIGHT, text_color=COR_ACENTO,
                hover_color=COR_BORDA,
                command=lambda d=dias: self._filtro_rapido(d)
            ).pack(side="left", padx=2)

        ctk.CTkButton(f, text="🔍 Filtrar",
                      font=FONTE_BTN, width=100,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white",
                      command=self._carregar
                      ).pack(side="left", padx=(8, 0))

    # ── Tabela ───────────────────────────────────────────────────
    def _build_tabela(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=2, column=0, padx=16, pady=8, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        cols   = ["Data/Hora", "Usuário", "Ação", "Módulo", "Detalhe"]
        widths = [140, 100, 130, 100, 400]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        cab.pack_propagate(False)

        h = ctk.CTkFrame(cab, fg_color="transparent")
        h.pack(fill="x", padx=4)
        for col, w in zip(cols, widths):
            ctk.CTkLabel(h, text=col,
                         font=("Courier New",14, "bold"),
                         text_color=COR_ACENTO, width=w,
                         anchor="w").pack(side="left", padx=2, pady=6)

        # Scroll
        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        # Rodapé contador
        self.lbl_total = ctk.CTkLabel(
            frame, text="",
            font=FONTE_SMALL, text_color=COR_TEXTO_SUB)
        self.lbl_total.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))

    # ── Carregar dados ───────────────────────────────────────────
    def _carregar(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        # Parse datas
        try:
            d_ini = datetime.strptime(
                self.ent_data_ini.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            d_ini = date.today().strftime("%Y-%m-%d")

        try:
            d_fim = datetime.strptime(
                self.ent_data_fim.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except Exception:
            d_fim = date.today().strftime("%Y-%m-%d")

        usuario = self.ent_usuario.get().strip() or None
        acao    = self.cmb_acao.get()
        acao    = None if acao == "Todas" else acao

        registros = listar_auditoria(d_ini, d_fim, usuario, acao)

        # Cores por ação
        cores_acao = {
            "LOGIN":         "#2E7D32",
            "LOGOUT":        "#546E7A",
            "VENDA":         "#1565C0",
            "CANCELAMENTO":  "#C62828",
            "SANGRIA":       "#E65100",
            "SUPRIMENTO":    "#1565C0",
            "FECHAMENTO":    "#6A1B9A",
            "PRODUTO":       "#F57F17",
            "CLIENTE":       "#00838F",
            "CONFIGURACAO":  "#4E342E",
        }

        widths = [140, 100, 130, 100, 400]

        if not registros:
            ctk.CTkLabel(self.scroll,
                         text="Nenhum registro encontrado.",
                         font=FONTE_LABEL,
                         text_color=COR_TEXTO_SUB).pack(pady=40)
        else:
            for i, r in enumerate(registros):
                bg  = COR_LINHA_PAR if i % 2 == 0 else COR_CARD
                lin = ctk.CTkFrame(self.scroll, fg_color=bg,
                                   corner_radius=4, height=32)
                lin.pack(fill="x", pady=1)
                lin.pack_propagate(False)

                row = ctk.CTkFrame(lin, fg_color="transparent")
                row.pack(fill="x", padx=4, pady=4)

                cor_acao = cores_acao.get(r.get("acao", ""), COR_TEXTO)

                vals = [
                    r.get("data_hora", "")[:16],
                    r.get("usuario", "—"),
                    r.get("acao", "—"),
                    r.get("modulo", "—"),
                    r.get("detalhe", "—")[:80],
                ]
                cores = [COR_TEXTO_SUB, COR_TEXTO, cor_acao,
                         COR_TEXTO_SUB, COR_TEXTO_SUB]
                bolds = [False, True, True, False, False]

                for v, c, w, bold in zip(vals, cores, widths, bolds):
                    ctk.CTkLabel(row, text=v,
                                 font=("Courier New",14,
                                       "bold" if bold else "normal"),
                                 text_color=c, width=w,
                                 anchor="w").pack(side="left", padx=2)

        self.lbl_total.configure(
            text=f"Total: {len(registros)} registro(s)")

    def _filtro_rapido(self, dias):
        hoje = date.today()
        ini  = (hoje - timedelta(days=dias)) if dias > 0 else hoje
        self.ent_data_ini.delete(0, "end")
        self.ent_data_ini.insert(0, ini.strftime("%d/%m/%Y"))
        self.ent_data_fim.delete(0, "end")
        self.ent_data_fim.insert(0, hoje.strftime("%d/%m/%Y"))
        self._carregar()

    def _exportar(self):
        from tkinter import filedialog
        import os, sys

        registros = listar_auditoria()
        if not registros:
            messagebox.showinfo("Exportar", "Nenhum registro para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
            initialfile=f"auditoria_{date.today().strftime('%Y%m%d')}.txt",
            title="Salvar Auditoria"
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"{'RELATÓRIO DE AUDITORIA':^80}\n")
            f.write(f"{'PDV Padaria Da Laine':^80}\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S'):^80}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"{'Data/Hora':<18} {'Usuário':<15} {'Ação':<18} "
                    f"{'Módulo':<12} Detalhe\n")
            f.write("-" * 80 + "\n")
            for r in registros:
                f.write(
                    f"{r.get('data_hora','')[:16]:<18} "
                    f"{r.get('usuario',''):<15} "
                    f"{r.get('acao',''):<18} "
                    f"{r.get('modulo',''):<12} "
                    f"{r.get('detalhe','')[:40]}\n"
                )
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Total de registros: {len(registros)}\n")

        messagebox.showinfo("✅ Exportado", f"Auditoria salva em:\n{path}")
