"""Unit tests for src/ui/email_preview_dialog.py"""
from PySide6.QtWidgets import QDialog

from src.domain.events import EmailDraft
from src.ui.email_preview_dialog import EmailPreviewDialog


def _draft() -> EmailDraft:
    return EmailDraft(
        assunto="Checklist DVRs",
        corpo="Bom dia,\n\nSegue o resumo.",
        destinatarios=["a@x.com", "b@x.com"],
        anexos=["C:/fake/checklist.pdf", "C:/fake/book.pdf"],
    )


def test_dialog_popula_campos_a_partir_do_draft(qtbot):
    dialog = EmailPreviewDialog(_draft())
    qtbot.addWidget(dialog)

    assert dialog._assunto.text() == "Checklist DVRs"
    assert "Segue o resumo" in dialog._corpo.toPlainText()
    assert "a@x.com" in dialog._destinatarios.text()
    assert "b@x.com" in dialog._destinatarios.text()
    # anexos listados
    assert dialog._anexos.count() == 2


def test_get_draft_reflete_edicoes(qtbot):
    dialog = EmailPreviewDialog(_draft())
    qtbot.addWidget(dialog)

    dialog._assunto.setText("ASSUNTO NOVO")
    dialog._corpo.setPlainText("corpo reescrito")
    dialog._destinatarios.setText("um@x.com; dois@x.com ;tres@x.com")

    out = dialog.get_draft()

    assert out.assunto == "ASSUNTO NOVO"
    assert out.corpo == "corpo reescrito"
    # split por ';' + strip dos espaços
    assert out.destinatarios == ["um@x.com", "dois@x.com", "tres@x.com"]


def test_get_draft_preserva_anexos_do_original(qtbot):
    """Anexos não são editáveis na tela — devem vir do draft original."""
    dialog = EmailPreviewDialog(_draft())
    qtbot.addWidget(dialog)

    out = dialog.get_draft()

    assert out.anexos == ["C:/fake/checklist.pdf", "C:/fake/book.pdf"]


def test_enviar_aceita_o_dialog(qtbot):
    dialog = EmailPreviewDialog(_draft())
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.accepted, timeout=2000):
        dialog._btn_enviar.click()

    assert dialog.result() == QDialog.DialogCode.Accepted


def test_cancelar_rejeita_o_dialog(qtbot):
    dialog = EmailPreviewDialog(_draft())
    qtbot.addWidget(dialog)

    with qtbot.waitSignal(dialog.rejected, timeout=2000):
        dialog._btn_cancelar.click()

    assert dialog.result() == QDialog.DialogCode.Rejected
