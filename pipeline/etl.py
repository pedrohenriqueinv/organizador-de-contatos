"""
Pipeline ETL - Organizador de Contatos
======================================
Módulo modular de Engenharia de Dados para extração, transformação
e carga de contatos fictícios em banco de dados PostgreSQL na nuvem (Neon).

Arquitetura:
    [API REST: RandomUser] -> [Pandas Transformation & Quality] -> [PostgreSQL Neon Cloud (SQLAlchemy)]

Autor: Engenharia de Dados
Data: 2026
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Carregar variáveis de ambiente a partir do arquivo .env
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DE LOGS ESTRUTURADOS
# ==============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

handler = logging.StreamHandler(sys.stdout)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[handler]
)
logger = logging.getLogger("ETL_Pipeline")

# Regex RFC-5322 simplificada para validação estrita de e-mails
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# ==============================================================================
# ETAPA 1: EXTRAÇÃO (EXTRACT)
# ==============================================================================
def extract_contacts(
    api_url: str = "https://randomuser.me/api/",
    results: int = 50,
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    Extrai contatos fictícios da API pública RandomUser.

    Args:
        api_url (str): Endpoint da API. Padrão: 'https://randomuser.me/api/'.
        results (int): Quantidade de registros a serem extraídos. Padrão: 50.
        timeout (int): Tempo limite da requisição HTTP em segundos.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários contendo os registros brutos.

    Raises:
        requests.RequestException: Em caso de falha na requisição HTTP.
        ValueError: Em caso de resposta vazia ou formato inesperado.
    """
    params = {"results": results}
    logger.info(f"[EXTRACT] Iniciando requisição para {api_url} (solicitando {results} registros)...")

    start_time = time.time()
    try:
        response = requests.get(api_url, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()

        results_data: List[Dict[str, Any]] = payload.get("results", [])
        if not results_data:
            raise ValueError("A API retornou uma lista de resultados vazia.")

        elapsed = time.time() - start_time
        logger.info(
            f"[EXTRACT] Sucesso: {len(results_data)} registros extraídos em {elapsed:.2f}s."
        )
        return results_data

    except requests.exceptions.Timeout as e:
        logger.error(f"[EXTRACT] Timeout na requisição HTTP ({timeout}s): {e}")
        raise
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "N/A"
        logger.error(f"[EXTRACT] Erro HTTP retornado pela API: {status} - {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"[EXTRACT] Erro inesperado de conexão na requisição: {e}")
        raise
    except ValueError as e:
        logger.error(f"[EXTRACT] Erro no formato de dados da API: {e}")
        raise


# ==============================================================================
# ETAPA 2: TRANSFORMAÇÃO E QUALIDADE DE DADOS (TRANSFORM)
# ==============================================================================
def validate_email(email: Optional[str]) -> bool:
    """
    Valida se uma string é um endereço de e-mail com formato válido.

    Args:
        email (Optional[str]): Endereço de e-mail a ser verificado.

    Returns:
        bool: True se o e-mail for válido, False caso contrário.
    """
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def clean_phone(phone: Optional[str]) -> str:
    """
    Limpa caracteres especiais de números telefônicos, mantendo apenas dígitos.

    Args:
        phone (Optional[str]): String bruta do telefone.

    Returns:
        str: Sequência numérica limpa ou string vazia se nulo/inválido.
    """
    if not phone or not isinstance(phone, str):
        return ""
    # Remove tudo que não for dígito
    digits_only = re.sub(r"\D", "", phone)
    return digits_only


def clean_name(name: Optional[str]) -> str:
    """
    Padroniza nomes com capitalização correta (.title()) e remoção de espaços extras.

    Args:
        name (Optional[str]): Nome bruto.

    Returns:
        str: Nome padronizado em formato Title Case.
    """
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().split()).title()


def transform_contacts(raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa, limpa, valida e transforma os dados brutos no esquema da tabela contatos_processados.

    Regras de Negócio e Qualidade:
        - Padronização de nomes completos e cidades com .title().
        - Limpeza e extração de dígitos para telefones.
        - Validação e normalização de e-mails em minúsculo.
        - Remoção de duplicatas com base no e-mail único.
        - Timestamp de auditoria para rastreamento de ingestão.

    Args:
        raw_data (List[Dict[str, Any]]): Lista de dicionários extraídos da API.

    Returns:
        pd.DataFrame: DataFrame estruturado pronto para carga em 'contatos_processados'.
    """
    if not raw_data:
        logger.warning("[TRANSFORM] Dados brutos vazios recebidos para transformação.")
        return pd.DataFrame()

    logger.info(f"[TRANSFORM] Iniciando transformação de {len(raw_data)} registros...")
    start_time = time.time()

    processed_rows: List[Dict[str, Any]] = []

    for item in raw_data:
        try:
            name_info = item.get("name", {})
            first_name = clean_name(name_info.get("first", ""))
            last_name = clean_name(name_info.get("last", ""))
            nome_completo = f"{first_name} {last_name}".strip()

            location = item.get("location", {})
            cidade = clean_name(location.get("city", ""))
            pais = clean_name(location.get("country", ""))

            email = str(item.get("email", "")).strip().lower()
            is_valid_email = validate_email(email)

            # Prioriza telefone celular ou fixo
            raw_phone = item.get("phone") or item.get("cell") or ""
            telefone = clean_phone(raw_phone)

            row = {
                "nome_completo": nome_completo,
                "email": email,
                "telefone": telefone,
                "cidade": cidade,
                "pais": pais,
                "is_valid_email": is_valid_email,
                "data_ingestao": datetime.now(timezone.utc)
            }
            processed_rows.append(row)

        except Exception as err:
            logger.warning(f"[TRANSFORM] Falha ao processar registro individual: {err}. Registro ignorado.")
            continue

    df = pd.DataFrame(processed_rows)

    if df.empty:
        logger.warning("[TRANSFORM] Nenhum registro válido após o parsing.")
        return df

    # Data Quality: Filtrar apenas e-mails válidos e não vazios
    initial_count = len(df)
    df = df[df["is_valid_email"] == True].copy()
    invalid_email_count = initial_count - len(df)
    if invalid_email_count > 0:
        logger.warning(f"[TRANSFORM] {invalid_email_count} registros descartados por e-mail inválido.")

    # Remove a coluna temporária de controle de qualidade
    df = df.drop(columns=["is_valid_email"])

    # Data Quality: Remoção de duplicatas com base no e-mail
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["email"], keep="first")
    duplicates_removed = before_dedup - len(df)
    if duplicates_removed > 0:
        logger.info(f"[TRANSFORM] {duplicates_removed} registros duplicados removidos com base no e-mail.")

    elapsed = time.time() - start_time
    logger.info(
        f"[TRANSFORM] Concluído: {len(df)} registros processados e limpos com sucesso em {elapsed:.2f}s."
    )
    return df


# ==============================================================================
# ETAPA 3: CARGA (LOAD)
# ==============================================================================
def get_db_engine(database_url: Optional[str] = None) -> Engine:
    """
    Cria e configura o Engine do SQLAlchemy para conexão com o PostgreSQL.

    Trata automaticamente divergências de prefixo comuns em serviços cloud
    (ex: 'postgres://' -> 'postgresql+psycopg2://').

    Args:
        database_url (Optional[str]): Connection string do PostgreSQL.
            Se omitido, busca da variável de ambiente DATABASE_URL.

    Returns:
        Engine: Instância configurada do SQLAlchemy Engine.

    Raises:
        ValueError: Se a connection string não estiver configurada.
        SQLAlchemyError: Se houver falha na inicialização do Engine.
    """
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "Variável de ambiente 'DATABASE_URL' não encontrada. "
            "Defina-a no arquivo .env ou nas variáveis do sistema."
        )

    # Normalização de URL para compatibilidade com SQLAlchemy 2.0 e psycopg2
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    logger.debug("[LOAD] Criando engine do SQLAlchemy...")
    try:
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=1800,
            echo=False
        )
        return engine
    except Exception as e:
        logger.error(f"[LOAD] Erro ao instanciar engine SQLAlchemy: {e}")
        raise SQLAlchemyError(f"Falha na criação do engine de banco de dados: {e}") from e


def load_contacts_to_postgres(
    df: pd.DataFrame,
    table_name: str = "contatos_processados",
    engine: Optional[Engine] = None,
    if_exists: str = "append"
) -> int:
    """
    Carrega o DataFrame tratado em uma tabela no PostgreSQL na nuvem.

    Args:
        df (pd.DataFrame): DataFrame estruturado gerado na etapa de transformação.
        table_name (str): Nome da tabela de destino. Padrão: 'contatos_processados'.
        engine (Optional[Engine]): Engine do SQLAlchemy. Se None, cria via get_db_engine().
        if_exists (str): Estratégia de inserção ('append', 'replace', 'fail'). Padrão: 'append'.

    Returns:
        int: Quantidade de linhas inseridas com sucesso.

    Raises:
        ValueError: Se o DataFrame estiver vazio.
        SQLAlchemyError: Se ocorrer erro durante a execução da carga.
    """
    if df.empty:
        logger.warning("[LOAD] DataFrame vazio. Nenhuma carga será executada.")
        return 0

    if engine is None:
        engine = get_db_engine()

    logger.info(f"[LOAD] Iniciando carga de {len(df)} registros na tabela '{table_name}' (modo: {if_exists})...")
    start_time = time.time()

    try:
        # Testa a conectividade com o banco antes de iniciar o upload
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.debug("[LOAD] Conexão com o banco PostgreSQL validada com sucesso.")

        # Inserção em lotes (batch) otimizada
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False,
            chunksize=500,
            method="multi"
        )

        elapsed = time.time() - start_time
        logger.info(
            f"[LOAD] Sucesso: {len(df)} contatos inseridos com sucesso na tabela '{table_name}' em {elapsed:.2f}s!"
        )
        return len(df)

    except SQLAlchemyError as err:
        logger.error(f"[LOAD] Erro de banco de dados durante a carga: {err}")
        raise
    except Exception as err:
        logger.error(f"[LOAD] Erro inesperado durante a carga: {err}")
        raise


# ==============================================================================
# ORQUESTRADOR PRINCIPAL (RUN PIPELINE)
# ==============================================================================
def run_pipeline(
    results_count: Optional[int] = None,
    table_name: Optional[str] = None,
    if_exists: str = "append",
    api_url: Optional[str] = None
) -> Tuple[bool, int]:
    """
    Executa o ciclo completo de ETL: Extração -> Transformação -> Carga.

    Args:
        results_count (Optional[int]): Total de contatos a extrair.
        table_name (Optional[str]): Nome da tabela de destino.
        if_exists (str): Estratégia de inserção no banco ('append' ou 'replace').
        api_url (Optional[str]): URL da API de contatos.

    Returns:
        Tuple[bool, int]: (Sucesso da operação, total de linhas carregadas).
    """
    total_start = time.time()
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO EXECUÇÃO DO PIPELINE ETL DE CONTATOS")
    logger.info("=" * 60)

    # Obter parâmetros de ambiente se não fornecidos
    results = results_count or int(os.getenv("API_RESULTS_COUNT", "50"))
    table = table_name or os.getenv("DB_TABLE_NAME", "contatos_processados")
    url = api_url or os.getenv("API_BASE_URL", "https://randomuser.me/api/")

    try:
        # 1. Extração
        raw_data = extract_contacts(api_url=url, results=results)

        # 2. Transformação
        df_clean = transform_contacts(raw_data=raw_data)

        if df_clean.empty:
            logger.warning("Nenhum registro transformado para carga.")
            return True, 0

        # 3. Carga
        loaded_rows = load_contacts_to_postgres(
            df=df_clean,
            table_name=table,
            if_exists=if_exists
        )

        total_elapsed = time.time() - total_start
        logger.info("=" * 60)
        logger.info(
            f"✅ PIPELINE CONCLUÍDO COM SUCESSO! "
            f"{loaded_rows} contatos inseridos com sucesso na nuvem em {total_elapsed:.2f}s."
        )
        logger.info("=" * 60)
        return True, loaded_rows

    except Exception as exc:
        total_elapsed = time.time() - total_start
        logger.error("=" * 60)
        logger.error(f"❌ FALHA NA EXECUÇÃO DO PIPELINE após {total_elapsed:.2f}s: {exc}")
        logger.error("=" * 60)
        return False, 0


if __name__ == "__main__":
    success, count = run_pipeline()
    if not success:
        sys.exit(1)
    sys.exit(0)
