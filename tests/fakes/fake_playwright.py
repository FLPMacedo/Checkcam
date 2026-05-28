try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    class PlaywrightTimeoutError(Exception):
        pass


class FakeCell:
    def __init__(self, text):
        self._text = text

    def text_content(self):
        return self._text

    def query_selector_all(self, selector):
        return []


class FakeRow:
    def __init__(self, cell_texts):
        self._cells = [FakeCell(t) for t in cell_texts]

    def query_selector_all(self, selector):
        return self._cells


class FakeKeyboard:
    def press(self, key):
        pass


class FakePage:
    def __init__(self, rows=None, raise_on_goto=False, raise_on_selector=False):
        self._rows = rows or []
        self._raise_on_goto = raise_on_goto
        self._raise_on_selector = raise_on_selector
        self.keyboard = FakeKeyboard()

    def goto(self, url, **kwargs):
        if self._raise_on_goto:
            raise PlaywrightTimeoutError("goto timeout")

    def fill(self, selector, value):
        pass

    def wait_for_timeout(self, ms):
        pass

    def click(self, selector):
        pass

    def wait_for_selector(self, selector, **kwargs):
        if self._raise_on_selector:
            raise PlaywrightTimeoutError("selector timeout")

    def query_selector_all(self, selector):
        return self._rows


class FakeBrowser:
    def __init__(self, page):
        self._page = page

    def new_page(self):
        return self._page

    def close(self):
        pass


class FakeChromium:
    def __init__(self, page):
        self._page = page

    def launch(self, **kwargs):
        return FakeBrowser(self._page)


class FakePlaywrightContext:
    def __init__(self, page):
        self.chromium = FakeChromium(page)


class FakeSyncPlaywright:
    """Context manager compatible with sync_playwright()."""

    def __init__(self, page):
        self._page = page

    def __enter__(self):
        return FakePlaywrightContext(self._page)

    def __exit__(self, *args):
        pass


# ─── Pre-configured factories ─────────────────────────────────────────────────

def make_playwright_with_hd(total_gb: float, livre_gb: float) -> FakeSyncPlaywright:
    """DVR online with HD data: two cells containing GB values."""
    rows = [FakeRow([f"{total_gb:.2f} GB", f"{livre_gb:.2f} GB"])]
    return FakeSyncPlaywright(FakePage(rows=rows))


def make_playwright_timeout_on_goto() -> FakeSyncPlaywright:
    """DVR that raises TimeoutError on the first page.goto() call."""
    return FakeSyncPlaywright(FakePage(raise_on_goto=True))


def make_playwright_no_gb_data() -> FakeSyncPlaywright:
    """DVR that navigates successfully but returns no GB values."""
    rows = [FakeRow(["sem dados", "outros textos"])]
    return FakeSyncPlaywright(FakePage(rows=rows))
