from __future__ import annotations

import os
from typing import Callable, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError

from src.core.connectivity import ping
from src.domain.models import DVR, HDStatus
from src.infra.app_config import AppConfig


def _find_chromium(playwright_path: str) -> str:
    """Localiza o executável do Chromium dentro do diretório do Playwright."""
    for folder in os.listdir(playwright_path):
        if folder.startswith("chromium"):
            exe = os.path.join(playwright_path, folder, "chrome-win64", "chrome.exe")
            if os.path.exists(exe):
                return exe
    raise RuntimeError(f"Chromium não encontrado em: {playwright_path}")


def analisar_hd(
    dvrs: List[DVR],
    config: AppConfig,
    on_log: Optional[Callable[[str], None]] = None,
) -> List[DVR]:
    """
    Navega na interface web de cada DVR e coleta o status do HD.

    Atualiza dvr.hd em cada objeto da lista e retorna a mesma lista.
    DVRs offline (sem ping) recebem HDStatus com status "OFFLINE - SEM PING".

    on_log: callback chamado para cada linha de saída.
            Se None, usa print() (comportamento legado).
    """
    _log = on_log or print

    _log("\n🔍 ANALISANDO HD DOS DVRs")

    chromium_path = _find_chromium(config.playwright_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path, headless=True)
        page = browser.new_page()

        for dvr in dvrs:
            _log(f"\n📡 DVR: {dvr.nome} ({dvr.ip})")

            if not ping(dvr.ip):
                _log("   ⛔ DVR NÃO RESPONDE AO PING")
                dvr.hd = HDStatus(status="OFFLINE - SEM PING")
                continue

            try:
                page.goto(
                    f"http://{dvr.ip}:{config.porta_http}/doc/page/login.asp",
                    timeout=70000,
                )
                page.fill("#username", config.usuario)
                page.fill("#password", config.senha)
                page.keyboard.press("Enter")
                page.wait_for_timeout(12000)

                page.goto(
                    f"http://{dvr.ip}:{config.porta_http}/doc/page/config.asp",
                    timeout=70000,
                )
                page.click("div[name='storage'] div.menu-title")
                page.click("div[name='storageManage']")
                page.wait_for_selector("div.table-row", timeout=70000)

                capacidades = []
                for row in page.query_selector_all("div.table-row"):
                    for cell in row.query_selector_all("span.table-cell"):
                        txt = cell.text_content().lower()
                        if "gb" in txt:
                            capacidades.append(float(txt.replace("gb", "").strip()))

                if capacidades:
                    dvr.hd = HDStatus(
                        total=f"{max(capacidades):.2f} GB",
                        livre=f"{min(capacidades):.2f} GB",
                        status="ONLINE - NORMAL",
                    )
                else:
                    dvr.hd = HDStatus(status="ONLINE - ERRO (HD)")

            except TimeoutError:
                dvr.hd = HDStatus(status="OFFLINE - SEM RESPOSTA")

            _log(
                f"   💽 Total: {dvr.hd.total} | Livre: {dvr.hd.livre} | {dvr.hd.status}"
            )

        browser.close()

    return dvrs
