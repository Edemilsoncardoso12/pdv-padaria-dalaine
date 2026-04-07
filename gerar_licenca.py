"""
gerar_licenca.py — Ferramenta do Desenvolvedor
NUNCA inclua este arquivo no .exe do cliente!
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.licenca import gerar_chave_licenca, salvar_licenca, get_id_computador

print("=" * 55)
print("  PDV Padaria Da Laine — Gerador de Licenças v2.0")
print("=" * 55)
print()
print("PASSO 1: Peça ao cliente para rodar o programa e")
print("         te passar o ID do computador dele.")
print()

cnpj         = input("CNPJ do cliente (só números): ").strip()
nome_empresa = input("Nome da empresa: ").strip()
id_pc        = input("ID do computador do cliente: ").strip().upper()

print()
print("Tipo de licença:")
print("  1 — Permanente (sem vencimento)  — R$ 800-1500")
print("  2 — Anual (1 ano)                — R$ 300-500")
print("  3 — Semestral (6 meses)          — R$ 200-300")
print("  4 — Mensal (30 dias)             — R$ 50-100")
print("  5 — Teste grátis (15 dias)       — Grátis")
tipo = input("Escolha (1-5): ").strip()

validade = {"1":36500,"2":365,"3":180,"4":30,"5":15}.get(tipo, 36500)

dados = gerar_chave_licenca(cnpj, nome_empresa, id_pc, validade)

pasta = input(f"\nPasta para salvar (Enter = pasta atual): ").strip() or "."
os.makedirs(pasta, exist_ok=True)
caminho = os.path.join(pasta, "licenca.key")
salvar_licenca(dados, caminho)

print()
print("=" * 55)
print("  LICENÇA GERADA!")
print("=" * 55)
print(f"  Empresa:     {dados['nome_empresa']}")
print(f"  CNPJ:        {dados['cnpj']}")
print(f"  Computador:  {dados['id_computador']}")
print(f"  Emissão:     {dados['data_emissao']}")
print(f"  Validade:    {dados['data_expira']}")
print(f"  Arquivo:     {caminho}")
print()
print("  Envie o licenca.key para o cliente colocar")
print("  na mesma pasta do PDV_Padaria_DaLaine.exe")
print("=" * 55)
input("\nPressione Enter para sair...")
