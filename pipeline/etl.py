"""
Pipeline ETL - Organizador de Contatos Reais (TXT / Arquivos)
=============================================================
Módulo de Engenharia de Dados para extração de contatos reais enviados por
usuários em formato TXT (blocos chave-valor ou tabelas), limpeza, padronização
e carga em banco de dados PostgreSQL na nuvem (Neon).

Arquitetura:
    [Arquivos TXT: dados/*.txt] -> [Pandas Transformation & Data Quality] -> [PostgreSQL Neon Cloud]

Autor: Engenharia de Dados
Data: 2026
"""

from __future__ import annotations

import argparse
import glob
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Carregar variáveis de ambiente a partir do arquivo .env
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DE LOGS ESTRUTURADOS UTF-8
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

# Expressões Regulares para validação e extração
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
RE_EMAIL_IN_TEXT = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
RE_TELEFONE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}")
RE_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")


# ==============================================================================
# ETAPA 1: EXTRAÇÃO DE ARQUIVOS TXT (EXTRACT)
# ==============================================================================
def normalizar_chave(chave: str) -> str:
    """Normaliza o nome do campo retirando acentos e espaços."""
    chave_norm = str(chave).strip().lower()
    chave_norm = unicodedata.normalize("NFKD", chave_norm)
    chave_norm = "".join(c for c in chave_norm if not unicodedata.combining(c))
    return chave_norm


def identificar_campo_chave(rotulo: str) -> str:
    """Mapeia rótulos do TXT para chaves padronizadas do sistema."""
    chave = normalizar_chave(rotulo)
    if chave in {"procurador", "nome", "nome completo", "contato", "cliente", "pessoa"}:
        return "nome_completo"
    if chave in {"empresa", "razao social", "organizacao", "loja", "company"}:
        return "empresa"
    if chave in {"email", "e-mail", "mail"}:
        return "email"
    if chave in {"telefone", "fone", "tel", "celular", "whatsapp", "whats", "numero"}:
        return "telefone"
    if chave in {"cidade", "city", "municipio"}:
        return "cidade"
    if chave in {"pais", "country", "estado", "uf"}:
        return "pais"
    if chave in {"cnpj", "cpf/cnpj", "documento"}:
        return "cnpj"
    if chave in {"capital social"}:
        return "capital_social"
    if chave in {"login", "usuario"}:
        return "login"
    if chave in {"tipo de acesso", "cargo", "funcao"}:
        return "tipo_acesso"
    if chave in {"ultimo acesso"}:
        return "ultimo_acesso"
    if chave in {"id"}:
        return "id_origem"
    return "outros"


def extrair_contatos_de_texto(conteudo_txt: str) -> List[Dict[str, Any]]:
    """
    Analisa o conteúdo textual bruto de um arquivo TXT estruturado em blocos
    ou tabelas e converte em registros de dicionários.

    Suporta:
        - Blocos 'Chave: Valor' com separadores (---, ===, linhas em branco).
        - Subseções (ex: '=== USUÁRIOS E PERFIS ===') mantendo a empresa associada.
        - Linhas tabulares separadas por pipe (|), vírgula ou tabulação.

    Args:
        conteudo_txt (str): String com o conteúdo completo do TXT.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários com os contatos extraídos.
    """
    if not conteudo_txt or not conteudo_txt.strip():
        logger.warning("[EXTRACT] Conteúdo de texto vazio recebido.")
        return []

    linhas = conteudo_txt.strip().splitlines()
    registros: List[Dict[str, Any]] = []

    registro_atual: Dict[str, Any] = {}
    empresa_contexto: str = ""
    cnpj_contexto: str = ""

    def salvar_registro_se_valido(reg: Dict[str, Any]):
        if reg and (reg.get("nome_completo") or reg.get("email") or reg.get("empresa")):
            registros.append(dict(reg))

    for linha in linhas:
        linha_limpa = linha.strip()
        if not linha_limpa:
            continue

        # Separadores de bloco (---, ===, ___, etc.)
        if re.match(r"^[-=_*]{3,}$", linha_limpa):
            salvar_registro_se_valido(registro_atual)
            # Mantém contexto da empresa se for bloco subsequente
            empresa_contexto = registro_atual.get("empresa", empresa_contexto)
            cnpj_contexto = registro_atual.get("cnpj", cnpj_contexto)
            registro_atual = {}
            if empresa_contexto:
                registro_atual["empresa"] = empresa_contexto
            if cnpj_contexto:
                registro_atual["cnpj"] = cnpj_contexto
            continue

        # Subseções de usuários (ex: === USUÁRIOS E PERFIS ===)
        if linha_limpa.startswith("=") and "USUÁRIOS" in linha_limpa.upper():
            salvar_registro_se_valido(registro_atual)
            empresa_contexto = registro_atual.get("empresa", empresa_contexto)
            cnpj_contexto = registro_atual.get("cnpj", cnpj_contexto)
            registro_atual = {}
            if empresa_contexto:
                registro_atual["empresa"] = empresa_contexto
            if cnpj_contexto:
                registro_atual["cnpj"] = cnpj_contexto
            continue

        # Formato Chave: Valor
        if ":" in linha_limpa:
            chave_bruta, valor_bruto = linha_limpa.split(":", 1)
            chave_identificada = identificar_campo_chave(chave_bruta)

            if chave_identificada != "outros":
                # Se encontrar um novo ID ou Empresa num registro que já tem nome/email, fecha o anterior
                if chave_identificada in {"id_origem", "empresa"} and ("nome_completo" in registro_atual or "email" in registro_atual):
                    salvar_registro_se_valido(registro_atual)
                    registro_atual = {}

                valor_limpo = valor_bruto.strip()
                registro_atual[chave_identificada] = valor_limpo

                if chave_identificada == "empresa":
                    empresa_contexto = valor_limpo
                elif chave_identificada == "cnpj":
                    cnpj_contexto = valor_limpo
            continue

        # Formato Tabular com pipes (ex: Carlos | carlos@empresa.com | (11) 9999-9999)
        if "|" in linha_limpa:
            partes = [p.strip() for p in linha_limpa.split("|") if p.strip()]
            if len(partes) >= 2:
                salvar_registro_se_valido(registro_atual)
                novo_reg: Dict[str, Any] = {}
                for parte in partes:
                    if RE_EMAIL_IN_TEXT.search(parte):
                        novo_reg["email"] = RE_EMAIL_IN_TEXT.search(parte).group()
                    elif RE_TELEFONE.search(parte):
                        novo_reg["telefone"] = parte
                    elif RE_CNPJ.search(parte):
                        novo_reg["cnpj"] = parte
                    elif not novo_reg.get("nome_completo"):
                        novo_reg["nome_completo"] = parte
                    elif not novo_reg.get("empresa"):
                        novo_reg["empresa"] = parte
                salvar_registro_se_valido(novo_reg)
                registro_atual = {}

    salvar_registro_se_valido(registro_atual)
    return registros


def extract_contacts(
    file_path: Optional[str] = None,
    api_url: Optional[str] = None,
    results: int = 50,
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    Função principal de Extração (Extract).

    Prioridade de Extração:
        1. Arquivo TXT especificado via 'file_path'.
        2. Arquivos TXT encontrados no diretório 'dados/' (ex: dados/amostra_contatos.txt).
        3. Fallback para API pública se configurado ou se nenhum TXT for encontrado.

    Args:
        file_path (Optional[str]): Caminho para arquivo TXT de contatos reais.
        api_url (Optional[str]): Endpoint alternativo de API.
        results (int): Quantidade de contatos na API caso utilizada.
        timeout (int): Timeout HTTP.

    Returns:
        List[Dict[str, Any]]: Registros brutos extraídos.
    """
    logger.info("[EXTRACT] Iniciando processo de extração de contatos...")

    # 1. Verificar se um arquivo TXT foi passado diretamente
    caminho_arquivo = file_path or os.getenv("INPUT_FILE_PATH")

    if not caminho_arquivo:
        # 2. Procurar arquivos .txt no diretório 'dados/'
        arquivos_txt = glob.glob("dados/*.txt") + glob.glob("*.txt")
        # Filtrar requirements.txt
        arquivos_txt = [f for f in arquivos_txt if not f.endswith("requirements.txt")]
        if arquivos_txt:
            caminho_arquivo = arquivos_txt[0]
            logger.info(f"[EXTRACT] Arquivo TXT detectado automaticamente: '{caminho_arquivo}'")

    # Extrair do arquivo TXT se existir
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        logger.info(f"[EXTRACT] Lendo contatos reais do arquivo: '{caminho_arquivo}'...")
        with open(caminho_arquivo, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()

        dados = extrair_contatos_de_texto(conteudo)
        logger.info(f"[EXTRACT] Sucesso: {len(dados)} contatos extraídos do arquivo TXT.")
        return dados

    # 3. Fallback para API RandomUser se nenhum arquivo for encontrado
    url = api_url or os.getenv("API_BASE_URL", "https://randomuser.me/api/")
    logger.info(f"[EXTRACT] Nenhum arquivo TXT local encontrado. Consultando API de amostra: {url}...")
    try:
        response = requests.get(url, params={"results": results}, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        raw_results = payload.get("results", [])

        # Mapeamento do formato da API para o formato unificado
        dados_unificados: List[Dict[str, Any]] = []
        for item in raw_results:
            name_info = item.get("name", {})
            first = name_info.get("first", "")
            last = name_info.get("last", "")
            loc = item.get("location", {})
            dados_unificados.append({
                "nome_completo": f"{first} {last}".strip(),
                "email": item.get("email", ""),
                "telefone": item.get("phone") or item.get("cell") or "",
                "cidade": loc.get("city", ""),
                "pais": loc.get("country", ""),
                "empresa": loc.get("state", "Empresa Parceira")
            })

        logger.info(f"[EXTRACT] Sucesso: {len(dados_unificados)} contatos extraídos via API.")
        return dados_unificados
    except Exception as e:
        logger.error(f"[EXTRACT] Falha na extração de dados: {e}")
        raise


# ==============================================================================
# ETAPA 2: TRANSFORMAÇÃO E QUALIDADE DE DADOS (TRANSFORM)
# ==============================================================================
def validate_email(email: Optional[str]) -> bool:
    """Valida se uma string é um endereço de e-mail com formato válido."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def clean_phone(phone: Optional[str]) -> str:
    """Limpa caracteres especiais de números telefônicos, mantendo apenas dígitos."""
    if not phone or not isinstance(phone, str):
        return ""
    # Se houver múltiplos telefones separados por |, pega o primeiro válido ou limpa dígitos
    primeiro_telefone = str(phone).split("|")[0].strip()
    digits_only = re.sub(r"\D", "", primeiro_telefone)
    return digits_only


def clean_name(name: Optional[str]) -> str:
    """Padroniza nomes com capitalização correta (.title()) e remoção de espaços extras."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().split()).title()


def transform_contacts(raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Processa, limpa, valida e transforma os dados brutos no esquema de banco de dados.

    Regras de Negócio e Qualidade:
        - Padronização de nomes completos e cidades com .title().
        - Limpeza e extração de dígitos para telefones.
        - Validação e normalização de e-mails em minúsculo.
        - Remoção de duplicatas com base no e-mail único.
        - Timestamp de auditoria para rastreamento de ingestão.

    Args:
        raw_data (List[Dict[str, Any]]): Lista de dicionários extraídos.

    Returns:
        pd.DataFrame: DataFrame estruturado pronto para carga em 'contatos_processados'.
    """
    if not raw_data:
        logger.warning("[TRANSFORM] Dados brutos vazios recebidos para transformação.")
        return pd.DataFrame()

    logger.info(f"[TRANSFORM] Iniciando transformação e limpeza de {len(raw_data)} registros...")
    start_time = time.time()

    processed_rows: List[Dict[str, Any]] = []

    for item in raw_data:
        try:
            nome_completo = clean_name(item.get("nome_completo", ""))
            empresa = clean_name(item.get("empresa", ""))

            # Se não houver nome de pessoa, usa a empresa como nome principal
            if not nome_completo and empresa:
                nome_completo = empresa

            email = str(item.get("email", "")).strip().lower()
            is_valid_email = validate_email(email)

            telefone = clean_phone(item.get("telefone", ""))
            cidade = clean_name(item.get("cidade", "")) or empresa or "São Paulo"
            pais = clean_name(item.get("pais", "")) or "Brasil"

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
            logger.warning(f"[TRANSFORM] Falha ao processar registro: {err}. Registro ignorado.")
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
    """Cria e configura o Engine do SQLAlchemy para o PostgreSQL."""
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
    """Carrega o DataFrame tratado em uma tabela no PostgreSQL na nuvem."""
    if df.empty:
        logger.warning("[LOAD] DataFrame vazio. Nenhuma carga será executada.")
        return 0

    if engine is None:
        engine = get_db_engine()

    logger.info(f"[LOAD] Iniciando carga de {len(df)} registros na tabela '{table_name}' (modo: {if_exists})...")
    start_time = time.time()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.debug("[LOAD] Conexão com o banco PostgreSQL validada com sucesso.")

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
    file_path: Optional[str] = None,
    table_name: Optional[str] = None,
    if_exists: str = "append"
) -> Tuple[bool, int]:
    """Executa o ciclo completo de ETL a partir de arquivo TXT real ou dados de entrada."""
    total_start = time.time()
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO EXECUÇÃO DO PIPELINE ETL DE CONTATOS REAIS")
    logger.info("=" * 60)

    table = table_name or os.getenv("DB_TABLE_NAME", "contatos_processados")

    try:
        # 1. Extração (TXT real ou diretório dados/)
        raw_data = extract_contacts(file_path=file_path)

        # 2. Transformação
        df_clean = transform_contacts(raw_data=raw_data)

        if df_clean.empty:
            logger.warning("Nenhum contato válido transformado para carga.")
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
            f"{loaded_rows} contatos reais inseridos com sucesso na nuvem em {total_elapsed:.2f}s."
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
    parser = argparse.ArgumentParser(description="Pipeline ETL de Contatos Reais")
    parser.add_argument("--file", type=str, default=None, help="Caminho para o arquivo TXT de contatos")
    parser.add_argument("--table", type=str, default=None, help="Nome da tabela de destino no PostgreSQL")
    args = parser.parse_args()

    success, count = run_pipeline(file_path=args.file, table_name=args.table)
    if not success:
        sys.exit(1)
    sys.exit(0)
