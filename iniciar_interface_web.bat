@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title Organizador de Contatos • Interface Web

echo.
echo  ======================================================
echo   ⚡ ORGANIZADOR DE CONTATOS CORPORATIVOS
echo   Interface Web Pro • Streamlit UI
echo  ======================================================
echo.

:: Verificar se o Python está instalado
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] O Python não foi encontrado no seu computador.
    echo         Baixe e instale o Python (3.10+) em: https://www.python.org/downloads/
    echo         Lembre-se de marcar "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: Criar .venv se não existir
if not exist ".venv\Scripts\python.exe" (
    echo  [1/2] Criando ambiente virtual (.venv)...
    python -m venv .venv
)

:: Instalar dependências se necessário
echo  [2/2] Verificando dependências...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    set PY_EXEC=.venv\Scripts\python.exe
) else (
    python -m pip install --quiet -r requirements.txt
    set PY_EXEC=python
)

echo.
echo  🚀 Abrindo a interface web no navegador...
echo  📍 Endereço local: http://localhost:8501
echo  💡 Pressione Ctrl+C nesta janela para encerrar o servidor.
echo.

%PY_EXEC% -m streamlit run organizador_contatos.py
pause
exit /b 0
