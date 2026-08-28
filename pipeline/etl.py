"""
Pipeline ETL - Organizador de Contatos Corporativos (com IA Fallback)
====================================================================
Módulo de Engenharia de Dados que preserva integralmente as regras originais de
padronização de listas em formato TXT (blocos chave-valor, empresas, perfis de
procuradores, telefones compostos, e-mails, CNPJ e outros campos), aplicando
limpeza rigorosa, suporte a Fallback com Inteligência Artificial (Google Gemini)
para textos caóticos e carga idempotente (Upsert) em banco PostgreSQL na nuvem (Neon).

Colunas Padronizadas Originais:
    ["ID", "Empresa", "CNPJ", "Capital Social", "Procurador/Nome", "Login",
     "Tipo de Acesso", "Último Acesso", "Telefones", "E-mail", "Outros", "Status"]

Segurança:
    Credenciais e chaves de API são lidas exclusivamente de variáveis de ambiente.

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
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Carregar variáveis de ambiente
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

# ==============================================================================
# REGRAS E SINÔNIMOS DO PARSER ORIGINAL (PRESERVAÇÃO INTEGRAL)
# ==============================================================================
SINONIMOS = {
    "Nome": ["nome", "contato", "cliente", "pessoa", "nome completo"],
    "Empresa": ["empresa", "organizacao", "organização", "company", "loja", "razao social", "razão social"],
    "CNPJ": ["cnpj", "cpf/cnpj", "documento", "doc"],
    "Funcao": ["funcao", "função", "cargo", "profissao", "profissão", "area", "área", "setor", "departamento"],
    "Telefone": ["telefone", "fone", "tel", "celular", "whatsapp", "whats", "numero", "número", "num", "cel"],
    "Email": ["email", "e-mail", "mail"],
}

COLUNAS_FINAIS = [
    "ID",
    "Empresa",
    "CNPJ",
    "Capital Social",
    "Procurador/Nome",
    "Login",
    "Tipo de Acesso",
    "Último Acesso",
    "Telefones",
    "E-mail",
    "Outros",
    "Status"
]
CAMPOS_PADRONIZADOS = [c for c in COLUNAS_FINAIS if c not in ("Outros", "Status")]

RE_EMAIL = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
RE_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
RE_TELEFONE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}")
RE_SEPARADORES = re.compile(r"[;,|\t]+")


def normalizar_texto(texto: str) -> str:
    """Remove acentos, espaços extras e coloca em minúsculo."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def identificar_campo(chave: str) -> str:
    """Recebe um rótulo e devolve a coluna padronizada original."""
    chave_norm = normalizar_texto(chave)
    if chave_norm == "cpf":
        return "Outros"
    if chave_norm in {"id"}:
        return "ID"
    if chave_norm in {"empresa", "razao social", "razão social"}:
        return "Empresa"
    if chave_norm in {"cnpj", "cpf/cnpj"}:
        return "CNPJ"
    if chave_norm in {"capital social"}:
        return "Capital Social"
    if chave_norm in {"procurador", "nome", "nome completo", "nome do procurador"}:
        return "Procurador/Nome"
    if chave_norm in {"login"}:
        return "Login"
    if chave_norm in {"tipo de acesso"}:
        return "Tipo de Acesso"
    if chave_norm in {"ultimo acesso", "último acesso"}:
        return "Último Acesso"
    if chave_norm in {"telefone", "fone", "tel", "celular", "whatsapp", "whats", "numero", "número", "num", "cel"}:
        return "Telefones"
    if chave_norm in {"email", "e-mail", "mail"}:
        return "E-mail"
    return "Outros"


def registro_vazio() -> Dict[str, Any]:
    """Retorna a estrutura de um registro vazio de acordo com COLUNAS_FINAIS."""
    return {campo: (False if campo == "Status" else "") for campo in COLUNAS_FINAIS}


def registro_tem_dados(registro: Dict[str, Any]) -> bool:
    """Verifica se há algum campo padronizado preenchido."""
    return any(bool(str(registro.get(c, "")).strip()) for c in CAMPOS_PADRONIZADOS)


def limpar_valor_campo(campo: str, valor: str) -> str:
    """Normaliza valores mantendo o texto estritamente padronizado."""
    valor = str(valor).strip()
    if not valor:
        return ""
    valor = re.sub(r"\s+", " ", valor)

    if campo in {"Telefones", "Telefone"}:
        telefones = []
        for parte in re.split(r"\s*(?:\||/)\s*", valor):
            parte = parte.strip()
            if not parte:
                continue
            if ":" in parte:
                parte = parte.split(":", 1)[1].strip()
            match = RE_TELEFONE.search(parte)
            if match:
                telefones.append(match.group().strip())
            elif re.search(r"\d", parte):
                telefones.append(parte)
        return " | ".join(dict.fromkeys(telefones))

    if campo in {"E-mail", "Email"}:
        emails = [m.group().strip() for m in RE_EMAIL.finditer(valor)]
        return " | ".join(dict.fromkeys(emails)) if emails else valor

    if campo == "CNPJ":
        cnps = [m.group().strip() for m in RE_CNPJ.finditer(valor)]
        return " | ".join(dict.fromkeys(cnps)) if cnps else valor

    valor = re.sub(r"\s*[-–:]\s*", " ", valor).strip(" ,;|-")
    return re.sub(r"\s{2,}", " ", valor).strip()


def adicionar_valor(registro: Dict[str, Any], campo: str, valor: str) -> None:
    """Adiciona um valor em um campo sem duplicar informações."""
    limpo = limpar_valor_campo(campo, valor)
    if not limpo:
        return

    atual = str(registro.get(campo, "")).strip()
    if not atual:
        registro[campo] = limpo
        return

    valores = [v.strip() for v in atual.split("|") if v.strip()]
    novos = [v.strip() for v in limpo.split("|") if v.strip()]
    for item in novos:
        if item not in valores:
            valores.append(item)
    registro[campo] = " | ".join(valores)


def garantir_tipos_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante a consistência de tipos e ordenação estrita das colunas."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_FINAIS)
    df_out = df.copy()
    for col in COLUNAS_FINAIS:
        if col not in df_out.columns:
            df_out[col] = False if col == "Status" else ""
        elif col == "Status":
            df_out[col] = df_out[col].astype(bool)
        else:
            df_out[col] = df_out[col].fillna("").astype(str)
            df_out[col] = df_out[col].apply(
                lambda x: str(int(float(x))) if (isinstance(x, str) and x.endswith('.0') and x[:-2].isdigit()) else str(x)
            )
            df_out[col] = df_out[col].replace("nan", "").replace("None", "")
    return df_out[COLUNAS_FINAIS]


# ==============================================================================
# ETAPA 1: EXTRAÇÃO E PARSER RIGOROSO DE TXT (EXTRACT)
# ==============================================================================
def parse_txt(conteudo: str) -> pd.DataFrame:
    """
    Parser oficial para relatórios em blocos com empresas e perfis de procuradores.
    Segue estritamente as regras originais de agregação por bloco e herança de dados.
    """
    conteudo = conteudo.replace("\r\n", "\n").replace("\r", "\n")
    blocos = re.split(r"\n(?:={10,}|-{10,})\s*\n", conteudo)
    contatos: List[Dict[str, Any]] = []

    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue

        linhas = [linha.strip() for linha in bloco.splitlines() if linha.strip()]
        registro_base = registro_vazio()
        registros: List[Dict[str, Any]] = []
        perfil_atual: Optional[Dict[str, Any]] = None
        dentro_perfis = False

        for linha in linhas:
            if not linha or linha.startswith("#"):
                continue
            if linha.startswith("=== USUÁRIOS E PERFIS ==="):
                dentro_perfis = True
                continue
            if linha.startswith("---"):
                if perfil_atual and any(perfil_atual.get(chave, "") for chave in ["Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"]):
                    registros.append(perfil_atual)
                perfil_atual = registro_vazio()
                continue
            if ":" not in linha:
                continue

            chave, valor = [parte.strip() for parte in linha.split(":", 1)]
            if not valor:
                continue

            if not dentro_perfis:
                campo = identificar_campo(chave)
                if campo in CAMPOS_PADRONIZADOS:
                    adicionar_valor(registro_base, campo, valor)
                else:
                    registro_base["Outros"] = f"{registro_base['Outros']} | {f'{chave}: {valor}'}".strip(" |")
            else:
                if perfil_atual is None:
                    perfil_atual = registro_vazio()
                campo = identificar_campo(chave)
                if campo in {"Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"}:
                    perfil_atual[campo] = valor
                elif campo in {"Telefones", "E-mail"}:
                    adicionar_valor(perfil_atual, campo, valor)
                else:
                    perfil_atual["Outros"] = f"{perfil_atual['Outros']} | {f'{chave}: {valor}'}".strip(" |")

        if perfil_atual and any(perfil_atual.get(chave, "") for chave in ["Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"]):
            registros.append(perfil_atual)

        if registros:
            for perfil in registros:
                registro = registro_vazio()
                for campo in ["ID", "Empresa", "CNPJ", "Capital Social", "Telefones", "E-mail"]:
                    registro[campo] = registro_base[campo]
                registro["Procurador/Nome"] = perfil.get("Procurador/Nome", "")
                registro["Login"] = perfil.get("Login", "")
                registro["Tipo de Acesso"] = perfil.get("Tipo de Acesso", "")
                registro["Último Acesso"] = perfil.get("Último Acesso", "")
                if perfil.get("Telefones"):
                    adicionar_valor(registro, "Telefones", perfil["Telefones"])
                if perfil.get("E-mail"):
                    adicionar_valor(registro, "E-mail", perfil["E-mail"])
                registro["Outros"] = " | ".join([v for v in [registro_base.get("Outros"), perfil.get("Outros")] if v])
                registro["Status"] = False
                contatos.append(registro)
        else:
            registro_base["Outros"] = registro_base["Outros"].strip(" |")
            registro_base["Status"] = False
            if registro_tem_dados(registro_base):
                contatos.append(registro_base)

    df_result = pd.DataFrame(contatos, columns=COLUNAS_FINAIS)
    return garantir_tipos_colunas(df_result)


def extract_contacts(file_path: Optional[str] = None) -> str:
    """Extrai o conteúdo de texto do arquivo especificado ou da pasta dados/."""
    caminho = file_path or os.getenv("INPUT_FILE_PATH")
    if not caminho:
        arquivos = glob.glob("dados/*.txt") + glob.glob("*.txt")
        arquivos = [f for f in arquivos if not f.endswith("requirements.txt")]
        if arquivos:
            caminho = arquivos[0]

    if not caminho or not os.path.exists(caminho):
        raise FileNotFoundError(
            f"Nenhum arquivo de contatos TXT encontrado. "
            f"Coloque seu arquivo em 'dados/*.txt' ou especifique via --file."
        )

    logger.info(f"[EXTRACT] Lendo arquivo TXT: '{caminho}'...")
    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        conteudo = f.read()

    logger.info(f"[EXTRACT] Leitura concluída: {len(conteudo.splitlines())} linhas carregadas.")
    return conteudo


# ==============================================================================
# ETAPA 2: TRANSFORMAÇÃO E QUALIDADE (TRANSFORM COM IA FALLBACK)
# ==============================================================================
def chave_deduplicacao(row: pd.Series) -> Optional[str]:
    """Gera chave única para deduplicação com base em telefones ou nomes."""
    texto_telefones = str(row.get("Telefones", ""))
    digitos = re.sub(r"\D", "", texto_telefones)
    if digitos:
        return f"tel:{digitos[:11]}"
    nome_norm = normalizar_texto(row.get("Procurador/Nome", ""))
    empresa_norm = normalizar_texto(row.get("Empresa", ""))
    if nome_norm:
        return f"nome:{nome_norm}:{empresa_norm}"
    return None


def transform_contacts(conteudo_txt: str) -> pd.DataFrame:
    """
    Executa o parser tradicional com fallback inteligente de IA para anomalias.

    Fluxo Híbrido:
        1. Tenta o parser determinístico tradicional (0.01s).
        2. Se o texto for caótico ou não gerar contatos válidos, aciona o Fallback de IA.
        3. Aplica deduplicação e garantia de tipos das 12 colunas.
    """
    logger.info("[TRANSFORM] Iniciando parsing e padronização das listas de contatos...")
    start_time = time.time()

    df = parse_txt(conteudo_txt)

    # Verificação de Resiliência: Se o parser tradicional não retornou registros
    # mas o conteúdo tem texto significativo, aciona o Fallback de IA
    if df.empty and conteudo_txt and len(conteudo_txt.strip()) > 20:
        logger.info("[TRANSFORM] Parser tradicional não identificou contatos estruturados. Acionando IA Fallback...")
        try:
            try:
                from pipeline.ai_fallback import extrair_contatos_com_ia
            except ImportError:
                from ai_fallback import extrair_contatos_com_ia

            contatos_ia = extrair_contatos_com_ia(conteudo_txt)
            if contatos_ia:
                df = pd.DataFrame(contatos_ia, columns=COLUNAS_FINAIS)
                df = garantir_tipos_colunas(df)
        except Exception as err:
            logger.warning(f"[TRANSFORM] Falha no fallback de IA: {err}")

    if df.empty:
        logger.warning("[TRANSFORM] Nenhum contato identificado no texto.")
        return df

    logger.info(f"[TRANSFORM] {len(df)} registros estruturados obtidos.")

    # Deduplicação inteligente
    df["_chave"] = df.apply(chave_deduplicacao, axis=1)
    before_count = len(df)
    df = df.drop_duplicates(subset=["_chave"], keep="first").drop(columns=["_chave"])
    removed_duplicates = before_count - len(df)
    if removed_duplicates > 0:
        logger.info(f"[TRANSFORM] {removed_duplicates} registros duplicados removidos.")

    elapsed = time.time() - start_time
    logger.info(f"[TRANSFORM] Padronização concluída com sucesso em {elapsed:.2f}s.")
    return df


# ==============================================================================
# ETAPA 3: CARGA NO POSTGRESQL (LOAD IDEMPOTENTE)
# ==============================================================================
def get_db_engine(database_url: Optional[str] = None) -> Engine:
    """Cria e configura o Engine do SQLAlchemy para o PostgreSQL."""
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL não configurada no ambiente ou .env.")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

    try:
        return create_engine(url, pool_pre_ping=True, pool_recycle=1800, echo=False)
    except Exception as e:
        logger.error(f"[LOAD] Erro ao instanciar Engine SQLAlchemy: {e}")
        raise SQLAlchemyError(f"Falha na conexão do banco: {e}") from e


def load_contacts_to_postgres(
    df: pd.DataFrame,
    table_name: str = "contatos_processados",
    engine: Optional[Engine] = None,
    if_exists: str = "append"
) -> int:
    """
    Carrega os contatos padronizados no PostgreSQL Neon de forma idempotente (Upsert).
    Evita erros de chave duplicada atualizando registros já existentes.
    """
    if df.empty:
        logger.warning("[LOAD] DataFrame vazio. Nenhuma carga realizada.")
        return 0

    if engine is None:
        engine = get_db_engine()

    logger.info(f"[LOAD] Iniciando carga de {len(df)} contatos na tabela '{table_name}'...")
    start_time = time.time()

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Preparar DataFrame para a tabela contatos_processados
        df_db = pd.DataFrame()
        df_db["nome_completo"] = df["Procurador/Nome"].where(df["Procurador/Nome"] != "", df["Empresa"])
        df_db["email"] = df["E-mail"].apply(lambda x: str(x).split("|")[0].strip() if x else "")
        df_db["telefone"] = df["Telefones"].apply(lambda x: re.sub(r"\D", "", str(x).split("|")[0]) if x else "")
        df_db["cidade"] = df["Empresa"]
        df_db["pais"] = df["CNPJ"]
        df_db["data_ingestao"] = datetime.now(timezone.utc)

        # Carga idempotente via Upsert (ON CONFLICT DO UPDATE)
        loaded_count = 0
        with engine.begin() as conn:
            for _, row in df_db.iterrows():
                email_val = str(row["email"]).strip()
                if not email_val:
                    continue

                stmt = text(f"""
                    INSERT INTO {table_name} (nome_completo, email, telefone, cidade, pais, data_ingestao)
                    VALUES (:nome_completo, :email, :telefone, :cidade, :pais, :data_ingestao)
                    ON CONFLICT (email) DO UPDATE SET
                        nome_completo = EXCLUDED.nome_completo,
                        telefone = EXCLUDED.telefone,
                        cidade = EXCLUDED.cidade,
                        pais = EXCLUDED.pais,
                        data_ingestao = EXCLUDED.data_ingestao;
                """)
                conn.execute(
                    stmt,
                    {
                        "nome_completo": row["nome_completo"],
                        "email": email_val,
                        "telefone": row["telefone"],
                        "cidade": row["cidade"],
                        "pais": row["pais"],
                        "data_ingestao": row["data_ingestao"]
                    }
                )
                loaded_count += 1

        elapsed = time.time() - start_time
        logger.info(
            f"[LOAD] Sucesso: {loaded_count} contatos sincronizados (upsert) na tabela '{table_name}' em {elapsed:.2f}s!"
        )
        return loaded_count

    except Exception as err:
        logger.error(f"[LOAD] Erro durante a carga no banco: {err}")
        raise


# ==============================================================================
# ORQUESTRADOR PRINCIPAL (RUN PIPELINE)
# ==============================================================================
def run_pipeline(
    file_path: Optional[str] = None,
    table_name: Optional[str] = None,
    if_exists: str = "append"
) -> Tuple[bool, int]:
    """Executa o ciclo completo de ETL com a padronização oficial de contatos e IA fallback."""
    total_start = time.time()
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO PIPELINE ETL DE CONTATOS (HÍBRIDO: REGRAS + IA)")
    logger.info("=" * 60)

    table = table_name or os.getenv("DB_TABLE_NAME", "contatos_processados")

    try:
        # 1. Extração
        txt_content = extract_contacts(file_path=file_path)

        # 2. Transformação (Parser Oficial + IA Fallback)
        df_padronizado = transform_contacts(conteudo_txt=txt_content)

        if df_padronizado.empty:
            logger.warning("Nenhum registro padronizado para carga.")
            return True, 0

        # 3. Carga no PostgreSQL
        linhas_carregadas = load_contacts_to_postgres(
            df=df_padronizado,
            table_name=table,
            if_exists=if_exists
        )

        total_elapsed = time.time() - total_start
        logger.info("=" * 60)
        logger.info(
            f"✅ PIPELINE CONCLUÍDO COM SUCESSO! "
            f"{linhas_carregadas} contatos sincronizados e salvos na nuvem em {total_elapsed:.2f}s."
        )
        logger.info("=" * 60)
        return True, linhas_carregadas

    except Exception as exc:
        total_elapsed = time.time() - total_start
        logger.error("=" * 60)
        logger.error(f"❌ FALHA NA EXECUÇÃO DO PIPELINE após {total_elapsed:.2f}s: {exc}")
        logger.error("=" * 60)
        return False, 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL de Contatos Corporativos")
    parser.add_argument("--file", type=str, default=None, help="Caminho para arquivo TXT")
    parser.add_argument("--table", type=str, default=None, help="Nome da tabela no PostgreSQL")
    args = parser.parse_args()

    success, count = run_pipeline(file_path=args.file, table_name=args.table)
    if not success:
        sys.exit(1)
    sys.exit(0)
