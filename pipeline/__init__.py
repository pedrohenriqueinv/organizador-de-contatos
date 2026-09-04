"""
Pacote de Engenharia de Dados - Pipeline ETL de Contatos com IA Fallback
"""
from pipeline.etl import (
    COLUNAS_FINAIS,
    CAMPOS_PADRONIZADOS,
    parse_txt,
    extract_contacts,
    transform_contacts,
    load_contacts_to_postgres,
    limpar_valor_campo,
    adicionar_valor,
    identificar_campo,
    garantir_tipos_colunas,
    get_db_engine,
    run_pipeline
)
from pipeline.ai_fallback import extrair_contatos_com_ia
from pipeline.auth_manager import (
    criar_nova_chave,
    listar_chaves,
    revogar_chave,
    reativar_chave,
    validar_credenciais_e_chave,
    obter_resumo_estatistico,
    obter_banco_chaves
)

__all__ = [
    "COLUNAS_FINAIS",
    "CAMPOS_PADRONIZADOS",
    "parse_txt",
    "extract_contacts",
    "transform_contacts",
    "load_contacts_to_postgres",
    "limpar_valor_campo",
    "adicionar_valor",
    "identificar_campo",
    "garantir_tipos_colunas",
    "get_db_engine",
    "run_pipeline",
    "extrair_contatos_com_ia",
    "criar_nova_chave",
    "listar_chaves",
    "revogar_chave",
    "reativar_chave",
    "validar_credenciais_e_chave",
    "obter_resumo_estatistico",
    "obter_banco_chaves"
]
