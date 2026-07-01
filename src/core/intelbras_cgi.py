"""
Leitura do status de HD de DVR/NVR Intelbras (Dahua-OEM) via API CGI.

Endpoint: ``/cgi-bin/storageDevice.cgi?action=getDeviceAllInfo`` com
autenticação HTTP **Digest**. Não usa navegador (mais rápido e robusto que o
scrape do Hikvision).

A resposta é texto no formato chave=valor da Dahua, ex.:

    list.info[0].State=Normal
    list.info[0].Detail[0].TotalBytes=1998998994944.000000
    list.info[0].Detail[0].UsedBytes=1234567890.000000

⚠ O parser foi escrito a partir do formato documentado da Dahua; **validar
contra o NVR real** (firmware pode variar nas chaves/unidades). O ``fetch`` é
injetável para permitir testes sem rede.
"""
from __future__ import annotations

import urllib.request
from typing import Callable, Optional

from src.domain.models import HDStatus

# Assinatura do fetch: (url, usuario, senha) → corpo da resposta (texto).
FetchFn = Callable[[str, str, str], str]

_GB = 1024 ** 3
_TIMEOUT_S = 15


def _fetch_digest(url: str, usuario: str, senha: str) -> str:
    """GET com autenticação HTTP Digest (padrão da CGI Intelbras/Dahua)."""
    gerenciador = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    gerenciador.add_password(None, url, usuario, senha)
    handler = urllib.request.HTTPDigestAuthHandler(gerenciador)
    opener = urllib.request.build_opener(handler)
    with opener.open(url, timeout=_TIMEOUT_S) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _to_float(valor: str) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _parse(texto: str) -> HDStatus:
    """Extrai total/livre e status do corpo da CGI getDeviceAllInfo."""
    total_bytes = 0.0
    used_bytes = 0.0
    tem_erro = False

    for linha in texto.splitlines():
        chave, sep, valor = linha.partition("=")
        if not sep:
            continue
        chave = chave.strip().lower()
        valor = valor.strip()

        if chave.endswith("totalbytes"):
            total_bytes += _to_float(valor)
        elif chave.endswith("usedbytes"):
            used_bytes += _to_float(valor)
        elif chave.endswith(".state"):
            if "normal" not in valor.lower():
                tem_erro = True

    if total_bytes <= 0:
        # Sem disco/sem dados → tratamos como erro de HD (igual ao Hikvision).
        return HDStatus(status="ONLINE - ERRO (HD)")

    livre_bytes = max(total_bytes - used_bytes, 0.0)
    status = "ONLINE - ERRO (HD)" if tem_erro else "ONLINE - NORMAL"
    return HDStatus(
        total=f"{total_bytes / _GB:.2f} GB",
        livre=f"{livre_bytes / _GB:.2f} GB",
        status=status,
    )


def ler_hd(
    ip: str,
    porta: str,
    usuario: str,
    senha: str,
    fetch: Optional[FetchFn] = None,
) -> HDStatus:
    """Consulta o HD do NVR Intelbras e devolve um HDStatus.

    Falha de rede/timeout → ``OFFLINE - SEM RESPOSTA`` (o DVR respondeu ao ping
    mas a CGI não respondeu).
    """
    fetch = fetch or _fetch_digest
    url = f"http://{ip}:{porta}/cgi-bin/storageDevice.cgi?action=getDeviceAllInfo"
    try:
        texto = fetch(url, usuario, senha)
    except Exception:  # noqa: BLE001 — qualquer falha de rede vira "sem resposta"
        return HDStatus(status="OFFLINE - SEM RESPOSTA")
    return _parse(texto)
