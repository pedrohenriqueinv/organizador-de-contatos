@echo off
cd /d "%~dp0"
title Organizador de Contatos - Taste UI Pro

echo.
echo ======================================================
echo   ORGANIZADOR DE CONTATOS CORPORATIVOS
echo   Pro Edition - Taste UI Design System
echo ======================================================
echo.

:: 1. Verificar Python no sistema
where python >nul 2>&1
if errorlevel 1 goto SEM_PYTHON

:: 2. Criar ambiente virtual se nao existir
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando ambiente virtual isolado...
    python -m venv .venv
)

:: 3. Instalar/Verificar dependencias
echo [2/3] Verificando dependencias...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    set "PY_EXEC=.venv\Scripts\python.exe"
) else (
    python -m pip install --quiet -r requirements.txt
    set "PY_EXEC=python"
)

echo [3/3] Ambiente configurado com sucesso!
echo.
echo ======================================================
echo  Escolha o modo de execucao:
echo.
echo    1 - Interface Web no Navegador
echo    2 - Interface de Texto no Terminal
echo ======================================================
echo.
set /p opcao="Digite a opcao desejada [1 ou 2] e pressione ENTER: "

if "%opcao%"=="2" goto CLI

:WEB
echo.
echo  Iniciando Interface Web no navegador...
echo  Endereco local: http://localhost:8501
echo  Feche esta janela para encerrar.
echo.
"%PY_EXEC%" -m streamlit run organizador_contatos.py
pause
exit /b 0

:CLI
echo.
echo  Iniciando Interface no Terminal...
echo.
"%PY_EXEC%" organizador_contatos.py
pause
exit /b 0

:SEM_PYTHON
echo.
echo [ERRO] O Python nao foi encontrado no seu computador.
echo        Baixe e instale o Python em: https://www.python.org/downloads/
echo        IMPORTANTE: Marque a opcao Add Python to PATH.
echo.
pause
exit /b 1
