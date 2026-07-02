from __future__ import annotations

import html
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from typing import Optional

from src.domain.events import ChecklistResult, EmailDraft, ProgressEvent
from src.domain.models import DVR, cameras_para_revisar, todas_as_cameras
from src.infra.app_config import AppConfig
from src.infra.snapshot_repo import SnapshotRepository
from src.ui.email_preview_dialog import EmailPreviewDialog
from src.ui.visual_review_dialog import VisualReviewDialog
from src.ui.worker import ChecklistWorker

# ── Paleta CMD ────────────────────────────────────────────────────────────────
_COR_NORMAL   = "#CCCCCC"   # texto padrão
_COR_CABECALHO= "#61D6D6"   # etapas / seções (cyan)
_COR_DVR      = "#F9F1A5"   # nome do DVR (amarelo)
_COR_HD       = "#B5CEA8"   # info de HD (verde claro)
_COR_OK       = "#16C60C"   # sucesso (verde vivo)
_COR_ERRO     = "#E74856"   # offline / erro (vermelho)
_COR_AVISO    = "#F9F1A5"   # avisos (amarelo)
_BG_TERMINAL  = "#0C0C0C"   # fundo preto CMD


def _cor_da_linha(texto: str) -> str:
    """Detecta a cor certa para uma linha pelo conteúdo."""
    t = texto.upper()
    # erros / offline têm prioridade
    if any(k in t for k in ("OFFLINE", "SEM CONEXÃO", "TIMEOUT", "ERRO", "⛔", "❌")):
        return _COR_ERRO
    # sucesso
    if any(k in t for k in ("... OK", "NORMAL", "CONCLUÍDO", "SUCESSO", "✅")):
        return _COR_OK
    # cabeçalhos de etapa (emojis de seção + tags [ETAPA])
    if any(k in texto for k in ("🔍", "🎥 CAPTURANDO", "👁", "🏁", "▶", "⏱")):
        return _COR_CABECALHO
    if texto.lstrip().startswith("[") and "]" in texto:
        return _COR_CABECALHO
    # nome do DVR
    if "📡" in texto:
        return _COR_DVR
    # info de HD
    if "💽" in texto:
        return _COR_HD
    return _COR_NORMAL


class MainWindow(QMainWindow):
    """
    Janela principal do CheckCam.

    Exibe campos de credenciais, botão para iniciar o checklist e
    um terminal estilizado (fundo preto, cores por tipo de mensagem)
    que replica a saída do CMD do sistema legado.
    """

    def __init__(
        self,
        dvrs: List[DVR],
        config: AppConfig,
        parent=None,
        snapshot_repo: Optional[SnapshotRepository] = None,
        instalacao_id: int = 0,
    ) -> None:
        super().__init__(parent)
        self._dvrs = dvrs
        self._config = config
        self._snapshot_repo = snapshot_repo
        self._instalacao_id = instalacao_id
        self._worker: ChecklistWorker | None = None
        self._pending_dvrs: List[DVR] = []
        self._review_dialog: VisualReviewDialog | None = None
        self._email_dialog: EmailPreviewDialog | None = None
        self._setup_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"CheckCam – {self._config.nome_instalacao}")
        self.setMinimumSize(780, 560)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(8, 8, 8, 8)

        # ── Credenciais ──────────────────────────────────────────────────────
        cred = QHBoxLayout()
        cred.addWidget(QLabel("Usuário:"))
        self.usuario_input = QLineEdit(self._config.usuario)
        self.usuario_input.setFixedWidth(160)
        cred.addWidget(self.usuario_input)

        cred.addSpacing(16)
        cred.addWidget(QLabel("Senha:"))
        self.senha_input = QLineEdit(self._config.senha)
        self.senha_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.senha_input.setFixedWidth(160)
        cred.addWidget(self.senha_input)

        cred.addStretch()
        root.addLayout(cred)

        # ── Botão ─────────────────────────────────────────────────────────────
        self.btn_iniciar = QPushButton("▶  Iniciar Checklist")
        self.btn_iniciar.setFixedHeight(36)
        self.btn_iniciar.clicked.connect(self._iniciar)
        root.addWidget(self.btn_iniciar)

        # ── Terminal ──────────────────────────────────────────────────────────
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {_BG_TERMINAL};
                color: {_COR_NORMAL};
                border: 1px solid #333333;
                padding: 4px;
            }}
        """)
        root.addWidget(self.log_area)

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _iniciar(self) -> None:
        self._config.usuario = self.usuario_input.text().strip()
        self._config.senha = self.senha_input.text()

        self.btn_iniciar.setEnabled(False)
        self.log_area.clear()
        self._log(f"▶ Iniciando checklist — {self._config.nome_instalacao}")

        self._worker = ChecklistWorker(
            self._dvrs,
            self._config,
            snapshot_repo=self._snapshot_repo,
            instalacao_id=self._instalacao_id,
        )
        self._worker.progress_signal.connect(self._on_progress)
        self._worker.log_signal.connect(self._on_log_detalhe)
        self._worker.capture_done_signal.connect(self._on_capture_done)
        self._worker.email_review_signal.connect(self._on_email_review)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_progress(self, event: ProgressEvent) -> None:
        self._log(f"[{event.etapa}] {event.mensagem}")

    def _on_log_detalhe(self, text: str) -> None:
        """Linhas detalhadas por DVR/câmera vindas do core via log_signal."""
        for linha in text.split("\n"):
            if linha.strip():
                self._log(linha)

    def _on_capture_done(self, dvrs: List[DVR]) -> None:
        """Recebido do worker: exibe diálogo de revisão visual na main thread.

        VisualReviewDialog espera List[Camera], não List[DVR].
        As câmeras são objetos mutáveis compartilhados: o status atualizado
        pelo diálogo já está refletido nos DVRs armazenados em _pending_dvrs.

        Se nenhuma câmera tiver imagem válida (todos os DVRs offline), o
        dialog é pulado e o worker é retomado imediatamente.
        """
        self._pending_dvrs = dvrs

        # Extrai cameras de todos os DVRs (referências compartilhadas — mutável)
        cameras = todas_as_cameras(dvrs)

        # Conta apenas as câmeras com imagem válida (não error_img)
        pendentes = cameras_para_revisar(cameras, self._config.error_img)

        if not pendentes:
            self._log("[VISUAL] Nenhuma câmera capturada — pulando revisão visual.")
            if self._worker is not None:
                self._worker.resume_after_visual(self._pending_dvrs)
            return

        self._log(f"[VISUAL] Abrindo revisão visual de {len(pendentes)} câmera(s)…")
        self._review_dialog = VisualReviewDialog(cameras, self._config.error_img, self)
        self._review_dialog.finished.connect(self._on_visual_review_done)
        self._review_dialog.show()

    def _on_visual_review_done(self, result_code: int) -> None:
        """Chamado quando o diálogo de revisão fecha — retoma o worker."""
        if self._worker is not None:
            self._worker.resume_after_visual(self._pending_dvrs)

    def _on_email_review(self, draft: EmailDraft) -> None:
        """Recebido do worker: abre o preview do e-mail na main thread.

        O worker está pausado aguardando ``resume_after_email``. Ao fechar o
        diálogo, retomamos com o rascunho editado (Enviar) ou com None
        (Cancelar) — neste caso o pipeline conclui sem enviar.
        """
        self._log("[EMAIL] Abrindo preview do e-mail para revisão…")
        self._email_dialog = EmailPreviewDialog(draft, self)
        self._email_dialog.finished.connect(self._on_email_review_done)
        self._email_dialog.show()

    def _on_email_review_done(self, result_code: int) -> None:
        """Chamado quando o preview do e-mail fecha — retoma o worker."""
        if self._worker is None or self._email_dialog is None:
            return
        if result_code == QDialog.DialogCode.Accepted:
            self._worker.resume_after_email(self._email_dialog.get_draft())
        else:
            self._log("[EMAIL] Envio cancelado pelo usuário.")
            self._worker.resume_after_email(None)

    def _on_finished(self, result: ChecklistResult) -> None:
        self._log("")
        self._log("─" * 60)
        self._log("✅ Checklist concluído com sucesso!")
        self._log(f"   Excel : {result.excel_path}")
        self._log(f"   PDF   : {result.pdf_path}")
        if result.book_path:
            self._log(f"   Book  : {result.book_path}")
        self._log("─" * 60)
        self.btn_iniciar.setEnabled(True)

        # Popup modal + fecha a janela ao confirmar — volta pra HomeWindow
        anexos = [result.pdf_path]
        if result.book_path:
            anexos.append(result.book_path)
        if result.email_enviado:
            linha_email = (
                f"E-mail enviado para {len(self._config.emails)} destinatário(s)."
            )
        else:
            linha_email = "E-mail NÃO enviado (cancelado no preview)."
        resumo = (
            f"Checklist de {self._config.nome_instalacao} concluído!\n\n"
            f"{linha_email}"
            f"\n\nArquivos gerados:\n  " + "\n  ".join(anexos)
        )
        QMessageBox.information(self, "Checklist concluído", resumo)
        self.close()

    def _on_error(self, msg: str) -> None:
        self._log(f"\n❌ Erro: {msg}")
        self.btn_iniciar.setEnabled(True)
        QMessageBox.critical(self, "Erro no checklist", msg)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, text: str) -> None:
        """Insere uma linha no terminal com cor automática baseada no conteúdo."""
        if not text.strip():
            self.log_area.insertHtml("<br>")
            self.log_area.verticalScrollBar().setValue(
                self.log_area.verticalScrollBar().maximum()
            )
            return

        cor = _cor_da_linha(text)

        # preserva espaços iniciais de indentação
        stripped = text.lstrip(" ")
        n_spaces = len(text) - len(stripped)
        safe = "&nbsp;" * n_spaces + html.escape(stripped)

        self.log_area.insertHtml(
            f'<span style="color:{cor}; white-space:pre;">{safe}</span><br>'
        )
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
