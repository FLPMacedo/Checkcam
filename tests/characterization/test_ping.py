"""
Characterization tests for ping().
"""
from tests.fakes.fake_subprocess import make_fake_run


def test_ping_retorna_true_quando_subprocess_retorna_0(legacy_module, monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    assert legacy_module.ping("192.168.1.1") is True


def test_ping_retorna_false_quando_subprocess_retorna_diferente_de_0(legacy_module, monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=1))
    assert legacy_module.ping("192.168.1.1") is False


def test_ping_retorna_false_quando_subprocess_lanca_excecao(legacy_module, monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(raise_exception=True))
    assert legacy_module.ping("192.168.1.1") is False
