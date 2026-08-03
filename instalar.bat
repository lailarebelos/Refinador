@echo off
cd /d "%~dp0"
chcp 65001 >nul
echo.
echo ========================================================
echo        Refinador - Instalacao
echo ========================================================
echo.
echo   Pasta: %~dp0
echo.

echo   [1/4] Verificando pre-requisitos...
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

REM npm e um arquivo .cmd - sem "call" o batch encerra aqui e nao volta.
call npm --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Node.js nao encontrado.
    echo.
    echo Baixe e instale a versao LTS em: https://nodejs.org
    echo Depois feche esta janela e execute "instalar.bat" novamente.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm --version') do echo   npm %%i encontrado.
echo.

echo   [2/4] Preparando ambiente Python...
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

echo   Ativando ambiente virtual...
call "venv\Scripts\activate.bat"

echo   Instalando dependencias Python (pode levar 1-2 minutos)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERRO: Falha ao instalar dependencias Python.
    pause
    exit /b 1
)
echo   Dependencias Python instaladas.
echo.

echo   [3/4] Preparando a interface...
echo.

if not exist "frontend\package.json" goto :sem_frontend

echo   Instalando dependencias da interface (pode levar 1-3 minutos)...
pushd "frontend"
call npm install
REM popd zera o errorlevel - guardar antes de voltar para a pasta anterior.
set "ERRO_NPM=%errorlevel%"
popd
if not "%ERRO_NPM%"=="0" (
    echo.
    echo ERRO: Falha ao instalar dependencias da interface.
    echo.
    echo Verifique sua conexao com a internet e execute "instalar.bat" novamente.
    echo Se voce estiver em rede corporativa, pode ser necessario configurar o
    echo proxy do npm com o time de TI.
    echo.
    pause
    exit /b 1
)
echo   Dependencias da interface instaladas.
goto :fim_frontend

:sem_frontend
echo   AVISO: pasta "frontend" nao encontrada - etapa ignorada.
echo   O programa nao vai abrir sem ela. Baixe o projeto completo novamente.

:fim_frontend
echo.

echo   [4/4] Configuracao final...
echo.

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo   Arquivo .env criado.
    )
)
echo   Concluido.

echo.
echo ========================================================
echo   Instalacao concluida com sucesso!
echo   Clique duas vezes em "iniciar.bat" para usar.
echo ========================================================
echo.
pause
