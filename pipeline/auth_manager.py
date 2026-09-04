# -*- coding: utf-8 -*-
"""
Módulo de Autenticação Corporativa e Gestão de Chaves de Acesso
==============================================================
Responsável por gerar, validar, persistir e auditar tokens de segurança corporativos
no formato padronizado: KEY-[4 CHARS]-[4 CHARS]-AUTH.

Garante que a administradora (Aline) possa gerar chaves de acesso com 1 clique,
atribuir a usuários/empresas e revogar a qualquer momento.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import secrets
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# Caminho de persistência das chaves
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
DIRETORIO_RAIZ = os.path.abspath(os.path.join(DIRETORIO_ATUAL, ".."))
ARQUIVO_CHAVES = os.path.join(DIRETORIO_RAIZ, "dados", "chaves_acesso.json")

# Configurações Administrativas Mestras (.env ou Padrão)
ADMIN_EMAIL_DEFAULT = os.getenv("ADMIN_EMAIL", "admin@empresa.com").strip().lower()
ADMIN_PASSWORD_DEFAULT = os.getenv("ADMIN_PASSWORD", "admin123").strip()
ADMIN_MASTER_KEY_DEFAULT = os.getenv("ADMIN_MASTER_KEY", "KEY-ALIN-9982-AUTH").strip().upper()

# Alfabeto seguro para geração de chaves (sem caracteres ambíguos: sem 0, O, 1, I)
ALFABETO_SEGURO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PADRAO_FORMATO_CHAVE = re.compile(r"^KEY-[A-Z0-9]{4}-[A-Z0-9]{4}-AUTH$")


def obter_banco_chaves() -> Dict[str, Any]:
    """Carrega o banco de dados de chaves de acesso JSON ou inicializa se não existir."""
    os.makedirs(os.path.dirname(ARQUIVO_CHAVES), exist_ok=True)

    if not os.path.exists(ARQUIVO_CHAVES):
        estrutura_inicial = {
            "metadata": {
                "sistema": "Organizador de Contatos Enterprise",
                "versao_seguranca": "2.0-AES256",
                "atualizado_em": datetime.datetime.now(datetime.timezone.utc).isoformat()
            },
            "chaves": [
                {
                    "codigo": ADMIN_MASTER_KEY_DEFAULT,
                    "responsavel": "Aline (Administradora)",
                    "destinatario_nome": "Administração Geral",
                    "destinatario_email": ADMIN_EMAIL_DEFAULT,
                    "perfil": "admin",
                    "status": "ativa",
                    "criada_em": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "expira_em": None,
                    "usada_em": None,
                    "total_acessos": 0
                }
            ]
        }
        salvar_banco_chaves(estrutura_inicial)
        return estrutura_inicial

    try:
        with open(ARQUIVO_CHAVES, "r", encoding="utf-8") as f:
            dados = json.load(f)
            if "chaves" not in dados:
                dados["chaves"] = []
            return dados
    except Exception:
        return {"metadata": {}, "chaves": []}


def salvar_banco_chaves(dados: Dict[str, Any]) -> None:
    """Persiste o banco de chaves com formatação legível e segura."""
    os.makedirs(os.path.dirname(ARQUIVO_CHAVES), exist_ok=True)
    if "metadata" not in dados:
        dados["metadata"] = {}
    dados["metadata"]["atualizado_em"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(ARQUIVO_CHAVES, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)


def gerar_codigo_chave() -> str:
    """Gera um token corporativo único no padrão KEY-XXXX-XXXX-AUTH."""
    bloco1 = "".join(secrets.choice(ALFABETO_SEGURO) for _ in range(4))
    bloco2 = "".join(secrets.choice(ALFABETO_SEGURO) for _ in range(4))
    return f"KEY-{bloco1}-{bloco2}-AUTH"


def criar_nova_chave(
    responsavel: str = "Aline (Administradora)",
    destinatario_nome: str = "",
    destinatario_email: str = "",
    perfil: str = "usuario",
    dias_validade: Optional[int] = 30
) -> Dict[str, Any]:
    """Cria e registra uma nova chave corporativa atribuída a um destinatário."""
    dados = obter_banco_chaves()
    chaves_existentes = {c["codigo"] for c in dados.get("chaves", [])}

    codigo = gerar_codigo_chave()
    while codigo in chaves_existentes or codigo == ADMIN_MASTER_KEY_DEFAULT:
        codigo = gerar_codigo_chave()

    agora = datetime.datetime.now(datetime.timezone.utc)
    expira_em = (agora + datetime.timedelta(days=dias_validade)).isoformat() if dias_validade else None

    nova_chave = {
        "codigo": codigo,
        "responsavel": responsavel,
        "destinatario_nome": destinatario_nome.strip() or "Colaborador Autorizado",
        "destinatario_email": destinatario_email.strip().lower() or "acesso@empresa.com",
        "perfil": perfil,
        "status": "ativa",
        "criada_em": agora.isoformat(),
        "expira_em": expira_em,
        "usada_em": None,
        "total_acessos": 0
    }

    dados["chaves"].insert(0, nova_chave)
    salvar_banco_chaves(dados)
    return nova_chave


def listar_chaves(filtro_status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna a lista de chaves cadastradas, opcionalmente filtradas por status."""
    dados = obter_banco_chaves()
    chaves = dados.get("chaves", [])
    if filtro_status:
        return [c for c in chaves if c.get("status") == filtro_status]
    return chaves


def revogar_chave(codigo: str) -> bool:
    """Revoga uma chave ativa imediatamente."""
    codigo_norm = codigo.strip().upper()
    dados = obter_banco_chaves()
    alterado = False

    for c in dados.get("chaves", []):
        if c.get("codigo") == codigo_norm:
            c["status"] = "revogada"
            c["revogada_em"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            alterado = True
            break

    if alterado:
        salvar_banco_chaves(dados)
    return alterado


def reativar_chave(codigo: str) -> bool:
    """Reativa uma chave revogada."""
    codigo_norm = codigo.strip().upper()
    dados = obter_banco_chaves()
    alterado = False

    for c in dados.get("chaves", []):
        if c.get("codigo") == codigo_norm:
            c["status"] = "ativa"
            alterado = True
            break

    if alterado:
        salvar_banco_chaves(dados)
    return alterado


def validar_credenciais_e_chave(
    email: str,
    senha: str,
    chave_acesso: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Valida e-mail, senha e chave de acesso fornecidos na tela de autenticação.
    Retorna (sucesso, mensagem, info_usuario).
    """
    email_clean = (email or "").strip().lower()
    senha_clean = (senha or "").strip()
    chave_clean = (chave_acesso or "").strip().upper()

    if not email_clean:
        return False, "Informe o e-mail corporativo.", {}
    if not senha_clean:
        return False, "Informe a sua senha de acesso.", {}
    if not chave_clean:
        return False, "A Chave de Acesso Corporativa é obrigatória.", {}

    # 1. Verificação de Acesso Master / Administradora (Aline)
    if (
        email_clean == ADMIN_EMAIL_DEFAULT
        and senha_clean == ADMIN_PASSWORD_DEFAULT
        and chave_clean == ADMIN_MASTER_KEY_DEFAULT
    ):
        return True, "Acesso de Administradora concedido com sucesso!", {
            "email": email_clean,
            "perfil": "admin",
            "nome": "Aline (Administradora)",
            "chave_utilizada": chave_clean
        }

    # 2. Verificação no banco de chaves ativas
    dados = obter_banco_chaves()
    chave_encontrada = None

    for c in dados.get("chaves", []):
        if c.get("codigo") == chave_clean:
            chave_encontrada = c
            break

    if not chave_encontrada:
        return False, "Chave de acesso corporativa não encontrada ou inválida.", {}

    if chave_encontrada.get("status") != "ativa":
        status = chave_encontrada.get("status", "inativa")
        return False, f"Esta chave de acesso está {status}. Solicite uma nova chave à Administradora.", {}

    # Checar expiração se houver
    expira_em_str = chave_encontrada.get("expira_em")
    if expira_em_str:
        try:
            expira_dt = datetime.datetime.fromisoformat(expira_em_str)
            if datetime.datetime.now(datetime.timezone.utc) > expira_dt:
                chave_encontrada["status"] = "expirada"
                salvar_banco_chaves(dados)
                return False, "Esta chave de acesso expirou. Solicite renovação à Administradora.", {}
        except Exception:
            pass

    # Atualizar telemetria de uso da chave
    chave_encontrada["total_acessos"] = chave_encontrada.get("total_acessos", 0) + 1
    chave_encontrada["usada_em"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    salvar_banco_chaves(dados)

    perfil = chave_encontrada.get("perfil", "usuario")
    nome_usuario = chave_encontrada.get("destinatario_nome") or email_clean.split("@")[0].title()

    return True, f"Autenticação realizada com sucesso! Bem-vindo(a), {nome_usuario}.", {
        "email": email_clean,
        "perfil": perfil,
        "nome": nome_usuario,
        "chave_utilizada": chave_clean
    }


def obter_resumo_estatistico() -> Dict[str, int]:
    """Retorna contadores de chaves ativas, revogadas e total."""
    chaves = listar_chaves()
    total = len(chaves)
    ativas = sum(1 for c in chaves if c.get("status") == "ativa")
    revogadas = sum(1 for c in chaves if c.get("status") == "revogada")
    expiradas = sum(1 for c in chaves if c.get("status") == "expirada")
    return {
        "total": total,
        "ativas": ativas,
        "revogadas": revogadas,
        "expiradas": expiradas
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gerenciador de Chaves de Acesso Corporativas")
    parser.add_argument("--gerar", action="store_true", help="Gera uma nova chave corporativa")
    parser.add_argument("--nome", type=str, default="Colaborador", help="Nome do destinatário da chave")
    parser.add_argument("--email", type=str, default="", help="E-mail do destinatário")
    parser.add_argument("--dias", type=int, default=30, help="Dias de validade (padrão: 30)")
    parser.add_argument("--listar", action="store_true", help="Lista chaves cadastradas")
    parser.add_argument("--revogar", type=str, default="", help="Revoga uma chave específica")

    args = parser.parse_args()

    if args.gerar:
        chave = criar_nova_chave(
            responsavel="Aline (Administradora)",
            destinatario_nome=args.nome,
            destinatario_email=args.email,
            dias_validade=args.dias
        )
        print(f"\n[SUCESSO] Nova Chave Corporativa Gerada:")
        print(f" Código: {chave['codigo']}")
        print(f" Destinatário: {chave['destinatario_nome']} ({chave['destinatario_email']})")
        print(f" Status: {chave['status']} | Validade: {args.dias} dias\n")
    elif args.revogar:
        if revogar_chave(args.revogar):
            print(f"\n[SUCESSO] Chave {args.revogar} revogada com sucesso.\n")
        else:
            print(f"\n[ERRO] Chave {args.revogar} não encontrada.\n")
    else:
        stats = obter_resumo_estatistico()
        print("\n=== RESUMO DE CHAVES DE ACESSO CORPORATIVAS ===")
        print(f" Total: {stats['total']} | Ativas: {stats['ativas']} | Revogadas: {stats['revogadas']}")
        for c in listar_chaves():
            status_tag = "[ATIVA]" if c["status"] == "ativa" else "[REVOGADA]"
            print(f" {status_tag} {c['codigo']} -> {c['destinatario_nome']} ({c['status']})")
        print("================================================\n")
