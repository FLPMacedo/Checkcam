from __future__ import annotations

from typing import Callable, List, Optional

from src.core.camera_capture import capturar_cameras
from src.core.hd_analyzer import analisar_hd
from src.core.visual_review import analisar_visual
from src.domain.events import ChecklistResult, EmailDraft, ProgressEvent
from src.domain.models import DVR
from src.infra.app_config import AppConfig
from src.infra.snapshot_repo import SnapshotRepository
from src.reports.book_builder import gerar_book_excel
from src.reports.email_sender import compor_email, enviar_draft
from src.reports.excel_builder import gerar_excel
from src.reports.pdf_exporter import exportar_pdf

# Tipo da função de revisão visual: recebe (dvrs, error_img) → dvrs
_VisualFn = Callable[[List[DVR], str], List[DVR]]

# Tipo do hook de preview de e-mail: recebe o rascunho e devolve uma versão
# (possivelmente editada) ou None para cancelar o envio.
_EmailReviewFn = Callable[[EmailDraft], Optional[EmailDraft]]


class ChecklistService:
    """
    Orquestra o pipeline completo de checklist:
      HD → Captura → Visual → Excel/PDF → Book PDF → E-mail.

    Emite um ProgressEvent via on_progress antes de cada etapa.

    O parâmetro visual_review_fn permite injetar uma implementação alternativa
    de revisão visual (ex.: QDialog em vez de cv2). Se omitido, usa a versão
    cv2 padrão (analisar_visual).

    Dois PDFs são gerados a cada execução:
      - Checklist: grid 4×N (ou 4×N + 2×N largo para 17+ câmeras)
      - Book:     uma câmera por página, imagem grande para inspeção detalhada

    Ambos vão como anexo no e-mail final.
    """

    def __init__(
        self,
        config: AppConfig,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
        visual_review_fn: Optional[_VisualFn] = None,
        on_log: Optional[Callable[[str], None]] = None,
        email_review_fn: Optional[_EmailReviewFn] = None,
        snapshot_repo: Optional[SnapshotRepository] = None,
        instalacao_id: int = 0,
    ) -> None:
        self._config = config
        self._on_progress = on_progress or (lambda e: None)
        self._visual_review_fn: _VisualFn = visual_review_fn or analisar_visual
        self._on_log = on_log  # None → core usa print()
        # Default: identidade → envia o rascunho como está (comportamento legado).
        self._email_review_fn: _EmailReviewFn = email_review_fn or (lambda d: d)
        # Persistência opcional: se presente, grava um snapshot ao fim do pipeline.
        self._snapshot_repo = snapshot_repo
        self._instalacao_id = instalacao_id

    # ── helpers ───────────────────────────────────────────────────────────────

    def _emit(self, etapa: str, mensagem: str, total: int = 0, atual: int = 0) -> None:
        self._on_progress(
            ProgressEvent(etapa=etapa, mensagem=mensagem, total=total, atual=atual)
        )

    # ── pipeline ──────────────────────────────────────────────────────────────

    def executar(self, dvrs: List[DVR]) -> ChecklistResult:
        """Executa todas as etapas e devolve o ChecklistResult."""

        self._emit("HD", "Analisando HDs dos DVRs...")
        dvrs = analisar_hd(dvrs, self._config, on_log=self._on_log)

        self._emit("CAPTURA", "Capturando imagens das câmeras...")
        dvrs = capturar_cameras(dvrs, self._config, on_log=self._on_log)

        self._emit("VISUAL", "Aguardando revisão visual...")
        dvrs = self._visual_review_fn(dvrs, self._config.error_img)

        self._emit("RELATORIO", "Gerando relatório Excel/PDF...")
        excel_path = gerar_excel(dvrs, self._config)
        pdf_path = exportar_pdf(excel_path)

        self._emit("BOOK", "Gerando book PDF (1 câmera por página)...")
        book_excel_path = gerar_book_excel(dvrs, self._config)
        book_path = exportar_pdf(book_excel_path)

        self._emit("EMAIL", "Enviando e-mail...")
        draft = compor_email(dvrs, pdf_path, self._config, book_path=book_path)
        draft = self._email_review_fn(draft)

        email_enviado = draft is not None
        if email_enviado:
            enviar_draft(draft, self._config)

        result = ChecklistResult(
            dvrs=dvrs,
            excel_path=excel_path,
            pdf_path=pdf_path,
            book_excel_path=book_excel_path,
            book_path=book_path,
            email_enviado=email_enviado,
        )

        # Persiste o snapshot depois do e-mail. Roda mesmo se o envio for
        # cancelado — o histórico do dashboard registra todo checklist executado.
        if self._snapshot_repo is not None:
            result.snapshot_id = self._snapshot_repo.gravar(
                self._instalacao_id, result
            )

        return result
