"""Unit tests for src/core/dvr_ntp.py (sem tocar em rede real)."""
from src.core import dvr_ntp
from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR

_TIME_XML = """<?xml version="1.0"?>
<Time xmlns="http://www.hikvision.com/ver20/XMLSchema">
<timeMode>NTP</timeMode>
<localTime>2026-07-03T11:45:31-03:00</localTime>
<timeZone>CST+3:00:00</timeZone>
</Time>"""

_NTP_XML = """<?xml version="1.0"?>
<NTPServerList xmlns="http://www.hikvision.com/ver20/XMLSchema">
<NTPServer><id>1</id><hostName>time1.google.com</hostName>
<portNo>123</portNo><synchronizeInterval>60</synchronizeInterval></NTPServer>
</NTPServerList>"""


def test_tag_extrai_valor():
    assert dvr_ntp._tag("<a>x</a><b>y</b>", "b") == "y"
    assert dvr_ntp._tag("<a></a>", "a") == ""
    assert dvr_ntp._tag("nada", "a") == ""


def test_ler_status_tempo_parseia(monkeypatch):
    def fake_get(url, usuario, senha, timeout=8):
        return _NTP_XML if "ntpServers" in url else _TIME_XML
    monkeypatch.setattr(dvr_ntp, "_get", fake_get)

    st = dvr_ntp.ler_status_tempo("10.0.0.222", "3077", "admin", "x")

    assert st.time_mode == "NTP"
    assert st.local_time == "2026-07-03T11:45:31-03:00"
    assert st.time_zone == "CST+3:00:00"
    assert st.ntp_host == "time1.google.com"
    assert st.ntp_port == "123"


def test_configurar_ntp_faz_puts_corretos(monkeypatch):
    chamadas = []
    def fake_put(url, xml, usuario, senha, timeout=8):
        chamadas.append((url, xml))
        return 200, "<statusString>OK</statusString>"
    monkeypatch.setattr(dvr_ntp, "_put", fake_put)

    ok = dvr_ntp.configurar_ntp("10.0.0.9", "3077", "admin", "x",
                                host="time1.google.com", timezone="CST+3:00:00")

    assert ok is True
    assert len(chamadas) == 2
    url_ntp, body_ntp = chamadas[0]
    url_time, body_time = chamadas[1]
    assert url_ntp.endswith("/ISAPI/System/time/ntpServers/1")
    assert "time1.google.com" in body_ntp
    assert 'xmlns="http://www.hikvision.com/ver20/XMLSchema"' in body_ntp
    assert url_time.endswith("/ISAPI/System/time")
    assert "<timeMode>NTP</timeMode>" in body_time
    assert "CST+3:00:00" in body_time


def test_configurar_ntp_falha_quando_put_nao_2xx(monkeypatch):
    monkeypatch.setattr(dvr_ntp, "_put", lambda *a, **k: (500, "erro"))
    ok = dvr_ntp.configurar_ntp("10.0.0.9", "3077", "admin", "x")
    assert ok is False


# ─── Orquestração sobre uma lista de DVRs ────────────────────────────────────

def _hik(nome="D", ip="10.0.0.9"):
    return DVR(nome=nome, ip=ip, qtd_cameras=1,
               marca=Marca.HIKVISION, tipo=TipoDispositivo.DVR)


def test_sincronizar_aplica_e_reporta(app_config, monkeypatch):
    monkeypatch.setattr(dvr_ntp, "ping", lambda ip: True)
    monkeypatch.setattr(dvr_ntp, "ler_status_tempo",
                        lambda *a, **k: dvr_ntp.StatusTempo(time_mode="manual"))
    aplicados = []
    monkeypatch.setattr(dvr_ntp, "configurar_ntp",
                        lambda *a, **k: aplicados.append(a) or True)

    res = dvr_ntp.sincronizar_dvrs([_hik("ADM3")], app_config, aplicar=True)

    assert len(res) == 1
    assert res[0].ok is True
    assert res[0].aplicado is True
    assert len(aplicados) == 1


def test_sincronizar_so_conferir_nao_escreve(app_config, monkeypatch):
    monkeypatch.setattr(dvr_ntp, "ping", lambda ip: True)
    monkeypatch.setattr(dvr_ntp, "ler_status_tempo",
                        lambda *a, **k: dvr_ntp.StatusTempo(time_mode="NTP"))
    chamou = []
    monkeypatch.setattr(dvr_ntp, "configurar_ntp",
                        lambda *a, **k: chamou.append(1) or True)

    res = dvr_ntp.sincronizar_dvrs([_hik()], app_config, aplicar=False)

    assert res[0].aplicado is False
    assert chamou == []


def test_sincronizar_pula_dvr_sem_ping(app_config, monkeypatch):
    monkeypatch.setattr(dvr_ntp, "ping", lambda ip: False)
    monkeypatch.setattr(dvr_ntp, "configurar_ntp",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria escrever")))

    res = dvr_ntp.sincronizar_dvrs([_hik("OFF")], app_config, aplicar=True)

    assert res[0].ok is False
    assert res[0].aplicado is False
    assert "ping" in res[0].mensagem.lower()
