@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo.
echo ========================================================
echo        Qualtrics Normalizer - Instalacao
echo ========================================================
echo.
echo   Pasta: %~dp0
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado.
    echo.
    echo Baixe e instale em: https://www.python.org/downloads/
    echo IMPORTANTE: Marque "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo   %%i encontrado.
echo.

if not exist "venv" (
    echo   Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ERRO: Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
    echo   Ambiente virtual criado.
) else (
    echo   Ambiente virtual ja existe.
)

echo.
echo   Ativando ambiente virtual...
call "venv\Scripts\activate.bat"

echo   Instalando dependencias (pode levar 1-2 minutos)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo   Dependencias instaladas.

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo.
        echo   Arquivo .env criado.
    )
)

echo.
echo ========================================================
echo   Instalacao concluida com sucesso!
echo   Clique duas vezes em "iniciar.bat" para usar.
echo ========================================================
echo.
pause
