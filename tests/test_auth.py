# -*- coding: utf-8 -*-
"""
Testes Unitários da Camada de Autenticação e Gestão de Chaves de Acesso
"""

import os
import re
import pytest
from pipeline.auth_manager import (
    criar_nova_chave,
    listar_chaves,
    revogar_chave,
    reativar_chave,
    validar_credenciais_e_chave,
    obter_resumo_estatistico,
    PADRAO_FORMATO_CHAVE,
    ADMIN_EMAIL_DEFAULT,
    ADMIN_PASSWORD_DEFAULT,
    ADMIN_MASTER_KEY_DEFAULT
)


class TestGestaoChavesAcesso:
    def test_geracao_chave_formato_padrao(self):
        chave = criar_nova_chave(
            responsavel="Aline (Administradora)",
            destinatario_nome="Lucas Engenheiro",
            destinatario_email="lucas@empresa.com"
        )
        assert "codigo" in chave
        assert PADRAO_FORMATO_CHAVE.match(chave["codigo"]) is not None
        assert chave["status"] == "ativa"
        assert chave["destinatario_nome"] == "Lucas Engenheiro"

    def test_login_administradora_master(self):
        sucesso, msg, info = validar_credenciais_e_chave(
            email=ADMIN_EMAIL_DEFAULT,
            senha=ADMIN_PASSWORD_DEFAULT,
            chave_acesso=ADMIN_MASTER_KEY_DEFAULT
        )
        assert sucesso is True
        assert info["perfil"] == "admin"

    def test_autenticacao_com_chave_ativa(self):
        nova_chave = criar_nova_chave(
            destinatario_nome="Maria Gestora",
            destinatario_email="maria@empresa.com"
        )
        sucesso, msg, info = validar_credenciais_e_chave(
            email="maria@empresa.com",
            senha="qualquer_senha",
            chave_acesso=nova_chave["codigo"]
        )
        assert sucesso is True
        assert info["nome"] == "Maria Gestora"
        assert info["perfil"] == "usuario"

    def test_bloqueio_com_chave_revogada(self):
        nova_chave = criar_nova_chave(
            destinatario_nome="Funcionario Demitido",
            destinatario_email="ex@empresa.com"
        )
        cod = nova_chave["codigo"]
        assert revogar_chave(cod) is True

        sucesso, msg, info = validar_credenciais_e_chave(
            email="ex@empresa.com",
            senha="123",
            chave_acesso=cod
        )
        assert sucesso is False
        assert "revogada" in msg.lower() or "inativa" in msg.lower()

    def test_bloqueio_campos_vazios(self):
        sucesso, msg, _ = validar_credenciais_e_chave("", "123", "KEY-XXXX-YYYY-AUTH")
        assert sucesso is False

        sucesso, msg, _ = validar_credenciais_e_chave("teste@empresa.com", "", "KEY-XXXX-YYYY-AUTH")
        assert sucesso is False

        sucesso, msg, _ = validar_credenciais_e_chave("teste@empresa.com", "123", "")
        assert sucesso is False

    def test_resumo_estatistico(self):
        stats = obter_resumo_estatistico()
        assert "total" in stats
        assert "ativas" in stats
        assert stats["total"] >= 1
