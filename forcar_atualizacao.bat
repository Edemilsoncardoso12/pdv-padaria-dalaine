@echo off
title Enviando Atualizacao - PDV Padaria Da Laine
color 0A
echo.
echo ================================================
echo   PDV Padaria Da Laine - Enviar Atualizacao
echo ================================================
echo.

cd /d C:\pdv_padaria

REM ── Pede a nova versao ──
set /p VERSAO="Nova versao (ex: 2.2.8): "

REM ── Atualiza versao.json com Python (encoding correto!) ──
echo Atualizando versao.json...
set /p NOTAS="Notas da versao: "
set /p OBRIG="Obrigatoria? (s/n): "
python -c "import json,datetime; obrig='%OBRIG%'.strip().lower()=='s'; dados={'versao':'%VERSAO%','data':datetime.date.today().isoformat(),'notas':'%NOTAS%','obrigatorio':obrig}; open('versao.json','w',encoding='utf-8').write(json.dumps(dados,indent=4,ensure_ascii=False)); print('versao.json atualizado!')"

REM ── Copia versao.json para dist se existir ──
if exist dist\PDV_Padaria_DaLaine\versao.json (
    copy /Y versao.json dist\PDV_Padaria_DaLaine\versao.json >nul
    echo versao.json copiado para dist!
)

REM ── Protege arquivos sensiveis ──
git rm --cached licenca.key >nul 2>&1
git rm --cached banco\padaria.db >nul 2>&1

REM ── Adiciona todos os arquivos de codigo ──
git add telas\*.py
git add utils\*.py
git add fiscal\*.py
git add banco\database.py
git add main.py
git add tema.py
git add versao.json
git add mensagem.json
git add gerar_exe.bat
git add forcar_atualizacao.bat
git add gerar_icone.py
git add requirements.txt

echo.
echo Status:
git status
echo.

REM ── Commit e push ──
git commit --allow-empty -m "v%VERSAO%"
git push origin main

if errorlevel 1 (
    echo.
    echo ERRO ao enviar! Verifique sua conexao.
    pause & exit /b 1
)

echo.
echo ================================================
echo   ENVIADO COM SUCESSO! v%VERSAO%
echo   A padaria atualiza automaticamente!
echo ================================================
echo.
pause
