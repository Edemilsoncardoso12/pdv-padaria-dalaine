@echo off
title Enviando Atualizacao - PDV Padaria Da Laine
color 0A
echo.
echo ================================================
echo   Enviando atualizacao para o GitHub
echo ================================================
echo.

cd /d C:\pdv_padaria

set /p MSG="Descricao da atualizacao (ex: Correcao na busca de produtos): "

git add .
git commit -m "%MSG%"
git push origin main

if errorlevel 1 (
    echo ERRO ao enviar! Verifique sua conexao.
    pause & exit /b 1
)

echo.
echo ================================================
echo   ATUALIZACAO ENVIADA COM SUCESSO!
echo ================================================
echo.
echo   O PDV da padaria vai baixar automaticamente
echo   na proxima vez que abrir o sistema.
echo.
pause
