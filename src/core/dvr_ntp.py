"""Conferência e correção de horário/NTP dos DVRs via ISAPI (Hikvision).

O DVR expõe a config de tempo por HTTP (mesmo caminho que o analisador de HD
usa para logar), então dá para ler o estado e reconfigurar o NTP sem depender
do RTSP. Escopo atual: DVR Hikvision. Intelbras usaria outra CGI (futuro).

Endpoints:
  GET /ISAPI/System/time                 → timeMode, localTime, timeZone
  GET /ISAPI/System/time/ntpServers      → servidor NTP configurado
  PUT /ISAPI/System/time/ntpServers/1    → define o servidor NTP
  PUT /ISAPI/System/time                 → timeMode=NTP + timeZone (dispara sync)
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, List, Optional

from src.core.connectivity import ping
from src.core.rtsp import resolver_porta_http, resolver_senha, resolver_usuario
from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR
from src.infra.app_config import AppConfig

# Padrões da frota (Brasília, UTC-3, na notação do Hikvision).
NTP_PADRAO = "time1.google.com"
TIMEZONE_BRASILIA = "CST+3:00:00"
_XMLNS = "http://www.hikvision.com/ver20/XMLSchema"


@dataclass
class StatusTempo:
    """Estado de tempo lido de um DVR."""

    time_mode: str = ""      # "NTP" | "manual"
    local_time: str = ""     # ISO 8601 com offset
    time_zone: str = ""
    ntp_host: str = ""
    ntp_port: str = ""


@dataclass
class ResultadoTempo:
    """Resultado por DVR da conferência/correção de horário."""

    dvr_nome: str
    ip: str
    status_antes: Optional[StatusTempo]
    aplicado: bool
    ok: bool
    mensagem: str


# ── Transporte HTTP (seams isolados para os testes) ──────────────────────────

def _opener(url: str, usuario: str, senha: str):
    pw = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    pw.add_password(None, url, usuario, senha)
    return urllib.request.build_opener(
        urllib.request.HTTPDigestAuthHandler(pw),
        urllib.request.HTTPBasicAuthHandler(pw),
    )


def _get(url: str, usuario: str, senha: str, timeout: float = 8.0) -> str:
    with _opener(url, usuario, senha).open(
        urllib.request.Request(url), timeout=timeout
    ) as r:
        return r.read().decode("utf-8", "replace")


def _put(url: str, xml: str, usuario: str, senha: str, timeout: float = 8.0):
    req = urllib.request.Request(url, data=xml.encode("utf-8"), method="PUT")
    req.add_header("Content-Type", "application/xml")
    try:
        with _opener(url, usuario, senha).open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _tag(xml: str, tag: str) -> str:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.DOTALL)
    return m.group(1).strip() if m else ""


def _base(ip: str, porta: str) -> str:
    return f"http://{ip}:{porta}"


# ── Leitura / escrita ────────────────────────────────────────────────────────

def ler_status_tempo(ip: str, porta: str, usuario: str, senha: str) -> StatusTempo:
    """Lê o estado de tempo e o NTP configurado do DVR."""
    t = _get(_base(ip, porta) + "/ISAPI/System/time", usuario, senha)
    n = _get(_base(ip, porta) + "/ISAPI/System/time/ntpServers", usuario, senha)
    return StatusTempo(
        time_mode=_tag(t, "timeMode"),
        local_time=_tag(t, "localTime"),
        time_zone=_tag(t, "timeZone"),
        ntp_host=_tag(n, "hostName"),
        ntp_port=_tag(n, "portNo"),
    )


def configurar_ntp(
    ip: str,
    porta: str,
    usuario: str,
    senha: str,
    host: str = NTP_PADRAO,
    timezone: str = TIMEZONE_BRASILIA,
    intervalo: str = "60",
) -> bool:
    """Aponta o NTP e coloca o DVR em modo NTP (o que dispara a sincronização).

    Retorna True se ambos os PUTs responderem 2xx.
    """
    base = _base(ip, porta)
    xml_ntp = (
        f'<NTPServer version="2.0" xmlns="{_XMLNS}">'
        "<id>1</id><addressingFormatType>hostname</addressingFormatType>"
        f"<hostName>{host}</hostName><portNo>123</portNo>"
        f"<synchronizeInterval>{intervalo}</synchronizeInterval></NTPServer>"
    )
    st_ntp, _ = _put(base + "/ISAPI/System/time/ntpServers/1", xml_ntp, usuario, senha)

    xml_time = (
        f'<Time version="2.0" xmlns="{_XMLNS}">'
        f"<timeMode>NTP</timeMode><timeZone>{timezone}</timeZone></Time>"
    )
    st_time, _ = _put(base + "/ISAPI/System/time", xml_time, usuario, senha)

    return 200 <= st_ntp < 300 and 200 <= st_time < 300


# ── Orquestração sobre a lista de DVRs ───────────────────────────────────────

def sincronizar_dvrs(
    dvrs: List[DVR],
    config: AppConfig,
    aplicar: bool = True,
    on_log: Optional[Callable[[str], None]] = None,
    host: str = NTP_PADRAO,
    timezone: str = TIMEZONE_BRASILIA,
) -> List[ResultadoTempo]:
    """Confere (e opcionalmente corrige) o horário/NTP de cada DVR Hikvision.

    ``aplicar=False`` = só relatório (não escreve). Câmeras IP e DVRs Intelbras
    são pulados (sem suporte ISAPI aqui). DVRs sem ping também são pulados.
    """
    _log = on_log or print
    resultados: List[ResultadoTempo] = []

    for dvr in dvrs:
        _log(f"\n🕐 {dvr.nome} ({dvr.ip})")

        if dvr.tipo == TipoDispositivo.CAMERA_IP or dvr.marca != Marca.HIKVISION:
            resultados.append(ResultadoTempo(
                dvr.nome, dvr.ip, None, False, False,
                "pulado (só DVR Hikvision é suportado)"))
            _log("   ℹ pulado (não é DVR Hikvision)")
            continue

        if not ping(dvr.ip):
            resultados.append(ResultadoTempo(
                dvr.nome, dvr.ip, None, False, False, "sem ping"))
            _log("   ⛔ sem ping")
            continue

        porta = resolver_porta_http(dvr, config)
        usuario = resolver_usuario(dvr, config)
        senha = resolver_senha(dvr, config)

        try:
            antes = ler_status_tempo(dvr.ip, porta, usuario, senha)
        except Exception as exc:  # noqa: BLE001
            resultados.append(ResultadoTempo(
                dvr.nome, dvr.ip, None, False, False, f"erro ao ler: {exc}"))
            _log(f"   ❌ erro ao ler: {exc}")
            continue

        _log(f"   modo={antes.time_mode} hora={antes.local_time} "
             f"ntp={antes.ntp_host or '(nenhum)'}")

        if not aplicar:
            resultados.append(ResultadoTempo(
                dvr.nome, dvr.ip, antes, False, True, "conferido (sem alterar)"))
            continue

        try:
            ok = configurar_ntp(dvr.ip, porta, usuario, senha,
                                 host=host, timezone=timezone)
        except Exception as exc:  # noqa: BLE001
            resultados.append(ResultadoTempo(
                dvr.nome, dvr.ip, antes, False, False, f"erro ao aplicar: {exc}"))
            _log(f"   ❌ erro ao aplicar: {exc}")
            continue

        msg = "NTP aplicado + sync forçada" if ok else "falha ao aplicar NTP"
        resultados.append(ResultadoTempo(dvr.nome, dvr.ip, antes, ok, ok, msg))
        _log(f"   {'✅' if ok else '❌'} {msg}")

    return resultados
