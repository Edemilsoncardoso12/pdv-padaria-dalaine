"""telas/configuracoes.py — Configurações — Tema Branco"""
import customtkinter as ctk
from tkinter import messagebox
from tema import *
from banco.database import get_config, set_config

class TelaConfiguracoes(ctk.CTkFrame):
    def __init__(self,master):
        super().__init__(master,fg_color=COR_FUNDO,corner_radius=0)
        self.grid_columnconfigure(0,weight=1); self.grid_rowconfigure(1,weight=1)
        self._build_header(); self._build_corpo(); self._carregar()

    def _build_header(self):
        hdr=ctk.CTkFrame(self,fg_color=COR_CARD,corner_radius=0,border_width=1,border_color=COR_BORDA,height=70)
        hdr.grid(row=0,column=0,sticky="ew"); hdr.grid_propagate(False)
        ctk.CTkLabel(hdr,text="⚙️  Configurações do Sistema",font=FONTE_TITULO,text_color=COR_ACENTO).pack(side="left",padx=24,pady=18)
        ctk.CTkButton(hdr,text="💾  Salvar Configurações",font=FONTE_BTN,fg_color=COR_SUCESSO,hover_color=COR_SUCESSO2,text_color="white",command=self._salvar).pack(side="right",padx=24,pady=16)

    def _build_corpo(self):
        scroll=ctk.CTkScrollableFrame(self,fg_color="transparent")
        scroll.grid(row=1,column=0,sticky="nsew",padx=16,pady=16); scroll.grid_columnconfigure(0,weight=1)

        # Empresa
        sec1=self._secao(scroll,0,"🏪  Dados da Empresa"); self.campos_empresa={}
        for i,(label,key) in enumerate([("Nome da Empresa","empresa_nome"),("CNPJ","empresa_cnpj"),("Inscrição Estadual","empresa_ie"),("Endereço Completo","empresa_end")]):
            ctk.CTkLabel(sec1,text=label,font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=i,column=0,pady=6,sticky="w")
            ent=ctk.CTkEntry(sec1,font=FONTE_LABEL,height=34,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); ent.grid(row=i,column=1,sticky="ew",pady=6,padx=(12,0)); sec1.grid_columnconfigure(1,weight=1); self.campos_empresa[key]=ent

        # NFC-e
        sec2=self._secao(scroll,1,"🧾  NFC-e — Focus NFe"); self.campos_nfce={}
        ctk.CTkLabel(sec2,text="Token da API",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=0,column=0,pady=6,sticky="w")
        ent=ctk.CTkEntry(sec2,font=FONTE_LABEL,height=34,show="*",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); ent.grid(row=0,column=1,sticky="ew",pady=6,padx=(12,0)); sec2.grid_columnconfigure(1,weight=1); self.campos_nfce["focusnfe_token"]=ent
        ctk.CTkLabel(sec2,text="Ambiente",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=1,column=0,pady=6,sticky="w")
        self.cmb_amb=ctk.CTkComboBox(sec2,values=["homologacao","producao"],font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb_amb.grid(row=1,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkLabel(sec2,text="💡 Crie conta gratuita em focusnfe.com.br",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=2,column=0,columnspan=2,pady=4,sticky="w")

        # Impressora
        sec3=self._secao(scroll,2,"🖨️  Impressora Térmica"); sec3.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(sec3,text="Tipo de conexão:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=0,column=0,pady=6,sticky="w")
        self.cmb_imp_tipo=ctk.CTkComboBox(sec3,values=["txt","usb_windows","rede","win32"],font=FONTE_LABEL,fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.cmb_imp_tipo.grid(row=0,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkLabel(sec3,text="Nome da impressora:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=1,column=0,pady=6,sticky="w")
        self.ent_impressora=ctk.CTkEntry(sec3,font=FONTE_LABEL,height=34,placeholder_text="Ex: POS-80",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.ent_impressora.grid(row=1,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkLabel(sec3,text="IP (rede):",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=2,column=0,pady=6,sticky="w")
        self.ent_imp_ip=ctk.CTkEntry(sec3,font=FONTE_LABEL,height=34,placeholder_text="192.168.1.100",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.ent_imp_ip.grid(row=2,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkLabel(sec3,text="Porta (rede):",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=3,column=0,pady=6,sticky="w")
        self.ent_imp_porta=ctk.CTkEntry(sec3,font=FONTE_LABEL,height=34,placeholder_text="9100",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.ent_imp_porta.grid(row=3,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkButton(sec3,text="🖨️  Testar Impressora",font=FONTE_BTN,fg_color="#6B7280",hover_color="#4B5563",text_color="white",command=self._testar_impressora).grid(row=4,column=0,columnspan=2,pady=8,sticky="w")
        ctk.CTkLabel(sec3,text="💡 Sem impressora: cupom salvo em cupons\\",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=5,column=0,columnspan=2,sticky="w")

        # Backup
        sec4=self._secao(scroll,3,"💾  Backup de Dados")
        ctk.CTkButton(sec4,text="💾  Fazer Backup Agora",font=FONTE_BTN,fg_color="#6B7280",hover_color="#4B5563",text_color="white",command=self._fazer_backup).pack(anchor="w",pady=4)
        ctk.CTkButton(sec4,text="📋  Ver Backups",font=FONTE_BTN,fg_color="#374151",hover_color="#1F2937",text_color="white",command=self._ver_backups).pack(anchor="w",pady=4)
        ctk.CTkLabel(sec4,text="💡 Backup automático diário ao iniciar",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(pady=4,anchor="w")

        # Balança
        sec4b=self._secao(scroll,4,"⚖️  Balança Serial"); sec4b.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(sec4b,text="Porta COM:",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).grid(row=0,column=0,pady=6,sticky="w")
        self.ent_balanca_porta=ctk.CTkEntry(sec4b,font=FONTE_LABEL,placeholder_text="Ex: COM1",fg_color=COR_CARD2,border_color=COR_BORDA2,text_color=COR_TEXTO); self.ent_balanca_porta.grid(row=0,column=1,sticky="ew",pady=6,padx=(12,0))
        ctk.CTkButton(sec4b,text="⚖️  Testar Balança",font=FONTE_BTN,fg_color="#6B7280",hover_color="#4B5563",text_color="white",command=self._testar_balanca).grid(row=1,column=0,columnspan=2,pady=4,sticky="w")

        # Usuários
        sec_u=self._secao(scroll,5,"👤  Gerenciar Usuários")
        ctk.CTkLabel(sec_u,text="Cadastrar, editar e controlar acesso de usuários do sistema",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(anchor="w",pady=(0,8))
        ctk.CTkButton(sec_u,text="👤  Abrir Gerenciamento de Usuários",font=FONTE_BTN,fg_color="#374151",hover_color="#1F2937",text_color="white",command=self._abrir_usuarios).pack(anchor="w",pady=4)

        # Segurança
        sec5=self._secao(scroll,6,"🔐  Segurança e Conformidade")
        ctk.CTkLabel(sec5,text="Verifique o status de segurança do sistema (PCI DSS / LGPD)",font=FONTE_SMALL,text_color=COR_TEXTO_SUB).pack(anchor="w",pady=(0,8))
        ctk.CTkButton(sec5,text="🔐  Abrir Painel de Segurança",font=FONTE_BTN,fg_color=COR_ACENTO,hover_color=COR_ACENTO2,text_color="white",command=self._abrir_seguranca).pack(anchor="w",pady=4)

        # Sobre
        sec6=self._secao(scroll,7,"ℹ️  Sobre")
        ctk.CTkLabel(sec6,text="PDV Padaria Da Laine  v2.0\nPython + CustomTkinter + SQLite\nNFC-e via Focus NFe\nSegurança: PCI DSS + LGPD",font=FONTE_SMALL,text_color=COR_TEXTO_SUB,justify="left").pack(pady=8,anchor="w")

    def _secao(self,parent,row,titulo):
        frame=ctk.CTkFrame(parent,fg_color=COR_CARD,corner_radius=12,border_width=1,border_color=COR_BORDA)
        frame.grid(row=row,column=0,sticky="ew",pady=8)
        ctk.CTkLabel(frame,text=titulo,font=FONTE_SUBTITULO,text_color=COR_ACENTO).pack(anchor="w",padx=16,pady=(14,4))
        ctk.CTkFrame(frame,height=1,fg_color=COR_BORDA).pack(fill="x",padx=16,pady=(0,8))
        inner=ctk.CTkFrame(frame,fg_color="transparent"); inner.pack(fill="both",padx=16,pady=(0,14)); return inner

    def _carregar(self):
        for key,ent in self.campos_empresa.items(): ent.delete(0,"end"); ent.insert(0,get_config(key) or "")
        for key,ent in self.campos_nfce.items(): ent.delete(0,"end"); ent.insert(0,get_config(key) or "")
        self.cmb_amb.set(get_config("focusnfe_amb") or "homologacao")
        self.ent_impressora.delete(0,"end"); self.ent_impressora.insert(0,get_config("impressora_nome") or "")
        self.cmb_imp_tipo.set(get_config("impressora_tipo") or "txt")
        self.ent_imp_ip.delete(0,"end"); self.ent_imp_ip.insert(0,get_config("impressora_ip") or "")
        self.ent_imp_porta.delete(0,"end"); self.ent_imp_porta.insert(0,get_config("impressora_porta") or "9100")
        self.ent_balanca_porta.delete(0,"end"); self.ent_balanca_porta.insert(0,get_config("balanca_porta") or "")

    def _salvar(self):
        for key,ent in self.campos_empresa.items(): set_config(key,ent.get())
        for key,ent in self.campos_nfce.items(): set_config(key,ent.get())
        set_config("focusnfe_amb",self.cmb_amb.get()); set_config("impressora_nome",self.ent_impressora.get())
        set_config("impressora_tipo",self.cmb_imp_tipo.get()); set_config("impressora_ip",self.ent_imp_ip.get())
        set_config("impressora_porta",self.ent_imp_porta.get()); set_config("balanca_porta",self.ent_balanca_porta.get())
        messagebox.showinfo("Salvo","✅ Configurações salvas!")

    def _testar_impressora(self):
        try:
            from utils.impressora import testar_impressora
            ok,msg=testar_impressora(); messagebox.showinfo("Impressora",msg)
        except Exception as e: messagebox.showerror("Erro",str(e))

    def _fazer_backup(self):
        try:
            from utils.backup import fazer_backup
            ok,msg,_=fazer_backup("manual")
            if ok: messagebox.showinfo("Backup",msg)
            else: messagebox.showerror("Backup",msg)
        except Exception as e: messagebox.showerror("Erro",str(e))

    def _ver_backups(self):
        from utils.backup import listar_backups
        bks=listar_backups()
        win=ctk.CTkToplevel(self); win.title("Backups"); win.geometry("600x400"); win.configure(fg_color=COR_CARD)
        ctk.CTkLabel(win,text="💾  Backups Disponíveis",font=FONTE_TITULO,text_color=COR_ACENTO).pack(pady=12)
        scroll=ctk.CTkScrollableFrame(win,fg_color=COR_CARD2); scroll.pack(fill="both",expand=True,padx=16,pady=(0,16))
        for b in bks:
            ctk.CTkLabel(scroll,text=f'{b["data"]}  |  {b["nome"]}  |  {b["tamanho_kb"]:.1f} KB',font=FONTE_SMALL,text_color=COR_TEXTO,anchor="w").pack(fill="x",pady=1,padx=8)
        if not bks: ctk.CTkLabel(scroll,text="Nenhum backup.",font=FONTE_LABEL,text_color=COR_TEXTO_SUB).pack(pady=20)

    def _abrir_usuarios(self):
        from telas.login import TelaUsuarios
        win = ctk.CTkToplevel(self)
        win.title("Gerenciar Usuários")
        win.geometry("900x600")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()
        frame = ctk.CTkFrame(win, fg_color=COR_FUNDO, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        TelaUsuarios(frame).grid(row=0, column=0, sticky="nsew")

    def _abrir_seguranca(self):
        from telas.seguranca_painel import PainelSeguranca
        PainelSeguranca(self)

    def _testar_balanca(self):
        try:
            from utils.balanca import get_peso_balanca
            porta=self.ent_balanca_porta.get() or "COM1"
            peso,msg=get_peso_balanca(porta); messagebox.showinfo("Balança",msg)
        except Exception as e: messagebox.showerror("Erro",str(e))
