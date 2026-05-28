"""Unit tests for src/reports/pdf_exporter.py"""
import os

from openpyxl import Workbook
from openpyxl.worksheet.pagebreak import Break

from tests.fakes.fake_win32com import FakeWin32ComClient, FakeWin32ComModule
from src.reports import pdf_exporter


def _criar_xlsx_real(path: str) -> None:
    """Cria um xlsx mínimo válido (load_workbook do pdf_exporter requer isso)."""
    wb = Workbook()
    wb.save(path)


def _criar_xlsx_com_break(path: str, break_id: int) -> None:
    """Cria xlsx com 1 page-break manual na row indicada."""
    wb = Workbook()
    ws = wb.active
    ws.row_breaks.append(Break(id=break_id))
    wb.save(path)


def test_exportar_pdf_retorna_caminho_pdf(tmp_path, monkeypatch):
    fake_client = FakeWin32ComClient()
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    _criar_xlsx_real(excel_path)

    result = pdf_exporter.exportar_pdf(excel_path)

    assert result.endswith(".pdf")


def test_exportar_pdf_cria_arquivo_pdf(tmp_path, monkeypatch):
    fake_client = FakeWin32ComClient()
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    _criar_xlsx_real(excel_path)

    result = pdf_exporter.exportar_pdf(excel_path)

    assert os.path.exists(result)


def test_exportar_pdf_reaplica_breaks_do_xlsx_via_com(tmp_path, monkeypatch):
    """Excel via COM nem sempre respeita os page-breaks salvos pelo openpyxl.
    O exporter deve LER as quebras do xlsx e re-aplicar via HPageBreaks.Add
    para garantir que o Excel honre."""
    from tests.fakes.fake_win32com import FakeWorksheet, FakeWorkbook, _FakeWorkbooks

    sheet_alvo = FakeWorksheet(name="Sheet")
    wb_fake = FakeWorkbook(worksheets=[sheet_alvo])

    class _ExcelAppComWb:
        Visible = True
        DisplayAlerts = True

        def __init__(self):
            self.Workbooks = _FakeWorkbooks(wb_fake)

        def Quit(self):
            pass

    fake_client = FakeWin32ComClient(excel_app=_ExcelAppComWb())
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    _criar_xlsx_com_break(excel_path, break_id=28)

    pdf_exporter.exportar_pdf(excel_path)

    assert sheet_alvo.HPageBreaks.added == [28], \
        f"Esperava HPageBreaks.Add(28), recebi {sheet_alvo.HPageBreaks.added}"


def test_exportar_pdf_centraliza_verticalmente(tmp_path, monkeypatch):
    """As 2 câmeras IP extras (bloco largo) ficavam no rodapé da página 2 —
    com CenterVertically=True elas ficam centralizadas verticalmente."""
    from tests.fakes.fake_win32com import FakeWorksheet, FakeWorkbook, _FakeWorkbooks

    sheet_alvo = FakeWorksheet()
    wb_fake = FakeWorkbook(worksheets=[sheet_alvo])

    class _ExcelAppComWb:
        Visible = True
        DisplayAlerts = True

        def __init__(self):
            self.Workbooks = _FakeWorkbooks(wb_fake)

        def Quit(self):
            pass

    fake_client = FakeWin32ComClient(excel_app=_ExcelAppComWb())
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    _criar_xlsx_real(excel_path)

    pdf_exporter.exportar_pdf(excel_path)

    assert sheet_alvo.PageSetup.CenterVertically is True


def test_exportar_pdf_fecha_workbook_e_encerra_excel(tmp_path, monkeypatch):
    """Garante que Close e Quit são chamados (sem leak de processo Excel)."""
    from tests.fakes.fake_win32com import FakeWorkbook

    close_calls = []
    quit_calls = []

    class _TrackingWorkbook(FakeWorkbook):
        def Close(self, save_changes):
            close_calls.append(save_changes)

    class _TrackingExcelApp:
        Visible = True
        DisplayAlerts = True

        def __init__(self):
            self._wb = _TrackingWorkbook()
            from tests.fakes.fake_win32com import _FakeWorkbooks
            self.Workbooks = _FakeWorkbooks(self._wb)

        def Quit(self):
            quit_calls.append(True)

    from tests.fakes.fake_win32com import FakeWin32ComClient, _FakeWorkbooks

    fake_client = FakeWin32ComClient(excel_app=_TrackingExcelApp())
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    _criar_xlsx_real(excel_path)

    pdf_exporter.exportar_pdf(excel_path)

    assert len(close_calls) == 1
    assert close_calls[0] is False   # não salvar alterações
    assert len(quit_calls) == 1
