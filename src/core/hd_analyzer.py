from __future__ import annotations

import os
from typing import Callable, List, Optional

from playwright.sync_api import sync_playwright, TimeoutError

from src.core import intelbras_cgi
from src.core.connectivity import ping
from src.core.rtsp import resolver_porta_http, resolver_senha, resolver_usuario
from src.domain.device import Marca, TipoDispositivo
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


def _hd_hikvision(page, dvr: DVR, config: AppConfig) -> HDStatus:
    """Scrape da interface web Hikvision para coletar o status do HD."""
    porta = resolver_porta_http(dvr, config)
    usuario = resolver_usuario(dvr, config)
    senha = resolver_senha(dvr, config)
    try:
        page.goto(
            f"http://{dvr.ip}:{porta}/doc/page/login.asp",
            timeout=70000,
        )
        page.fill("#username", usuario)
        page.fill("#password", senha)
        page.keyboard.press("Enter")
        page.wait_for_timeout(12000)

        page.goto(
            f"http://{dvr.ip}:{porta}/doc/page/config.asp",
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
            return HDStatus(
                total=f"{max(capacidades):.2f} GB",
                livre=f"{min(capacidades):.2f} GB",
                status="ONLINE - NORMAL",
            )
        return HDStatus(status="ONLINE - ERRO (HD)")

    except TimeoutError:
        return HDStatus(status="OFFLINE - SEM RESPOSTA")


def _hd_intelbras(dvr: DVR, config: AppConfig) -> HDStatus:
    """Leitura do HD via API CGI (Dahua-OEM)."""
    return intelbras_cgi.ler_hd(
        ip=dvr.ip,
        porta=resolver_porta_http(dvr, config),
        usuario=resolver_usuario(dvr, config),
        senha=resolver_senha(dvr, config),
    )


def _precisa_browser(dvrs: List[DVR]) -> bool:
    """True se algum dispositivo exige o navegador (scrape Hikvision DVR)."""
    return any(
        d.marca == Marca.HIKVISION and d.tipo == TipoDispositivo.DVR
        for d in dvrs
    )


def _processar(dvrs, config, page, _log) -> None:
    """Loop principal: ping + dispatch da leitura de HD por marca/tipo."""
    for dvr in dvrs:
        _log(f"\n📡 DVR: {dvr.nome} ({dvr.ip})")

        if not ping(dvr.ip):
            _log("   ⛔ DVR NÃO RESPONDE AO PING")
            dvr.hd = HDStatus(status="OFFLINE - SEM PING")
            continue

        # Câmera IP não tem HD de gravação — pula a análise.
        if dvr.tipo == TipoDispositivo.CAMERA_IP:
            dvr.hd = HDStatus(status="N/A - CÂMERA IP")
            _log("   ℹ Câmera IP — sem HD para verificar")
            continue

        if dvr.marca == Marca.INTELBRAS:
            dvr.hd = _hd_intelbras(dvr, config)
        else:
            dvr.hd = _hd_hikvision(page, dvr, config)

        _log(
            f"   💽 Total: {dvr.hd.total} | Livre: {dvr.hd.livre} | {dvr.hd.status}"
        )


def analisar_hd(
    dvrs: List[DVR],
    config: AppConfig,
    on_log: Optional[Callable[[str], None]] = None,
) -> List[DVR]:
    """
    Coleta o status do HD de cada dispositivo, despachando por marca × tipo:

      - Hikvision/DVR → scrape da interface web (Playwright)
      - Intelbras/DVR → API CGI storageDevice.cgi (Digest)
      - Câmera IP     → pula (sem HD de gravação)

    Atualiza dvr.hd em cada objeto da lista e retorna a mesma lista.
    DVRs sem ping recebem HDStatus "OFFLINE - SEM PING".

    O navegador (Chromium) só é aberto quando há ao menos um dispositivo
    Hikvision/DVR — instalações puramente Intelbras/câmera IP não dependem do
    Playwright.

    on_log: callback chamado para cada linha de saída.
            Se None, usa print() (comportamento legado).
    """
    _log = on_log or print
    _log("\n🔍 ANALISANDO HD DOS DVRs")

    if _precisa_browser(dvrs):
        chromium_path = _find_chromium(config.playwright_path)
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chromium_path, headless=True)
            page = browser.new_page()
            _processar(dvrs, config, page, _log)
            browser.close()
    else:
        _processar(dvrs, config, None, _log)

    return dvrs
