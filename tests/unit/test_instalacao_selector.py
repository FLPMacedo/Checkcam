"""Unit tests for src/ui/instalacao_selector.py"""
from PySide6.QtWidgets import QMessageBox

from src.domain.instalacao import Instalacao
from src.infra.instalacao_repo import InstalacaoRepository
from src.ui.instalacao_selector import InstalacaoSelectorWidget


def _repo(tmp_path) -> InstalacaoRepository:
    return InstalacaoRepository(str(tmp_path / "test.db"))


def test_lista_mostra_nomes_das_instalacoes(qtbot, tmp_path):
    repo = _repo(tmp_path)
    repo.salvar(Instalacao(nome="107 - Antônio Carlos", usuario="a", senha="b"))
    repo.salvar(Instalacao(nome="101 - Unidade", usuario="a", senha="b"))

    widget = InstalacaoSelectorWidget(repo)
    qtbot.addWidget(widget)

    nomes = [widget._list.item(i).text() for i in range(widget._list.count())]
    assert "107 - Antônio Carlos" in nomes
    assert "101 - Unidade" in nomes


def test_remover_instalacao_atualiza_lista(qtbot, tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    repo.salvar(Instalacao(nome="Para remover", usuario="a", senha="b"))

    widget = InstalacaoSelectorWidget(repo)
    qtbot.addWidget(widget)

    widget._list.setCurrentRow(0)
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )

    widget._remover()

    assert widget._list.count() == 0
