"""Unit tests for src/ui/instalacao_form.py — auto-fill de caminhos."""
import pytest

from src.domain.instalacao import Instalacao
from src.ui.instalacao_form import InstalacaoFormDialog


def test_form_preenche_caminhos_vazios_ao_salvar_nova_instalacao(qtbot):
    """Usuário cria 'Nova', preenche só o nome e clica OK → caminhos auto-preenchidos."""
    dialog = InstalacaoFormDialog()
    qtbot.addWidget(dialog)

    dialog._nome.setText("LPA POSTOS")
    # Não preenche os caminhos
    dialog._aceitar()

    inst = dialog.get_instalacao()
    # Não pode haver caminho vazio após o aceitar
    assert inst.base_dir != ""
    assert inst.relatorios_dir != ""
    assert inst.logs_dir != ""
    assert inst.ffmpeg_path != ""
    assert inst.playwright_path != ""
    assert inst.error_img != ""
    # Caminhos contêm o slug do nome
    assert "LPA_POSTOS" in inst.relatorios_dir


def test_form_preserva_caminhos_existentes_quando_o_usuario_preenche(qtbot):
    """Se o usuário já preencheu um caminho custom, NÃO sobrescrever."""
    dialog = InstalacaoFormDialog()
    qtbot.addWidget(dialog)

    dialog._nome.setText("X")
    dialog._relatorios_dir.setText(r"C:\meus_relatorios_custom")
    dialog._aceitar()

    inst = dialog.get_instalacao()
    assert inst.relatorios_dir == r"C:\meus_relatorios_custom"
    # Os outros (vazios) foram preenchidos
    assert inst.base_dir != ""


def test_form_nao_aceita_sem_nome(qtbot, monkeypatch):
    """Nome continua sendo obrigatório."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda *a, **kw: QMessageBox.StandardButton.Ok,
    )

    dialog = InstalacaoFormDialog()
    qtbot.addWidget(dialog)

    # Spy no accept
    accepted = []
    monkeypatch.setattr(
        InstalacaoFormDialog, "accept",
        lambda self: accepted.append(True),
    )

    dialog._nome.setText("")
    dialog._aceitar()

    assert accepted == []


def test_form_edicao_de_existente_preserva_todos_os_caminhos(qtbot):
    """Editando uma instalação existente, os caminhos NÃO devem mudar."""
    inst_original = Instalacao(
        id=1,
        nome="EXISTENTE",
        base_dir=r"C:\original\base",
        relatorios_dir=r"C:\original\relatorios",
        logs_dir=r"C:\original\logs",
        ffmpeg_path=r"C:\original\ffmpeg.exe",
        playwright_path=r"C:\original\playwright",
        error_img=r"C:\original\error.jpg",
    )

    dialog = InstalacaoFormDialog(inst_original)
    qtbot.addWidget(dialog)

    dialog._aceitar()
    inst = dialog.get_instalacao()

    assert inst.base_dir == r"C:\original\base"
    assert inst.relatorios_dir == r"C:\original\relatorios"
    assert inst.logs_dir == r"C:\original\logs"
