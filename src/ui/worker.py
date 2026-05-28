from __future__ import annotations

import threading
from typing import List

from PySide6.QtCore import QThread, Signal

from src.domain.models import DVR
from src.infra.app_config import AppConfig
from src.services.checklist_service import ChecklistService


class ChecklistWorker(QThread):
    """
    Executa o pipeline de checklist em thread secundária.

    O pipeline é particionado na etapa de revisão visual:
      1. HD + Captura rodam normalmente em background.
      2. Ao chegar na revisão visual, o worker emite ``capture_done_signal``
         com a lista de DVRs e bloqueia (threading.Event) aguardando que a
         main thread exiba o diálogo de revisão e chame ``resume_after_visual``.
      3. Após o desbloqueio, o worker conclui com relatório + e-mail.

    Signals
    -------
    progress_signal(object)      : ProgressEvent emitido a cada etapa
    capture_done_signal(object)  : emitido antes da revisão visual (list[DVR])
    finished_signal(object)      : ChecklistResult ao concluir com sucesso
    error_signal(str)            : mensagem de erro em caso de exceção
    """

    progress_signal: Signal = Signal(object)
    capture_done_signal: Signal = Signal(object)
    finished_signal: Signal = Signal(object)
    error_signal: Signal = Signal(str)
    log_signal: Signal = Signal(str)   # linha de detalhe por DVR/câmera

    def __init__(self, dvrs: List[DVR], config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._dvrs = dvrs
        self._config = config
        self._visual_done = threading.Event()
        self._dvrs_reviewed: List[DVR] = []

    # ── Chamado pela main thread quando o diálogo de revisão fecha ────────────

    def resume_after_visual(self, dvrs: List[DVR]) -> None:
        """
        Deve ser chamado pela MainWindow após o VisualReviewDialog fechar.
        Desbloqueia o worker para continuar com relatório e e-mail.
        """
        self._dvrs_reviewed = dvrs
        self._visual_done.set()

    # ── Bridge injetada no ChecklistService ───────────────────────────────────

    def _visual_review_bridge(self, dvrs: List[DVR], error_img: str) -> List[DVR]:
        """
        Função injetada como visual_review_fn no ChecklistService.

        Pausa a thread do worker, sinaliza a main thread via
        capture_done_signal e aguarda resume_after_visual().
        """
        self._visual_done.clear()
        self.capture_done_signal.emit(dvrs)
        self._visual_done.wait()
        return self._dvrs_reviewed

    # ── QThread.run ───────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            service = ChecklistService(
                self._config,
                on_progress=self.progress_signal.emit,
                visual_review_fn=self._visual_review_bridge,
                on_log=self.log_signal.emit,
            )
            result = service.executar(self._dvrs)
            self.finished_signal.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.error_signal.emit(str(exc))
