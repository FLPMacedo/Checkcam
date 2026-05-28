"""Unit tests for src/core/connectivity.py"""
from src.core import connectivity
from tests.fakes.fake_subprocess import make_fake_run


def test_ping_retorna_true_quando_returncode_0(monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    assert connectivity.ping("192.168.1.1") is True


def test_ping_retorna_false_quando_returncode_nao_zero(monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=1))
    assert connectivity.ping("192.168.1.1") is False


def test_ping_retorna_false_quando_subprocess_lanca_excecao(monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(raise_exception=True))
    assert connectivity.ping("192.168.1.1") is False
