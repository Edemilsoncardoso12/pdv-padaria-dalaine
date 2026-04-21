"""telas/login.py — Login — Tema Branco — Senha Scrypt"""
import customtkinter as ctk
from tkinter import messagebox
import hashlib, os, base64
from banco.database import get_conn
from tema import *

# ── Hash de senha com scrypt ──────────────────────────────────────────────────
def hash_senha(senha):
    """scrypt — muito mais seguro que SHA-256"""
    salt = b"pdv_padaria_laine_2025_fixed"
    h = hashlib.scrypt(
        senha.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return "scrypt:" + base64.b64encode(h).decode()

def hash_senha_legado(senha):
    """SHA-256 antigo — para migração automática"""
    salt = "pdv_padaria_laine_2025"
    return hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()

def verificar_login(login, senha):
    """Verifica login — aceita hash novo e legado"""
    conn = get_conn()
    # Tenta hash novo (scrypt)
    user = conn.execute(
        "SELECT * FROM usuarios WHERE login=? AND senha=? AND ativo=1",
        (login, hash_senha(senha))).fetchone()
    if not user:
        # Tenta hash legado (SHA-256)
        user = conn.execute(
            "SELECT * FROM usuarios WHERE login=? AND senha=? AND ativo=1",
            (login, hash_senha_legado(senha))).fetchone()
        if user:
            # Migra para scrypt automaticamente
            conn.execute("UPDATE usuarios SET senha=? WHERE id=?",
                        (hash_senha(senha), user["id"]))
            conn.commit()
    conn.close()
    return user

def registrar_log(usuario, acao):
    conn = get_conn()
    conn.execute(
        "INSERT INTO log_acesso(usuario,acao) VALUES(?,?)",
        (usuario, acao))
    conn.commit()
    conn.close()

def inicializar_usuarios():
    conn = get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, login TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL, perfil TEXT DEFAULT 'OPERADOR',
        ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT(datetime('now','localtime')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS log_acesso(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT, acao TEXT,
        data_hora TEXT DEFAULT(datetime('now','localtime')))""")
    # Inserir admin se não existir
    existe_admin = conn.execute(
        "SELECT id FROM usuarios WHERE login='admin'").fetchone()
    if not existe_admin:
        conn.execute(
            "INSERT INTO usuarios(nome,login,senha,perfil) VALUES(?,?,?,?)",
            ("Administrador","admin",hash_senha("admin123"),"ADMIN"))

    # Inserir caixa se não existir
    existe_caixa = conn.execute(
        "SELECT id FROM usuarios WHERE login='caixa'").fetchone()
    if not existe_caixa:
        conn.execute(
            "INSERT INTO usuarios(nome,login,senha,perfil) VALUES(?,?,?,?)",
            ("Operador Caixa","caixa",hash_senha("1234"),"OPERADOR"))

    conn.commit()
    conn.close()


# ── Tela de Login ─────────────────────────────────────────────────────────────
class TelaLogin(ctk.CTkToplevel):
    def __init__(self, master, callback):
        super().__init__(master)
        self.callback  = callback
        self.tentativas = 0
        self.title("PDV Padaria Da Laine — Login")
        self.geometry("420x580")
        self.resizable(False, False)
        self.configure(fg_color=COR_FUNDO)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        inicializar_usuarios()
        self._build()
        self.after(200, lambda: self.ent_login.focus_set())

    def _fechar(self):
        self.master.destroy()

    def _build(self):
        import sys
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        card = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=16,
                            border_width=1, border_color=COR_BORDA)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9)

        logo_path = os.path.join(base, "logo.png")
        try:
            from PIL import Image
            img = ctk.CTkImage(Image.open(logo_path), size=(110,110))
            ctk.CTkLabel(card, image=img, text="").pack(pady=(28,8))
        except Exception:
            ctk.CTkLabel(card, text="🥐",
                         font=("Arial",56)).pack(pady=(28,8))

        ctk.CTkLabel(card, text="Padaria Da Laine",
                     font=("Georgia",24,"bold"),
                     text_color=COR_ACENTO).pack()
        ctk.CTkLabel(card, text="Sistema PDV — Acesso Restrito",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(2,20))

        ctk.CTkFrame(card, height=1,
                     fg_color=COR_BORDA).pack(fill="x", padx=28, pady=(0,20))

        ctk.CTkLabel(card, text="Usuário",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=28)
        self.ent_login = ctk.CTkEntry(
            card, font=FONTE_LABEL, height=42,
            placeholder_text="Digite seu usuário...",
            corner_radius=8,
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_login.pack(fill="x", padx=28, pady=(4,12))
        self.ent_login.bind("<Return>", lambda e: self.ent_senha.focus_set())

        ctk.CTkLabel(card, text="Senha",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w", padx=28)
        self.ent_senha = ctk.CTkEntry(
            card, font=FONTE_LABEL, height=42,
            placeholder_text="Digite sua senha...",
            show="●", corner_radius=8,
            fg_color=COR_CARD2, border_color=COR_BORDA2,
            text_color=COR_TEXTO)
        self.ent_senha.pack(fill="x", padx=28, pady=(4,4))
        self.ent_senha.bind("<Return>", lambda e: self._entrar())

        self.lbl_erro = ctk.CTkLabel(
            card, text="", font=FONTE_SMALL, text_color=COR_PERIGO)
        self.lbl_erro.pack(pady=(4,8))

        self.btn_entrar = ctk.CTkButton(
            card, text="🔓  ENTRAR",
            font=FONTE_BTN, height=48,
            fg_color=COR_ACENTO, hover_color=COR_ACENTO2,
            text_color="white", corner_radius=10,
            command=self._entrar)
        self.btn_entrar.pack(fill="x", padx=28, pady=(4,8))

        ctk.CTkLabel(card,
                     text="Admin: admin / admin123   |   Caixa: caixa / 1234",
                     font=("Courier New",13),
                     text_color=COR_BORDA2).pack(pady=(0,24))

    def _entrar(self):
        login = self.ent_login.get().strip()
        senha = self.ent_senha.get().strip()
        if not login or not senha:
            self.lbl_erro.configure(text="⚠️  Preencha usuário e senha.")
            return
        if self.tentativas >= 5:
            self.lbl_erro.configure(text="🔒  Muitas tentativas. Reinicie.")
            self.btn_entrar.configure(state="disabled")
            return
        user = verificar_login(login, senha)
        if user:
            registrar_log(user["nome"], "LOGIN")
            self.destroy()
            self.callback(dict(user))
        else:
            self.tentativas += 1
            restantes = 5 - self.tentativas
            self.lbl_erro.configure(
                text=f"❌  Incorreto. ({restantes} tentativas restantes)")
            self.ent_senha.delete(0, "end")
            self.ent_senha.focus_set()


# ── Alterar Senha ─────────────────────────────────────────────────────────────
class TelaAlterarSenha(ctk.CTkToplevel):
    def __init__(self, master, usuario_id, nome):
        super().__init__(master)
        self.usuario_id = usuario_id
        self.title("Alterar Senha")
        self.geometry("380x320")
        self.configure(fg_color=COR_CARD)
        self.grab_set()
        self._build(nome)

    def _build(self, nome):
        ctk.CTkLabel(self, text="🔑  Alterar Senha",
                     font=FONTE_TITULO, text_color=COR_ACENTO).pack(pady=(20,8))
        ctk.CTkLabel(self, text=f"Usuário: {nome}",
                     font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(pady=(0,16))
        self.campos = {}
        for label, key in [("Senha atual","atual"),
                            ("Nova senha","nova"),
                            ("Confirmar nova","confirmar")]:
            ctk.CTkLabel(self, text=label,
                         font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).pack(anchor="w", padx=28)
            ent = ctk.CTkEntry(self, font=FONTE_LABEL, height=38,
                               show="●",
                               fg_color=COR_CARD2, border_color=COR_BORDA2,
                               text_color=COR_TEXTO)
            ent.pack(fill="x", padx=28, pady=(2,10))
            self.campos[key] = ent
        ctk.CTkButton(self, text="💾  Salvar Nova Senha",
                      font=FONTE_BTN, height=44,
                      fg_color=COR_SUCESSO, hover_color=COR_SUCESSO2,
                      text_color="white",
                      command=self._salvar).pack(fill="x", padx=28, pady=8)

    def _salvar(self):
        atual     = self.campos["atual"].get()
        nova      = self.campos["nova"].get()
        confirmar = self.campos["confirmar"].get()
        conn = get_conn()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE id=? AND senha=?",
            (self.usuario_id, hash_senha(atual))).fetchone()
        if not user:
            # Tenta legado
            user = conn.execute(
                "SELECT * FROM usuarios WHERE id=? AND senha=?",
                (self.usuario_id, hash_senha_legado(atual))).fetchone()
        if not user:
            messagebox.showerror("Erro","Senha atual incorreta.",parent=self)
            conn.close(); return
        if len(nova) < 4:
            messagebox.showerror("Erro","Mínimo 4 caracteres.",parent=self)
            conn.close(); return
        if nova != confirmar:
            messagebox.showerror("Erro","Senhas não conferem.",parent=self)
            conn.close(); return
        conn.execute("UPDATE usuarios SET senha=? WHERE id=?",
                    (hash_senha(nova), self.usuario_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Sucesso","✅ Senha alterada!",parent=self)
        self.destroy()


# ── Gerenciar Usuários ────────────────────────────────────────────────────────
class TelaUsuarios(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=COR_FUNDO, corner_radius=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.usuario_sel = None
        self._build_header()
        self._build_corpo()
        self._carregar()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0,
                           border_width=1, border_color=COR_BORDA, height=70)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="👥  Gerenciar Usuários",
                     font=FONTE_TITULO,
                     text_color=COR_ACENTO).grid(
            row=0, column=0, padx=24, pady=18, sticky="w")
        bf = ctk.CTkFrame(hdr, fg_color="transparent")
        bf.grid(row=0, column=1, padx=24, sticky="e")
        for txt, cor, hover, cmd in [
            ("➕ Novo",    COR_SUCESSO, COR_SUCESSO2, self._novo),
            ("✏️ Editar",  COR_ACENTO,  COR_ACENTO2,  self._editar),
            ("🔑 Senha",   "#6B7280",   "#4B5563",    self._alterar_senha),
            ("🗑️ Excluir", COR_PERIGO,  COR_PERIGO2,  self._excluir),
        ]:
            ctk.CTkButton(bf, text=txt, font=FONTE_BTN, width=100,
                          fg_color=cor, hover_color=hover,
                          text_color="white",
                          command=cmd).pack(side="left", padx=4)

    def _build_corpo(self):
        frame = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=12,
                             border_width=1, border_color=COR_BORDA)
        frame.grid(row=1, column=0, padx=16, pady=16, sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        cols  = ["Nome","Login","Perfil","Status","Criado em"]
        pesos = [4,3,2,2,3]
        cab = ctk.CTkFrame(frame, fg_color=COR_ACENTO_LIGHT,
                           corner_radius=8, height=36)
        cab.grid(row=0, column=0, sticky="ew", padx=8, pady=(8,0))
        cab.grid_propagate(False)
        for i,(c,p) in enumerate(zip(cols,pesos)):
            cab.grid_columnconfigure(i,weight=p)
            ctk.CTkLabel(cab,text=c,
                         font=("Courier New",14,"bold"),
                         text_color=COR_ACENTO).grid(
                row=0,column=i,padx=6,pady=6,sticky="w")
        self.scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.scroll.grid(row=1,column=0,sticky="nsew",padx=8,pady=8)
        self.scroll.grid_columnconfigure(0,weight=1)
        self.linhas=[]; self.id_map=[]

    def _carregar(self):
        conn=get_conn()
        users=conn.execute(
            "SELECT * FROM usuarios ORDER BY perfil,nome").fetchall()
        conn.close()
        for w in self.scroll.winfo_children(): w.destroy()
        self.linhas.clear(); self.id_map.clear(); self.usuario_sel=None
        pesos=[4,3,2,2,3]
        for idx,u in enumerate(users):
            self.id_map.append(u["id"])
            cor_bg=COR_LINHA_PAR if idx%2==0 else COR_CARD
            row_f=ctk.CTkFrame(self.scroll,fg_color=cor_bg,
                               corner_radius=6,height=36)
            row_f.grid(row=idx,column=0,sticky="ew",pady=1)
            row_f.grid_propagate(False)
            for i,p in enumerate(pesos): row_f.grid_columnconfigure(i,weight=p)
            status="✅ Ativo" if u["ativo"] else "❌ Inativo"
            cor_s=COR_SUCESSO if u["ativo"] else COR_PERIGO
            cor_p=COR_ACENTO if u["perfil"]=="ADMIN" else COR_TEXTO
            vals=[u["nome"],u["login"],u["perfil"],
                  status,u["criado_em"][:10]]
            cores=[COR_TEXTO,COR_TEXTO_SUB,cor_p,cor_s,COR_TEXTO_SUB]
            for i,(v,c) in enumerate(zip(vals,cores)):
                ctk.CTkLabel(row_f,text=v,font=FONTE_SMALL,
                             text_color=c).grid(row=0,column=i,padx=6,sticky="w")
            i_cap=idx
            row_f.bind("<Button-1>",lambda e,i=i_cap:self._sel(i))
            self.linhas.append(row_f)

    def _sel(self,idx):
        for f in self.linhas:
            f.configure(fg_color=COR_LINHA_PAR if self.linhas.index(f)%2==0 else COR_CARD)
        self.linhas[idx].configure(fg_color=COR_LINHA_SEL)
        self.usuario_sel=self.id_map[idx]

    def _novo(self): FormularioUsuario(self,None,self._carregar)
    def _editar(self):
        if not self.usuario_sel:
            messagebox.showwarning("Selecione","Selecione um usuário."); return
        FormularioUsuario(self,self.usuario_sel,self._carregar)
    def _alterar_senha(self):
        if not self.usuario_sel:
            messagebox.showwarning("Selecione","Selecione um usuário."); return
        conn=get_conn()
        u=conn.execute("SELECT nome FROM usuarios WHERE id=?",
                       (self.usuario_sel,)).fetchone()
        conn.close()
        if u: TelaAlterarSenha(self,self.usuario_sel,u["nome"])
    def _excluir(self):
        if not self.usuario_sel:
            messagebox.showwarning("Selecione","Selecione um usuário."); return
        if messagebox.askyesno("Excluir","Desativar este usuário?"):
            conn=get_conn()
            conn.execute("UPDATE usuarios SET ativo=0 WHERE id=?",
                        (self.usuario_sel,))
            conn.commit(); conn.close(); self._carregar()


class FormularioUsuario(ctk.CTkToplevel):
    def __init__(self,master,user_id,callback):
        super().__init__(master)
        self.user_id=user_id; self.callback=callback
        self.title("Usuário"); self.geometry("400x420")
        self.configure(fg_color=COR_CARD); self.grab_set(); self._build()
        if user_id: self._preencher()

    def _build(self):
        titulo="✏️  Editar" if self.user_id else "➕  Novo Usuário"
        ctk.CTkLabel(self,text=titulo,font=FONTE_TITULO,
                     text_color=COR_ACENTO).pack(pady=(20,16))
        self.campos={}
        for label,key,show in[("Nome completo","nome",""),
                               ("Login","login",""),
                               ("Senha","senha","●")]:
            ctk.CTkLabel(self,text=label,font=FONTE_SMALL,
                         text_color=COR_TEXTO_SUB).pack(anchor="w",padx=28)
            ent=ctk.CTkEntry(self,font=FONTE_LABEL,height=38,show=show,
                             fg_color=COR_CARD2,border_color=COR_BORDA2,
                             text_color=COR_TEXTO)
            ent.pack(fill="x",padx=28,pady=(4,10))
            self.campos[key]=ent
        ctk.CTkLabel(self,text="Perfil",font=FONTE_SMALL,
                     text_color=COR_TEXTO_SUB).pack(anchor="w",padx=28)
        self.cmb=ctk.CTkComboBox(self,
            values=["ADMIN","OPERADOR","FUNCIONARIO"],
            font=FONTE_LABEL,
            fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO)
        self.cmb.pack(fill="x",padx=28,pady=(4,16))
        self.cmb.set("OPERADOR")
        ctk.CTkButton(self,text="💾  Salvar",font=FONTE_BTN,height=44,
                      fg_color=COR_SUCESSO,hover_color=COR_SUCESSO2,
                      text_color="white",command=self._salvar).pack(
            fill="x",padx=28,pady=8)

    def _preencher(self):
        conn=get_conn()
        u=conn.execute("SELECT * FROM usuarios WHERE id=?",
                       (self.user_id,)).fetchone()
        conn.close()
        if u:
            self.campos["nome"].insert(0,u["nome"])
            self.campos["login"].insert(0,u["login"])
            self.cmb.set(u["perfil"])

    def _salvar(self):
        nome=self.campos["nome"].get().strip()
        login=self.campos["login"].get().strip()
        senha=self.campos["senha"].get().strip()
        if not nome or not login:
            messagebox.showerror("Erro","Nome e login obrigatórios.",parent=self)
            return
        conn=get_conn()
        if self.user_id:
            if senha:
                conn.execute(
                    "UPDATE usuarios SET nome=?,login=?,senha=?,perfil=? WHERE id=?",
                    (nome,login,hash_senha(senha),self.cmb.get(),self.user_id))
            else:
                conn.execute(
                    "UPDATE usuarios SET nome=?,login=?,perfil=? WHERE id=?",
                    (nome,login,self.cmb.get(),self.user_id))
        else:
            if not senha:
                messagebox.showerror("Erro","Senha obrigatória.",parent=self)
                conn.close(); return
            conn.execute(
                "INSERT INTO usuarios(nome,login,senha,perfil) VALUES(?,?,?,?)",
                (nome,login,hash_senha(senha),self.cmb.get()))
        conn.commit(); conn.close()
        self.callback(); self.destroy()
