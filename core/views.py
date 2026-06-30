from django.shortcuts import render
from django.http import HttpResponse

import zipfile
from collections import defaultdict

from .services.auditor import identificar_docs
from .services.auditor_core import auditar_dados
from .services.excel import gerar_excel


from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'auditex/index.html')


@login_required
def upload(request):

    resultado_final = {}
    total_pastas = 0
    total_itens = 0

    if request.method == 'POST':

        empresa = request.POST.get('empresa')
        arquivo_zip = request.FILES.get('zipfile')

        if arquivo_zip:

            # =========================
            # CONTAGEM DE PASTAS/ITENS
            # =========================
            with zipfile.ZipFile(arquivo_zip) as z:

                arquivos = [
                    f for f in z.namelist()
                    if not f.endswith('/')
                ]

                pastas = defaultdict(int)

                for item in arquivos:
                    pasta_raiz = item.split('/')[0]
                    pastas[pasta_raiz] += 1

                total_pastas = len(pastas)
                total_itens = sum(pastas.values())

            # reset arquivo
            arquivo_zip.seek(0)

            # =========================
            # CHECKLIST
            # =========================
            resultado_checklist = identificar_docs(
                arquivo_zip,
                empresa
            )

            # reset arquivo
            arquivo_zip.seek(0)

            # =========================
            # AUDITORIA
            # =========================
            resultado_auditoria = auditar_dados(
                arquivo_zip,
                empresa
            )

            # =========================
            # MERGE FINAL
            # =========================
            resultado_final = {}

            for operacao in resultado_checklist.keys():

                checklist = resultado_checklist.get(operacao, {})
                auditoria = resultado_auditoria.get(operacao, {})

                status_final = (
                    "Completa"
                    if checklist.get("status") == "Completa"
                    and len(auditoria.get("inconsistencias", [])) == 0
                    else "Incompleta"
                )

                resultado_final[operacao] = {

                    "status": status_final,
                    "faltando": checklist.get("faltando", []),

                    "inconsistencias": auditoria.get("inconsistencias", []),
                    "alertas": auditoria.get("alertas", []),
                    "dados": auditoria.get("dados_extraidos", {})
                }

            # salva sessão
            request.session["resultado"] = resultado_final

    return render(request, 'auditex/upload.html', {
        "resultado": resultado_final if request.method == "POST" else None,
        "total_pastas": total_pastas,
        "total_itens": total_itens
    })


@login_required
def export_excel(request):

    resultado = request.session.get("resultado")

    if not resultado:
        return HttpResponse("Nada para exportar")

    file = gerar_excel(resultado)

    response = HttpResponse(
        file.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="auditoria.xlsx"'
    )

    return response