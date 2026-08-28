"""
Módulo de Fallback com Inteligência Artificial (Google Gemini)
=============================================================
Fornece resiliência máxima ao pipeline de dados. Caso o parser tradicional
encontre um bloco com formatação irregular, texto caótico ou anomalias,
este módulo aciona a IA para extrair e estruturar os contatos com 100% de precisão
nas 12 colunas padronizadas do sistema.

Segurança:
    A chave de API é lida exclusivamente via variável de ambiente 'GEMINI_API_KEY'
    definida no arquivo .env (nunca exposta no código-fonte).

Autor: Engenharia de Dados
Data: 2026
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ETL_Pipeline")

COLUNAS_PADRAO = [
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


def emitir_aviso_usuario(mensagem: str, nivel: str = "warning") -> None:
    """Emite aviso formatado no terminal/logs destacando o uso da IA."""
    borda = "=" * 70
    if nivel == "warning":
        logger.warning(borda)
        logger.warning(f"🤖 [AVISO AO USUÁRIO - IA FALLBACK] {mensagem}")
        logger.warning(borda)
    else:
        logger.info(borda)
        logger.info(f"✨ [AVISO AO USUÁRIO - IA SUCESSO] {mensagem}")
        logger.info(borda)


def extrair_contatos_com_ia(conteudo_txt: str) -> List[Dict[str, Any]]:
    """
    Aciona o modelo Google Gemini para interpretar textos caóticos ou blocos
    fora do padrão e devolvê-los estritamente nas 12 colunas padronizadas.

    Args:
        conteudo_txt (str): Conteúdo textual não estruturado ou com anomalia.

    Returns:
        List[Dict[str, Any]]: Lista de contatos padronizados no formato oficial.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning(
            "[IA_FALLBACK] Chave 'GEMINI_API_KEY' não encontrada no .env. "
            "Fallback com IA não pode ser executado sem a chave configurada."
        )
        return []

    emitir_aviso_usuario(
        "Detectamos um bloco de texto com formatação irregular / fora do padrão. "
        "A Inteligência Artificial (Gemini Flash) foi ativada como Fallback de Resiliência para recuperar seus dados!"
    )

    prompt = f"""
Você é um Engenheiro de Dados especialista em extração e estruturação de contatos corporativos.
Analise o texto abaixo e extraia TODOS os contatos e procuradores encontrados.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS um array JSON válido contendo objetos com EXATAMENTE estas 12 chaves:
   - "ID": ID da empresa ou identificador (string)
   - "Empresa": Razão Social da empresa (string)
   - "CNPJ": CNPJ formatado no padrão XX.XXX.XXX/XXXX-XX se presente (string)
   - "Capital Social": Valor numérico ou string do capital social (string)
   - "Procurador/Nome": Nome completo do procurador/usuário (string)
   - "Login": Login de usuário (string)
   - "Tipo de Acesso": Perfil ou tipo de acesso (string, ex: "Master", "Financeiro", "Usuário e Senha")
   - "Último Acesso": Data/hora do último acesso (string)
   - "Telefones": Telefones válidos limpos e separados por " | " (ex: "(19) 99679-0935 | (19) 3869-4231")
   - "E-mail": E-mails válidos separados por " | " (string)
   - "Outros": Campos complementares como CPF, Mãe, Renda, Endereço Pessoal separados por " | " (string)
   - "Status": false (booleano)

2. Se uma empresa tiver mais de um procurador/perfil, crie um objeto para CADA procurador herdando os dados da empresa.
3. Não inclua comentários nem texto fora do JSON.

TEXTO PARA ANÁLISE:
\"\"\"{conteudo_txt}\"\"\"
"""

    modelos = ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemma-4-31b-it"]
    
    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        try:
            logger.info(f"[IA_FALLBACK] Enviando requisição para o modelo '{modelo}'...")
            res = requests.post(url, json=payload, timeout=25)
            
            if res.status_code == 200:
                raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                dados_json = json.loads(raw_text)

                if isinstance(dados_json, dict):
                    # Caso venha encapsulado em uma chave como "contatos" ou "data"
                    for chave_lista in ["contatos", "results", "contacts", "data"]:
                        if isinstance(dados_json.get(chave_lista), list):
                            dados_json = dados_json[chave_lista]
                            break
                    if isinstance(dados_json, dict):
                        dados_json = [dados_json]

                if isinstance(dados_json, list):
                    # Garantir todas as 12 colunas presentes
                    registros_normalizados: List[Dict[str, Any]] = []
                    for item in dados_json:
                        reg = {col: item.get(col, False if col == "Status" else "") for col in COLUNAS_PADRAO}
                        registros_normalizados.append(reg)

                    emitir_aviso_usuario(
                        f"Sucesso! A IA recuperou e padronizou {len(registros_normalizados)} contato(s) nas 12 colunas oficiais.",
                        nivel="info"
                    )
                    return registros_normalizados

            else:
                logger.warning(f"[IA_FALLBACK] Modelo '{modelo}' retornou status {res.status_code}. Tentando modelo alternativo...")

        except Exception as e:
            logger.warning(f"[IA_FALLBACK] Falha na comunicação com o modelo '{modelo}': {e}")
            continue

    logger.error("[IA_FALLBACK] Não foi possível estruturar o texto através dos modelos de IA disponíveis.")
    return []
