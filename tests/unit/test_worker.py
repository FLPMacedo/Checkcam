"""Unit tests for src/ui/worker.py"""
from src.domain.events import ChecklistResult, ProgressEvent
from src.domain.models import DVR
from src.ui import worker


def _dvr():
    return [DVR(nome="DVR_TESTE", ip="1.2.3.4", qtd_cameras=1)]


def _make_mock_service(progress_etapas=None, raise_msg=None, call_visual=False):
    """Retorna uma classe MockService configurável.

    call_visual=True faz o mock chamar visual_review_fn, simulando o ponto
    de pausa que o ChecklistWorker injeta para a revisão visual na main thread.
    """
    etapas = progress_etapas or []
    msg = raise_msg
    do_visual = call_visual

    class MockService:
        def __init__(self, config, on_progress=None, visual_review_fn=None, on_log=None):
            self._on_progress = on_progress or (lambda e: None)
            self._visual_fn = visual_review_fn or (lambda dvrs, e: dvrs)

        def executar(self, dvrs):
            if msg:
                raise RuntimeError(msg)
            for etapa in etapas:
                self._on_progress(ProgressEvent(etapa=etapa, mensagem="teste"))
            if do_visual:
                dvrs = self._visual_fn(dvrs, "error.jpg")
            return ChecklistResult(dvrs=dvrs, excel_path="/x.xlsx", pdf_path="/x.pdf")

    return MockService


def test_worker_emite_progresso_via_signal(qtbot, app_config, monkeypatch):
    monkeypatch.setattr(worker, "ChecklistService",
                        _make_mock_service(progress_etapas=["HD", "CAPTURA"]))

    w = worker.ChecklistWorker(_dvr(), app_config)
    recebidos = []
    w.progress_signal.connect(recebidos.append)

    with qtbot.waitSignal(w.finished_signal, timeout=5000):
        w.start()

    assert len(recebidos) == 2
    assert recebidos[0].etapa == "HD"
    assert recebidos[1].etapa == "CAPTURA"


def test_worker_emite_finished_com_resultado(qtbot, app_config, monkeypatch):
    monkeypatch.setattr(worker, "ChecklistService", _make_mock_service())

    w = worker.ChecklistWorker(_dvr(), app_config)
    resultados = []
    w.finished_signal.connect(resultados.append)

    with qtbot.waitSignal(w.finished_signal, timeout=5000):
        w.start()

    assert len(resultados) == 1
    assert isinstance(resultados[0], ChecklistResult)
    assert resultados[0].sucesso is True


def test_worker_emite_error_signal_quando_servico_falha(qtbot, app_config, monkeypatch):
    monkeypatch.setattr(worker, "ChecklistService",
                        _make_mock_service(raise_msg="falha simulada"))

    w = worker.ChecklistWorker(_dvr(), app_config)
    erros = []
    w.error_signal.connect(erros.append)

    with qtbot.waitSignal(w.error_signal, timeout=5000):
        w.start()

    assert len(erros) == 1
    assert "falha simulada" in erros[0]


def test_worker_termina_apos_execucao(qtbot, app_config, monkeypatch):
    monkeypatch.setattr(worker, "ChecklistService", _make_mock_service())

    w = worker.ChecklistWorker(_dvr(), app_config)

    with qtbot.waitSignal(w.finished_signal, timeout=5000):
        w.start()

    qtbot.waitUntil(lambda: not w.isRunning(), timeout=3000)
    assert not w.isRunning()


def test_worker_emite_capture_done_signal(qtbot, app_config, monkeypatch):
    """capture_done_signal é emitido quando o serviço chama visual_review_fn."""
    monkeypatch.setattr(worker, "ChecklistService",
                        _make_mock_service(call_visual=True))

    w = worker.ChecklistWorker(_dvr(), app_config)
    capture_received = []
    w.capture_done_signal.connect(capture_received.append)

    # Auto-resume para não bloquear o teste indefinidamente
    w.capture_done_signal.connect(lambda dvrs: w.resume_after_visual(dvrs))

    with qtbot.waitSignal(w.finished_signal, timeout=5000):
        w.start()

    assert len(capture_received) == 1


def test_worker_retoma_pipeline_apos_resume_after_visual(qtbot, app_config, monkeypatch):
    """Worker conclui e emite finished_signal depois de resume_after_visual()."""
    monkeypatch.setattr(worker, "ChecklistService",
                        _make_mock_service(call_visual=True))

    w = worker.ChecklistWorker(_dvr(), app_config)
    resultados = []
    w.finished_signal.connect(resultados.append)

    w.capture_done_signal.connect(lambda dvrs: w.resume_after_visual(dvrs))

    with qtbot.waitSignal(w.finished_signal, timeout=5000):
        w.start()

    assert len(resultados) == 1
    assert isinstance(resultados[0], ChecklistResult)
