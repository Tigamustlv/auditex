import zipfile


from .pdf_reader import (
    extrair_texto_pdf,
    parse_ccb,
    parse_comprovante,
    parse_termo,
    limpar_cpf,
    normalizar_nome,
    extrair_parc,
    extrair_valor_total
)


# =========================
# IDENTIFICAÇÃO MAIS RÁPIDA
# =========================

def identificar_tipo(nome_arquivo):

    nome = nome_arquivo.lower()

    if 'contrato assinado' in nome:
        return "ccb"

    if 'payment_receipt' in nome:
        return "comprovante"

    if (
        'termo de consentimento' in nome
        or 'evidências' in nome
    ):
        return "termo"

    return None


# =========================
# MAIN
# =========================

def auditar_dados(arquivo_zip, empresa):

    resultado = {}

    operacoes = {}

    with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:

        arquivos = zip_ref.namelist()

        # =========================
        # LEITURA + CLASSIFICAÇÃO
        # =========================
        for arquivo in arquivos:

            if arquivo.endswith('/'):
                continue

            partes = arquivo.split('/')

            if len(partes) < 2:
                continue

            operacao = partes[0]
            nome_arquivo = partes[-1]

            if operacao not in operacoes:
                operacoes[operacao] = {
                    "ccb": None,
                    "comprovante": None,
                    "termo": None
                }

            tipo = identificar_tipo(nome_arquivo)

            if not tipo:
                continue

            # abre PDF apenas se necessário
            try:
                with zip_ref.open(arquivo) as pdf_file:

                    texto = extrair_texto_pdf(pdf_file)

                    if tipo == "ccb":

                        pdf_file.seek(0)
                        valor_total, valor_formatado, qtd_parcelas = extrair_parc(pdf_file)
                        vlrTCCB = extrair_valor_total(texto)

                        ccb = parse_ccb(texto)

                        ccb['Quantidade de Parcelas'] = qtd_parcelas
                        ccb['Valor Total Parcelas'] = round(valor_total, 2)

                        operacoes[operacao]["ccb"] = ccb

                    elif tipo == "comprovante":
                        operacoes[operacao]["comprovante"] = parse_comprovante(texto)

                    elif tipo == "termo":
                        operacoes[operacao]["termo"] = parse_termo(texto)
            except Exception:
                continue
            
    # =========================
    # VALIDAÇÕES
    # =========================

    for operacao, docs in operacoes.items():

        inconsistencias = []
        alertas = []

        ccb = docs.get("ccb")
        comprovante = docs.get("comprovante")
        termo = docs.get("termo")

        # =====================
        # KG
        # =====================
        if ccb and ccb.get("kg") != operacao:
            inconsistencias.append("KG divergente da pasta da operação")

        # =====================
        # ENDOSSO
        # =====================
        if ccb and not ccb.get("tem_endosso"):
            alertas.append("Necessário termo de endosso")



        # ================
        # ASSINATURA
        # ================


        if ccb:

            assinante = ccb.get('assinante')

            if assinante and assinante != empresa:
                alertas.append(
                    f'CCB assinada por {assinante.upper()} encontrada na auditoria da {empresa.upper()}'
                )

            elif not assinante:
                alertas.append(
                    f'Assinante não presente na lista de empresas FGTS'
                )
        # =====================
        # NOMES
        # =====================
        nomes = []

        if ccb and ccb.get("nome"):
            nomes.append(normalizar_nome(ccb["nome"]))

        if comprovante and comprovante.get("nome"):
            nomes.append(normalizar_nome(comprovante["nome"]))

        if termo and termo.get("nome"):
            nomes.append(normalizar_nome(termo["nome"]))

        if len(set(nomes)) > 1 and len(nomes) > 0:
            inconsistencias.append("Nome divergente entre documentos")

        # =====================
        # VALOR
        # =====================
        if ccb and comprovante:
            if ccb.get("valor") != comprovante.get("valor"):
                inconsistencias.append("Valor divergente entre CCB e comprovante")


        if abs(valor_total - vlrTCCB) > 0.01:
            inconsistencias.append("Valor divergente entre CCB x SumParcelas")
        else:
            alertas.append("Valor total batendo entre CCB x SumParcelas")

        # =====================
        # CPF
        # =====================
        if ccb:

            cpf_ccb = limpar_cpf(ccb.get("cpf", ""))
            miolo_ccb = cpf_ccb[3:9]

            if comprovante:
                if comprovante.get("cpf_miolo") != miolo_ccb:
                    inconsistencias.append("CPF divergente entre CCB e comprovante")

            if termo:
                cpf_termo = limpar_cpf(termo.get("cpf", ""))

                if cpf_termo != cpf_ccb:
                    inconsistencias.append("CPF divergente entre CCB e termo")

        resultado[operacao] = {
            "inconsistencias": inconsistencias,
            "alertas": alertas,
            "dados_extraidos": docs
        }


    return resultado