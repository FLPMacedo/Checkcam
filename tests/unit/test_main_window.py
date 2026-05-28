"""Unit tests for src/ui/main_window.py"""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLineEdit, QPushButton, QTextEdit
from PySide6.QtCore import QThread

from src.domain.events import ProgressEvent
from src.domain.models import DVR
from src.ui import main_window
from src.ui.main_window import MainWindow


def _dvr():
    return [DVR(nome="DVR_TESTE", ip="1.2.3.4", qtd_cameras=1)]


def _window(qtbot, app_config, dvrs=None):
    w = MainWindow(dvrs or _dvr(), app_config)
    qtbot.addWidget(w)
    return w


class _FakeWorker(QThread):
    """Worker que não faz nada — apenas registra se start() foi chamado."""

    progress_signal = Signal(object)
    capture_done_signal = Signal(object)
    finished_signal = Signal(object)
    error_signal = Signal(str)
    log_signal = Signal(str)

    started_count = 0

    def __init__(self, dvrs, config, parent=None):
        super().__init__(parent)
        _FakeWorker.started_count = 0

    def start(self):
        _FakeWorker.started_count += 1
        # não chama super().start() para não executar run()

    def run(self):  # pragma: no cover
        pass


def test_widgets_de_credencial_existem(qtbot, app_config):
    w = _window(qtbot, app_config)

    assert isinstance(w.usuario_input, QLineEdit)
    assert isinstance(w.senha_input, QLineEdit)
    assert w.senha_input.echoMode() == QLineEdit.EchoMode.Password


def test_log_area_e_somente_leitura(qtbot, app_config):
    w = _window(qtbot, app_config)

    assert isinstance(w.log_area, QTextEdit)
    assert w.log_area.isReadOnly() is True


def test_clicar_iniciar_inicia_worker(qtbot, app_config, monkeypatch):
    monkeypatch.setattr(main_window, "ChecklistWorker", _FakeWorker)

    w = _window(qtbot, app_config)
    assert _FakeWorker.started_count == 0

    qtbot.mouseClick(w.btn_iniciar, Qt.MouseButton.LeftButton)

    assert _FakeWorker.started_count == 1


def test_on_progress_acrescenta_mensagem_ao_log(qtbot, app_config):
    w = _window(qtbot, app_config)

    evento = ProgressEvent(etapa="HD", mensagem="Analisando HDs...")
    w._on_progress(evento)

    assert "HD" in w.log_area.toPlainText()
    assert "Analisando HDs..." in w.log_area.toPlainText()


def test_on_capture_done_instancia_dialog_de_revisao(qtbot, app_config, monkeypatch):
    """_on_capture_done deve extrair cameras dos DVRs e criar VisualReviewDialog."""
    from PySide6.QtWidgets import QDialog
    from src.domain.models import Camera

    recebidos = []

    class FakeDialog(QDialog):
        def __init__(self, cameras, error_img, parent=None):
            super().__init__(parent)
            recebidos.append(cameras)

        def show(self):
            pass  # não exibe janela real nos testes

    monkeypatch.setattr(main_window, "VisualReviewDialog", FakeDialog)

    # DVR com 2 câmeras
    dvr = DVR(nome="DVR_TESTE", ip="1.2.3.4", qtd_cameras=2)
    dvr.cameras = [Camera("C1", "foto1.jpg"), Camera("C2", "foto2.jpg")]

    w = _window(qtbot, app_config)
    w._on_capture_done([dvr])

    # dialog foi criado com List[Camera], não List[DVR]
    assert len(recebidos) == 1
    assert all(isinstance(c, Camera) for c in recebidos[0])
    assert len(recebidos[0]) == 2


def test_on_capture_done_todas_offline_pula_dialog_e_retoma_worker(
    qtbot, app_config, monkeypatch
):
    """Regressão: DVR offline → todas cameras com error_img → não abre dialog,
    chama resume_after_visual imediatamente (evita dialog vazio travado)."""
    from PySide6.QtWidgets import QDialog
    from src.domain.models import Camera

    dialog_criado = []

    class FakeDialog(QDialog):
        def __init__(self, cameras, error_img, parent=None):
            super().__init__(parent)
            dialog_criado.append(True)

        def show(self):
            pass

    monkeypatch.setattr(main_window, "VisualReviewDialog", FakeDialog)

    retomadas = []

    class FakeWorker:
        def resume_after_visual(self, dvrs):
            retomadas.append(dvrs)

    dvr = DVR(nome="OFFLINE_DVR", ip="1.2.3.4", qtd_cameras=2)
    dvr.cameras = [
        Camera("C1", app_config.error_img, "NAO_ANALISADO"),
        Camera("C2", app_config.error_img, "NAO_ANALISADO"),
    ]

    w = _window(qtbot, app_config)
    w._worker = FakeWorker()
    w._on_capture_done([dvr])

    # Dialog não foi criado, worker retomado direto
    assert dialog_criado == []
    assert len(retomadas) == 1


def test_on_visual_review_done_resume_worker(qtbot, app_config):
    """Após fechar o diálogo, resume_after_visual do worker deve ser chamado."""
    from PySide6.QtWidgets import QDialog

    chamadas = []

    class FakeWorker:
        def resume_after_visual(self, dvrs):
            chamadas.append(dvrs)

    w = _window(qtbot, app_config)
    w._worker = FakeWorker()
    w._pending_dvrs = _dvr()

    w._on_visual_review_done(QDialog.DialogCode.Accepted)

    assert len(chamadas) == 1
