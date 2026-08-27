# 🔄 Pipeline de Dados ETL - Organizador de Contatos

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Cloud-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.2+-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/pytest-passing-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![CI/CD Schedule](https://img.shields.io/badge/GitHub%20Actions-Scheduled%20Daily-2088FF.svg?logo=github-actions&logoColor=white)](https://github.com/features/actions)

Pipeline de Engenharia de Dados ponta a ponta (**ETL**) de nível profissional para ingestão, enriquecimento, limpeza e carga de contatos fictícios originados de API REST pública em um banco de dados relacional **PostgreSQL na nuvem**, com orquestração automatizada via **GitHub Actions**.

---

## 📐 Diagrama de Arquitetura

```mermaid
flowchart TD
    subgraph S["🌐 Origem dos Dados (Source)"]
        API["API REST RandomUser<br/><code>https://randomuser.me/api/?results=50</code>"]
    end

    subgraph P["⚙️ Pipeline ETL Modular (Python 3.11)"]
        direction TB
        E["1. EXTRAÇÃO (Extract)<br/>• <code>requests.Session</code> com Timeout<br/>• Tratamento de Códigos HTTP & Retries"]
        
        T["2. TRANSFORMAÇÃO & DATA QUALITY (Transform)<br/>• Padronização de Nomes (<code>.title()</code>)<br/>• Validação Estrita de E-mails (Regex RFC-5322)<br/>• Sanitização de Telefones (Apenas Dígitos)<br/>• Desduplicação por E-mail Único<br/>• Tipagem ISO de Datas e Coordenadas"]
        
        L["3. CARGA (Load)<br/>• Engine <code>SQLAlchemy 2.0</code> + <code>psycopg2</code><br/>• Batch Ingestion (<code>chunksize=500</code>)<br/>• Normalização de Connection String"]
        
        E --> T --> L
    end

    subgraph D["☁️ Destino em Nuvem (Data Warehouse / Relational DB)"]
        PG[("PostgreSQL Cloud<br/>(Neon / Supabase / AWS RDS)<br/>Tabela: <code>contatos</code>")]
    end

    subgraph O["⏱️ Orquestração & Observabilidade"]
        GHA["GitHub Actions CI/CD<br/>• Cron Diário (12:00 UTC)<br/>• Gatilho Manual (workflow_dispatch)"]
        LOGS["Logs Estruturados & Métricas<br/>• Níveis INFO / WARNING / ERROR<br/>• Tempos de Execução & Contadores"]
    end

    API -->|JSON Payload| E
    L -->|Bulk Insert| PG
    GHA -->|Executa & Monitora| P
    P -.->|Exporta Métricas| LOGS
```

---

## 🛠️ Decisões Técnicas de Engenharia de Dados

### 1. **Modularidade e Separação de Responsabilidades**
- O pipeline foi estruturado em módulos independentes (`extract_contacts`, `transform_contacts`, `load_contacts_to_postgres`), permitindo manutenção facilitada, reutilização de código e testes unitários isolados para cada etapa.

### 2. **Qualidade de Dados (Data Quality) & Sanitização**
- **Nomes e Cidades**: Aplicação de capitalização canônica (`.title()`) e remoção de espaços em branco duplicados (`" ".join(text.split())`).
- **Validação de E-mails**: Filtragem ativa descartando registros com formato inválido por meio de expressão regular em conformidade com o padrão RFC.
- **Sanitização Telefônica**: Extração exclusivamente dos dígitos numéricos, eliminando máscaras, parênteses e traços espúrios para padronização analítica.
- **Desduplicação**: Deduplicação automática de registros com base na chave de negócio `email` (`drop_duplicates(subset=['email'])`).

### 3. **Idempotência e Resiliência na Carga (Load)**
- Suporte a estratégias de carga configuráveis (`append` ou `replace`).
- Compatibilidade automática com múltiplos provedores cloud (ex: correção automática do prefixo legado `postgres://` para o driver moderno `postgresql+psycopg2://` exigido pelo SQLAlchemy 2.0+).
- Inserção em lotes (`chunksize=500`, `method="multi"`) para redução de latência e overhead de rede.

### 4. **Observabilidade e Logs Estruturados**
- Utilização da biblioteca nativa `logging` configurável via variável de ambiente `LOG_LEVEL` (INFO, DEBUG, ERROR), emitindo timestamps UTC, severidade, contadores de registros e tempo gasto por etapa.

### 5. **Testabilidade Rigorosa (Pytest & Mocks)**
- Cobertura de testes unitários para todas as regras de validação e transformação sem depender de rede ou conexões externas ativas (uso de fixtures e `unittest.mock`).

---

## 📂 Estrutura do Projeto

```text
Organizador-de-contatos/
├── .github/
│   └── workflows/
│       └── pipeline_schedule.yml  # Orquestração diária Cron (12:00 UTC) e manual
├── pipeline/
│   ├── __init__.py                # Exportação dos componentes do pipeline
│   └── etl.py                     # Pipeline modular (Extract, Transform, Load)
├── tests/
│   ├── __init__.py
│   └── test_etl.py                # Suíte de testes unitários com pytest
├── .env.example                   # Modelo de variáveis de ambiente
├── .gitignore                     # Proteção de credenciais, logs e caches
├── requirements.txt               # Dependências do projeto
└── README.md                      # Documentação técnica de arquitetura
```

---

## 🚀 Como Executar Localmente

### 1. Pré-requisitos
- **Python 3.10+** instalado
- Acesso a um banco de dados PostgreSQL (ex: instância gratuita no [Neon.tech](https://neon.tech) ou [Supabase](https://supabase.com))

### 2. Clonar e Acessar o Projeto
```bash
cd Organizador-de-contatos
```

### 3. Criar e Ativar o Ambiente Virtual
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 5. Configurar as Variáveis de Ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```
Edite o `.env` e configure a sua connection string real:
```env
DATABASE_URL=postgresql://usuario:senha@ep-exemplo.neon.tech/neondb?sslmode=require
API_RESULTS_COUNT=50
LOG_LEVEL=INFO
DB_TABLE_NAME=contatos
```

### 6. Executar os Testes Unitários
```bash
pytest tests/ -v
```

### 7. Executar o Pipeline ETL
```bash
python pipeline/etl.py
```

---

## 🧪 Schema da Tabela no PostgreSQL (`contatos`)

| Coluna | Tipo de Dado | Descrição |
| :--- | :--- | :--- |
| `uuid` | `VARCHAR` | Identificador único universal do usuário |
| `username` | `VARCHAR` | Nome de usuário |
| `first_name` | `VARCHAR` | Primeiro nome padronizado (`.title()`) |
| `last_name` | `VARCHAR` | Sobrenome padronizado (`.title()`) |
| `full_name` | `VARCHAR` | Nome completo padronizado |
| `gender` | `VARCHAR` | Gênero |
| `email` | `VARCHAR` | E-mail normalizado e validado |
| `is_valid_email` | `BOOLEAN` | Flag de validação do formato do e-mail |
| `phone` | `VARCHAR` | Telefone sanitizado (apenas dígitos) |
| `cell` | `VARCHAR` | Celular sanitizado (apenas dígitos) |
| `address` | `VARCHAR` | Endereço formatado |
| `city` | `VARCHAR` | Cidade padronizada |
| `state` | `VARCHAR` | Estado padronizado |
| `country` | `VARCHAR` | País padronizado |
| `postcode` | `VARCHAR` | Código postal / CEP |
| `latitude` | `FLOAT` | Latitude geográfica |
| `longitude` | `FLOAT` | Longitude geográfica |
| `age` | `INTEGER` | Idade |
| `birth_date` | `TIMESTAMP` | Data de nascimento |
| `registered_date` | `TIMESTAMP` | Data de registro |
| `picture_url` | `VARCHAR` | URL da foto em alta resolução |
| `ingested_at` | `TIMESTAMP` | Timestamp UTC do momento da ingestão |

---

## ☁️ Configuração do CI/CD no GitHub Actions

O workflow [`.github/workflows/pipeline_schedule.yml`](.github/workflows/pipeline_schedule.yml) executa diariamente às **12:00 UTC** e permite execuções manuais.

Para habilitar a conexão com o banco no GitHub Actions:
1. No seu repositório no GitHub, vá em **Settings** > **Secrets and variables** > **Actions**.
2. Clique em **New repository secret**.
3. Nome: `DATABASE_URL`
4. Valor: `postgresql://usuario:senha@seu-host.neon.tech/banco?sslmode=require`
5. Salve o secret.

Para disparar manualmente:
- Acesse a aba **Actions** > selecione **ETL Contacts Pipeline Scheduler** > clique em **Run workflow**.

---

## 👨‍💻 Boas Práticas e Padrões Aplicados
- **Type Hints**: Anotações de tipo estáticas em 100% das funções para clareza e análise estática.
- **Fail-Fast & Resiliência**: Checagem de conectividade de banco (`SELECT 1`) e validação de payloads HTTP antes do processamento pesado.
- **Segurança**: Sem hardcode de credenciais (conformidade com o Twelve-Factor App).
