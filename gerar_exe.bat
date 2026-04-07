@echo off
title Gerando icone e EXE - PDV Padaria Da Laine v2.0
color 0A
echo.
echo ================================================
echo   PDV Padaria Da Laine v2.0
echo   Gerando executavel final...
echo ================================================
echo.

cd /d C:\pdv_padaria

:: Verificar Python
echo [1/5] Verificando Python...
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    pause & exit /b 1
)

:: Instalar dependencias
echo.
echo [2/5] Instalando dependencias...
python -m pip install customtkinter pillow pyinstaller --quiet --upgrade

:: Limpar builds anteriores
echo.
echo [3/5] Limpando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist PDV_Padaria_DaLaine.spec del /q PDV_Padaria_DaLaine.spec
if exist logo.ico del /q logo.ico

:: Criar logo.ico com script Python dedicado
echo.
echo [4/5] Gerando icone...
python gerar_icone.py
if not exist logo.ico (
    echo Aviso: icone nao gerado, continuando sem icone...
)

:: Gerar EXE
echo.
echo [5/5] Gerando EXE (aguarde 5-10 minutos)...
echo.

if exist logo.ico (
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name "PDV_Padaria_DaLaine" ^
        --icon "logo.ico" ^
        --add-data "logo.png;." ^
        --add-data "tema.py;." ^
        --add-data "banco;banco" ^
        --add-data "telas;telas" ^
        --add-data "utils;utils" ^
        --add-data "fiscal;fiscal" ^
        --hidden-import customtkinter ^
        --hidden-import PIL ^
        --hidden-import PIL.Image ^
        --hidden-import sqlite3 ^
        --hidden-import tkinter ^
        --hidden-import tkinter.messagebox ^
        --hidden-import hashlib ^
        --hidden-import json ^
        --hidden-import threading ^
        --hidden-import urllib.request ^
        --hidden-import ssl ^
        --hidden-import base64 ^
        --hidden-import logging ^
        --collect-all customtkinter ^
        --noconfirm ^
        main.py
) else (
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name "PDV_Padaria_DaLaine" ^
        --add-data "logo.png;." ^
        --add-data "tema.py;." ^
        --add-data "banco;banco" ^
        --add-data "telas;telas" ^
        --add-data "utils;utils" ^
        --add-data "fiscal;fiscal" ^
        --hidden-import customtkinter ^
        --hidden-import PIL ^
        --hidden-import PIL.Image ^
        --hidden-import sqlite3 ^
        --hidden-import tkinter ^
        --collect-all customtkinter ^
        --noconfirm ^
        main.py
)

if errorlevel 1 (
    echo.
    echo ERRO ao gerar EXE!
    pause & exit /b 1
)

:: Copiar arquivos
if exist licenca.key copy /y licenca.key dist\licenca.key >nul
if exist logo.ico copy /y logo.ico dist\logo.ico >nul

echo.
echo ================================================
echo   EXE GERADO COM SUCESSO!
echo ================================================
echo   Arquivo: dist\PDV_Padaria_DaLaine.exe
echo   Licenca: dist\licenca.key
echo ================================================
echo.
set /p abrir="Abrir pasta dist\? (S/N): "
if /i "%abrir%"=="S" explorer dist\
pause
