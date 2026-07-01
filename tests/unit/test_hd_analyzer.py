"""Unit tests for src/core/hd_analyzer.py"""
import pytest

from src.core import hd_analyzer
from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR, HDStatus
from tests.fakes.fake_playwright import (
    make_playwright_with_hd,
    make_playwright_timeout_on_goto,
    make_playwright_no_gb_data,
)


def test_dvr_sem_ping_tem_hd_offline(app_config, monkeypatch):
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: False)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", lambda: make_playwright_with_hd(3000, 1500))

    dvrs = [DVR(nome="DVR_A", ip="192.168.1.1", qtd_cameras=2)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "OFFLINE - SEM PING"
    assert result[0].hd.total == "-"
    assert result[0].hd.livre == "-"
    assert result[0].cameras == []


def test_dvr_online_com_dados_gb_tem_hd_normal(app_config, monkeypatch):
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: True)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", lambda: make_playwright_with_hd(3000.0, 1500.0))

    dvrs = [DVR(nome="DVR_B", ip="192.168.1.2", qtd_cameras=2)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "ONLINE - NORMAL"
    assert result[0].hd.total == "3000.00 GB"
    assert result[0].hd.livre == "1500.00 GB"


def test_dvr_online_sem_dados_gb_tem_hd_erro(app_config, monkeypatch):
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: True)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", lambda: make_playwright_no_gb_data())

    dvrs = [DVR(nome="DVR_C", ip="192.168.1.3", qtd_cameras=2)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "ONLINE - ERRO (HD)"


def test_dvr_playwright_timeout_tem_hd_sem_resposta(app_config, monkeypatch):
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: True)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", lambda: make_playwright_timeout_on_goto())

    dvrs = [DVR(nome="DVR_D", ip="192.168.1.4", qtd_cameras=2)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "OFFLINE - SEM RESPOSTA"


# ─── Intelbras (CGI) e câmera IP ─────────────────────────────────────────────

def _explode_se_chamado():
    def _boom():
        raise AssertionError("sync_playwright NÃO deveria ser chamado")
    return _boom


def test_intelbras_dvr_usa_cgi_sem_abrir_browser(app_config, monkeypatch):
    """DVR Intelbras lê HD via CGI; o navegador não deve ser aberto."""
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: True)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", _explode_se_chamado())

    chamado = {}

    def fake_ler_hd(ip, porta, usuario, senha):
        chamado["ip"] = ip
        return HDStatus(total="4.00 GB", livre="3.00 GB", status="ONLINE - NORMAL")

    monkeypatch.setattr(hd_analyzer.intelbras_cgi, "ler_hd", fake_ler_hd)

    dvrs = [DVR(nome="NVR", ip="10.9.130.10", qtd_cameras=16,
                marca=Marca.INTELBRAS, tipo=TipoDispositivo.DVR)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert chamado["ip"] == "10.9.130.10"
    assert result[0].hd.status == "ONLINE - NORMAL"
    assert result[0].hd.total == "4.00 GB"


def test_camera_ip_pula_hd_sem_browser(app_config, monkeypatch):
    """Câmera IP não tem HD → status N/A e nenhum navegador é aberto."""
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: True)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", _explode_se_chamado())

    dvrs = [DVR(nome="CAM 1", ip="10.9.130.31", qtd_cameras=1,
                marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "N/A - CÂMERA IP"


def test_camera_ip_sem_ping_fica_offline(app_config, monkeypatch):
    monkeypatch.setattr(hd_analyzer, "ping", lambda ip: False)
    monkeypatch.setattr(hd_analyzer, "sync_playwright", _explode_se_chamado())

    dvrs = [DVR(nome="CAM", ip="10.9.130.31", qtd_cameras=1,
                marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP)]
    result = hd_analyzer.analisar_hd(dvrs, app_config)

    assert result[0].hd.status == "OFFLINE - SEM PING"
