"""telas/tela_bloqueio.py — Tela de Licença Inválida"""
import customtkinter as ctk
import sys

class TelaBloqueio(ctk.CTk):
    def __init__(self, mensagem, dados=None):
        super().__init__()
        self.title("PDV — Licença Necessária")
        self.geometry("480x380")
        self.resizable(False, False)
        self.configure(fg_color="#1A1A1A")
        self._build(mensagem)

    def _build(self, mensagem):
        ctk.CTkLabel(self, text="🔒", font=("Arial",58)).pack(pady=(30,4))
        ctk.CTkLabel(self, text="Sistema Bloqueado",
                     font=("Georgia",22, "bold"),
                     text_color="#EF4444").pack()
        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=40, pady=12)
        ctk.CTkLabel(self, text=mensagem,
                     font=("Courier New",13),
                     text_color="#9CA3AF",
                     justify="center",
                     wraplength=400).pack(padx=30)
        ctk.CTkFrame(self, height=1, fg_color="#333").pack(fill="x", padx=40, pady=12)

        # Mostra ID do PC para facilitar contato
        try:
            from utils.licenca import get_id_computador
            id_pc = get_id_computador()
            ctk.CTkLabel(self,
                         text=f"ID deste computador: {id_pc}",
                         font=("Courier New",13, "bold"),
                         text_color="#F59E0B").pack()
            ctk.CTkLabel(self,
                         text="Informe este código ao desenvolvedor",
                         font=("Courier New",12),
                         text_color="#6B7280").pack()
        except Exception:
            pass

        ctk.CTkButton(self, text="Fechar",
                      font=("Georgia",14, "bold"),
                      fg_color="#374151", hover_color="#4B5563",
                      text_color="white", width=120, height=38,
                      command=sys.exit).pack(pady=16)
