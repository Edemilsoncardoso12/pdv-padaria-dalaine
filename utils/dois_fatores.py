"""
utils/dois_fatores.py — Autenticação em Dois Fatores (2FA)
Para administradores do sistema.
Usa código numérico de 6 dígitos por email ou código offline.
"""
import os, sys, random, hashlib, json
from datetime import datetime, timedelta

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Armazena códigos temporários em memória
_codigos_2fa = {}  # {usuario_id: {codigo, expira}}

def gerar_codigo_2fa(usuario_id):
    """Gera código de 6 dígitos válido por 5 minutos"""
    codigo  = str(random.randint(100000, 999999))
    expira  = datetime.now() + timedelta(minutes=5)
    _codigos_2fa[usuario_id] = {"codigo": codigo, "expira": expira}
    return codigo

def verificar_codigo_2fa(usuario_id, codigo_digitado):
    """Verifica se o código está correto e não expirou"""
    dados = _codigos_2fa.get(usuario_id)
    if not dados:
        return False, "Código não gerado."
    if datetime.now() > dados["expira"]:
        del _codigos_2fa[usuario_id]
        return False, "Código expirado. Solicite novo."
    if dados["codigo"] != codigo_digitado.strip():
        return False, "Código incorreto."
    del _codigos_2fa[usuario_id]
    return True, "OK"

def enviar_codigo_email(email, codigo, nome_empresa="Padaria Da Laine"):
    """Envia código por email (requer configuração SMTP)"""
    try:
        from banco.database import get_config
        smtp_host = get_config("smtp_host") or ""
        smtp_user = get_config("smtp_user") or ""
        smtp_pass = get_config("smtp_pass") or ""
        if not smtp_host or not smtp_user:
            return False, "Email não configurado."
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(
            f"Seu código de acesso administrativo:\n\n"
            f"  {codigo}\n\n"
            f"Válido por 5 minutos.\n"
            f"Se não foi você, contate o suporte imediatamente.",
            "plain", "utf-8")
        msg["Subject"] = f"[{nome_empresa}] Código 2FA: {codigo}"
        msg["From"]    = smtp_user
        msg["To"]      = email
        with smtplib.SMTP_SSL(smtp_host, 465, timeout=10) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [email], msg.as_string())
        return True, f"Código enviado para {email}"
    except Exception as e:
        return False, str(e)


class Dialogo2FA:
    """Diálogo de autenticação em dois fatores"""
    def __init__(self, master, usuario_id, usuario_nome,
                 email=None, callback_ok=None, callback_cancel=None):
        import customtkinter as ctk
        try:
            from tema import (COR_CARD, COR_ACENTO, COR_ACENTO2,
                              COR_BORDA, COR_PERIGO, COR_SUCESSO,
                              COR_SUCESSO2, COR_TEXTO, COR_TEXTO_SUB,
                              FONTE_TITULO, FONTE_LABEL, FONTE_SMALL,
                              FONTE_BTN, COR_CARD2, COR_BORDA2)
        except ImportError:
            return

        self.usuario_id   = usuario_id
        self.callback_ok  = callback_ok
        self.tentativas   = 0

        win = ctk.CTkToplevel(master)
        win.title("Verificação de Segurança")
        win.geometry("400x380")
        win.configure(fg_color=COR_CARD)
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW",
                     lambda: callback_cancel() if callback_cancel else win.destroy())

        ctk.CTkLabel(win, text="🔐  Verificação Admin",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(24,4))
        ctk.CTkLabel(win,
                     text=f"Confirmação necessária para: {usuario_nome}",
                     font=FONTE_SMALL, text_color=COR_TEXTO_SUB).pack()

        ctk.CTkFrame(win, height=1,
                     fg_color=COR_BORDA).pack(fill="x", padx=24, pady=12)

        # Gera e mostra código offline (sem email)
        codigo = gerar_codigo_2fa(usuario_id)

        ctk.CTkLabel(win,
                     text="Código de verificação gerado:",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack()

        # Mostra código em destaque (modo sem email)
        frame_cod = ctk.CTkFrame(win, fg_color="#F0FDF4",
                                  corner_radius=12,
                                  border_width=2,
                                  border_color=COR_SUCESSO)
        frame_cod.pack(padx=40, pady=8, fill="x")
        ctk.CTkLabel(frame_cod, text=codigo,
                     font=("Courier New",32,"bold"),
                     text_color=COR_SUCESSO).pack(pady=12)
        ctk.CTkLabel(frame_cod,
                     text="Válido por 5 minutos",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(0,8))

        # Se tem email configurado, envia por email também
        if email:
            ok_mail, msg_mail = enviar_codigo_email(email, codigo)
            ctk.CTkLabel(win, text=msg_mail,
                         font=FONTE_SMALL,
                         text_color=COR_SUCESSO if ok_mail else COR_TEXTO_SUB
                         ).pack()

        ctk.CTkLabel(win, text="Digite o código acima:",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(8,4))

        ent = ctk.CTkEntry(win, font=("Courier New",22),
                           width=160, justify="center",
                           fg_color=COR_CARD2,
                           border_color=COR_ACENTO,
                           text_color=COR_TEXTO)
        ent.pack(pady=4)
        ent.focus_set()

        lbl_erro = ctk.CTkLabel(win, text="",
                                font=FONTE_SMALL,
                                text_color=COR_PERIGO)
        lbl_erro.pack()

        def confirmar():
            self.tentativas += 1
            if self.tentativas > 3:
                win.destroy()
                if callback_cancel:
                    callback_cancel()
                return
            ok, msg = verificar_codigo_2fa(usuario_id, ent.get())
            if ok:
                win.destroy()
                if callback_ok:
                    callback_ok()
            else:
                lbl_erro.configure(
                    text=f"{msg} ({3-self.tentativas} tentativas restantes)")
                ent.delete(0, "end")

        ent.bind("<Return>", lambda e: confirmar())
        ctk.CTkButton(win, text="✅  Confirmar",
                      font=FONTE_BTN, height=42,
                      fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
                      text_color="white",
                      command=confirmar).pack(
            fill="x", padx=40, pady=8)
