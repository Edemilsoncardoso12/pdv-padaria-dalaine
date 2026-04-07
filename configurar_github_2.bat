@echo off
title Conectando ao GitHub
color 0A
echo.
echo ================================================
echo   Conectando repositorio ao GitHub
echo ================================================
echo.

cd /d C:\pdv_padaria

set /p URL="Cole o link HTTPS do repositorio (ex: https://github.com/usuario/pdv-padaria-dalaine.git): "

git remote add origin %URL%
git branch -M main
git push -u origin main

if errorlevel 1 (
    echo.
    echo ERRO ao conectar! Verifique o link e tente novamente.
    pause & exit /b 1
)

echo.
echo ================================================
echo   GITHUB CONFIGURADO COM SUCESSO!
echo ================================================
echo.
echo   Seu codigo esta em: %URL%
echo.
echo   Para enviar atualizacoes futuras:
echo   Execute: enviar_atualizacao.bat
echo.
pause
