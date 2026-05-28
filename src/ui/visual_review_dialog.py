from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
)

from src.domain.models import Camera

_STATUS_KEYS: dict[Qt.Key, str] = {
    Qt.Key.Key_1: "OK",
    Qt.Key.Key_2: "EMBAÇADA_SUJA",
    Qt.Key.Key_3: "DISTORCIDA",
    Qt.Key.Key_4: "TONALIDADE_CLARA_ESCURA",
    Qt.Key.Key_5: "NAO_RECONHECIDA",
}


class VisualReviewDialog(QDialog):
    """
    Diálogo de revisão visual — substitui o cv2.imshow do legado.

    Exibe cada câmera em tela cheia e aguarda input do teclado:
        1 → OK
        2 → EMBAÇADA_SUJA
        3 → DISTORCIDA
        4 → TONALIDADE_CLARA_ESCURA
        5 → NAO_RECONHECIDA
        Q / Escape → interrompe; câmeras restantes mantêm status atual

    Câmeras cuja imagem coincide com error_img são ignoradas.
    Câmeras cuja imagem não pode ser carregada recebem status "ERRO_IMAGEM".
    """

    def __init__(
        self,
        cameras: List[Camera],
        error_img: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._cameras = [c for c in cameras if c.imagem != error_img]
        self._idx = 0
        self._setup_ui()
        # Defere _show_current() para depois do __init__ retornar.
        # Garante que o caller consiga conectar `finished` antes de
        # um possível accept() automático (caso _cameras esteja vazio).
        QTimer.singleShot(0, self._show_current)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        self.setWindowTitle("Revisão Visual")
        self.setMinimumSize(900, 650)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14pt; padding: 6px;")
        layout.addWidget(self.info_label)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label, stretch=1)

        hint = QLabel(
            "1 OK  │  2 EMBAÇADA/SUJA  │  3 DISTORCIDA  │  "
            "4 TONALIDADE  │  5 NÃO RECONHECIDA  │  Q/ESC sair"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("background:#111; color:#eee; font-size:11pt; padding:6px;")
        layout.addWidget(hint)

    # ── Navegação ─────────────────────────────────────────────────────────────

    def _show_current(self) -> None:
        if self._idx >= len(self._cameras):
            self.accept()
            return

        cam = self._cameras[self._idx]

        # Atualiza info e título ANTES de tentar carregar a imagem.
        # Garante que o usuário sempre veja qual câmera está em foco,
        # mesmo se o pixmap falhar (em vez de tela em branco silenciosa).
        self.info_label.setText(
            f"Câmera {self._idx + 1}/{len(self._cameras)} — {cam.nome}"
        )
        self.setWindowTitle(f"Revisão Visual – {cam.nome}")

        # Tenta carregar a imagem; calcula tamanho de escala em runtime,
        # baseado no tamanho atual do label, para evitar imagem minúscula
        # em monitores pequenos ou imagem cortada em monitores grandes.
        pixmap = QPixmap(cam.imagem)

        if pixmap.isNull():
            cam.status = "ERRO_IMAGEM"
            self.image_label.clear()
            self.image_label.setStyleSheet(
                "color: #E74856; font-size: 13pt; padding: 24px;"
                "background:#1a1a1a;"
            )
            self.image_label.setText(
                f"⚠  Imagem não pôde ser carregada pelo Qt.\n\n"
                f"Caminho: {cam.imagem}\n\n"
                f"Pressione 1-5 para classificar ou Q/ESC para sair."
            )
            return

        # Imagem carregada — limpa estilo de erro caso tenha sido aplicado antes
        self.image_label.setStyleSheet("")
        self.image_label.setText("")

        # Escala usando o tamanho atual do label (preserva proporção)
        target = self.image_label.size()
        if target.width() < 200 or target.height() < 200:
            # fallback se ainda não foi layoutado
            target = pixmap.size().scaled(
                1600, 900, Qt.AspectRatioMode.KeepAspectRatio
            )

        scaled = pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    # ── Input ─────────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.key()

        if key in _STATUS_KEYS:
            self._cameras[self._idx].status = _STATUS_KEYS[key]
            self._idx += 1
            self._show_current()
        elif key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.reject()
        else:
            super().keyPressEvent(event)
