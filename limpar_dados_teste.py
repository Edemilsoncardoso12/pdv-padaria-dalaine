"""
limpar_dados_teste.py
Apaga TODOS os dados de teste e deixa o sistema limpo para produção.
Execute UMA VEZ antes de entregar para o cliente.
"""
import sqlite3
import os
import sys
import shutil

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def limpar():
    base   = get_base_dir()
    db_path = os.path.join(base, "banco", "padaria.db")

    if not os.path.exists(db_path):
        print("Banco não encontrado!")
        return

    # Backup antes de limpar
    backup = db_path + ".backup_antes_limpeza"
    shutil.copy2(db_path, backup)
    print(f"Backup salvo em: {backup}")

    conn = sqlite3.connect(db_path)
    tabelas = [
        "itens_venda",
        "vendas",
        "pagamentos",
        "sangria_suprimento",
        "caixa",
        "log_acesso",
        "auditoria",
        "fichas_tecnicas",
        "clientes",
        "movimentacao_estoque",
    ]

    for tabela in tabelas:
        try:
            conn.execute(f"DELETE FROM {tabela}")
            print(f"✅ Tabela {tabela} limpa")
        except Exception as e:
            print(f"⚠️  {tabela}: {e}")

    # Zerar estoque dos produtos
    try:
        conn.execute("UPDATE produtos SET estoque_atual=0")
        print("✅ Estoque zerado")
    except Exception as e:
        print(f"⚠️  estoque: {e}")

    # Apagar produtos de teste (manter só se quiser)
    resp = input("\nApagar produtos de teste também? (S/N): ").strip().upper()
    if resp == "S":
        try:
            conn.execute("DELETE FROM produtos")
            conn.execute("DELETE FROM grupos_produto")
            print("✅ Produtos apagados")
        except Exception as e:
            print(f"⚠️  produtos: {e}")

    # Resetar usuários para padrão
    resp2 = input("Resetar usuários para admin/admin123 e caixa/1234? (S/N): ").strip().upper()
    if resp2 == "S":
        import hashlib, base64
        def hash_scrypt(senha):
            salt = b"pdv_padaria_laine_2025_fixed"
            h = hashlib.scrypt(senha.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
            return "scrypt:" + base64.b64encode(h).decode()

        conn.execute("DELETE FROM usuarios")
        conn.execute("""INSERT INTO usuarios(nome,login,senha,perfil)
                        VALUES(?,?,?,?)""",
                     ("Administrador","admin",hash_scrypt("admin123"),"ADMIN"))
        conn.execute("""INSERT INTO usuarios(nome,login,senha,perfil)
                        VALUES(?,?,?,?)""",
                     ("Operador Caixa","caixa",hash_scrypt("1234"),"OPERADOR"))
        print("✅ Usuários resetados: admin/admin123  |  caixa/1234")

    conn.commit()
    conn.close()

    # Limpar cupons de teste
    pasta_cupons = os.path.join(base, "cupons")
    if os.path.exists(pasta_cupons):
        resp3 = input("Apagar cupons de teste? (S/N): ").strip().upper()
        if resp3 == "S":
            shutil.rmtree(pasta_cupons)
            os.makedirs(pasta_cupons)
            print("✅ Cupons apagados")

    # Limpar logs
    pasta_logs = os.path.join(base, "logs")
    if os.path.exists(pasta_logs):
        resp4 = input("Apagar logs de teste? (S/N): ").strip().upper()
        if resp4 == "S":
            shutil.rmtree(pasta_logs)
            os.makedirs(pasta_logs)
            print("✅ Logs apagados")

    print("\n" + "="*50)
    print("  SISTEMA LIMPO E PRONTO PARA PRODUÇÃO!")
    print("="*50)
    print("\n  Login: admin / admin123")
    print("  Login: caixa / 1234")
    print("\n  TROQUE AS SENHAS ANTES DE ENTREGAR!")
    print("="*50)

if __name__ == "__main__":
    print("="*50)
    print("  LIMPEZA DE DADOS DE TESTE")
    print("  PDV Padaria Da Laine")
    print("="*50)
    print("\n⚠️  ATENÇÃO: Esta operação é IRREVERSÍVEL!")
    print("   (Um backup será feito automaticamente)")
    resp = input("\nContinuar? (S/N): ").strip().upper()
    if resp == "S":
        limpar()
    else:
        print("Cancelado.")
