"""
Pacote de Engenharia de Dados - Pipeline ETL
"""
from pipeline.etl import (
    extract_contacts,
    transform_contacts,
    load_contacts_to_postgres,
    validate_email,
    clean_phone,
    clean_name,
    get_db_engine,
    run_pipeline
)

__all__ = [
    "extract_contacts",
    "transform_contacts",
    "load_contacts_to_postgres",
    "validate_email",
    "clean_phone",
    "clean_name",
    "get_db_engine",
    "run_pipeline"
]
