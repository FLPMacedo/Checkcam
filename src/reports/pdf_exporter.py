from __future__ import annotations

import win32com.client


def exportar_pdf(excel_path: str) -> str:
    """
    Abre excel_path via COM do Excel, configura impressão em paisagem
    ajustada a 1 página de largura e exporta para PDF.

    Fecha o workbook e encerra o processo Excel ao final.
    Retorna o caminho do PDF gerado (mesmo prefixo, extensão .pdf).
    """
    pdf_path = excel_path.replace(".xlsx", ".pdf")

    excel_app = win32com.client.DispatchEx("Excel.Application")
    excel_app.Visible = False
    excel_app.DisplayAlerts = False

    wb = excel_app.Workbooks.Open(excel_path)

    for sheet in wb.Worksheets:
        sheet.ResetAllPageBreaks()

        last_row = sheet.UsedRange.Rows.Count
        sheet.PageSetup.PrintArea = f"$A$1:$H${last_row}"

        ps = sheet.PageSetup
        ps.Orientation = 2        # Paisagem
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False
        ps.CenterHorizontally = True

    wb.ExportAsFixedFormat(0, pdf_path)
    wb.Close(False)
    excel_app.Quit()

    return pdf_path
