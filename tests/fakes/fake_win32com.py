class _FakePageSetup:
    PrintArea = ""
    Orientation = 1
    Zoom = True
    FitToPagesWide = 1
    FitToPagesTall = 1
    CenterHorizontally = False


class _FakeRows:
    Count = 10


class _FakeUsedRange:
    Rows = _FakeRows()


class FakeWorksheet:
    def __init__(self):
        self.UsedRange = _FakeUsedRange()
        self.PageSetup = _FakePageSetup()

    def ResetAllPageBreaks(self):
        pass


class FakeWorkbook:
    def __init__(self, worksheets=None):
        self.Worksheets = worksheets or [FakeWorksheet()]
        self.export_calls = []

    def ExportAsFixedFormat(self, format_type, path):
        self.export_calls.append(path)
        open(path, "wb").close()

    def Close(self, save_changes):
        pass


class _FakeWorkbooks:
    def __init__(self, workbook):
        self._wb = workbook

    def Open(self, path):
        return self._wb


class FakeExcelApp:
    def __init__(self, workbook=None):
        self.Visible = True
        self.DisplayAlerts = True
        self._wb = workbook or FakeWorkbook()
        self.Workbooks = _FakeWorkbooks(self._wb)

    def Quit(self):
        pass


class _FakeAttachments:
    def __init__(self):
        self.paths = []

    def Add(self, path):
        self.paths.append(path)


class FakeMail:
    def __init__(self):
        self.To = ""
        self.Subject = ""
        self.Body = ""
        self.Attachments = _FakeAttachments()
        self.sent = False

    def Send(self):
        self.sent = True


class FakeOutlookApp:
    def __init__(self):
        self.last_mail = None

    def CreateItem(self, item_type):
        self.last_mail = FakeMail()
        return self.last_mail


class FakeWin32ComClient:
    """
    Drop-in replacement for the win32com.client module.

    Holds one ExcelApp and one OutlookApp so tests can inspect calls
    after the function under test completes.
    """

    def __init__(self, excel_app=None, outlook_app=None):
        self.excel = excel_app or FakeExcelApp()
        self.outlook = outlook_app or FakeOutlookApp()

    def DispatchEx(self, prog_id):
        if "Excel" in prog_id:
            return self.excel
        raise ValueError(f"DispatchEx: unrecognised prog_id {prog_id!r}")

    def Dispatch(self, prog_id):
        if "Outlook" in prog_id:
            return self.outlook
        raise ValueError(f"Dispatch: unrecognised prog_id {prog_id!r}")


class FakeWin32ComModule:
    """
    Drop-in replacement for the entire win32com package.

    Use with monkeypatch.setattr(legacy_module, "win32com", FakeWin32ComModule(fake_client))
    so that legacy_module.win32com.client.Dispatch / DispatchEx hit the fake.
    """

    def __init__(self, client: FakeWin32ComClient = None):
        self.client = client or FakeWin32ComClient()
