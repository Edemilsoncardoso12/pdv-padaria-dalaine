"""
utils/backup.py — Backup Automático do Banco de Dados
"""
import os
import sys
import shutil
from datetime import datetime

# BASE_DIR
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH      = os.path.join(BASE_DIR, "banco", "padaria.db")
BACKUP_DIR   = os.path.join(BASE_DIR, "backups")
MAX_BACKUPS  = 30


def fazer_backup(motivo="auto"):
    """
    Copia o banco de dados para a pasta backups/
    Retorna (sucesso: bool, mensagem: str, caminho: str)
    """
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        if not os.path.exists(DB_PATH):
            return False, "Banco de dados não encontrado.", ""

        agora    = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome     = f"padaria_{agora}_{motivo}.db"
        destino  = os.path.join(BACKUP_DIR, nome)

        shutil.copy2(DB_PATH, destino)

        # Limpar backups antigos (manter últimos MAX_BACKUPS)
        _limpar_backups_antigos()

        tamanho = os.path.getsize(destino) / 1024
        return True, f"✅ Backup salvo!\n{nome}\n({tamanho:.1f} KB)", destino

    except Exception as e:
        return False, f"❌ Erro no backup: {e}", ""


def _limpar_backups_antigos():
    """Remove backups mais antigos, mantendo apenas os últimos MAX_BACKUPS"""
    try:
        arquivos = sorted([
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("padaria_") and f.endswith(".db")
        ])
        while len(arquivos) > MAX_BACKUPS:
            os.remove(os.path.join(BACKUP_DIR, arquivos[0]))
            arquivos.pop(0)
    except Exception:
        pass


def listar_backups():
    """Lista todos os backups disponíveis"""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        arquivos = sorted([
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("padaria_") and f.endswith(".db")
        ], reverse=True)
        result = []
        for f in arquivos:
            path = os.path.join(BACKUP_DIR, f)
            tam  = os.path.getsize(path) / 1024
            data = datetime.fromtimestamp(
                os.path.getmtime(path)).strftime("%d/%m/%Y %H:%M")
            result.append({"nome": f, "caminho": path,
                           "tamanho_kb": tam, "data": data})
        return result
    except Exception:
        return []


def restaurar_backup(caminho_backup):
    """Restaura um backup (substitui o banco atual)"""
    try:
        if not os.path.exists(caminho_backup):
            return False, "Arquivo de backup não encontrado."

        # Faz backup do atual antes de restaurar
        fazer_backup("pre_restauracao")

        shutil.copy2(caminho_backup, DB_PATH)
        return True, "✅ Backup restaurado com sucesso!\nReinicie o sistema."
    except Exception as e:
        return False, f"❌ Erro ao restaurar: {e}"


def backup_automatico_inicializacao():
    """
    Chamado ao iniciar o sistema.
    Faz backup apenas 1x por dia.
    """
    try:
        hoje  = datetime.now().strftime("%Y%m%d")
        ja_fez = any(
            hoje in f
            for f in os.listdir(BACKUP_DIR)
            if f.endswith(".db")
        ) if os.path.exists(BACKUP_DIR) else False

        if not ja_fez:
            fazer_backup("diario")
    except Exception:
        pass
