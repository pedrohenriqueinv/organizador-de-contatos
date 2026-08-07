#!/usr/bin/env bash

# Script de Inicialização para Linux e macOS
# Organizador de Contatos Corporativos

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================"
echo "⚡ ORGANIZADOR DE CONTATOS CORPORATIVOS"
echo "Pro Edition • Taste UI Design System"
echo "======================================================"
echo ""

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ [ERRO] Python 3 não foi encontrado."
    echo "Por favor, instale o Python 3.10 ou superior para continuar."
    exit 1
fi

# Criar ambiente virtual se não existir
if [ ! -d ".venv" ]; then
    echo "📦 [1/3] Criando ambiente virtual (.venv)..."
    python3 -m venv .venv
fi

# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
echo "🔄 [2/3] Instalando/Verificando dependências..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "✅ [3/3] Ambiente pronto!"
echo ""
echo "Escolha o modo de execução:"
echo "  [1] Interface Web no Navegador (Streamlit)"
echo "  [2] Interface de Texto no Terminal (CLI - Rich)"
echo ""
read -p "Digite a opção [1 ou 2] (padrão: 1): " opcao

if [ "$opcao" == "2" ]; then
    echo "🚀 Iniciando CLI..."
    python organizador_contatos.py
else
    echo "🚀 Iniciando Interface Web em http://localhost:8501 ..."
    streamlit run organizador_contatos.py
fi
