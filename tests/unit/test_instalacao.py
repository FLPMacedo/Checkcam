"""Unit tests for src/domain/instalacao.py"""
from src.domain.instalacao import Instalacao
from src.domain.models import DVR


def test_instalacao_valores_padrao():
    inst = Instalacao(nome="Teste", usuario="u", senha="s")
    assert inst.id == 0
    assert inst.porta_http == "3077"
    assert inst.porta_rtsp == "3078"
    assert inst.dvrs == []
    assert inst.emails == []


def test_to_app_config_copia_credenciais():
    inst = Instalacao(
        nome="X", usuario="admin", senha="pass123",
        porta_http="8080", porta_rtsp="8081",
    )
    cfg = inst.to_app_config()
    assert cfg.usuario == "admin"
    assert cfg.senha == "pass123"
    assert cfg.porta_http == "8080"
    assert cfg.porta_rtsp == "8081"


def test_to_app_config_nome_instalacao():
    inst = Instalacao(nome="107 - Antônio Carlos", usuario="u", senha="s")
    cfg = inst.to_app_config()
    assert cfg.nome_instalacao == "107 - Antônio Carlos"


def test_to_app_config_emails():
    inst = Instalacao(
        nome="X", usuario="u", senha="s",
        emails=["a@b.com", "c@d.com"],
    )
    cfg = inst.to_app_config()
    assert cfg.emails == ["a@b.com", "c@d.com"]
