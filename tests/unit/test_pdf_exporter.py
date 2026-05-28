"""Unit tests for src/reports/pdf_exporter.py"""
import os

from tests.fakes.fake_win32com import FakeWin32ComClient, FakeWin32ComModule
from src.reports import pdf_exporter


def test_exportar_pdf_retorna_caminho_pdf(tmp_path, monkeypatch):
    fake_client = FakeWin32ComClient()
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    open(excel_path, "wb").close()

    result = pdf_exporter.exportar_pdf(excel_path)

    assert result.endswith(".pdf")


def test_exportar_pdf_cria_arquivo_pdf(tmp_path, monkeypatch):
    fake_client = FakeWin32ComClient()
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    open(excel_path, "wb").close()

    result = pdf_exporter.exportar_pdf(excel_path)

    assert os.path.exists(result)


def test_exportar_pdf_preserva_page_breaks_definidos_no_xlsx(tmp_path, monkeypatch):
    """Regressão: ResetAllPageBreaks() apagava as quebras definidas no openpyxl.
    O exporter NÃO deve chamar isso — quebras vêm do xlsx e devem ser respeitadas."""
    from tests.fakes.fake_win32com import FakeWorksheet, FakeWorkbook

    ws_com_breaks = FakeWorksheet()
    wb = FakeWorkbook(worksheets=[ws_com_breaks])

    class _ExcelAppComWb:
        Visible = True
        DisplayAlerts = True

        def __init__(self):
            from tests.fakes.fake_win32com import _FakeWorkbooks
            self.Workbooks = _FakeWorkbooks(wb)

        def Quit(self):
            pass

    fake_client = FakeWin32ComClient(excel_app=_ExcelAppComWb())
    monkeypatch.setattr(pdf_exporter, "win32com", FakeWin32ComModule(fake_client))

    excel_path = str(tmp_path / "relatorio.xlsx")
    open(excel_path, "wb").close()

    pdf_exporter.exportar_pdf(excel_path)

    assert ws_com_breaks.reset_page_breaks_calls == 0, \
        "ResetAllPageBreaks() foi chamado — apaga quebras de página do xlsx"


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
    open(excel_path, "wb").close()

    pdf_exporter.exportar_pdf(excel_path)

    assert len(close_calls) == 1
    assert close_calls[0] is False   # não salvar alterações
    assert len(quit_calls) == 1
