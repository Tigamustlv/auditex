from openpyxl import Workbook
from io import BytesIO


def gerar_excel(resultado):

    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoria"

    # =========================
    # CABEÇALHO
    # =========================
    ws.append([
        "KG",
        "Status",
        "Pendências",
        "Inconsistências",
        "Alertas",


        "Nome CCB",
        "CPF CCB",
        "Valor CCB",

        "Nome OK",
        "CPF OK",
        "Valor OK",

        "Endosso" 
        ])

    # =========================
    # LINHAS
    # =========================
    for kg, dados in resultado.items():

        dados = dados or {}

        raw = dados.get("dados") or {}

        ccb = raw.get("ccb") or {}
        comp = raw.get("comprovante") or {}
        termo = raw.get("termo") or {}

        inconsistencias = dados.get("inconsistencias", [])

        # =========================
        # FLAGS (OK / NOK)
        # =========================
        nome_ok = "OK" if "Nome divergente entre documentos" not in inconsistencias else "NOK"

        cpf_ok = "OK" if not any("CPF divergente" in i for i in inconsistencias) else "NOK"

        valor_ok = "OK" if "Valor divergente entre CCB e comprovante" not in inconsistencias else "NOK"

        endosso_status = "SIM" if ccb.get("tem_endosso", False) else "NÃO"


        # =========================
        # LINHA
        # =========================
        ws.append([
            kg,
            dados.get("status", "-"),
            ", ".join(dados.get("faltando", [])) or "-",
            ", ".join(inconsistencias) or "-",
            ", ".join(dados.get("alertas", [])) or "-",

            ccb.get("nome", "-"),
            ccb.get("cpf", "-"),
            ccb.get("valor", "-"),

            nome_ok,
            cpf_ok,
            valor_ok,

            endosso_status
        ])

    # =========================
    # OUTPUT
    # =========================
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output