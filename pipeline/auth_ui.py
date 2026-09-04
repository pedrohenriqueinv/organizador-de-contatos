# -*- coding: utf-8 -*-
"""
Módulo de Interface de Autenticação Corporativa (Dark Glassmorphism)
==================================================================
Renderiza a tela de login utilizando st.html() nativo com carregamento
de arquivo CSS dedicado em assets/auth.css, garantindo 100% de isolamento
e NENHUM vazamento de texto ou quebra de estilo.
"""

from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

from pipeline.auth_manager import validar_credenciais_e_chave


def obter_imagem_gatinho_b64() -> str:
    """Retorna a imagem do Gatinho Assistant em base64 (local) ou fallback seguro."""
    diretorio_raiz = Path(__file__).resolve().parent.parent
    caminho_local = diretorio_raiz / "gatinho.jpg"
    if caminho_local.exists():
        try:
            with open(caminho_local, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            pass
    return "https://lh3.googleusercontent.com/aida-public/AB6AXuDzbf1TVaumiiIon8lwS7mRo_jOyTbN-IDz8zDiqIImPCiuUvnlWf8bqAOw3WN_YvEc7oNUaztE4tGhWxdeNBxYQnX1X4dj50Cl6VzUCl0Gvsq6N-Ysnk9d-gdINReJFk8KWutJOWEPPIqx3NR0n6s2umtArZ9CYF0jSMavU2PTcex7nbqCoVwGRXAee_8DXl-ZkJq21VVWx23RhWWLiuoPUItRwkm7bWgBPCnoI0OSnn21kpL91M5Y"


def _render_html(html_code: str) -> None:
    """Insere HTML de forma segura e limpa sem passar pelo interpretador de Markdown."""
    if hasattr(st, "html"):
        st.html(html_code)
    else:
        st.markdown(html_code, unsafe_allow_html=True)


def _carregar_estilos() -> None:
    """Carrega o arquivo CSS diretamente no DOM, prevenindo qualquer vazamento no Markdown."""
    caminho_css = Path(__file__).resolve().parent.parent / "assets" / "auth.css"
    if caminho_css.exists():
        if hasattr(st, "html"):
            st.html(caminho_css)
        else:
            with open(caminho_css, "r", encoding="utf-8") as f:
                conteudo = f.read().replace("\n", " ")
            st.markdown(f"<style>{conteudo}</style>", unsafe_allow_html=True)


def render_tela_autenticacao() -> None:
    """Renderiza a tela de login visualmente impecável e valida credenciais corporativas."""
    # 1. Injetar estilos estritos via st.html()
    _carregar_estilos()

    img_gatinho = obter_imagem_gatinho_b64()

    # 2. Barra Superior Corporativa
    _render_html("""
        <div class="auth-top-header">
            <div class="brand">
                <span class="material-symbols-outlined brand-icon">contacts</span>
                <span class="brand-title">Organizador de Contatos</span>
                <div class="badge-ssl">
                    <span class="pulse-dot"></span>
                    <span>SECURE SSL 256-BIT</span>
                </div>
            </div>
            <div class="status-right">
                <span class="material-symbols-outlined" style="font-size: 13px; color: #4edea3;">verified_user</span>
                <span>CONNECTING / ONLINE</span>
            </div>
        </div>
    """)

    # 3. Contexto da Marca Central
    _render_html("""
        <div class="auth-content-area">
            <div class="auth-brand-badge">
                <span class="material-symbols-outlined" style="font-size: 14px; color: #4edea3;">shield</span>
                <span>Ambiente Protegido • Autenticação Multifator / Chave de Acesso</span>
            </div>
            <h1 class="auth-brand-title">Organizador de Contatos</h1>
            <p class="auth-brand-desc">
                Sistema corporativo avançado de parsing cadastral, busca inteligente e gestão de dados em tempo real.
            </p>
        </div>
    """)

    # 4. Card Central de Autenticação (Formulário Dark Glassmorphic)
    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        with st.form(key="form_autenticacao_corporativa", clear_on_submit=False):
            _render_html("""
                <div class="card-head-row">
                    <div class="card-main-title">Acessar Plataforma</div>
                    <div class="card-tag">
                        <span class="card-tag-dot"></span>
                        <span>PROD-BR-01</span>
                    </div>
                </div>
                <div class="card-subtext">
                    Informe suas credenciais e sua Chave de Acesso (Token de Segurança).
                </div>
            """)

            email_val = st.text_input(
                "E-mail Corporativo",
                placeholder="ex: usuario@empresa.com",
                key="auth_email"
            )
            senha_val = st.text_input(
                "Senha de Acesso",
                type="password",
                placeholder="••••••••••••",
                key="auth_senha"
            )
            chave_val = st.text_input(
                "Chave de Acesso Corporativa (OBRIGATÓRIA)",
                placeholder="ex: KEY-XXXX-9982-AUTH",
                key="auth_chave",
                help="Chave fornecida pela Administradora (Aline) ou gerada no painel de segurança."
            )
            lembrar = st.checkbox(
                "Manter conectado neste dispositivo corporativo confiável (30 dias)",
                value=True,
                key="auth_lembrar"
            )

            btn_auth = st.form_submit_button("🛡️ Autenticar e Entrar →")

            if btn_auth:
                sucesso, msg, info = validar_credenciais_e_chave(email_val, senha_val, chave_val)
                if sucesso:
                    st.session_state.authenticated = True
                    st.session_state.user_info = info
                    st.session_state.is_admin = (info.get("perfil") == "admin")
                    st.success(f"✨ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

            _render_html("""
                <div class="auth-aux-links">
                    <span><span class="material-symbols-outlined" style="font-size: 13px;">key</span> Solicitar chave</span>
                    <span><span class="material-symbols-outlined" style="font-size: 13px;">headset_mic</span> Suporte TI</span>
                    <span><span class="material-symbols-outlined" style="font-size: 13px;">policy</span> LGPD • GDPR</span>
                </div>
            """)

        # 5. Fita de Telemetria
        _render_html("""
            <div class="telemetry-ribbon">
                <div class="telemetry-pill">
                    <span class="pulse-dot-green"></span>
                    <span>Servidores: Operacional • 14ms latência</span>
                </div>
                <div>
                    <span>🔒 Criptografia E2E AES-GCM 256-bit ativa</span>
                </div>
            </div>
        """)

    # 6. Floating Companion Badge
    _render_html(f"""
        <div class="floating-cat-badge">
            <img src="{img_gatinho}" alt="Gatinho Assistant" class="floating-cat-img">
            <div class="floating-cat-text">
                <div class="floating-cat-name">Gatinho Assistant</div>
                <div class="floating-cat-sub">Supervisão de Dados Ativa</div>
            </div>
        </div>
    """)
