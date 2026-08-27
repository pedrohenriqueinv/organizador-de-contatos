"""
Suíte de Testes Unitários - Pipeline ETL de Contatos Reais
==========================================================
Validações de parsing de TXT, limpeza de dados, validação de e-mails,
sanitização de telefones, desduplicação e carga com Pytest.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from pipeline.etl import (
    clean_name,
    clean_phone,
    extract_contacts,
    extrair_contatos_de_texto,
    get_db_engine,
    load_contacts_to_postgres,
    transform_contacts,
    validate_email,
)


# ==============================================================================
# FIXTURES DE DADOS DE TESTE (TXT REAL)
# ==============================================================================
@pytest.fixture
def sample_txt_content():
    return """
ID: 101
Empresa: TechCorp Soluções Ltda
CNPJ: 12.345.678/0001-90
Procurador: carlos eduardo silva
Telefone: (11) 98765-4321 | (11) 3456-7835
Email: carlos@techcorp.com.br
---
ID: 102
Empresa: Nexus Logística e Transportes S.A.
CNPJ: 98.765.432/0001-10
Procurador: Roberto Mendes
Telefone: (21) 98877-6655
Email: roberto@nexuslog.com.br
"""


@pytest.fixture
def sample_raw_contacts():
    return [
        {
            "nome_completo": "carlos eduardo da silva",
            "email": "carlos.silva@example.com",
            "telefone": "(11) 98765-4321",
            "cidade": "são paulo",
            "pais": "brasil",
            "empresa": "TechCorp"
        },
        {
            "nome_completo": "ANA SOUZA",
            "email": "ana.souza@corp.com.br",
            "telefone": "+55 (21) 3344-5566",
            "cidade": "rio de janeiro",
            "pais": "brasil",
            "empresa": "Nexus"
        },
    ]


# ==============================================================================
# TESTES UNITÁRIOS: PARSING DE ARQUIVOS TXT
# ==============================================================================
class TestTxtParser:
    def test_parse_txt_blocks(self, sample_txt_content):
        contatos = extrair_contatos_de_texto(sample_txt_content)
        assert len(contatos) == 2
        assert contatos[0]["nome_completo"] == "carlos eduardo silva"
        assert contatos[0]["email"] == "carlos@techcorp.com.br"
        assert contatos[0]["empresa"] == "TechCorp Soluções Ltda"
        assert contatos[1]["nome_completo"] == "Roberto Mendes"

    def test_parse_txt_empty(self):
        contatos = extrair_contatos_de_texto("")
        assert contatos == []

    def test_parse_tabular_pipe(self):
        txt_pipes = "Lucas Mendes | lucas@empresa.com | (31) 98765-4321 | Tech SA"
        contatos = extrair_contatos_de_texto(txt_pipes)
        assert len(contatos) == 1
        assert contatos[0]["email"] == "lucas@empresa.com"


# ==============================================================================
# TESTES UNITÁRIOS: VALIDAÇÃO DE E-MAIL
# ==============================================================================
class TestEmailValidation:
    @pytest.mark.parametrize(
        "email,expected",
        [
            ("user@example.com", True),
            ("carlos.silva@empresa.com.br", True),
            ("nome+tag@servico.co.uk", True),
            ("email_invalido", False),
            ("@semusuario.com", False),
            ("sem_dominio@", False),
            ("", False),
            (None, False),
        ],
    )
    def test_validate_email_formats(self, email, expected):
        assert validate_email(email) == expected


# ==============================================================================
# TESTES UNITÁRIOS: SANITIZAÇÃO DE TELEFONE
# ==============================================================================
class TestPhoneCleaning:
    @pytest.mark.parametrize(
        "raw_phone,expected_digits",
        [
            ("(11) 98765-4321", "11987654321"),
            ("(11) 98765-4321 | (11) 3456-7835", "11987654321"),
            ("+55 (21) 3344-5566", "552133445566"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_clean_phone(self, raw_phone, expected_digits):
        assert clean_phone(raw_phone) == expected_digits


# ==============================================================================
# TESTES UNITÁRIOS: PADRONIZAÇÃO DE NOMES
# ==============================================================================
class TestNameCleaning:
    @pytest.mark.parametrize(
        "raw_name,expected",
        [
            ("carlos eduardo", "Carlos Eduardo"),
            ("ANA SOUZA", "Ana Souza"),
            ("  maria   clara  ", "Maria Clara"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_clean_name(self, raw_name, expected):
        assert clean_name(raw_name) == expected


# ==============================================================================
# TESTES UNITÁRIOS: TRANSFORMAÇÃO E QUALIDADE DE DADOS (PANDAS)
# ==============================================================================
class TestTransformContacts:
    def test_transform_success(self, sample_raw_contacts):
        df = transform_contacts(sample_raw_contacts)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "nome_completo" in df.columns
        assert "email" in df.columns
        assert "telefone" in df.columns

        # Verifica padronização com .title()
        assert df.loc[0, "nome_completo"] == "Carlos Eduardo Da Silva"
        assert df.loc[1, "nome_completo"] == "Ana Souza"

    def test_transform_deduplication(self, sample_raw_contacts):
        # Adiciona duplicata
        duplicado = list(sample_raw_contacts)
        duplicado.append(dict(sample_raw_contacts[0]))
        df = transform_contacts(duplicado)

        assert len(df) == 2

    def test_transform_empty_data(self):
        df = transform_contacts([])
        assert isinstance(df, pd.DataFrame)
        assert df.empty


# ==============================================================================
# TESTES UNITÁRIOS: CONEXÃO E CARGA DE BANCO DE DADOS
# ==============================================================================
class TestDatabaseLoad:
    def test_get_db_engine_missing_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(ValueError, match="DATABASE_URL"):
            get_db_engine(None)

    def test_load_contacts_empty_dataframe(self):
        df_empty = pd.DataFrame()
        loaded = load_contacts_to_postgres(df_empty)
        assert loaded == 0

    @patch("pandas.DataFrame.to_sql")
    def test_load_contacts_success(self, mock_to_sql, sample_raw_contacts):
        df = transform_contacts(sample_raw_contacts)
        mock_engine = MagicMock()

        loaded_count = load_contacts_to_postgres(df, table_name="contatos_processados", engine=mock_engine)
        assert loaded_count == len(df)
        mock_to_sql.assert_called_once()
