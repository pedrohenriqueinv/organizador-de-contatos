@echo off
cd /d "%~dp0"
title Organizador de Contatos - Interface Web

echo.
echo ======================================================
echo   ORGANIZADOR DE CONTATOS CORPORATIVOS
echo   Interface Web Pro - Streamlit UI
echo ======================================================
echo.

:: 1. Verificar Python
where python >nul 2>&1
if errorlevel 1 goto SEM_PYTHON

:: 2. Criar .venv se nao existir
if not exist ".venv\Scripts\python.exe" (
    echo [1/2] Criando ambiente virtual...
    python -m venv .venv
)

:: 3. Instalar dependencias
echo [2/2] Verificando dependencias...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    set "PY_EXEC=.venv\Scripts\python.exe"
) else (
    python -m pip install --quiet -r requirements.txt
    set "PY_EXEC=python"
)

echo.
echo  Abrindo a interface web no navegador...
echo  Endereco local: http://localhost:8501
echo  Pressione Ctrl+C nesta janela para encerrar.
echo.

"%PY_EXEC%" -m streamlit run organizador_contatos.py
pause
exit /b 0

:SEM_PYTHON
echo.
echo [ERRO] O Python nao foi encontrado no seu computador.
echo        Baixe e instale o Python em: https://www.python.org/downloads/
echo        Lembre-se de marcar Add Python to PATH.
echo.
pause
exit /b 1
