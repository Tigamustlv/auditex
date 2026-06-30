import pdfplumber
import re


ASSINANTES = {
"V8": "MAISAGIL",
"Prata": "PRATA DIGITAL",
"Taya": "TAYA TECH"
}

# =========================
# UTILITÁRIOS
# =========================

def extrair_texto_pdf(pdf_file):
    texto = ""

    with pdfplumber.open(pdf_file) as pdf:
        for pagina in pdf.pages:
            conteudo = pagina.extract_text()
            if conteudo:
                texto += conteudo + "\n"

    return texto


def limpar_cpf(cpf):
    return re.sub(r'\D', '', cpf or "")


def normalizar_nome(nome):
    return (nome or "").lower().strip()


def normalizar_valor(valor):
    if not valor:
        return None
    return valor.replace("R$", "").strip()


# =========================
# CCB
# =========================

def extrair_cpf_ccb(texto):

    # padrão principal
    match = re.search(
        r'CPF\s*sob\s*n[ºo]\s*([\d\.\-]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        return limpar_cpf(match.group(1))

    # fallback (PDF quebrado)
    match2 = re.search(
        r'CPF.*?(\d{3}\.\d{3}\.\d{3}-\d{2})',
        texto,
        re.DOTALL
    )

    if match2:
        return limpar_cpf(match2.group(1))

    return None


def extrair_valor_liberado(texto):

    # regra principal: após "a.m."
    match = re.search(
        r'a\.m\.\s*R\$\s*([\d\.,]+)',
        texto,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    # fallback: label explícito
    match2 = re.search(
        r'Valor Liberado ao Cliente.*?R\$\s*([\d\.,]+)',
        texto,
        re.DOTALL
    )

    if match2:
        return match2.group(1)

    return None

def extrair_valor_total(texto):

    match = re.search(
    r'Valor Total da Dívida:\s*R\$\s*([\d\.,]+)',
    texto
    )
    
    if match:
        vlrTCCB = float(
            match.group(1)
            .replace('.', '')
            .replace(',', '.')
        )

    else:
        vlrTCCB = "Valor Não encontrado."

    return(vlrTCCB)


def extrair_parc(pdf_file):
    qtd_parcelas = 0
    valor_total = 0.0

    with pdfplumber.open(pdf_file) as pdf:
        tabela = pdf.pages[1].extract_tables()[0]

        for linha in tabela:
            if linha and linha[0] and linha[0].isdigit():
                qtd_parcelas += 1

                valor = linha[3]
                valor = valor.replace(".", "").replace(",", ".")
                valor_total += float(valor)

    valor_formatado = (
        f"{valor_total:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return valor_total, valor_formatado, qtd_parcelas
     

def parse_ccb(
    texto,
    qtd_parcelas=None,
    valor_total_parcelas=None
):

    dados = {}

    # KG
    kg = re.search(r'KG Nº\s*(\S+)', texto)
    if kg:
        dados['kg'] = kg.group(1).strip()

    # Nome
    nome = re.search(r'Nome:\s*(.*?)\,', texto)
    if nome:
        dados['nome'] = nome.group(1).strip()

    # CPF
    dados['cpf'] = extrair_cpf_ccb(texto)

    # Valor liberado
    dados['valor'] = extrair_valor_liberado(texto)

    # Endosso
    dados['tem_endosso'] = 'termo de endosso' in texto.lower()

    assinante_encontrado = None
    texto_lower = texto.lower()

    for chave_empresa, nome_assinante in ASSINANTES.items():

        if nome_assinante.lower() in texto_lower:
            assinante_encontrado = chave_empresa
            break

    dados['assinante'] = assinante_encontrado

    dados['Valor Total CCB'] = extrair_valor_total(texto)

    # Novos campos (somente se forem informados)
    if qtd_parcelas is not None:
        dados['Quantidade de Parcelas'] = qtd_parcelas

    if valor_total_parcelas is not None:
        dados['Valor Total Parcelas'] = valor_total_parcelas

    return dados



# =========================
# COMPROVANTE
# =========================

def parse_comprovante(texto):

    dados = {}

    linhas = [
        l.strip()
        for l in texto.splitlines()
        if l.strip()
    ]

    # valor
    for i, linha in enumerate(linhas):
        if linha.lower() == 'valor':
            if i + 1 < len(linhas):
                dados['valor'] = normalizar_valor(linhas[i + 1])

    # nome
    for i, linha in enumerate(linhas):
        if linha.lower() == 'nome':
            if i + 1 < len(linhas):
                dados['nome'] = linhas[i + 1]

    # CPF mascarado
    cpf = re.search(r'\*{3}\.(\d{3})\.(\d{3})-\*{2}', texto)

    if cpf:
        dados['cpf_miolo'] = cpf.group(1) + cpf.group(2)

    return dados


# =========================
# TERMO
# =========================

def parse_termo(texto):

    dados = {}

    nome = re.search(
        r'Nome do assinante:\s*(.*)',
        texto
    )

    if nome:
        dados['nome'] = nome.group(1).strip()

    cpf = re.search(
        r'Número do CPF:\s*(\d+)',
        texto
    )

    if cpf:
        dados['cpf'] = limpar_cpf(cpf.group(1))

    return dados


# =========================
# VALIDAÇÃO (LEGACY)
# =========================

def validar_operacao(ccb, comp, termo):

    return {
        "nome_ok":
            normalizar_nome(ccb.get("nome")) ==
            normalizar_nome(comp.get("nome")) ==
            normalizar_nome(termo.get("nome")),

        "cpf_ok":
            limpar_cpf(ccb.get("cpf")) ==
            limpar_cpf(comp.get("cpf")) ==
            limpar_cpf(termo.get("cpf")),

        "valor_ok":
            normalizar_valor(ccb.get("valor")) ==
            normalizar_valor(comp.get("valor")),

        "endosso_ok":
            ccb.get("tem_endosso", False) is True
    }