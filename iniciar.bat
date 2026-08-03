@echo off
cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ========================================================
echo      Refinador - Iniciando...
echo ========================================================
echo.
echo   Pasta: %~dp0
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERRO: Ambiente virtual nao encontrado ou incompleto.
    echo Execute "instalar.bat" primeiro.
    echo.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo ERRO: Dependencias do frontend nao instaladas.
    echo Execute "npm install" dentro da pasta frontend.
    echo.
    pause
    exit /b 1
)

echo   Iniciando backend (FastAPI, porta 8000)...
start "Refinador - Backend" cmd /k ""%~dp0venv\Scripts\python.exe" -m uvicorn backend.api:app --port 8000"

echo   Iniciando frontend (React/Vite)...
start "Refinador - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo   Tudo certo. Abra o endereco que o Vite mostrar na
echo   janela "Refinador - Frontend" (ex.: http://localhost:5173).
echo   Para encerrar, feche as duas janelas abertas.
echo.
pause
