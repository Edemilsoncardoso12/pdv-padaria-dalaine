# 🥐 PDV Padaria Da Laine

Sistema de Ponto de Venda completo para padaria.  
Desenvolvido em Python + CustomTkinter + SQLite.

---

## 📦 ESTRUTURA DO PROJETO

```
pdv_padaria/
├── main.py                  ← Arquivo principal (execute este)
├── requirements.txt         ← Dependências Python
├── gerar_exe.bat            ← Gera o .exe para distribuição
├── banco/
│   ├── __init__.py
│   └── database.py          ← Banco de dados SQLite + todas as funções
├── telas/
│   ├── __init__.py
│   ├── caixa.py             ← PDV / Caixa principal
│   ├── produtos.py          ← Cadastro de produtos
│   ├── estoque.py           ← Controle de estoque
│   ├── relatorios.py        ← Relatórios de vendas
│   └── configuracoes.py     ← Configurações do sistema
└── banco/
    └── padaria.db           ← Criado automaticamente na 1ª execução
```

---

## 🚀 COMO INSTALAR E RODAR

### Passo 1 — Instalar Python
Baixe em: https://www.python.org/downloads/
> ⚠️ Marque "Add Python to PATH" durante a instalação

### Passo 2 — Instalar dependências
Abra o CMD na pasta do projeto e execute:
```bash
pip install -r requirements.txt
```

### Passo 3 — Rodar o sistema
```bash
python main.py
```

---

## 📦 GERAR .EXE (para distribuir)

Execute o arquivo `gerar_exe.bat` com duplo clique.  
O .exe será gerado em: `dist/PDV_Padaria_DaLaine.exe`

> Requer PyInstaller: `pip install pyinstaller`

---

## 🧾 MÓDULOS DO SISTEMA

### 🛒 PDV / Caixa
- Abertura e fechamento de caixa com valor inicial
- Busca de produto por código de barras ou nome
- Pesquisa de produto com lista completa
- Tabela de itens com quantidade, preço e desconto
- Modal de pagamento: Dinheiro, Débito, Crédito, PIX
- Cálculo automático de troco
- CPF na nota
- Registro de venda no banco de dados
- Baixa automática de estoque

### 📦 Produtos
- Listagem com filtro de busca
- Cadastro completo: código de barras, NCM, preço, grupo, marca
- Editar e excluir produtos
- Alerta visual de estoque mínimo

### 📊 Estoque
- Entrada, saída e ajuste de estoque
- Alerta de produtos abaixo do mínimo
- Histórico completo de movimentações

### 📈 Relatórios
- Cards de resumo: total vendido, nº de vendas, ticket médio
- Filtro por: Hoje / 7 dias / 30 dias / Tudo
- Tabela completa de vendas com forma de pagamento

### ⚙️ Configurações
- Dados da empresa (CNPJ, IE, endereço)
- Token da API Focus NFe para emissão de NFC-e
- Ambiente: Homologação / Produção
- Configuração de impressora térmica

---

## 🧾 EMISSÃO DE NFC-e

### Passo 1 — Criar conta Focus NFe
Acesse: https://focusnfe.com.br  
Crie sua conta gratuita (ambiente de homologação é grátis para testes)

### Passo 2 — Obter token
No painel Focus NFe, copie o token da API

### Passo 3 — Configurar no sistema
Em **Configurações → NFC-e**, cole o token e selecione o ambiente

### Passo 4 — Certificado Digital
Compre um certificado A1 (~R$ 150/ano) e configure na Focus NFe

---

## 💾 BANCO DE DADOS

O sistema usa **SQLite** — um arquivo local `banco/padaria.db`.  
- Zero configuração necessária
- Funciona 100% offline
- Backup = copiar o arquivo `padaria.db`

---

## 🖨️ IMPRESSORA TÉRMICA

Para imprimir cupons, instale:
```bash
pip install python-escpos
```
E configure o nome/porta da impressora em **Configurações**.

---

## 📞 PRÓXIMAS VERSÕES PLANEJADAS

- [ ] Impressão de cupom não fiscal
- [ ] Emissão de NFC-e integrada
- [ ] Relatório PDF exportável
- [ ] Cadastro de clientes
- [ ] Integração com balança
- [ ] Backup automático em nuvem
- [ ] Tela de login com usuários

---

Desenvolvido com ❤️ para Padaria Da Laine
