"""Unit tests for src/core/rtsp.py"""
import pytest

from src.core import rtsp
from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR


def _dvr(**kwargs) -> DVR:
    base = dict(nome="D", ip="10.0.0.5", qtd_cameras=4)
    base.update(kwargs)
    return DVR(**base)


def test_hikvision_dvr_usa_streaming_channels(app_config):
    dvr = _dvr(marca=Marca.HIKVISION, tipo=TipoDispositivo.DVR)
    url = rtsp.rtsp_url(dvr, 3, app_config)
    # canal 3 → "301"; porta herda da instalação (3078)
    assert url == "rtsp://admin:admin123@10.0.0.5:3078/Streaming/Channels/301"


def test_intelbras_dvr_usa_realmonitor_com_canal(app_config):
    dvr = _dvr(marca=Marca.INTELBRAS, tipo=TipoDispositivo.DVR)
    url = rtsp.rtsp_url(dvr, 5, app_config)
    # Intelbras sem override → porta default 554
    assert url == (
        "rtsp://admin:admin123@10.0.0.5:554/cam/realmonitor?channel=5&subtype=0"
    )


def test_intelbras_camera_ip_sempre_canal_1(app_config):
    dvr = _dvr(marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP)
    # mesmo pedindo canal 7, câmera IP usa channel=1
    url = rtsp.rtsp_url(dvr, 7, app_config)
    assert "channel=1&subtype=0" in url


def test_hikvision_camera_ip_usa_canal_1(app_config):
    dvr = _dvr(marca=Marca.HIKVISION, tipo=TipoDispositivo.CAMERA_IP)
    url = rtsp.rtsp_url(dvr, 9, app_config)
    assert url.endswith("/Streaming/Channels/101")


def test_override_de_porta_rtsp_por_dispositivo(app_config):
    dvr = _dvr(marca=Marca.INTELBRAS, porta_rtsp="8554")
    url = rtsp.rtsp_url(dvr, 1, app_config)
    assert "@10.0.0.5:8554/" in url


def test_override_de_credenciais_por_dispositivo(app_config):
    dvr = _dvr(usuario="cam_user", senha="cam_pass")
    url = rtsp.rtsp_url(dvr, 1, app_config)
    assert "rtsp://cam_user:cam_pass@" in url


def test_senha_com_caracteres_especiais_e_url_encoded(app_config):
    dvr = _dvr(usuario="u", senha="a@b/c")
    url = rtsp.rtsp_url(dvr, 1, app_config)
    # @ → %40, / → %2F
    assert "u:a%40b%2Fc@" in url


def test_resolver_porta_rtsp_hikvision_herda_instalacao(app_config):
    dvr = _dvr(marca=Marca.HIKVISION)
    assert rtsp.resolver_porta_rtsp(dvr, app_config) == "3078"


def test_resolver_porta_rtsp_intelbras_default_554(app_config):
    dvr = _dvr(marca=Marca.INTELBRAS)
    assert rtsp.resolver_porta_rtsp(dvr, app_config) == "554"


def test_resolver_credenciais_herda_quando_vazio(app_config):
    dvr = _dvr()
    assert rtsp.resolver_usuario(dvr, app_config) == "admin"
    assert rtsp.resolver_senha(dvr, app_config) == "admin123"


# ─── Chave de criptografia (retry com 'verification code' do Hikvision) ─────

def test_rtsp_url_com_chave_usa_chave_no_lugar_da_senha(app_config):
    dvr = _dvr(usuario="u", senha="senha_normal",
               chave_criptografia="MINHA_CHAVE_HIK")
    url = rtsp.rtsp_url_com_chave_criptografia(dvr, 1, app_config)
    assert "MINHA_CHAVE_HIK" in url
    assert "senha_normal" not in url


def test_rtsp_url_com_chave_url_encoda_caracteres_especiais(app_config):
    dvr = _dvr(usuario="u", chave_criptografia="a@b/c")
    url = rtsp.rtsp_url_com_chave_criptografia(dvr, 1, app_config)
    assert "u:a%40b%2Fc@" in url


def test_rtsp_url_com_chave_sem_chave_levanta_value_error(app_config):
    dvr = _dvr(chave_criptografia="")
    with pytest.raises(ValueError, match="chave_criptografia"):
        rtsp.rtsp_url_com_chave_criptografia(dvr, 1, app_config)


def test_rtsp_url_com_chave_usa_a_chave_informada(app_config):
    """rtsp_url_com_chave monta a URL com uma chave arbitrária (2ª/3ª chave)."""
    dvr = _dvr(usuario="u", senha="senha_normal")
    url = rtsp.rtsp_url_com_chave(dvr, 1, app_config, "SEGUNDA_CHAVE")
    assert "SEGUNDA_CHAVE" in url
    assert "senha_normal" not in url


def test_rtsp_url_normal_nao_e_afetada_pela_chave(app_config):
    """Presença de chave não muda a URL normal (só vale no retry)."""
    dvr = _dvr(usuario="u", senha="s", chave_criptografia="CHAVE")
    url = rtsp.rtsp_url(dvr, 1, app_config)
    assert "u:s@" in url
    assert "CHAVE" not in url
