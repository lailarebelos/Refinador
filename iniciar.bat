@echo off
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ========================================================
echo      Qualtrics Normalizer - Iniciando...
echo ========================================================
echo.
echo   Pasta: %~dp0
echo.

if not exist "venv\Scripts\activate.bat" (
    echo ERRO: Ambiente virtual nao encontrado.
    echo Execute "instalar.bat" primeiro.
    echo.
    pause
    exit /b 1
)

echo   Ativando ambiente virtual...
call "venv\Scripts\activate.bat"

echo   Verificando Streamlit...
where streamlit >nul 2>&1
if errorlevel 1 (
    echo ERRO: Streamlit nao encontrado.
    echo Execute "instalar.bat" novamente.
    echo.
    pause
    exit /b 1
)

echo   Tudo certo. O navegador vai abrir em instantes.
echo   Para encerrar, feche esta janela.
echo.

streamlit run "app.py" --server.headless=true --browser.gatherUsageStats=false

echo.
echo ========================================================
echo   O aplicativo foi encerrado.
echo ========================================================
echo.
pause
