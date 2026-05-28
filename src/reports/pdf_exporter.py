from __future__ import annotations

from typing import Dict, List

import win32com.client
from openpyxl import load_workbook


def exportar_pdf(excel_path: str) -> str:
    """
    Abre excel_path via COM do Excel e exporta como PDF.

    PERFORMANCE: page setup (orientação, margens, fit-to-page, centralização)
    é setado pelos *_builders via openpyxl e gravado no xlsx. NÃO precisamos
    re-aplicar via COM aqui — isso era um loop de ~1500 chamadas COM em
    workbooks com muitas sheets (book com 200+ câmeras = 200+ sheets).

    A única coisa que justifica tocar nas sheets via COM são page-breaks
    manuais, que o Excel às vezes não honra direto do xlsx. Se o xlsx
    não tem page-breaks (caso comum agora com a estratégia "1 sheet por
    seção"), pulamos o loop inteiro.

    ScreenUpdating=False e EnableEvents=False reduzem overhead do Excel
    durante a abertura/export.

    Retorna o caminho do PDF gerado (mesmo prefixo, extensão .pdf).
    """
    pdf_path = excel_path.replace(".xlsx", ".pdf")

    # ── 1. Pre-leio as quebras manuais do xlsx (so se houver) ──
    breaks_por_sheet = _ler_breaks(excel_path)

    # ── 2. Abre via COM com flags de performance ──
    excel_app = win32com.client.DispatchEx("Excel.Application")
    excel_app.Visible = False
    excel_app.DisplayAlerts = False
    excel_app.ScreenUpdating = False
    excel_app.EnableEvents = False

    wb = excel_app.Workbooks.Open(excel_path)

    # ── 3. Re-aplica page-breaks (só se o xlsx tem algum) ──
    # Excel via COM nem sempre honra page-breaks salvos pelo openpyxl;
    # quando há, re-aplicamos via HPageBreaks.Add (confiável).
    if breaks_por_sheet:
        for sheet in wb.Worksheets:
            breaks = breaks_por_sheet.get(sheet.Name)
            if breaks:
                sheet.ResetAllPageBreaks()
                for row_idx in breaks:
                    sheet.HPageBreaks.Add(sheet.Rows(row_idx))

    # ── 4. Exporta ──
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
