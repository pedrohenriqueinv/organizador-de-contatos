@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title Organizador de Contatos • Taste UI Pro

echo.
echo  ======================================================
echo   ⚡ ORGANIZADOR DE CONTATOS CORPORATIVOS
echo   Pro Edition • Taste UI Design System
echo  ======================================================
echo.

:: 1. Verificar se o Python está instalado no sistema
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] O Python não foi encontrado no seu computador.
    echo         Por favor, baixe e instale o Python (3.10 ou superior) em:
    echo         https://www.python.org/downloads/
    echo.
    echo         IMPORTANTE: Marque a opção "Add Python to PATH" durante a instalação.
    echo.
    pause
    exit /b 1
)

:: 2. Criar ambiente virtual (.venv) se não existir
if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] Criando ambiente virtual isolado (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  [AVISO] Não foi possível criar o .venv, usando Python global...
    )
)

:: 3. Instalar/Verificar dependências
echo  [2/3] Verificando dependências (pandas, rich, streamlit)...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
    set PY_EXEC=.venv\Scripts\python.exe
) else (
    python -m pip install --quiet -r requirements.txt
    set PY_EXEC=python
)

echo  [3/3] Ambiente configurado com sucesso!
echo.
echo  ======================================================
echo   Escolha o modo de execução:
echo.
echo     [1] Interface Web no Navegador (Recomendado - Streamlit)
echo     [2] Interface de Texto no Terminal (CLI - Rich)
echo.
set /p opcao="Digite a opção desejada [1 ou 2] (padrão: 1): "

if "%opcao%"=="2" goto cli

:web
echo.
echo  🚀 Iniciando Interface Web no navegador...
echo  📍 Endereço: http://localhost:8501
echo  💡 Feche esta janela ou pressione Ctrl+C para encerrar.
echo.
%PY_EXEC% -m streamlit run organizador_contatos.py
pause
exit /b 0

:cli
echo.
echo  🚀 Iniciando Interface de Terminal (CLI)...
echo.
%PY_EXEC% organizador_contatos.py
pause
exit /b 0
