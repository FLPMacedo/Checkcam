from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.domain.events import EmailDraft


class EmailPreviewDialog(QDialog):
    """
    Preview editável do e-mail antes do envio.

    Exibe o rascunho composto pelo pipeline (assunto, destinatários e corpo
    editáveis; anexos apenas para conferência) e deixa o operador ajustar o
    texto antes de confirmar.

    Use ``get_draft()`` após ``exec()``/``accepted`` para obter o rascunho com
    as edições. Se o diálogo for rejeitado (Cancelar/Esc), a MainWindow trata
    como cancelamento do envio.
    """

    def __init__(self, draft: EmailDraft, parent=None) -> None:
        super().__init__(parent)
        self._draft = draft
        self.setWindowTitle("Revisar e-mail antes de enviar")
        self.setMinimumSize(720, 600)
        self._build_ui()
        self._populate()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form = QFormLayout()

        self._assunto = QLineEdit()
        form.addRow("Assunto", self._assunto)

        self._destinatarios = QLineEdit()
        self._destinatarios.setPlaceholderText("um;dois@email.com;tres@email.com")
        form.addRow("Destinatários", self._destinatarios)
        root.addLayout(form)

        dica = QLabel("Separe os destinatários por ponto-e-vírgula ( ; ).")
        dica.setStyleSheet("color:#888; font-size:9pt;")
        root.addWidget(dica)

        root.addWidget(QLabel("Mensagem"))
        self._corpo = QTextEdit()
        self._corpo.setFont(QFont("Segoe UI", 10))
        self._corpo.setAcceptRichText(False)
        root.addWidget(self._corpo, stretch=1)

        root.addWidget(QLabel("Anexos (somente leitura)"))
        self._anexos = QListWidget()
        self._anexos.setMaximumHeight(90)
        root.addWidget(self._anexos)

        # ── Enviar / Cancelar ──
        buttons = QDialogButtonBox()
        self._btn_enviar = QPushButton("✉  Enviar")
        self._btn_enviar.setDefault(True)
        self._btn_cancelar = QPushButton("Cancelar envio")
        buttons.addButton(self._btn_enviar, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self._btn_cancelar, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── Preenchimento ─────────────────────────────────────────────────────────

    def _populate(self) -> None:
        self._assunto.setText(self._draft.assunto)
        self._destinatarios.setText(";".join(self._draft.destinatarios))
        self._corpo.setPlainText(self._draft.corpo)
        for anexo in self._draft.anexos:
            self._anexos.addItem(anexo)

    # ── API pública ─────────────────────────────────────────────────────────

    def get_draft(self) -> EmailDraft:
        """Retorna o rascunho com as edições feitas na tela.

        Anexos são preservados do rascunho original (não editáveis aqui).
        """
        destinatarios = [
            e.strip()
            for e in self._destinatarios.text().split(";")
            if e.strip()
        ]
        return EmailDraft(
            assunto=self._assunto.text(),
            corpo=self._corpo.toPlainText(),
            destinatarios=destinatarios,
            anexos=list(self._draft.anexos),
        )
