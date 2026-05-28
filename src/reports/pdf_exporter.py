from __future__ import annotations

from typing import Dict, List

import win32com.client
from openpyxl import load_workbook


def exportar_pdf(excel_path: str) -> str:
    """
    Abre excel_path via COM do Excel, configura impressão em paisagem
    ajustada a 1 página de largura e exporta para PDF.

    Page-breaks manuais definidos no xlsx (via openpyxl) NÃO são aplicados
    de forma confiável pelo Excel quando o arquivo é aberto via COM. Por
    isso, esta função:
      1. Lê as quebras com openpyxl ANTES de abrir via COM
      2. Reseta quebras existentes no Excel (auto + manuais que não foram lidas)
      3. Re-aplica as quebras lidas via HPageBreaks.Add (confiável)

    Centraliza horizontal E verticalmente — útil para o bloco de câmeras IP
    extras que sai sozinho numa página secundária.

    Retorna o caminho do PDF gerado (mesmo prefixo, extensão .pdf).
    """
    pdf_path = excel_path.replace(".xlsx", ".pdf")

    # ── 1. Lê as quebras de página manuais do xlsx via openpyxl ──
    breaks_por_sheet = _ler_breaks(excel_path)

    # ── 2. Abre via COM e exporta ──
    excel_app = win32com.client.DispatchEx("Excel.Application")
    excel_app.Visible = False
    excel_app.DisplayAlerts = False

    wb = excel_app.Workbooks.Open(excel_path)

    for sheet in wb.Worksheets:
        # Reseta quebras (limpa auto-breaks do Excel + manuais não confiáveis)
        sheet.ResetAllPageBreaks()

        # Re-aplica as quebras manuais lidas do xlsx, via COM (confiável)
        for row_idx in breaks_por_sheet.get(sheet.Name, []):
            sheet.HPageBreaks.Add(sheet.Rows(row_idx))

        last_row = sheet.UsedRange.Rows.Count
        sheet.PageSetup.PrintArea = f"$A$1:$H${last_row}"

        ps = sheet.PageSetup
        ps.Orientation = 2          # Paisagem
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False
        ps.CenterHorizontally = True
        ps.CenterVertically = True  # centra o conteúdo na vertical da página

    wb.ExportAsFixedFormat(0, pdf_path)
    wb.Close(False)
    excel_app.Quit()

    return pdf_path


def _ler_breaks(excel_path: str) -> Dict[str, List[int]]:
    """Devolve {nome_da_aba: [row_id, ...]} para todas as quebras manuais."""
    wb_op = load_workbook(excel_path)
    resultado: Dict[str, List[int]] = {}
    for ws in wb_op.worksheets:
        if ws.row_breaks and ws.row_breaks.brk:
            resultado[ws.title] = [b.id for b in ws.row_breaks.brk]
    return resultado
