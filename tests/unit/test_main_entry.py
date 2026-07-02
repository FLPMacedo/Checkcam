"""Unit tests for main.py — roteamento do entry point."""
import main


def test_sem_argumento_roda_o_checklist(monkeypatch):
    chamado = {}
    def fake_checklist():
        chamado["app"] = True
        return 0

    monkeypatch.setattr(main, "_run_checklist", fake_checklist)
    monkeypatch.setattr(main, "_run_dashboard", lambda: chamado.setdefault("dash", True))

    rc = main.main(["CheckCam.exe"])

    assert chamado == {"app": True}
    assert rc == 0


def test_argumento_dashboard_abre_o_dashboard(monkeypatch):
    chamado = {}
    def fake_checklist():
        chamado["app"] = True
        return 0

    monkeypatch.setattr(main, "_run_checklist", fake_checklist)
    monkeypatch.setattr(main, "_run_dashboard", lambda: chamado.setdefault("dash", True))

    rc = main.main(["CheckCam.exe", "--dashboard"])

    assert chamado == {"dash": True}
    assert rc == 0
