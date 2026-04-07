@echo off
title Configurando GitHub - PDV Padaria Da Laine
color 0A
echo.
echo ================================================
echo   Configurando GitHub para atualizacao remota
echo ================================================
echo.

cd /d C:\pdv_padaria

:: Verificar Git
git --version
if errorlevel 1 (
    echo ERRO: Git nao encontrado!
    echo Instale em: git-scm.com/download/win
    pause & exit /b 1
)

:: Configurar identidade
echo.
echo [1/4] Configurando identidade Git...
set /p NOME="Seu nome completo: "
set /p EMAIL="Seu email do GitHub: "
git config --global user.name "%NOME%"
git config --global user.email "%EMAIL%"
echo OK!

:: Inicializar repositorio
echo.
echo [2/4] Inicializando repositorio...
if not exist .git (
    git init
    echo OK!
) else (
    echo Repositorio ja existe!
)

:: Criar .gitignore
echo.
echo [3/4] Criando .gitignore...
(
echo __pycache__/
echo *.pyc
echo *.pyo
echo build/
echo dist/
echo *.spec
echo banco/padaria.db
echo banco/.config_seguro
echo banco/.dispositivos
echo banco/fila_nfce.json
echo licenca.key
echo logs/
echo cupons/
echo backups/
echo *.ico
echo .env
) > .gitignore
echo OK!

:: Primeiro commit
echo.
echo [4/4] Fazendo primeiro commit...
git add .
git commit -m "PDV Padaria Da Laine v2.0 - versao inicial"
echo OK!

echo.
echo ================================================
echo   REPOSITORIO LOCAL CONFIGURADO!
echo ================================================
echo.
echo   Proximo passo:
echo   1. Acesse github.com
echo   2. Clique em "New repository"
echo   3. Nome: pdv-padaria-dalaine
echo   4. Privado (Private)
echo   5. NAO marque nenhuma opcao extra
echo   6. Clique "Create repository"
echo   7. Copie o link HTTPS do repositorio
echo   8. Execute: configurar_github_2.bat
echo.
pause
