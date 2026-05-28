"""Unit tests for src/infra/app_config.py"""
from src.infra.app_config import AppConfig


def test_senha_rtsp_e_url_encoded_quando_tem_caracteres_especiais():
    config = AppConfig(usuario="admin", senha="pass@word!")
    assert config.senha_rtsp == "pass%40word%21"


def test_senha_rtsp_igual_senha_quando_sem_caracteres_especiais():
    config = AppConfig(usuario="admin", senha="admin123")
    assert config.senha_rtsp == "admin123"


def test_porta_http_default():
    config = AppConfig(usuario="admin", senha="x")
    assert config.porta_http == "3077"


def test_porta_rtsp_default():
    config = AppConfig(usuario="admin", senha="x")
    assert config.porta_rtsp == "3078"


def test_emails_default_lista_vazia():
    config = AppConfig(usuario="admin", senha="x")
    assert config.emails == []


def test_emails_nao_compartilhados_entre_instancias():
    c1 = AppConfig(usuario="a", senha="x")
    c2 = AppConfig(usuario="b", senha="x")
    c1.emails.append("a@x.com")
    assert c2.emails == []
