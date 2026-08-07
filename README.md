# ⚡ Organizador de Contatos Corporativos • Taste UI Pro Edition

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![UI CLI](https://img.shields.io/badge/Rich-CLI-green.svg)](https://rich.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](#-licença)

Aplicativo de alta performance desenvolvido em **Python (Streamlit & Rich CLI)** para parsing, organização, filtragem e gestão de contatos corporativos. Apresenta interface moderna no padrão **Taste UI (Deep Midnight Glassmorphic Design)**: estética escura, tipografia refinada (`Plus Jakarta Sans` & `JetBrains Mono`), cartões com iluminação ambiente e busca inteligente por terminação numérica.

---

## ⚡ Instalação Rápida ("Só Baixar e Usar")

O projeto possui **configuração automática em 1 clique**. Não é necessário instalar bibliotecas manualmente.

### 🪟 No Windows:
1. Baixe o código ([Download ZIP](https://github.com/) ou `git clone`).
2. Dê um duplo clique no arquivo **`iniciar.bat`** (menu de escolha) ou **`iniciar_interface_web.bat`** (direto na web).
3. O script criará o ambiente isolado e instalará as dependências automaticamente!

### 🐧 / 🍎 No Linux ou macOS:
1. Abra o terminal na pasta do projeto.
2. Execute o comando:
   ```bash
   chmod +x iniciar.sh && ./iniciar.sh
   ```

---

## ✨ Destaques de Design & Funcionalidades

- **🎨 Design System Deep Midnight Glassmorphism:** Fundo escuro luxuoso com gradiente ambiente dinâmico e cards em vidro fosco (`backdrop-filter: blur(24px)`).
- **📊 KPI Metrics Cards Dinâmicos:** Indicadores em tempo real de Total de Contatos, Concluídos, Pendentes e Empresas Únicas.
- **📞 Busca Inteligente por Terminação:** Pesquisa rápida pelos **últimos dígitos do telefone**, com destaque instantâneo por pílulas neon.
- **🏷️ Status Pills & Formatação:** Tags para CNPJ, e-mails, status (`Concluído` vs `Pendente`) e tipografia mono-espaçada para dados numéricos.
- **🧪 Base de Demonstração em 1-Clique:** Botão integrado para carregar dados fictícios de teste sem precisar de um arquivo `.txt` inicial.
- **📂 Exportação Flexível:** Exporte sua base organizada em formato `.csv`.
- **💻 Suporte Dual-Mode:** Funciona tanto no navegador (Web App com Streamlit) quanto no terminal (CLI interativo com Rich).

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** (Interface Web)
- **Rich** (Interface CLI Terminal)
- **Pandas** (Estruturação e manipulação de dados)
- **Google Fonts** (Plus Jakarta Sans, Inter & JetBrains Mono)

---

## 🔒 Segurança e Boas Práticas (GitHub Ready)

Este repositório está pré-configurado com regras de segurança rigorosas:
- **Proteção por `.gitignore`:** Impede o envio acidental de dados pessoais, planilhas geradas (`.csv`, `.xlsx`), arquivos de variáveis de ambiente (`.env`), chaves e pastas de sistema (`.venv`, `__pycache__`).
- **Dados Fictícios:** O arquivo de amostra localizado em `dados/amostra_contatos.txt` contém apenas dados corporativos de teste totalmente fictícios.

---

## 💻 Execução Manual (Desenvolvedores)

Se preferir rodar os comandos manualmente no seu terminal:

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Executar Interface Web:**
   ```bash
   streamlit run organizador_contatos.py
   ```
   Acesse em: `http://localhost:8501`

3. **Executar Interface CLI (Terminal):**
   ```bash
   python organizador_contatos.py
   ```

---

## 📁 Estrutura do Repositório

```text
Organizador-de-contatos/
├── dados/
│   └── amostra_contatos.txt   # Base de contatos fictícios para testes
├── .gitignore                 # Filtro de segurança para o Git
├── iniciar.bat                # Inicializador automático (Windows Menu)
├── iniciar_interface_web.bat  # Inicializador automático (Windows Web)
├── iniciar.sh                 # Inicializador automático (Linux / macOS)
├── organizador_contatos.py    # Código-fonte principal (Web & CLI)
├── requirements.txt           # Dependências do projeto Python
└── README.md                  # Documentação do projeto
```

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
