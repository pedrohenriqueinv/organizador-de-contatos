"""
=======================================================================================
 ORGANIZADOR DE CONTATOS CORPORATIVOS
 Design System: Taste Skill (Anti-Slop Pro Frontend Framework)
 Aesthetics: Deep Midnight Dark Glassmorphism, Modern Typography, Micro-Interactions
=======================================================================================
"""

import html
import os
import re
import sys
import textwrap
import unicodedata
import pandas as pd
from rich import box
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Importação condicional do Streamlit para suportar execução direta no Terminal (CLI)
try:
    import streamlit as st
    STREAMLIT_DISPONIVEL = True
except ImportError:
    st = None
    STREAMLIT_DISPONIVEL = False


def configurar_console_windows() -> None:
    """Garante cores e emojis bonitos no terminal do Windows (cmd / Windows Terminal)."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        if handle and handle != -1:
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


# ---------------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (STREAMLIT)
# ---------------------------------------------------------------------------------
if STREAMLIT_DISPONIVEL and hasattr(st, "runtime") and st.runtime.exists():
    st.set_page_config(
        page_title="Organizador de Contatos",
        page_icon="📇",
        layout="wide",
        initial_sidebar_state="expanded"
    )

# ---------------------------------------------------------------------------------
# REGRAS E SINÔNIMOS DO PARSER (PRESERVAÇÃO INTEGRAL DA LÓGICA ORIGINAL)
# ---------------------------------------------------------------------------------
SINONIMOS = {
    "Nome": ["nome", "contato", "cliente", "pessoa", "nome completo"],
    "Empresa": ["empresa", "organizacao", "organização", "company", "loja", "razao social", "razão social"],
    "CNPJ": ["cnpj", "cpf/cnpj", "documento", "doc"],
    "Funcao": ["funcao", "função", "cargo", "profissao", "profissão", "area", "área", "setor", "departamento"],
    "Telefone": ["telefone", "fone", "tel", "celular", "whatsapp", "whats", "numero", "número", "num", "cel"],
    "Email": ["email", "e-mail", "mail"],
}

COLUNAS_FINAIS = ["ID", "Empresa", "CNPJ", "Capital Social", "Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso", "Telefones", "E-mail", "Outros", "Status"]
CAMPOS_PADRONIZADOS = [c for c in COLUNAS_FINAIS if c not in ("Outros", "Status")]

RE_EMAIL = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
RE_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}")
RE_TELEFONE = re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?\(?\d{2}\)?[\s.\-]?\d{4,5}[\s.\-]?\d{4}")
RE_SEPARADORES = re.compile(r"[;,|\t]+")


def normalizar_texto(texto: str) -> str:
    """Remove acentos, espaços extras e coloca em minúsculo."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def identificar_campo(chave: str) -> str:
    """Recebe um rótulo e devolve a coluna padronizada."""
    chave_norm = normalizar_texto(chave)
    if chave_norm == "cpf":
        return "Outros"
    if chave_norm in {"id"}:
        return "ID"
    if chave_norm in {"empresa", "razao social", "razão social"}:
        return "Empresa"
    if chave_norm in {"cnpj", "cpf/cnpj"}:
        return "CNPJ"
    if chave_norm in {"capital social"}:
        return "Capital Social"
    if chave_norm in {"procurador", "nome", "nome completo", "nome do procurador"}:
        return "Procurador/Nome"
    if chave_norm in {"login"}:
        return "Login"
    if chave_norm in {"tipo de acesso"}:
        return "Tipo de Acesso"
    if chave_norm in {"ultimo acesso", "último acesso"}:
        return "Último Acesso"
    if chave_norm in {"telefone", "fone", "tel", "celular", "whatsapp", "whats", "numero", "número", "num", "cel"}:
        return "Telefones"
    if chave_norm in {"email", "e-mail", "mail"}:
        return "E-mail"
    return "Outros"


def registro_vazio() -> dict:
    return {campo: (False if campo == "Status" else "") for campo in COLUNAS_FINAIS}


def registro_tem_dados(registro: dict) -> bool:
    return any(registro[c] for c in CAMPOS_PADRONIZADOS)


def limpar_valor_campo(campo: str, valor: str) -> str:
    """Normaliza valores mantendo o texto limpo."""
    valor = str(valor).strip()
    if not valor:
        return ""
    valor = re.sub(r"\s+", " ", valor)

    if campo in {"Telefones", "Telefone"}:
        telefones = []
        for parte in re.split(r"\s*(?:\||/)\s*", valor):
            parte = parte.strip()
            if not parte:
                continue
            if ":" in parte:
                parte = parte.split(":", 1)[1].strip()
            match = RE_TELEFONE.search(parte)
            if match:
                telefones.append(match.group().strip())
            elif re.search(r"\d", parte):
                telefones.append(parte)
        return " | ".join(dict.fromkeys(telefones))

    if campo in {"E-mail", "Email"}:
        emails = [m.group().strip() for m in RE_EMAIL.finditer(valor)]
        return " | ".join(dict.fromkeys(emails)) if emails else valor

    if campo == "CNPJ":
        cnps = [m.group().strip() for m in RE_CNPJ.finditer(valor)]
        return " | ".join(dict.fromkeys(cnps)) if cnps else valor

    valor = re.sub(r"\s*[-–:]\s*", " ", valor).strip(" ,;|-")
    return re.sub(r"\s{2,}", " ", valor).strip()


def adicionar_valor(registro: dict, campo: str, valor: str) -> None:
    """Adiciona um valor em um campo sem duplicar informações."""
    limpo = limpar_valor_campo(campo, valor)
    if not limpo:
        return

    atual = str(registro[campo]).strip()
    if not atual:
        registro[campo] = limpo
        return

    valores = [v.strip() for v in atual.split("|") if v.strip()]
    novos = [v.strip() for v in limpo.split("|") if v.strip()]
    for item in novos:
        if item not in valores:
            valores.append(item)
    registro[campo] = " | ".join(valores)


def formatar_telefone_html(telefone: str, busca_terminacao: str = "") -> str:
    """Destaca visualmente os dois últimos dígitos do telefone com uma pílula no HTML."""
    if pd.isna(telefone):
        return ""

    texto = str(telefone).strip()
    if not texto:
        return ""

    partes = []
    for parte in re.split(r"\s*(?:\||/)\s*", texto):
        parte = parte.strip()
        if not parte:
            continue
        numeros = re.sub(r"\D", "", parte)
        if busca_terminacao and len(numeros) >= 2 and numeros[-2:] == busca_terminacao:
            digit_positions = [idx for idx, char in enumerate(parte) if char.isdigit()]
            if len(digit_positions) >= 2:
                start = digit_positions[-2]
                end = digit_positions[-1] + 1
                parte = (
                    f"{html.escape(parte[:start])}"
                    f"<span class='phone-badge'>{html.escape(parte[start:end])}</span>"
                    f"{html.escape(parte[end:])}"
                )
            else:
                parte = html.escape(parte)
        else:
            parte = html.escape(parte)
        partes.append(parte)
    return " <span class='phone-sep'>•</span> ".join(partes)


def montar_tabela_html(df: pd.DataFrame, busca_terminacao: str = "") -> str:
    """Renderiza a tabela estilizada em HTML com visual Taste Skill Dark Glass."""
    colunas = ["Procurador/Nome", "Empresa", "CNPJ", "Capital Social", "Telefones", "E-mail", "Outros", "Status"]
    
    if df.empty:
        return """
        <div class='empty-table-box'>
            <div class='empty-icon'>🔍</div>
            <div class='empty-title'>Nenhum contato encontrado</div>
            <div class='empty-sub'>Ajuste seus termos de busca ou filtros para visualizar os resultados.</div>
        </div>
        """

    linhas = [
        "<div class='table-container'>",
        "<table class='custom-table'>",
        "<thead><tr>"
    ]
    for coluna in colunas:
        icon_map = {
            "Procurador/Nome": "👤 ",
            "Empresa": "🏢 ",
            "CNPJ": "📄 ",
            "Capital Social": "💰 ",
            "Telefones": "📞 ",
            "E-mail": "✉️ ",
            "Outros": "📌 ",
            "Status": "⚡ "
        }
        ic = icon_map.get(coluna, "")
        linhas.append(f"<th>{ic}{coluna}</th>")
    linhas.append("</tr></thead><tbody>")

    for _, row in df.fillna("").iterrows():
        status_val = bool(row.get("Status", False))
        status_badge = (
            "<span class='status-badge completed'><span class='status-dot'></span>Concluído</span>"
            if status_val
            else "<span class='status-badge pending'><span class='status-dot'></span>Pendente</span>"
        )
        
        celulas = []
        for coluna in colunas:
            if coluna == "Status":
                celulas.append(f"<td class='text-center'>{status_badge}</td>")
                continue

            valor = "" if pd.isna(row[coluna]) else str(row[coluna])
            if coluna == "Telefones":
                valor = formatar_telefone_html(valor, busca_terminacao)
            elif coluna in {"CNPJ", "ID"}:
                valor = f"<code class='code-pill'>{html.escape(valor)}</code>" if valor else "-"
            elif coluna == "E-mail":
                if valor:
                    emails_formatted = [f"<span class='email-tag'>{html.escape(e.strip())}</span>" for e in valor.split("|")]
                    valor = " ".join(emails_formatted)
                else:
                    valor = "-"
            elif coluna == "Empresa":
                valor = f"<span class='empresa-name'>{html.escape(valor)}</span>" if valor else "-"
            elif coluna == "Procurador/Nome":
                valor = f"<span class='nome-procurador'>{html.escape(valor)}</span>" if valor else "-"
            else:
                valor = html.escape(valor).replace('\n', '<br>')
                if not valor:
                    valor = "-"
            celulas.append(f"<td>{valor}</td>")
        linhas.append(f"<tr>{''.join(celulas)}</tr>")

    linhas.append("</tbody></table></div>")
    return "".join(linhas)


def garantir_tipos_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que a coluna Status seja bool e todas as outras sejam str para evitar erros de tipo no Streamlit."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_FINAIS)
    df_out = df.copy()
    for col in COLUNAS_FINAIS:
        if col not in df_out.columns:
            df_out[col] = False if col == "Status" else ""
        elif col == "Status":
            df_out[col] = df_out[col].astype(bool)
        else:
            df_out[col] = df_out[col].fillna("").astype(str)
            df_out[col] = df_out[col].apply(lambda x: str(int(float(x))) if (isinstance(x, str) and x.endswith('.0') and x[:-2].isdigit()) else str(x))
            df_out[col] = df_out[col].replace("nan", "").replace("None", "")
    return df_out[COLUNAS_FINAIS]


def parse_txt(conteudo: str) -> pd.DataFrame:
    """Parser para relatórios em blocos com empresa + procuradores/usuários."""
    conteudo = conteudo.replace("\r\n", "\n").replace("\r", "\n")
    blocos = re.split(r"\n(?:={10,}|-{10,})\s*\n", conteudo)
    contatos = []

    for bloco in blocos:
        bloco = bloco.strip()
        if not bloco:
            continue

        linhas = [linha.strip() for linha in bloco.splitlines() if linha.strip()]
        registro_base = registro_vazio()
        registros = []
        perfil_atual = None
        dentro_perfis = False

        for linha in linhas:
            if not linha or linha.startswith("#"):
                continue
            if linha.startswith("=== USUÁRIOS E PERFIS ==="):
                dentro_perfis = True
                continue
            if linha.startswith("---"):
                if perfil_atual and any(perfil_atual.get(chave, "") for chave in ["Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"]):
                    registros.append(perfil_atual)
                perfil_atual = registro_vazio()
                continue
            if ":" not in linha:
                continue

            chave, valor = [parte.strip() for parte in linha.split(":", 1)]
            if not valor:
                continue

            if not dentro_perfis:
                campo = identificar_campo(chave)
                if campo in CAMPOS_PADRONIZADOS:
                    adicionar_valor(registro_base, campo, valor)
                else:
                    registro_base["Outros"] = f"{registro_base['Outros']} | {f'{chave}: {valor}'}".strip(" |")
            else:
                if perfil_atual is None:
                    perfil_atual = registro_vazio()
                campo = identificar_campo(chave)
                if campo in {"Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"}:
                    perfil_atual[campo] = valor
                elif campo in {"Telefones", "E-mail"}:
                    adicionar_valor(perfil_atual, campo, valor)
                else:
                    perfil_atual["Outros"] = f"{perfil_atual['Outros']} | {f'{chave}: {valor}'}".strip(" |")

        if perfil_atual and any(perfil_atual.get(chave, "") for chave in ["Procurador/Nome", "Login", "Tipo de Acesso", "Último Acesso"]):
            registros.append(perfil_atual)

        if registros:
            for perfil in registros:
                registro = registro_vazio()
                for campo in ["ID", "Empresa", "CNPJ", "Capital Social", "Telefones", "E-mail"]:
                    registro[campo] = registro_base[campo]
                registro["Procurador/Nome"] = perfil.get("Procurador/Nome", "")
                registro["Login"] = perfil.get("Login", "")
                registro["Tipo de Acesso"] = perfil.get("Tipo de Acesso", "")
                registro["Último Acesso"] = perfil.get("Último Acesso", "")
                if perfil.get("Telefones"):
                    adicionar_valor(registro, "Telefones", perfil["Telefones"])
                if perfil.get("E-mail"):
                    adicionar_valor(registro, "E-mail", perfil["E-mail"])
                registro["Outros"] = " | ".join([v for v in [registro_base.get("Outros"), perfil.get("Outros")] if v])
                registro["Status"] = False
                contatos.append(registro)
        else:
            registro_base["Outros"] = registro_base["Outros"].strip(" |")
            registro_base["Status"] = False
            if registro_tem_dados(registro_base):
                contatos.append(registro_base)

    return garantir_tipos_colunas(pd.DataFrame(contatos, columns=COLUNAS_FINAIS))


def chave_deduplicacao(row) -> str:
    """Gera chave para identificar contatos duplicados."""
    texto_telefones = str(row.get("Telefones", row.get("Telefone", "")))
    digitos = re.sub(r"\D", "", texto_telefones)
    if digitos:
        return f"tel:{digitos}"
    nome_norm = normalizar_texto(row.get("Procurador/Nome", row.get("Nome", "")))
    return f"nome:{nome_norm}" if nome_norm else None


def mesclar_contatos(df_antigo: pd.DataFrame, df_novo: pd.DataFrame) -> pd.DataFrame:
    """Junta contatos antigos e novos evitando duplicatas."""
    combinado = pd.concat([df_antigo, df_novo], ignore_index=True)
    combinado["_chave"] = combinado.apply(chave_deduplicacao, axis=1)

    sem_chave = combinado[combinado["_chave"].isna()].drop(columns=["_chave"])
    com_chave = combinado[combinado["_chave"].notna()]

    registros_mesclados = []
    for _, grupo in com_chave.groupby("_chave", sort=False):
        registro = {}
        for campo in CAMPOS_PADRONIZADOS + ["Outros"]:
            valores_preenchidos = [str(v) for v in grupo[campo] if str(v).strip()]
            registro[campo] = valores_preenchidos[0] if valores_preenchidos else ""
        registro["Status"] = bool(grupo["Status"].any())
        registros_mesclados.append(registro)

    df_dedup = pd.DataFrame(registros_mesclados, columns=COLUNAS_FINAIS)
    resultado = pd.concat([df_dedup, sem_chave], ignore_index=True)
    return garantir_tipos_colunas(resultado)


def carregar_dados_exemplo() -> pd.DataFrame:
    """Carrega dados de demonstração a partir do arquivo de amostra se existir."""
    caminho_amostra = os.path.join("dados", "amostra_contatos.txt")
    if os.path.exists(caminho_amostra):
        with open(caminho_amostra, "r", encoding="utf-8") as f:
            return parse_txt(f.read())
    else:
        # Fallback inline
        txt_demo = """ID: 101
Empresa: TechCorp Soluções Ltda
CNPJ: 12.345.678/0001-90
Capital Social: R$ 500.000,00
Procurador: Carlos Eduardo Silva
Telefone: (11) 98765-4321 | (11) 3456-7835
Email: carlos@techcorp.com.br
---
=== USUÁRIOS E PERFIS ===
Procurador: Mariana Oliveira
Telefone: (11) 97123-4535
Email: mariana@techcorp.com.br
----------------------------------------
ID: 102
Empresa: Nexus Logística S.A.
CNPJ: 98.765.432/0001-10
Procurador: Roberto Mendes
Telefone: (21) 98877-6655 | (21) 2544-3335
Email: roberto@nexuslog.com.br"""
        return parse_txt(txt_demo)


# ---------------------------------------------------------------------------------
# RECURSOS VISUAIS CLI (RICH TERMINAL - VISUAL MODERNO E ACOLHEDOR)
# ---------------------------------------------------------------------------------
COR_ROSA = "#f9a8d4"        # rosa suave
COR_ROSA_FORTE = "#ec4899"  # rosa vibrante
COR_LAVANDA = "#c4b5fd"     # lilás suave
COR_LILAS = "#a78bfa"       # lilás médio
COR_CEU = "#93c5fd"         # azul céu suave
COR_MENTA = "#86efac"       # menta
COR_VERDE = "#4ade80"       # verde suave
COR_AMARELO = "#fcd34d"     # amarelo suave
COR_VERMELHO = "#fca5a5"    # vermelho suave
COR_PESSEGO = "#fdba74"     # pêssego
COR_TEXTO = "#f5f0e6"       # texto creme
COR_SUAVE = "#a8a29e"       # texto secundário


def texto_gradiente(texto: str, cores: list) -> Text:
    """Aplica um gradiente suave de cores a um texto."""
    t = Text()
    if not texto:
        return t
    n = max(len(texto) - 1, 1)
    for i, ch in enumerate(texto):
        cor = cores[int(round(i * (len(cores) - 1) / n))]
        t.append(ch, style=f"bold {cor}")
    return t


def painel_cabecalho() -> Panel:
    """Banner de boas-vindas com gradiente suave e tom acolhedor."""
    titulo = texto_gradiente("⚡ ORGANIZADOR DE CONTATOS PRO ⚡", [COR_ROSA, COR_LILAS, COR_CEU])
    subtitulo = Text(
        "Interface inteligente para parsing, busca por terminação e gestão de contatos corporativos ✨",
        style=f"italic {COR_SUAVE}",
    )
    conteudo = Text()
    conteudo.append_text(titulo)
    conteudo.append("\n")
    conteudo.append_text(subtitulo)
    return Panel(Align.center(conteudo), border_style=COR_ROSA, box=box.ROUNDED, padding=(1, 2))


def painel_kpis(total: int, feitos: int, pendentes: int) -> Panel:
    """Indicadores principais em cartões suaves."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(
        f"[bold {COR_ROSA}]📁 Contatos Total[/bold {COR_ROSA}]\n[bold {COR_TEXTO}]{total}[/bold {COR_TEXTO}]",
        f"[bold {COR_VERDE}]✅ Concluídos[/bold {COR_VERDE}]\n[bold {COR_TEXTO}]{feitos}[/bold {COR_TEXTO}]",
        f"[bold {COR_AMARELO}]⏳ Pendentes[/bold {COR_AMARELO}]\n[bold {COR_TEXTO}]{pendentes}[/bold {COR_TEXTO}]",
    )
    return Panel(grid, border_style=COR_LAVANDA, box=box.ROUNDED, padding=(0, 1))


ITENS_MENU = [
    ("1", "📥  Importar arquivo .txt"),
    ("2", "📇  Listar todos os contatos"),
    ("3", "🔍  Pesquisar contatos (Busca geral / Terminação)"),
    ("4", "➕  Adicionar novo contato manualmente"),
    ("5", "✏️   Editar / alternar status do checklist"),
    ("6", "🗑️   Excluir contato"),
    ("7", "💾  Exportar base (.csv)"),
    ("8", "🧹  Limpar base de dados"),
    ("0", "🚪  Sair"),
]


def painel_menu() -> Panel:
    """Menu principal em formato de cartão amigável."""
    menu = Table(show_header=False, box=None, padding=(0, 1), pad_edge=False)
    menu.add_column("num", style=f"bold {COR_ROSA}", width=5, justify="right")
    menu.add_column("desc", style=COR_TEXTO)
    for num, desc in ITENS_MENU:
        menu.add_row(num, desc)
    return Panel(
        menu,
        title=f"[bold {COR_LILAS}]🌸 Selecione uma opção:[/bold {COR_LILAS}]",
        border_style=COR_ROSA,
        box=box.ROUNDED,
    )


def painel_titulo(texto: str, cor: str = COR_CEU) -> Panel:
    return Panel(Align.center(Text(texto, style=f"bold {cor}")), border_style=cor, box=box.ROUNDED)


def painel_sucesso(texto: str) -> Panel:
    return Panel(Text(f"✨ {texto}", style=f"bold {COR_VERDE}"), border_style=COR_VERDE, box=box.ROUNDED)


def painel_aviso(texto: str) -> Panel:
    return Panel(Text(f"💡 {texto}", style=f"bold {COR_AMARELO}"), border_style=COR_AMARELO, box=box.ROUNDED)


def painel_erro(texto: str) -> Panel:
    return Panel(Text(f"🥺 {texto}", style=f"bold {COR_VERMELHO}"), border_style=COR_VERMELHO, box=box.ROUNDED)


def formatar_telefone_rich(telefone: str, busca_terminacao: str = "") -> str:
    """Destaca os dois últimos dígitos do telefone no terminal Rich."""
    if pd.isna(telefone):
        return ""
    texto = str(telefone).strip()
    if not texto:
        return ""

    partes = []
    for parte in re.split(r"\s*(?:\||/)\s*", texto):
        parte = parte.strip()
        if not parte:
            continue
        numeros = re.sub(r"\D", "", parte)
        if busca_terminacao and len(numeros) >= 2 and numeros[-2:] == busca_terminacao:
            digit_positions = [idx for idx, char in enumerate(parte) if char.isdigit()]
            if len(digit_positions) >= 2:
                start = digit_positions[-2]
                end = digit_positions[-1] + 1
                parte = (
                    f"{parte[:start]}"
                    f"[bold #1f2937 on {COR_ROSA}]{parte[start:end]}[/bold #1f2937 on {COR_ROSA}]"
                    f"{parte[end:]}"
                )
        partes.append(parte)
    return " | ".join(partes)


def renderizar_tabela_cli(df: pd.DataFrame, busca_terminacao: str = "", max_linhas: int = 15, inicio: int = 0) -> Table:
    """Cria uma tabela Rich estilizada para o terminal."""
    table = Table(
        box=box.ROUNDED,
        border_style=COR_LAVANDA,
        header_style=f"bold {COR_LILAS}",
        title_style=f"bold {COR_CEU}",
        expand=True,
    )

    table.add_column("#", style=f"bold {COR_ROSA}", width=4, justify="right")
    table.add_column("Procurador/Nome", style=COR_TEXTO, min_width=20)
    table.add_column("Empresa", style=COR_CEU, min_width=18)
    table.add_column("CNPJ", style=COR_SUAVE, width=18)
    table.add_column("Telefones", style=COR_AMARELO, min_width=18)
    table.add_column("E-mail", style=COR_MENTA, min_width=20)
    table.add_column("Status", justify="center", width=12)

    df_subset = df.iloc[inicio : inicio + max_linhas] if max_linhas > 0 else df

    for idx, row in df_subset.iterrows():
        num_linha = str(idx + 1)
        nome = str(row.get("Procurador/Nome", "") or "")
        empresa = str(row.get("Empresa", "") or "")
        cnpj = str(row.get("CNPJ", "") or "")
        tel_raw = str(row.get("Telefones", "") or "")
        tel_formatted = formatar_telefone_rich(tel_raw, busca_terminacao)
        email = str(row.get("E-mail", "") or "")
        status_bool = bool(row.get("Status", False))

        status_str = (
            f"[bold {COR_VERDE}]✓ Feito[/bold {COR_VERDE}]"
            if status_bool
            else f"[bold {COR_AMARELO}]⏳ Pendente[/bold {COR_AMARELO}]"
        )

        table.add_row(
            num_linha,
            nome[:28] if len(nome) > 28 else (nome or f"[{COR_SUAVE}]-[/{COR_SUAVE}]"),
            empresa[:24] if len(empresa) > 24 else (empresa or f"[{COR_SUAVE}]-[/{COR_SUAVE}]"),
            cnpj or f"[{COR_SUAVE}]-[/{COR_SUAVE}]",
            tel_formatted or f"[{COR_SUAVE}]-[/{COR_SUAVE}]",
            email[:26] if len(email) > 26 else (email or f"[{COR_SUAVE}]-[/{COR_SUAVE}]"),
            status_str,
        )

    return table


def run_cli() -> None:
    """Interface Interativa via Linha de Comando (Rich CLI)."""
    configurar_console_windows()
    console = Console()

    df_contatos = None
    arquivo_salvo = "contatos_organizados.csv"
    if os.path.exists(arquivo_salvo):
        try:
            df_contatos = pd.read_csv(arquivo_salvo).fillna("")
            if "Status" in df_contatos.columns:
                df_contatos["Status"] = df_contatos["Status"].astype(bool)
        except Exception:
            df_contatos = None

    while True:
        console.clear()
        console.print(painel_cabecalho())

        total = len(df_contatos) if df_contatos is not None else 0
        feitos = int(df_contatos["Status"].sum()) if (df_contatos is not None and not df_contatos.empty and "Status" in df_contatos.columns) else 0
        pendentes = total - feitos

        console.print(painel_kpis(total, feitos, pendentes))
        console.print(painel_menu())

        opcao = Prompt.ask("\n[bold]Escolha uma opção[/bold]", choices=[item[0] for item in ITENS_MENU], default="1")

        if opcao == "1":
            console.clear()
            console.print(painel_titulo("📥 Importar Arquivo .TXT"))
            caminho = Prompt.ask("Digite o caminho do arquivo .txt (ou ENTER para usar arquivo de exemplo)", default=os.path.join("dados", "amostra_contatos.txt"))
            if not os.path.exists(caminho):
                console.print(painel_erro(f"Arquivo '{caminho}' não encontrado!"))
            else:
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        texto = f.read()
                except UnicodeDecodeError:
                    with open(caminho, "r", encoding="latin-1") as f:
                        texto = f.read()

                df_novo = parse_txt(texto)
                if df_novo.empty:
                    console.print(painel_aviso("Nenhum contato válido foi lido do arquivo."))
                else:
                    if df_contatos is not None and not df_contatos.empty:
                        acumular = Confirm.ask("Já existem contatos na memória. Deseja ACUMULAR novos dados?", default=True)
                        if acumular:
                            df_contatos = mesclar_contatos(df_contatos, df_novo)
                        else:
                            df_contatos = df_novo
                    else:
                        df_contatos = df_novo
                    df_contatos.to_csv(arquivo_salvo, index=False, encoding="utf-8-sig")
                    console.print(painel_sucesso(f"{len(df_novo)} contatos importados com sucesso!"))

            Prompt.ask(f"\n[italic {COR_SUAVE}]Pressione ENTER para voltar ao menu...[/italic {COR_SUAVE}]")

        elif opcao == "2":
            console.clear()
            console.print(painel_titulo("📇 Todos os Contatos"))
            if df_contatos is None or df_contatos.empty:
                console.print(painel_aviso("Nenhum contato carregado na base."))
            else:
                console.print(renderizar_tabela_cli(df_contatos, max_linhas=0))
            Prompt.ask(f"\n[italic {COR_SUAVE}]Pressione ENTER para voltar...[/italic {COR_SUAVE}]")

        elif opcao == "3":
            console.clear()
            console.print(painel_titulo("🔍 Pesquisa Geral e Terminação Telefônica"))
            if df_contatos is None or df_contatos.empty:
                console.print(painel_aviso("Nenhum contato carregado para pesquisar."))
            else:
                termo = Prompt.ask("Digite o termo de busca geral (ou ENTER para ignorar)", default="")
                terminacao = Prompt.ask("Digite os 2 últimos dígitos do telefone (ex: 35, ou ENTER para ignorar)", default="")
                
                df_fil = df_contatos.copy()
                if termo.strip():
                    t_norm = termo.strip().lower()
                    mascara = df_fil.apply(
                        lambda r: t_norm in str(r.get("Procurador/Nome", "")).lower()
                        or t_norm in str(r.get("Empresa", "")).lower()
                        or t_norm in str(r.get("Telefones", "")).lower()
                        or t_norm in str(r.get("E-mail", "")).lower(),
                        axis=1
                    )
                    df_fil = df_fil[mascara]

                dig = re.sub(r"\D", "", terminacao)
                if len(dig) == 2:
                    mascara_term = df_fil["Telefones"].apply(
                        lambda tel: any(re.sub(r"\D", "", t)[-2:] == dig for t in str(tel).split("|") if t.strip())
                    )
                    df_fil = df_fil[mascara_term]

                console.print(f"\n✨ Foram encontrados [bold {COR_ROSA}]{len(df_fil)}[/bold {COR_ROSA}] contatos correspondentes:\n")
                console.print(renderizar_tabela_cli(df_fil, busca_terminacao=dig, max_linhas=0))

            Prompt.ask(f"\n[italic {COR_SUAVE}]Pressione ENTER para voltar ao menu...[/italic {COR_SUAVE}]")

        elif opcao == "7":
            console.clear()
            console.print(painel_titulo("💾 Exportar Base (.csv)"))
            if df_contatos is None or df_contatos.empty:
                console.print(painel_aviso("Nenhuma base carregada."))
            else:
                nome_exp = Prompt.ask("Nome do arquivo de saída", default="contatos_organizados.csv")
                df_contatos.to_csv(nome_exp, index=False, encoding="utf-8-sig")
                console.print(painel_sucesso(f"Base salva com sucesso em '{nome_exp}'!"))
            Prompt.ask(f"\n[italic {COR_SUAVE}]Pressione ENTER para voltar...[/italic {COR_SUAVE}]")

        elif opcao == "8":
            console.clear()
            console.print(painel_titulo("🧹 Limpar Base de Dados", cor=COR_VERMELHO))
            if df_contatos is not None and not df_contatos.empty:
                if Confirm.ask("Tem certeza que deseja apagar todos os contatos?", default=False):
                    df_contatos = None
                    if os.path.exists(arquivo_salvo):
                        os.remove(arquivo_salvo)
                    console.print(painel_sucesso("Base limpa com sucesso!"))
            Prompt.ask(f"\n[italic {COR_SUAVE}]Pressione ENTER para voltar...[/italic {COR_SUAVE}]")

        elif opcao == "0":
            console.clear()
            console.print(painel_sucesso("Até logo! 👋✨"))
            break


def obter_gatinho_base64() -> str:
    """Retorna a imagem do gatinho em formato base64 para renderização confiável em HTML."""
    caminho = "gatinho.jpg"
    if os.path.exists(caminho):
        try:
            import base64
            with open(caminho, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            return ""
    return ""


# ---------------------------------------------------------------------------------
# INTERFACE STREAMLIT - TASTE SKILL (PRO FRONTEND STANDARDS)
# ---------------------------------------------------------------------------------
def run_app() -> None:
    if not STREAMLIT_DISPONIVEL:
        return

    # Inicialização de Session State (Sempre inicia 100% zerado aguardando o usuário)
    if "df_contatos" not in st.session_state:
        st.session_state.df_contatos = None
    if "nome_arquivo_atual" not in st.session_state:
        st.session_state.nome_arquivo_atual = None

    # --- SIDEBAR CONTROL PANEL (TASTE SKILL GLASS DESIGN) ---
    with st.sidebar:
        st.markdown("""
            <div class="sidebar-brand">
                <div class="brand-icon">📇</div>
                <div class="brand-text">
                    <div class="brand-title">Organizador de Contatos</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<hr class='glass-divider'>", unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section-title">⚙️ CONFIGURAÇÕES DE DADOS</div>', unsafe_allow_html=True)
        modo_importacao = st.radio(
            "Modo de Importação:",
            options=["🔄 Substituir Base Atual", "➕ Acumular Novos Dados"],
            index=0,
            help="Substituir reseta a tabela. Acumular junta novos registros evitando duplicatas por telefone/nome."
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">⚡ AÇÕES RÁPIDAS</div>', unsafe_allow_html=True)
        
        col_side1, col_side2 = st.columns(2)
        with col_side1:
            if st.button("🧪 Usar Demo", help="Carrega a base de demonstração instantaneamente"):
                st.session_state.df_contatos = carregar_dados_exemplo()
                st.session_state.nome_arquivo_atual = "amostra_contatos.txt (Demo)"
                st.rerun()
        with col_side2:
            if st.button("🗑️ Limpar Base", help="Limpa todos os dados da memória"):
                st.session_state.df_contatos = None
                st.session_state.nome_arquivo_atual = None
                if os.path.exists("contatos_organizados.csv"):
                    try:
                        os.remove("contatos_organizados.csv")
                    except Exception:
                        pass
                st.rerun()

        st.markdown("<br><hr class='glass-divider'>", unsafe_allow_html=True)
        st.markdown("""
            <div class="sidebar-footer">
                <div>Organizador de Contatos</div>
            </div>
        """, unsafe_allow_html=True)

    # --- INJEÇÃO DE CSS TASTE SKILL SYSTEM ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* RESET E VARIÁVEIS DO SISTEMA TASTE SKILL */
        :root {
            --bg-canvas: #07090e;
            --card-glass-bg: rgba(15, 18, 28, 0.72);
            --card-glass-hover: rgba(22, 27, 42, 0.85);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glass-hover: rgba(255, 255, 255, 0.22);
            --accent-indigo: #6366f1;
            --accent-indigo-glow: rgba(99, 102, 241, 0.35);
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --text-title: #ffffff;
            --text-body: #e2e8f0;
            --text-muted: #94a3b8;
            --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-heading: 'Plus Jakarta Sans', sans-serif;
            --font-code: 'JetBrains Mono', monospace;
        }

        html, body, [class*="css"] {
            font-family: var(--font-main) !important;
            color: var(--text-body) !important;
        }

        /* FUNDO COM TEXTURA SVG E AMBIENT GLOW MESH */
        .stApp {
            background-color: var(--bg-canvas) !important;
            background-image: 
                radial-gradient(ellipse 90% 60% at 50% -10%, rgba(99, 102, 241, 0.16), transparent 70%),
                radial-gradient(ellipse 60% 40% at 85% 60%, rgba(6, 182, 212, 0.08), transparent 60%),
                radial-gradient(ellipse 50% 50% at 15% 85%, rgba(16, 185, 129, 0.06), transparent 60%),
                url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.025'/%3E%3C/svg%3E") !important;
            background-attachment: fixed !important;
        }

        /* ESCONDE CABEÇALHO PADRÃO STREAMLIT */
        [data-testid="stHeader"] {
            background: transparent !important;
        }

        /* SIDEBAR GLASSMORPHISM APERFEIÇOADO */
        [data-testid="stSidebar"] {
            background: rgba(10, 12, 19, 0.82) !important;
            backdrop-filter: blur(28px) saturate(200%) !important;
            -webkit-backdrop-filter: blur(28px) saturate(200%) !important;
            border-right: 1px solid var(--border-glass) !important;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 0;
        }

        .brand-icon {
            font-size: 1.8rem;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.2));
            border: 1px solid var(--border-glass-hover);
            border-radius: 14px;
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }

        .brand-title {
            font-family: var(--font-heading);
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        .brand-badge {
            font-size: 0.68rem;
            font-family: var(--font-code);
            color: var(--accent-cyan);
            font-weight: 600;
            letter-spacing: 0.05em;
        }

        .glass-divider {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-glass-hover), transparent);
            margin: 16px 0;
        }

        .sidebar-section-title {
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--text-muted);
            letter-spacing: 0.08em;
            margin-bottom: 10px;
        }

        .sidebar-footer {
            text-align: center;
            font-size: 0.78rem;
            color: var(--text-muted);
        }
        
        .footer-sub {
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 2px;
        }

        /* HERO APP HEADER */
        .hero-container {
            text-align: center;
            padding: 2.2rem 1rem 1.8rem 1rem;
            position: relative;
        }

        .hero-badge-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(99, 102, 241, 0.12);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 9999px;
            padding: 6px 16px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #a5b4fc;
            letter-spacing: 0.03em;
            margin-bottom: 1rem;
            box-shadow: 0 0 20px var(--accent-indigo-glow);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-emerald);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-emerald);
            animation: pulse-glow 2s infinite;
        }

        @keyframes pulse-glow {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .hero-title-app {
            font-family: var(--font-heading);
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            background: linear-gradient(135deg, #ffffff 30%, #cbd5e1 70%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.6rem;
            line-height: 1.1;
        }

        .hero-sub-app {
            font-size: 1.05rem;
            color: var(--text-muted);
            max-width: 680px;
            margin: 0 auto;
            line-height: 1.6;
            font-weight: 400;
        }

        /* CARD GLASS CONTAINER (TASTE SKILL STANDARD) */
        .card-glass {
            background: var(--card-glass-bg) !important;
            backdrop-filter: blur(24px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
            border: 1px solid var(--border-glass) !important;
            border-radius: 20px !important;
            padding: 1.6rem !important;
            margin-bottom: 1.4rem !important;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }

        .card-glass:hover {
            border-color: var(--border-glass-hover) !important;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.55), 0 0 30px rgba(99, 102, 241, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        }

        .widget-header {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: var(--font-heading);
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
            margin-bottom: 0.3rem;
        }

        .widget-subtitle {
            font-size: 0.86rem;
            color: var(--text-muted);
            margin-bottom: 1.2rem;
        }

        /* KPI METRICS GRID */
        .kpi-card {
            background: rgba(18, 22, 34, 0.65) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid var(--border-glass) !important;
            border-radius: 18px !important;
            padding: 1.3rem 1.2rem !important;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35) !important;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-indigo), var(--accent-cyan));
            opacity: 0.6;
            transition: opacity 0.25s ease;
        }

        .kpi-card:hover {
            transform: translateY(-3px) !important;
            border-color: var(--border-glass-hover) !important;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5) !important;
        }

        .kpi-card:hover::before {
            opacity: 1;
        }

        .kpi-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.6rem;
        }

        .kpi-icon {
            font-size: 1.3rem;
            background: rgba(255, 255, 255, 0.06);
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .kpi-val {
            font-family: var(--font-heading);
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            color: #ffffff !important;
            letter-spacing: -0.03em !important;
            line-height: 1 !important;
        }

        .kpi-label {
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            color: var(--text-muted) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            margin-top: 0.4rem !important;
        }

        .kpi-tag {
            font-size: 0.72rem;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 9999px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        .kpi-tag.success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .kpi-tag.warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .kpi-tag.info {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        /* ESTILIZAÇÃO DOS INPUTS STREAMLIT */
        div[data-baseweb="input"] {
            background: rgba(10, 14, 23, 0.7) !important;
            border: 1px solid var(--border-glass) !important;
            border-radius: 12px !important;
            color: #ffffff !important;
            padding: 4px 12px !important;
            transition: all 0.2s ease !important;
        }

        div[data-baseweb="input"]:focus-within, div[data-baseweb="input"]:hover {
            border-color: var(--accent-indigo) !important;
            box-shadow: 0 0 20px var(--accent-indigo-glow) !important;
            background: rgba(15, 20, 32, 0.85) !important;
        }

        div[data-baseweb="input"] input {
            color: #ffffff !important;
            font-size: 0.95rem !important;
            font-family: var(--font-main) !important;
        }

        /* BOTÕES ESTILIZADOS TASTE SKILL */
        .stButton > button, .stDownloadButton > button {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.85), rgba(124, 58, 237, 0.85)) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 12px !important;
            padding: 0.65rem 1.6rem !important;
            font-family: var(--font-heading) !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.01em !important;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.35) !important;
            width: 100% !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
            border-color: rgba(255, 255, 255, 0.4) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 30px rgba(99, 102, 241, 0.5) !important;
        }

        /* FILE UPLOADER PERSONALIZADO */
        [data-testid="stFileUploader"] {
            background: rgba(12, 16, 26, 0.5) !important;
            border: 2px dashed rgba(99, 102, 241, 0.35) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            transition: all 0.25s ease !important;
        }

        [data-testid="stFileUploader"]:hover {
            border-color: var(--accent-indigo) !important;
            background: rgba(18, 24, 40, 0.7) !important;
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.15) !important;
        }

        /* TABELA HTML PERSONALIZADA (TASTE DARK GLASS) */
        .table-container {
            width: 100%;
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--border-glass);
            background: rgba(10, 13, 20, 0.6);
            backdrop-filter: blur(16px);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.45);
        }

        .custom-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.88rem;
            color: var(--text-body);
        }

        .custom-table thead th {
            background: rgba(20, 25, 38, 0.85);
            color: #ffffff;
            text-align: left;
            padding: 0.95rem 1.1rem;
            font-family: var(--font-heading);
            font-weight: 700;
            letter-spacing: 0.04em;
            border-bottom: 1px solid var(--border-glass-hover);
            text-transform: uppercase;
            font-size: 0.74rem;
            white-space: nowrap;
        }

        .custom-table tbody tr {
            transition: all 0.15s ease;
            border-left: 3px solid transparent;
        }

        .custom-table tbody tr:hover {
            background: rgba(30, 37, 56, 0.5);
            border-left-color: var(--accent-indigo);
        }

        .custom-table tbody td {
            padding: 0.9rem 1.1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: middle;
            line-height: 1.4;
        }

        .custom-table tbody tr:last-child td {
            border-bottom: none;
        }

        .text-center {
            text-align: center !important;
        }

        /* BADGES E COMPONENTES DE TABELA */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.76rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .status-badge.completed {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.35);
        }

        .status-badge.pending {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }

        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }

        .status-badge.completed .status-dot {
            background-color: #34d399;
            box-shadow: 0 0 8px #34d399;
        }

        .status-badge.pending .status-dot {
            background-color: #fbbf24;
            box-shadow: 0 0 8px #fbbf24;
        }

        .phone-badge {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            font-family: var(--font-code);
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            box-shadow: 0 0 12px rgba(37, 99, 235, 0.6);
            letter-spacing: 0.05em;
        }

        .phone-sep {
            color: rgba(255, 255, 255, 0.25);
            margin: 0 4px;
        }

        .code-pill {
            font-family: var(--font-code);
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: #cbd5e1;
        }

        .email-tag {
            display: inline-block;
            color: #93c5fd;
            background: rgba(147, 197, 253, 0.08);
            border: 1px solid rgba(147, 197, 253, 0.2);
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.8rem;
            margin-right: 4px;
        }

        .nome-procurador {
            font-weight: 600;
            color: #ffffff;
        }

        .empresa-name {
            color: #e2e8f0;
            font-weight: 500;
        }

        .empty-table-box {
            text-align: center;
            padding: 3rem 1rem;
            background: rgba(12, 15, 24, 0.5);
            border: 1px dashed var(--border-glass-hover);
            border-radius: 16px;
        }

        .empty-icon {
            font-size: 2.5rem;
            margin-bottom: 0.6rem;
        }

        .empty-title {
            font-family: var(--font-heading);
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.3rem;
        }

        .empty-sub {
            font-size: 0.88rem;
            color: var(--text-muted);
        }

        /* BARRA DE PROGRESSO */
        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, var(--accent-indigo), var(--accent-emerald)) !important;
            border-radius: 9999px !important;
        }

        .stProgress > div > div {
            background-color: rgba(255, 255, 255, 0.08) !important;
            border-radius: 9999px !important;
            height: 10px !important;
        }

        /* GATINHO FLUTUANTE WIDGET (TASTE GLASS) */
        .floating-cat-box {
            position: fixed;
            bottom: 25px;
            right: 25px;
            z-index: 99999;
            background: rgba(12, 15, 23, 0.85);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--border-glass-hover);
            border-radius: 20px;
            padding: 10px 14px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7), 0 0 20px rgba(99, 102, 241, 0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .floating-cat-box:hover {
            border-color: rgba(99, 102, 241, 0.5);
            transform: translateY(-4px) scale(1.03);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(99, 102, 241, 0.3);
        }

        .floating-cat-box img {
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .cat-text-container {
            text-align: left;
        }

        .cat-title {
            font-family: var(--font-heading);
            font-size: 0.82rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .cat-sub {
            font-size: 0.72rem;
            color: var(--text-muted);
        }

        /* VÍDEO DO GATINHO NO FUNDO (DESFOCADO) */
        .bottom-cat-video-card {
            position: relative;
            width: 100%;
            height: 220px;
            border-radius: 22px;
            overflow: hidden;
            margin-top: 2rem;
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-glass-hover);
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.6);
        }

        .blurred-bg-video {
            position: absolute;
            top: 50%;
            left: 50%;
            min-width: 100%;
            min-height: 100%;
            width: auto;
            height: auto;
            transform: translate(-50%, -50%);
            filter: blur(8px) brightness(0.6) saturate(120%);
            object-fit: cover;
            pointer-events: none;
        }

        .video-overlay-tint {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at center, rgba(10, 13, 20, 0.25) 0%, rgba(7, 9, 14, 0.8) 100%);
        }

        .video-card-content {
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 1.5rem;
        }

        .video-cat-badge {
            font-size: 0.82rem;
            font-weight: 700;
            color: #ffffff;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            padding: 4px 14px;
            border-radius: 9999px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            margin-bottom: 0.6rem;
            letter-spacing: 0.03em;
        }

        .video-card-title {
            font-family: var(--font-heading);
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.03em;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.7);
        }

        .video-card-sub {
            font-size: 0.9rem;
            color: #cbd5e1;
            margin-top: 0.3rem;
            text-shadow: 0 1px 6px rgba(0, 0, 0, 0.7);
        }
        </style>
    """, unsafe_allow_html=True)

    # --- GATINHO FLUTUANTE WIDGET (DEEP GLASS TASTE) ---
    cat_b64 = obter_gatinho_base64()
    if cat_b64:
        st.markdown(f"""
            <div class="floating-cat-box">
                <img src="{cat_b64}" width="48" height="48" style="object-fit: cover; border-radius: 12px;">
                <div class="cat-text-container">
                    <div class="cat-title"><span class="pulse-dot"></span> Gatinho Assistant</div>
                    <div class="cat-sub">Supervisão de Dados 🐾</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --- HERO APP HEADER ---
    st.markdown("""
        <div class="hero-container">
            <div class="hero-title-app">Organizador de Contatos</div>
            <div class="hero-sub-app">
                Sistema avançado de parsing cadastral, busca inteligente por terminação numérica e gestão corporativa em tempo real.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 1. UPLOAD WIDGET CARD ---
    st.markdown("""
        <div class="card-glass">
            <div class="widget-header">📥 1. Carregar Relatório de Contatos (.TXT)</div>
            <div class="widget-subtitle">Arraste ou selecione o arquivo .TXT para extração automática de dados estruturados</div>
    """, unsafe_allow_html=True)

    arquivo = st.file_uploader("Selecione o arquivo TXT", type=["txt"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    if arquivo is not None and st.session_state.nome_arquivo_atual != arquivo.name:
        bytes_conteudo = arquivo.getvalue()
        try:
            texto = bytes_conteudo.decode("utf-8")
        except UnicodeDecodeError:
            texto = bytes_conteudo.decode("latin-1")

        df_novo = parse_txt(texto)

        if df_novo.empty:
            st.warning("⚠️ Nenhum contato válido foi identificado no arquivo fornecido.")
        else:
            if modo_importacao.startswith("➕") and st.session_state.df_contatos is not None:
                st.session_state.df_contatos = mesclar_contatos(st.session_state.df_contatos, df_novo)
                st.success(f"✅ {len(df_novo)} novos contatos processados e mesclados!")
            else:
                st.session_state.df_contatos = df_novo
                st.success(f"✅ Base carregada! {len(df_novo)} contatos estruturados.")
            
            st.session_state.df_contatos.to_csv("contatos_organizados.csv", index=False, encoding="utf-8-sig")
            st.session_state.nome_arquivo_atual = arquivo.name

    # --- STATE VAZIO / EMPTY HERO CARD ---
    if st.session_state.df_contatos is None or st.session_state.df_contatos.empty:
        st.markdown("""
            <div class="card-glass" style="text-align: center; padding: 2.5rem 1.5rem !important;">
                <div style="font-size: 3rem; margin-bottom: 0.8rem;">📂</div>
                <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: #ffffff; margin-bottom: 0.4rem;">Nenhum arquivo de contatos ativo</div>
                <div style="font-size: 0.92rem; color: var(--text-muted); max-width: 500px; margin: 0 auto 1.5rem auto;">
                    Carregue um arquivo de contatos em formato .TXT acima ou clique abaixo para testar o sistema com a base de demonstração.
                </div>
            </div>
        """, unsafe_allow_html=True)
        col_demo_center, _ = st.columns([1, 0.001])
        with col_demo_center:
            if st.button("✨ Carregar Base de Demonstração (Demo)"):
                st.session_state.df_contatos = carregar_dados_exemplo()
                st.session_state.nome_arquivo_atual = "amostra_contatos.txt (Demo)"
                st.session_state.df_contatos.to_csv("contatos_organizados.csv", index=False, encoding="utf-8-sig")
                st.rerun()
        st.stop()

    df = st.session_state.df_contatos

    # --- 2. KPI METRICS SUMMARY GRID ---
    total = len(df)
    feitos = int(df["Status"].sum()) if "Status" in df.columns else 0
    pendentes = total - feitos
    pct_concluido = int((feitos / total) * 100) if total > 0 else 0
    empresas_unicas = len(df["Empresa"].unique()) if "Empresa" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-top">
                    <div class="kpi-icon">📁</div>
                    <span class="kpi-tag info">Total</span>
                </div>
                <div class="kpi-val">{total}</div>
                <div class="kpi-label">Contatos na Base</div>
            </div>
        ''', unsafe_allow_html=True)

    with c2:
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-top">
                    <div class="kpi-icon">✅</div>
                    <span class="kpi-tag success">{pct_concluido}% Taxa</span>
                </div>
                <div class="kpi-val">{feitos}</div>
                <div class="kpi-label">Concluídos</div>
            </div>
        ''', unsafe_allow_html=True)

    with c3:
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-top">
                    <div class="kpi-icon">⏳</div>
                    <span class="kpi-tag warning">A Fazer</span>
                </div>
                <div class="kpi-val">{pendentes}</div>
                <div class="kpi-label">Pendentes</div>
            </div>
        ''', unsafe_allow_html=True)

    with c4:
        st.markdown(f'''
            <div class="kpi-card">
                <div class="kpi-top">
                    <div class="kpi-icon">🏢</div>
                    <span class="kpi-tag info">Empresas</span>
                </div>
                <div class="kpi-val">{empresas_unicas}</div>
                <div class="kpi-label">Organizações Únicas</div>
            </div>
        ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. FILTROS E PESQUISA TELEFÔNICA WIDGET CARD ---
    st.markdown("""
        <div class="card-glass">
            <div class="widget-header">🔍 2. Filtros & Busca por Terminação</div>
            <div class="widget-subtitle">Pesquise por nome, empresa ou filtre pelos 2 últimos dígitos dos números telefônicos</div>
    """, unsafe_allow_html=True)

    col_b1, col_b2, col_b3 = st.columns([2.5, 1.5, 1.2])
    with col_b1:
        busca_geral = st.text_input("Busca Geral", placeholder="🔎 Pesquisar nome, empresa, e-mail...", label_visibility="collapsed")
    with col_b2:
        busca_terminacao = st.text_input("Final Telefone", placeholder="📞 Últimos 2 dígitos (Ex: 35)", max_chars=2, label_visibility="collapsed")
    with col_b3:
        filtro_status = st.selectbox("Status", ["Todos", "Pendentes ⏳", "Concluídos ✅"], label_visibility="collapsed")

    st.markdown("</div>", unsafe_allow_html=True)

    # Aplicação dos Filtros
    df_filtrado = df.copy()
    if busca_geral.strip():
        termo = busca_geral.strip().lower()
        mascara_geral = df_filtrado.apply(
            lambda row: termo in str(row.get("Procurador/Nome", "")).lower()
            or termo in str(row.get("Empresa", "")).lower()
            or termo in str(row.get("Telefones", "")).lower()
            or termo in str(row.get("E-mail", "")).lower()
            or termo in str(row.get("CNPJ", "")).lower()
            or termo in str(row.get("Outros", "")).lower(),
            axis=1,
        )
        df_filtrado = df_filtrado[mascara_geral]

    if busca_terminacao.strip():
        digitos = re.sub(r"\D", "", busca_terminacao)
        if len(digitos) == 2:
            mascara_terminacao = df_filtrado["Telefones"].apply(
                lambda tel: any(re.sub(r"\D", "", t)[-2:] == digitos for t in str(tel).split("|") if t.strip())
            )
            df_filtrado = df_filtrado[mascara_terminacao]

    if filtro_status == "Pendentes ⏳":
        df_filtrado = df_filtrado[df_filtrado["Status"] == False]
    elif filtro_status == "Concluídos ✅":
        df_filtrado = df_filtrado[df_filtrado["Status"] == True]

    # --- 4. EXIBIÇÃO DA TABELA HTML TASTE GLASS ---
    st.markdown(f"""
        <div class="card-glass">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.8rem;">
                <div class="widget-header" style="margin-bottom: 0;">📊 3. Visualização dos Contatos Estruturados</div>
                <div style="font-size: 0.82rem; font-weight: 600; color: var(--accent-indigo); background: rgba(99, 102, 241, 0.12); padding: 4px 12px; border-radius: 9999px; border: 1px solid rgba(99, 102, 241, 0.3);">
                    Exibindo {len(df_filtrado)} de {total} contatos
                </div>
            </div>
    """, unsafe_allow_html=True)
    
    st.markdown(montar_tabela_html(df_filtrado, busca_terminacao=busca_terminacao.strip()), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 5. CHECKLIST E EDIÇÃO WIDGET CARD ---
    st.markdown("""
        <div class="card-glass">
            <div class="widget-header">✅ 4. Controle de Status & Edição Interativa</div>
            <div class="widget-subtitle">Marque os contatos como concluídos ou edite os dados em tempo real</div>
    """, unsafe_allow_html=True)

    df_editor_input = garantir_tipos_colunas(df_filtrado)

    df_editado = st.data_editor(
        df_editor_input,
        width='stretch',
        hide_index=True,
        column_config={
            "Status": st.column_config.CheckboxColumn("Concluído?", default=False),
            "ID": st.column_config.TextColumn("ID"),
            "Empresa": st.column_config.TextColumn("Empresa"),
            "CNPJ": st.column_config.TextColumn("CNPJ"),
            "Capital Social": st.column_config.TextColumn("Capital Social"),
            "Procurador/Nome": st.column_config.TextColumn("Procurador/Nome"),
            "Login": st.column_config.TextColumn("Login"),
            "Tipo de Acesso": st.column_config.TextColumn("Tipo de Acesso"),
            "Último Acesso": st.column_config.TextColumn("Último Acesso"),
            "Telefones": st.column_config.TextColumn("Telefones"),
            "E-mail": st.column_config.TextColumn("E-mail"),
            "Outros": st.column_config.TextColumn("Outros Dados"),
        },
        key="editor_contatos",
    )

    if "df_contatos" in st.session_state and st.session_state.df_contatos is not None:
        estado = st.session_state.df_contatos.copy()
        colunas = [c for c in df_editado.columns if c in estado.columns]
        estado.loc[df_filtrado.index, colunas] = df_editado[colunas].values
        st.session_state.df_contatos = estado
        # Persiste alterações no arquivo local
        st.session_state.df_contatos.to_csv("contatos_organizados.csv", index=False, encoding="utf-8-sig")

    total_atual = len(st.session_state.df_contatos)
    feitos_atual = int(st.session_state.df_contatos["Status"].sum())
    progresso = feitos_atual / total_atual if total_atual else 0
    
    st.markdown(f"<div style='font-size: 0.84rem; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; margin-top: 12px;'>Progresso Geral do Checklist: {int(progresso * 100)}% ({feitos_atual}/{total_atual})</div>", unsafe_allow_html=True)
    st.progress(progresso)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 6. EXPORTAÇÃO WIDGET CARD ---
    st.markdown("""
        <div class="card-glass">
            <div class="widget-header">💾 5. Exportar Base Organizada</div>
            <div class="widget-subtitle">Baixe a base de dados tratada e atualizada no formato CSV</div>
    """, unsafe_allow_html=True)

    csv_bytes = st.session_state.df_contatos.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Baixar Tabela Organizada (.CSV)",
        data=csv_bytes,
        file_name="contatos_organizados.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # --- VÍDEO DO GATINHO NO FUNDO (DESFOCADO) AO FINAL DA PÁGINA ---
    video_path = "gatinho.mp4"
    if os.path.exists(video_path):
        try:
            import base64
            with open(video_path, "rb") as f:
                v_encoded = base64.b64encode(f.read()).decode("utf-8")
                video_src = f"data:video/mp4;base64,{v_encoded}"
        except Exception:
            video_src = "https://assets.mixkit.co/videos/preview/mixkit-cat-looking-at-the-camera-41555-large.mp4"
    else:
        video_src = "https://assets.mixkit.co/videos/preview/mixkit-cat-looking-at-the-camera-41555-large.mp4"

    st.markdown(f"""
        <div class="bottom-cat-video-card">
            <video autoplay loop muted playsinline class="blurred-bg-video">
                <source src="{video_src}" type="video/mp4">
            </video>
            <div class="video-overlay-tint"></div>
            <div class="video-card-content">
                <div class="video-cat-badge">🐾 Gatinho Assistant</div>
                <div class="video-card-title">Organizador de Contatos</div>
                <div class="video-card-sub">Sistema de Processamento e Gestão Cadastral</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------------
# PONTO DE ENTRADA DO APLICATIVO
# ---------------------------------------------------------------------------------
if __name__ == "__main__":
    if STREAMLIT_DISPONIVEL and hasattr(st, "runtime") and st.runtime.exists():
        run_app()
    else:
        run_cli()
