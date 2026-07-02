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
    email_review_signal = Signal(object)
    finished_signal = Signal(object)
    error_signal = Signal(str)
    log_signal = Signal(str)

    started_count = 0

    def __init__(self, dvrs, config, parent=None, snapshot_repo=None,
                 instalacao_id=0):
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


def test_main_window_repassa_snapshot_repo_e_instalacao_id_ao_worker(
    qtbot, app_config, monkeypatch
):
    """MainWindow constrói o ChecklistWorker com snapshot_repo e instalacao_id."""
    capturado = {}

    class _SpyWorker(_FakeWorker):
        def __init__(self, dvrs, config, parent=None, snapshot_repo=None,
                     instalacao_id=0):
            super().__init__(dvrs, config, parent)
            capturado["snapshot_repo"] = snapshot_repo
            capturado["instalacao_id"] = instalacao_id

    monkeypatch.setattr(main_window, "ChecklistWorker", _SpyWorker)

    sentinela = object()
    w = MainWindow(_dvr(), app_config, snapshot_repo=sentinela, instalacao_id=5)
    qtbot.addWidget(w)
    qtbot.mouseClick(w.btn_iniciar, Qt.MouseButton.LeftButton)

    assert capturado["snapshot_repo"] is sentinela
    assert capturado["instalacao_id"] == 5


def test_botao_abrir_dashboard_spawna_processo(qtbot, app_config, monkeypatch):
    chamado = []
    monkeypatch.setattr(main_window, "spawn_dashboard", lambda db="": chamado.append(db))

    w = MainWindow(_dvr(), app_config, db_path="meu.db")
    qtbot.addWidget(w)
    qtbot.mouseClick(w.btn_dashboard, Qt.MouseButton.LeftButton)

    assert chamado == ["meu.db"]


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


# ─── Fechamento automático após conclusão ────────────────────────────────────

def test_on_finished_mostra_resumo_e_fecha_janela(qtbot, app_config, monkeypatch):
    """Quando o pipeline termina (e-mail enviado), a janela deve fechar
    automaticamente após o usuário confirmar o popup de sucesso."""
    from src.domain.events import ChecklistResult

    # Não bloqueia o teste no popup; devolve False (usuário não abriu dashboard)
    resumos = []
    monkeypatch.setattr(
        main_window.MainWindow, "_popup_conclusao",
        lambda self, resumo: resumos.append(resumo) or False,
    )

    # Spy no close()
    closes = []
    monkeypatch.setattr(
        main_window.MainWindow, "close", lambda self: closes.append(True)
    )

    w = _window(qtbot, app_config)
    result = ChecklistResult(
        dvrs=_dvr(),
        excel_path="C:/fake/checklist.xlsx",
        pdf_path="C:/fake/checklist.pdf",
        book_excel_path="C:/fake/book.xlsx",
        book_path="C:/fake/book.pdf",
    )
    w._on_finished(result)

    # Popup mostrado e janela fechada
    assert len(resumos) == 1
    assert len(closes) == 1


def test_on_finished_abrir_dashboard_spawna_processo(qtbot, app_config, monkeypatch):
    """Se o usuário clica 'Abrir Dashboard' no popup final, spawna o processo."""
    from src.domain.events import ChecklistResult

    monkeypatch.setattr(
        main_window.MainWindow, "_popup_conclusao", lambda self, resumo: True
    )
    monkeypatch.setattr(main_window.MainWindow, "close", lambda self: None)
    chamado = []
    monkeypatch.setattr(main_window, "spawn_dashboard", lambda db="": chamado.append(db))

    w = MainWindow(_dvr(), app_config, db_path="pipe.db")
    qtbot.addWidget(w)
    w._on_finished(ChecklistResult(dvrs=_dvr(), excel_path="x", pdf_path="y"))

    assert chamado == ["pipe.db"]


def test_on_finished_loga_caminho_do_book(qtbot, app_config, monkeypatch):
    """O caminho do book PDF deve aparecer no log junto com o checklist."""
    from src.domain.events import ChecklistResult

    monkeypatch.setattr(
        main_window.MainWindow, "_popup_conclusao", lambda self, resumo: False
    )
    monkeypatch.setattr(main_window.MainWindow, "close", lambda self: None)

    w = _window(qtbot, app_config)
    result = ChecklistResult(
        dvrs=_dvr(),
        excel_path="C:/fake/x.xlsx",
        pdf_path="C:/fake/x.pdf",
        book_path="C:/fake/book_xyz.pdf",
    )
    w._on_finished(result)

    log_text = w.log_area.toPlainText()
    assert "book_xyz.pdf" in log_text


# ─── Preview de e-mail ───────────────────────────────────────────────────────

def test_on_email_review_abre_dialog_com_o_draft(qtbot, app_config, monkeypatch):
    """_on_email_review instancia o EmailPreviewDialog com o draft recebido."""
    from PySide6.QtWidgets import QDialog
    from src.domain.events import EmailDraft

    recebidos = []

    class FakeDialog(QDialog):
        def __init__(self, draft, parent=None):
            super().__init__(parent)
            recebidos.append(draft)

        def show(self):
            pass

    monkeypatch.setattr(main_window, "EmailPreviewDialog", FakeDialog)

    w = _window(qtbot, app_config)
    draft = EmailDraft(assunto="Assunto X")
    w._on_email_review(draft)

    assert len(recebidos) == 1
    assert recebidos[0].assunto == "Assunto X"


def test_on_email_review_done_aceito_retoma_com_draft_editado(qtbot, app_config):
    from PySide6.QtWidgets import QDialog
    from src.domain.events import EmailDraft

    retomados = []

    class FakeWorker:
        def resume_after_email(self, draft):
            retomados.append(draft)

    class FakeDialog:
        def get_draft(self):
            return EmailDraft(assunto="EDITADO")

    w = _window(qtbot, app_config)
    w._worker = FakeWorker()
    w._email_dialog = FakeDialog()

    w._on_email_review_done(QDialog.DialogCode.Accepted)

    assert len(retomados) == 1
    assert retomados[0].assunto == "EDITADO"


def test_on_email_review_done_rejeitado_retoma_com_none(qtbot, app_config):
    from PySide6.QtWidgets import QDialog
    from src.domain.events import EmailDraft

    retomados = []

    class FakeWorker:
        def resume_after_email(self, draft):
            retomados.append(draft)

    class FakeDialog:
        def get_draft(self):
            return EmailDraft(assunto="NAO_DEVE_USAR")

    w = _window(qtbot, app_config)
    w._worker = FakeWorker()
    w._email_dialog = FakeDialog()

    w._on_email_review_done(QDialog.DialogCode.Rejected)

    assert retomados == [None]


def test_on_finished_email_cancelado_mostra_aviso(qtbot, app_config, monkeypatch):
    """Quando email_enviado=False, o popup informa que o e-mail NÃO foi enviado."""
    from PySide6.QtWidgets import QMessageBox
    from src.domain.events import ChecklistResult

    resumos = []
    monkeypatch.setattr(
        main_window.MainWindow, "_popup_conclusao",
        lambda self, resumo: resumos.append(resumo) or False,
    )
    monkeypatch.setattr(main_window.MainWindow, "close", lambda self: None)

    w = _window(qtbot, app_config)
    result = ChecklistResult(
        dvrs=_dvr(),
        excel_path="C:/fake/x.xlsx",
        pdf_path="C:/fake/x.pdf",
        email_enviado=False,
    )
    w._on_finished(result)

    # O resumo do popup deve mencionar o cancelamento do e-mail
    texto = resumos[0]
    assert "NÃO enviado" in texto or "cancelado" in texto.lower()
