"""Unit tests for src/ui/dashboard_launcher.py"""
import sys

from src.ui import dashboard_launcher


def test_spawn_dashboard_chama_popen_com_modulo(monkeypatch):
    capturado = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            capturado["args"] = args
            capturado["kwargs"] = kwargs

    monkeypatch.setattr(dashboard_launcher.subprocess, "Popen", FakePopen)

    dashboard_launcher.spawn_dashboard("C:/dados/checkcam.db")

    assert capturado["args"] == [sys.executable, "-m", "dashboard.desktop"]
    assert capturado["kwargs"]["env"]["CHECKCAM_DB"] == "C:/dados/checkcam.db"


def test_spawn_dashboard_sem_db_herda_ambiente(monkeypatch):
    capturado = {}

    class FakePopen:
        def __init__(self, args, **kwargs):
            capturado["kwargs"] = kwargs

    monkeypatch.setattr(dashboard_launcher.subprocess, "Popen", FakePopen)

    dashboard_launcher.spawn_dashboard("")

    # env=None → o subprocesso herda o ambiente do processo pai.
    assert capturado["kwargs"]["env"] is None
