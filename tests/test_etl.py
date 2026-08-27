"""
Suíte de Testes Unitários - Pipeline ETL de Contatos
===================================================
Validações de limpeza de dados, validação de e-mails, sanitização de telefones,
desduplicação e resiliência da transformação com Pytest.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import requests

from pipeline.etl import (
    clean_name,
    clean_phone,
    extract_contacts,
    get_db_engine,
    load_contacts_to_postgres,
    transform_contacts,
    validate_email,
)


# ==============================================================================
# FIXTURES DE DADOS DE TESTE
# ==============================================================================
@pytest.fixture
def sample_raw_contacts():
    """Retorna uma lista de contatos brutos simulando a resposta da RandomUser API."""
    return [
        {
            "login": {"uuid": "u-001", "username": "carlos_silva"},
            "name": {"first": "carlos eduardo", "last": "da silva"},
            "gender": "male",
            "email": "carlos.silva@example.com",
            "phone": "(11) 98765-4321",
            "cell": "(11) 91234-5678",
            "location": {
                "street": {"number": 100, "name": "avenida paulista"},
                "city": "são paulo",
                "state": "são paulo",
                "country": "brazil",
                "postcode": "01310-100",
                "coordinates": {"latitude": "-23.5615", "longitude": "-46.6559"},
            },
            "dob": {"date": "1990-05-15T00:00:00.000Z", "age": 34},
            "registered": {"date": "2020-01-10T12:00:00.000Z"},
            "picture": {"large": "https://randomuser.me/api/portraits/men/1.jpg"},
        },
        {
            "login": {"uuid": "u-002", "username": "ana_souza"},
            "name": {"first": "ANA", "last": "SOUZA"},
            "gender": "female",
            "email": "ana.souza@corp.com.br",
            "phone": "+55 (21) 3344-5566",
            "cell": "2199887766",
            "location": {
                "street": {"number": 50, "name": "rua das flores"},
                "city": "rio de janeiro",
                "state": "rio de janeiro",
                "country": "brazil",
                "postcode": "20000-000",
                "coordinates": {"latitude": "-22.9068", "longitude": "-43.1729"},
            },
            "dob": {"date": "1995-10-20T00:00:00.000Z", "age": 29},
            "registered": {"date": "2021-06-15T08:30:00.000Z"},
            "picture": {"large": "https://randomuser.me/api/portraits/women/2.jpg"},
        },
    ]


@pytest.fixture
def contacts_with_duplicates_and_invalids(sample_raw_contacts):
    """Retorna contatos contendo registros duplicados e e-mails inválidos."""
    data = list(sample_raw_contacts)
    
    # Registro com e-mail duplicado (mesmo de carlos.silva@example.com)
    data.append({
        "login": {"uuid": "u-003", "username": "carlos_duplicate"},
        "name": {"first": "Carlos", "last": "Silva Clonado"},
        "email": "carlos.silva@example.com",
        "phone": "11987654321",
        "location": {"city": "São Paulo", "country": "Brazil"},
    })

    # Registro com e-mail inválido
    data.append({
        "login": {"uuid": "u-004", "username": "invalid_user"},
        "name": {"first": "Usuario", "last": "Invalido"},
        "email": "email_sem_arroba_ponto_com",
        "phone": "12345",
        "location": {},
    })

    return data


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
            ("contato_123@sub.dominio.org", True),
            ("email_invalido", False),
            ("@semusuario.com", False),
            ("sem_dominio@", False),
            ("usuario@.com", False),
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
            ("+55 (21) 3344-5566", "552133445566"),
            ("0800-7070-1234", "080070701234"),
            ("123456", "123456"),
            ("", ""),
            (None, ""),
            ("sem-numeros", ""),
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
        assert "cidade" in df.columns
        assert "pais" in df.columns
        assert "data_ingestao" in df.columns

        # Verifica padronização com .title()
        assert df.loc[0, "nome_completo"] == "Carlos Eduardo Da Silva"
        assert df.loc[0, "cidade"] == "São Paulo"
        assert df.loc[0, "pais"] == "Brazil"
        assert df.loc[1, "nome_completo"] == "Ana Souza"
        assert df.loc[1, "cidade"] == "Rio De Janeiro"

        # Verifica limpeza de telefones
        assert df.loc[0, "telefone"] == "11987654321"
        assert df.loc[1, "telefone"] == "552133445566"

    def test_transform_deduplication(self, contacts_with_duplicates_and_invalids):
        df = transform_contacts(contacts_with_duplicates_and_invalids)

        # Havia 2 contatos válidos + 1 duplicado + 1 com email inválido
        # Resultado esperado: apenas 2 contatos únicos e válidos
        assert len(df) == 2
        assert list(df["email"]) == ["carlos.silva@example.com", "ana.souza@corp.com.br"]

    def test_transform_empty_data(self):
        df = transform_contacts([])
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_transform_malformed_record(self):
        raw_data = [
            {"invalid_key": 123},  # Registro sem campos esperados
            {
                "login": {"uuid": "u-ok"},
                "name": {"first": "Lucas", "last": "Mendes"},
                "email": "lucas.mendes@test.com",
            },
        ]
        df = transform_contacts(raw_data)
        assert len(df) == 1
        assert df.iloc[0]["nome_completo"] == "Lucas Mendes"


# ==============================================================================
# TESTES UNITÁRIOS: EXTRAÇÃO COM MOCK HTTP
# ==============================================================================
class TestExtractContacts:
    @patch("pipeline.etl.requests.get")
    def test_extract_success(self, mock_get, sample_raw_contacts):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": sample_raw_contacts}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        results = extract_contacts(api_url="https://fake-url.com", results=2)
        assert len(results) == 2
        assert results[0]["name"]["first"] == "carlos eduardo"

    @patch("pipeline.etl.requests.get")
    def test_extract_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            extract_contacts(api_url="https://fake-url.com")


# ==============================================================================
# TESTES UNITÁRIOS: CONEXÃO E CARGA DE BANCO DE DADOS
# ==============================================================================
class TestDatabaseLoad:
    def test_get_db_engine_missing_env(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(ValueError, match="DATABASE_URL"):
            get_db_engine(None)

    def test_get_db_engine_url_normalization(self, monkeypatch):
        # Testa conversão de postgres:// para postgresql+psycopg2://
        url = "postgres://user:pass@localhost:5432/testdb"
        with patch("pipeline.etl.create_engine") as mock_engine:
            get_db_engine(url)
            mock_engine.assert_called_once()
            called_url = mock_engine.call_args[0][0]
            assert called_url.startswith("postgresql+psycopg2://")

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
