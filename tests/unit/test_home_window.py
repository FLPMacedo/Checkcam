"""Unit tests for src/ui/home_window.py — botão de dashboard."""
from PySide6.QtCore import Qt

from src.infra.instalacao_repo import InstalacaoRepository
from src.ui import home_window
from src.ui.home_window import HomeWindow


def test_botao_abrir_dashboard_spawna_processo(qtbot, tmp_path, monkeypatch):
    chamado = []
    monkeypatch.setattr(home_window, "spawn_dashboard", lambda db="": chamado.append(db))

    repo = InstalacaoRepository(str(tmp_path / "h.db"))
    w = HomeWindow(repo, db_path="h.db")
    qtbot.addWidget(w)

    qtbot.mouseClick(w.btn_dashboard, Qt.MouseButton.LeftButton)

    assert chamado == ["h.db"]
