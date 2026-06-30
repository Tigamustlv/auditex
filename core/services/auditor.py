import zipfile


PADROES = {

    'Taya': [

        ('ccb', lambda nome: '_contrato assinado' in nome.lower()),

        ('receipt', lambda nome: 'payment_receipt' in nome.lower()),

        (
            'document',
            lambda nome: any(p in nome.lower() for p in [
                '_rg_',
                '_cnh_'
            ])
        ),

        ('selfie', lambda nome: 'foto do cliente' in nome.lower()),

        ('termo_consentimento', lambda nome: any(p in nome.lower() for p in ['_termo de consentimento_', 'evidências'])),
    ],

    'Prata': [

        ('CCB', lambda nome: 'contract' in nome.lower()),
    ],

    'V8': [
        ('ccb', lambda nome: 'ccb' in nome.lower()),
        ('receipt', lambda nome: 'receipt' in nome.lower()),
        ('document', lambda nome: 'document' in nome.lower()),
        ('selfie', lambda nome: 'selfie' in nome.lower())
    ]

}


def identificar_docs(arquivo_zip, empresa):

    checklist = PADROES[empresa]

    operacoes = {}

    with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:

        arquivos = zip_ref.namelist()

        for arquivo in arquivos:

            # Ignora pastas vazias
            if arquivo.endswith('/'):
                continue

            partes = arquivo.split('/')

            # Garante estrutura:
            # Operacao1/arquivo.pdf
            if len(partes) < 2:
                continue

            operacao = partes[0]

            nome_arquivo = partes[-1].lower()

            # Cria operação caso não exista
            if operacao not in operacoes:

                operacoes[operacao] = []

            # Verifica padrões
            for doc_nome, regra in checklist:

                if regra(nome_arquivo):

                    # Evita duplicidade
                    if doc_nome not in operacoes[operacao]:

                        operacoes[operacao].append(doc_nome)

    resultado = {}

    # Validação final
    for operacao, docs in operacoes.items():

        faltando = []

        for doc_nome, regra in checklist:

            if doc_nome not in docs:

                faltando.append(doc_nome)

        resultado[operacao] = {

            'status': (
                'Completa'
                if not faltando
                else 'Incompleta'
            ),

            'faltando': faltando,

            'documentos_enviados': docs
        }

    return resultado


