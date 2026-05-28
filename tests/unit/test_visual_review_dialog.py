"""Unit tests for src/ui/visual_review_dialog.py"""
from PySide6.QtCore import Qt

from src.domain.models import Camera
from src.ui.visual_review_dialog import VisualReviewDialog


def _cam(imagem: str, status: str = "PENDENTE") -> Camera:
    return Camera(nome="C1", imagem=imagem, status=status)


def test_dialog_classifica_camera_com_tecla_1(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    qtbot.keyPress(dialog, Qt.Key.Key_1)

    assert cam.status == "OK"


def test_dialog_classifica_camera_com_tecla_3(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    qtbot.keyPress(dialog, Qt.Key.Key_3)

    assert cam.status == "DISTORCIDA"


def test_dialog_esc_rejeita_sem_alterar_status(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    dialog.show()

    with qtbot.waitSignal(dialog.rejected, timeout=3000):
        qtbot.keyPress(dialog, Qt.Key.Key_Escape)

    assert cam.status == "PENDENTE"


def test_dialog_ignora_cameras_com_error_img(qtbot, error_jpg):
    cam = _cam(str(error_jpg))
    dialog = VisualReviewDialog([cam], str(error_jpg))
    qtbot.addWidget(dialog)

    assert len(dialog._cameras) == 0


def test_dialog_sem_cameras_aceita_automaticamente(qtbot):
    from PySide6.QtWidgets import QDialog

    dialog = VisualReviewDialog([], "error.jpg")
    qtbot.addWidget(dialog)

    # _show_current() é deferido via QTimer; aguardamos o finished disparar.
    with qtbot.waitSignal(dialog.finished, timeout=2000):
        pass

    assert dialog._cameras == []
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_dialog_sem_cameras_dispara_finished_apos_connect(qtbot):
    """Regressão: o accept() automático precisa ocorrer depois do connect()."""
    dialog = VisualReviewDialog([], "error.jpg")
    qtbot.addWidget(dialog)

    recebido = []
    dialog.finished.connect(recebido.append)

    # Sinal chega após o evento loop processar o QTimer.
    qtbot.waitUntil(lambda: len(recebido) == 1, timeout=2000)
    assert len(recebido) == 1


def test_dialog_imagem_invalida_mostra_mensagem_visivel(qtbot, tmp_path):
    """Regressão: pixmap nulo (arquivo inexistente) → mensagem de erro
    visível na tela, em vez de pular silenciosamente para o próximo."""
    cam = _cam(str(tmp_path / "inexistente.jpg"))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    # Aguarda o QTimer disparar _show_current
    qtbot.wait(50)

    # info_label deve estar preenchido (não silencioso)
    assert "C1" in dialog.info_label.text()
    # image_label deve mostrar texto de erro (não pixmap)
    assert "não pôde ser carregada" in dialog.image_label.text()
    # status da câmera deve ter sido marcado
    assert cam.status == "ERRO_IMAGEM"
