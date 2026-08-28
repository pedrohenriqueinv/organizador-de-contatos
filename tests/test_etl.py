"""
Suíte de Testes Unitários - Pipeline ETL de Contatos Corporativos
================================================================
Testes para o parser rigoroso de TXT, padronização de listas,
regras de negócio, deduplicação e carga no PostgreSQL.
"""

from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from pipeline.etl import (
    COLUNAS_FINAIS,
    CAMPOS_PADRONIZADOS,
    adicionar_valor,
    garantir_tipos_colunas,
    get_db_engine,
    identificar_campo,
    limpar_valor_campo,
    load_contacts_to_postgres,
    normalizar_texto,
    parse_txt,
    registro_tem_dados,
    registro_vazio,
    transform_contacts,
)


@pytest.fixture
def txt_completo():
    return """ID: 35379
Empresa: FASCIATA EMPREENDIMENTOS I. LTDA
CNPJ: 08.235.887/0001-09
Capital Social: 11536937.0
Email: marcelofiguinha@acrodi.com.br
Telefone: (19) 99679-0935 (CELULAR)

=== USUÁRIOS E PERFIS ===

--- Procurador 2 ---
Login: MCRF00166
Nome: MARCELO CORTES REMISIO FIGUINH
CPF: 32007992850
Tipo de Acesso: Usuário e Senha
Último Acesso: 16/03/2026 - 11h04
Telefone: (19) 99657-9384 (CELULAR)
Email: ironfigas@hotmail.com
"""


class TestParserPadronizacao:
    def test_identificar_campo(self):
        assert identificar_campo("Empresa") == "Empresa"
        assert identificar_campo("Razão Social") == "Empresa"
        assert identificar_campo("CNPJ") == "CNPJ"
        assert identificar_campo("Procurador") == "Procurador/Nome"
        assert identificar_campo("Nome") == "Procurador/Nome"
        assert identificar_campo("Telefone") == "Telefones"
        assert identificar_campo("Email") == "E-mail"
        assert identificar_campo("CPF") == "Outros"

    def test_limpar_valor_campo(self):
        # Telefones com formatação e tipos
        tel = "(19) 99679-0935 (CELULAR)"
        assert limpar_valor_campo("Telefones", tel) == "(19) 99679-0935"

        # Telefones múltiplos
        tels = "(19) 99679-0935 (CELULAR) | (19) 3869-4231 (FIXO)"
        assert limpar_valor_campo("Telefones", tels) == "(19) 99679-0935 | (19) 3869-4231"

        # Emails
        email = "marcelofiguinha@acrodi.com.br"
        assert limpar_valor_campo("E-mail", email) == "marcelofiguinha@acrodi.com.br"

        # CNPJ
        cnpj = "08.235.887/0001-09"
        assert limpar_valor_campo("CNPJ", cnpj) == "08.235.887/0001-09"

    def test_parse_txt_estrutura(self, txt_completo):
        df = parse_txt(txt_completo)

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == COLUNAS_FINAIS
        assert len(df) == 1

        row = df.iloc[0]
        assert row["ID"] == "35379"
        assert row["Empresa"] == "FASCIATA EMPREENDIMENTOS I. LTDA"
        assert row["CNPJ"] == "08.235.887/0001-09"
        assert row["Procurador/Nome"] == "MARCELO CORTES REMISIO FIGUINH"
        assert row["Login"] == "MCRF00166"
        assert row["Tipo de Acesso"] == "Usuário e Senha"
        assert "ironfigas@hotmail.com" in row["E-mail"]
        assert "99657-9384" in row["Telefones"]

    def test_transform_contacts_pipeline(self, txt_completo):
        df = transform_contacts(txt_completo)
        assert len(df) == 1
        assert df.iloc[0]["CNPJ"] == "08.235.887/0001-09"

    def test_load_contacts_empty(self):
        assert load_contacts_to_postgres(pd.DataFrame()) == 0

    def test_load_contacts_success(self, txt_completo):
        df = transform_contacts(txt_completo)
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        loaded = load_contacts_to_postgres(df, engine=mock_engine)
        assert loaded == 1
        assert mock_conn.execute.called

    @patch("pipeline.ai_fallback.requests.post")
    def test_ai_fallback_trigger(self, mock_post, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key_for_test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '[{"ID": "999", "Empresa": "Alpha Tech", "CNPJ": "11.222.333/0001-99", "Capital Social": "100000", "Procurador/Nome": "Roberto Silva", "Login": "roberto", "Tipo de Acesso": "Master", "Último Acesso": "20/08/2026", "Telefones": "(11) 98888-7777", "E-mail": "roberto@alpha.com", "Outros": "TI", "Status": false}]'
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response

        texto_caotico = "Contato urgente do Roberto Silva na Alpha Tech, fone 11 98888-7777"
        df = transform_contacts(texto_caotico)
        assert not df.empty
        assert df.iloc[0]["Procurador/Nome"] == "Roberto Silva"
        assert df.iloc[0]["Empresa"] == "Alpha Tech"


