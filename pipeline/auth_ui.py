# -*- coding: utf-8 -*-
"""
Módulo de Interface de Autenticação Corporativa (Dark Glassmorphism)
==================================================================
Renderiza a tela de login idêntica ao design system Taste Skill / Tailwind,
garantindo compatibilidade total com o Streamlit sem vazamento de tags CSS/HTML.
"""

from __future__ import annotations

import base64
import os
import streamlit as st

from pipeline.auth_manager import validar_credenciais_e_chave


def obter_imagem_gatinho_b64() -> str:
    """Retorna a imagem do Gatinho Assistant em base64 (local) ou URL de fallback."""
    diretorio_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    caminho_local = os.path.join(diretorio_raiz, "gatinho.jpg")
    if os.path.exists(caminho_local):
        try:
            with open(caminho_local, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            pass
    return "https://lh3.googleusercontent.com/aida-public/AB6AXuDzbf1TVaumiiIon8lwS7mRo_jOyTbN-IDz8zDiqIImPCiuUvnlWf8bqAOw3WN_YvEc7oNUaztE4tGhWxdeNBxYQnX1X4dj50Cl6VzUCl0Gvsq6N-Ysnk9d-gdINReJFk8KWutJOWEPPIqx3NR0n6s2umtArZ9CYF0jSMavU2PTcex7nbqCoVwGRXAee_8DXl-ZkJq21VVWx23RhWWLiuoPUItRwkm7bWgBPCnoI0OSnn21kpL91M5Y"


# CSS Estrito sem indentação para não ser interpretado como código Markdown pelo Streamlit
AUTH_CSS = """<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" rel="stylesheet">
<style>
/* Esconder barras e sidebar nativa do Streamlit na tela de login */
[data-testid="stSidebar"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { visibility: hidden !important; }

/* Reset e Fundo Dark Glassmorphism */
html, body, .stApp {
background: radial-gradient(circle at 50% 12%, rgba(78, 222, 163, 0.08) 0%, transparent 45%),
            radial-gradient(circle at 85% 85%, rgba(76, 215, 246, 0.07) 0%, transparent 40%),
            #0c1322 !important;
min-height: 100vh !important;
font-family: 'Inter', sans-serif !important;
color: #dce2f7 !important;
}

.main, .block-container {
padding: 0 !important;
max-width: 100% !important;
background: transparent !important;
}

/* Header Superior Fixo */
.auth-top-header {
width: 100%;
height: 56px;
background: rgba(7, 14, 29, 0.85);
backdrop-filter: blur(16px);
-webkit-backdrop-filter: blur(16px);
border-bottom: 1px solid rgba(60, 74, 66, 0.4);
display: flex;
align-items: center;
justify-content: space-between;
padding: 0 2rem;
box-sizing: border-box;
position: relative;
z-index: 100;
}
.auth-top-header .brand {
display: flex;
align-items: center;
gap: 10px;
}
.auth-top-header .brand-icon {
color: #4edea3;
font-size: 20px;
}
.auth-top-header .brand-title {
font-size: 15px;
font-weight: 600;
color: #dce2f7;
letter-spacing: -0.01em;
}
.auth-top-header .badge-ssl {
display: flex;
align-items: center;
gap: 6px;
font-family: 'JetBrains Mono', monospace;
font-size: 10.5px;
color: #4cd7f6;
letter-spacing: 0.08em;
margin-left: 12px;
padding-left: 12px;
border-left: 1px solid rgba(60, 74, 66, 0.5);
}
.auth-top-header .pulse-dot {
width: 7px;
height: 7px;
border-radius: 50%;
background: #4cd7f6;
box-shadow: 0 0 8px #4cd7f6;
display: inline-block;
}
.auth-top-header .status-right {
display: flex;
align-items: center;
gap: 8px;
background: rgba(25, 31, 47, 0.85);
padding: 4px 14px;
border-radius: 9999px;
font-family: 'JetBrains Mono', monospace;
font-size: 10.5px;
color: #bbcabf;
border: 1px solid rgba(255, 255, 255, 0.06);
}

/* Área Central de Conteúdo */
.auth-content-area {
max-width: 620px;
margin: 2rem auto 0 auto;
padding: 0 1rem;
display: flex;
flex-direction: column;
align-items: center;
text-align: center;
}
.auth-brand-badge {
display: inline-flex;
align-items: center;
gap: 6px;
background: #232a3a;
padding: 5px 14px;
border-radius: 9999px;
font-family: 'JetBrains Mono', monospace;
font-size: 11px;
letter-spacing: 0.06em;
color: #bbcabf;
margin-bottom: 12px;
border: 1px solid rgba(255, 255, 255, 0.08);
}
.auth-brand-title {
font-size: 34px;
font-weight: 700;
color: #dce2f7;
letter-spacing: -0.02em;
margin: 0 0 8px 0;
line-height: 1.2;
}
.auth-brand-desc {
font-size: 14.5px;
color: #bbcabf;
max-width: 580px;
line-height: 1.5;
margin: 0 auto 1.5rem auto;
}

/* Formulário Streamlit estilizado como Glassmorphic Card */
div[data-testid="stForm"] {
width: 100% !important;
max-width: 540px !important;
margin: 0 auto !important;
background: rgba(20, 27, 43, 0.95) !important;
border: 1px solid rgba(255, 255, 255, 0.09) !important;
border-radius: 16px !important;
padding: 2rem 2.2rem !important;
backdrop-filter: blur(24px) !important;
-webkit-backdrop-filter: blur(24px) !important;
box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(78, 222, 163, 0.12) !important;
position: relative !important;
box-sizing: border-box !important;
}
div[data-testid="stForm"]::before {
content: '';
position: absolute;
top: 0;
left: 15%;
right: 15%;
height: 2px;
background: linear-gradient(90deg, transparent, #4edea3, transparent);
}

.card-head-row {
display: flex;
align-items: center;
justify-content: space-between;
margin-bottom: 4px;
width: 100%;
}
.card-main-title {
font-size: 22px;
font-weight: 600;
color: #dce2f7;
letter-spacing: -0.01em;
}
.card-tag {
background: #2e3545;
color: #4cd7f6;
font-family: 'JetBrains Mono', monospace;
font-size: 10.5px;
padding: 3px 8px;
border-radius: 4px;
display: inline-flex;
align-items: center;
gap: 5px;
}
.card-tag-dot {
width: 6px;
height: 6px;
border-radius: 50%;
background: #4cd7f6;
display: inline-block;
}
.card-subtext {
font-size: 13px;
color: #bbcabf;
margin-bottom: 20px;
text-align: left;
width: 100%;
}

/* Inputs de Texto */
div[data-testid="stForm"] div[data-testid="stTextInput"] {
margin-bottom: 8px !important;
text-align: left !important;
}
div[data-testid="stForm"] div[data-testid="stTextInput"] label {
font-size: 12px !important;
font-weight: 500 !important;
color: #dce2f7 !important;
margin-bottom: 3px !important;
}
div[data-testid="stForm"] input {
background: #070e1d !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
color: #dce2f7 !important;
border-radius: 8px !important;
height: 44px !important;
padding: 0 12px !important;
font-size: 13px !important;
transition: all 0.2s ease !important;
}
div[data-testid="stForm"] input:focus {
border-color: #4edea3 !important;
background: #141b2b !important;
box-shadow: 0 0 0 2px rgba(78, 222, 163, 0.25) !important;
}

/* Checkbox */
div[data-testid="stForm"] div[data-testid="stCheckbox"] {
margin-top: 4px !important;
margin-bottom: 12px !important;
text-align: left !important;
}
div[data-testid="stForm"] div[data-testid="stCheckbox"] label {
font-size: 12px !important;
color: #bbcabf !important;
}

/* Botão de Autenticação */
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
width: 100% !important;
height: 48px !important;
background: linear-gradient(90deg, #10b981 0%, #03b5d3 100%) !important;
color: #002113 !important;
font-weight: 600 !important;
font-size: 14px !important;
border: none !important;
border-radius: 8px !important;
box-shadow: 0 8px 20px rgba(16, 185, 129, 0.25) !important;
transition: all 0.2s ease !important;
cursor: pointer !important;
margin-top: 4px !important;
}
div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:hover {
opacity: 0.95 !important;
box-shadow: 0 10px 25px rgba(16, 185, 129, 0.4) !important;
transform: translateY(-1px) !important;
}

/* Links Auxiliares no Rodapé do Card */
.auth-aux-links {
margin-top: 20px;
padding-top: 14px;
border-top: 1px solid rgba(60, 74, 66, 0.45);
display: flex;
align-items: center;
justify-content: space-between;
font-size: 11.5px;
color: #bbcabf;
flex-wrap: wrap;
gap: 8px;
width: 100%;
}
.auth-aux-links span {
display: inline-flex;
align-items: center;
gap: 4px;
color: #bbcabf;
}

/* Fita de Telemetria */
.telemetry-ribbon {
max-width: 540px;
margin: 14px auto 2.5rem auto;
display: flex;
align-items: center;
justify-content: space-between;
font-size: 11px;
color: #bbcabf;
padding: 0 4px;
box-sizing: border-box;
font-family: 'JetBrains Mono', monospace;
width: 100%;
}
.telemetry-pill {
display: inline-flex;
align-items: center;
gap: 6px;
background: rgba(25, 31, 47, 0.7);
padding: 4px 10px;
border-radius: 9999px;
border: 1px solid rgba(255, 255, 255, 0.05);
}
.pulse-dot-green {
width: 6px;
height: 6px;
border-radius: 50%;
background: #4edea3;
display: inline-block;
}

/* Floating Companion Badge (Bottom-Right) */
.floating-cat-badge {
position: fixed;
bottom: 24px;
right: 24px;
background: rgba(35, 42, 58, 0.94);
backdrop-filter: blur(14px);
-webkit-backdrop-filter: blur(14px);
border: 1px solid rgba(78, 222, 163, 0.3);
border-radius: 9999px;
padding: 6px 16px 6px 8px;
display: flex;
align-items: center;
gap: 10px;
box-shadow: 0 10px 30px rgba(0,0,0,0.6);
z-index: 9999;
}
.floating-cat-img {
width: 36px !important;
height: 36px !important;
max-width: 36px !important;
max-height: 36px !important;
border-radius: 8px !important;
object-fit: cover !important;
border: 1px solid #10b981 !important;
display: block !important;
}
.floating-cat-text {
display: flex;
flex-direction: column;
text-align: left;
}
.floating-cat-name {
font-size: 12px;
font-weight: 600;
color: #dce2f7;
line-height: 1.2;
}
.floating-cat-sub {
font-family: 'JetBrains Mono', monospace;
font-size: 9.5px;
color: #bbcabf;
line-height: 1.2;
}
</style>
"""


def render_tela_autenticacao() -> None:
    """Renderiza a tela de login visualmente impecável e valida credenciais."""
    img_gatinho = obter_imagem_gatinho_b64()

    # 1. Injetar CSS e Fontes sem indentação
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    # 2. Barra Superior
    st.markdown("""<div class="auth-top-header">
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
</div>""", unsafe_allow_html=True)

    # 3. Contexto da Marca Central
    st.markdown("""<div class="auth-content-area">
<div class="auth-brand-badge">
<span class="material-symbols-outlined" style="font-size: 14px; color: #4edea3;">shield</span>
<span>Ambiente Protegido • Autenticação Multifator / Chave de Acesso</span>
</div>
<h1 class="auth-brand-title">Organizador de Contatos</h1>
<p class="auth-brand-desc">
Sistema corporativo avançado de parsing cadastral, busca inteligente e gestão de dados em tempo real.
</p>
</div>""", unsafe_allow_html=True)

    # 4. Card Central de Autenticação (Formulário)
    col_l, col_center, col_r = st.columns([1, 1.8, 1])
    with col_center:
        with st.form(key="form_autenticacao_corporativa", clear_on_submit=False):
            st.markdown("""<div class="card-head-row">
<div class="card-main-title">Acessar Plataforma</div>
<div class="card-tag">
<span class="card-tag-dot"></span>
<span>PROD-BR-01</span>
</div>
</div>
<div class="card-subtext">
Informe suas credenciais e sua Chave de Acesso (Token de Segurança).
</div>""", unsafe_allow_html=True)

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

            st.markdown("""<div class="auth-aux-links">
<span><span class="material-symbols-outlined" style="font-size: 13px;">key</span> Solicitar chave</span>
<span><span class="material-symbols-outlined" style="font-size: 13px;">headset_mic</span> Suporte TI</span>
<span><span class="material-symbols-outlined" style="font-size: 13px;">policy</span> LGPD • GDPR</span>
</div>""", unsafe_allow_html=True)

        # 5. Fita de Telemetria
        st.markdown("""<div class="telemetry-ribbon">
<div class="telemetry-pill">
<span class="pulse-dot-green"></span>
<span>Servidores: Operacional • 14ms latência</span>
</div>
<div>
<span>🔒 Criptografia E2E AES-GCM 256-bit ativa</span>
</div>
</div>""", unsafe_allow_html=True)

    # 6. Floating Companion Badge
    st.markdown(f"""<div class="floating-cat-badge">
<img src="{img_gatinho}" alt="Gatinho Assistant" class="floating-cat-img">
<div class="floating-cat-text">
<div class="floating-cat-name">Gatinho Assistant</div>
<div class="floating-cat-sub">Supervisão de Dados Ativa</div>
</div>
</div>""", unsafe_allow_html=True)
