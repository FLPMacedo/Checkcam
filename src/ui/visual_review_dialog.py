from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.domain.models import Camera

_STATUS_KEYS: dict[Qt.Key, str] = {
    Qt.Key.Key_1: "OK",
    Qt.Key.Key_2: "EMBAÇADA_SUJA",
    Qt.Key.Key_3: "DISTORCIDA",
    Qt.Key.Key_4: "TONALIDADE_CLARA_ESCURA",
    Qt.Key.Key_5: "NAO_RECONHECIDA",
    Qt.Key.Key_6: "NAO_INSTALADA",
}

# Texto curto que aparece no painel lateral direito, para cada tecla
_HINT_LABELS = [
    ("1", "OK"),
    ("2", "EMBAÇADA / SUJA"),
    ("3", "DISTORCIDA"),
    ("4", "TONALIDADE"),
    ("5", "NÃO RECONHECIDA"),
    ("6", "NÃO INSTALADA"),
]

_PANEL_BG = "#1a1a1a"
_PANEL_FG = "#e6e6e6"
_ACCENT   = "#4EC9B0"   # ciano/turquesa para as teclas e contador
_MUTED    = "#888888"


class VisualReviewDialog(QDialog):
    """
    Diálogo de revisão visual — substitui o cv2.imshow do legado.

    Layout horizontal:
      ┌──────────┬──────────────────────────┬──────────┐
      │  INFO    │                          │  TECLAS  │
      │ (esq.)   │       IMAGEM             │ (dir.)   │
      │ contador │       (centro)           │  1 OK    │
      │ nome     │                          │  2 EMB.  │
      │          │                          │  ...     │
      └──────────┴──────────────────────────┴──────────┘

    Resolve dois problemas do layout anterior:
      - Nome enorme em cima do vídeo "comendo" altura útil
      - Barra de teclas no rodapé escondida pela barra de tarefas do Windows

    Aguarda input do teclado:
        1 → OK            3 → DISTORCIDA              5 → NAO_RECONHECIDA
        2 → EMBAÇADA_SUJA 4 → TONALIDADE_CLARA_ESCURA 6 → NAO_INSTALADA
        0 / ← / Backspace → volta para a câmera anterior (corrigir clique errado)
        Q / Esc → interrompe revisão

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
        self.setStyleSheet("QDialog { background:#000; }")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_info_panel())
        root.addWidget(self._build_image_area(), stretch=1)
        root.addWidget(self._build_hints_panel())

    def _build_info_panel(self) -> QWidget:
        """Painel esquerdo: contador + nome da câmera."""
        self.info_panel = QWidget()
        self.info_panel.setMinimumWidth(220)
        self.info_panel.setMaximumWidth(260)
        self.info_panel.setStyleSheet(
            f"background:{_PANEL_BG}; color:{_PANEL_FG};"
        )

        layout = QVBoxLayout(self.info_panel)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(12)

        header = QLabel("CÂMERA")
        header.setStyleSheet(
            f"font-size:10pt; color:{_MUTED}; letter-spacing:2px;"
        )
        layout.addWidget(header)

        self.counter_label = QLabel("—")
        self.counter_label.setStyleSheet(
            f"font-size:22pt; color:{_ACCENT}; font-weight:bold;"
        )
        layout.addWidget(self.counter_label)

        self.name_label = QLabel("—")
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            f"font-size:13pt; color:{_PANEL_FG}; font-weight:600;"
        )
        layout.addWidget(self.name_label)

        # ── separador visual ──
        layout.addSpacing(18)

        sub_dvr = QLabel("DVR")
        sub_dvr.setStyleSheet(
            f"font-size:9pt; color:{_MUTED}; letter-spacing:2px;"
        )
        layout.addWidget(sub_dvr)

        self.dvr_label = QLabel("—")
        self.dvr_label.setWordWrap(True)
        self.dvr_label.setStyleSheet(
            f"font-size:11pt; color:{_PANEL_FG};"
        )
        layout.addWidget(self.dvr_label)

        layout.addStretch()
        return self.info_panel

    def _build_image_area(self) -> QWidget:
        """Área central: imagem da câmera, fundo preto."""
        container = QWidget()
        container.setStyleSheet("background:#000;")
        wrap = QVBoxLayout(container)
        wrap.setContentsMargins(8, 8, 8, 8)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color:#aaa;")
        wrap.addWidget(self.image_label, stretch=1)
        return container

    def _build_hints_panel(self) -> QWidget:
        """Painel direito: lista vertical das teclas 1–5 + Q/ESC."""
        self.hints_panel = QWidget()
        self.hints_panel.setMinimumWidth(210)
        self.hints_panel.setMaximumWidth(260)
        self.hints_panel.setStyleSheet(
            f"background:{_PANEL_BG}; color:{_PANEL_FG};"
        )

        layout = QVBoxLayout(self.hints_panel)
        layout.setContentsMargins(20, 28, 20, 20)
        layout.setSpacing(14)

        header = QLabel("CLASSIFICAR")
        header.setStyleSheet(
            f"font-size:10pt; color:{_MUTED}; letter-spacing:2px;"
        )
        layout.addWidget(header)

        for key, descricao in _HINT_LABELS:
            linha = QLabel(
                f'<span style="color:{_ACCENT}; font-size:18pt; font-weight:bold;">{key}</span>'
                f'  <span style="color:{_PANEL_FG}; font-size:10pt;">{descricao}</span>'
            )
            linha.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(linha)

        # ── separador entre classificar e navegar ──
        layout.addSpacing(16)
        nav_header = QLabel("NAVEGAR")
        nav_header.setStyleSheet(
            f"font-size:10pt; color:{_MUTED}; letter-spacing:2px;"
        )
        layout.addWidget(nav_header)

        voltar = QLabel(
            f'<span style="color:{_ACCENT}; font-size:18pt; font-weight:bold;">0</span>'
            f'  <span style="color:{_PANEL_FG}; font-size:10pt;">VOLTAR</span>'
        )
        voltar.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(voltar)

        layout.addStretch()

        rodape = QLabel(
            f'<span style="color:{_MUTED}; font-size:9pt;">Q / ESC para sair</span>'
        )
        rodape.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(rodape)
        return self.hints_panel

    # ── Navegação ─────────────────────────────────────────────────────────────

    def _show_current(self) -> None:
        if self._idx >= len(self._cameras):
            self.accept()
            return

        cam = self._cameras[self._idx]

        # Atualiza painel lateral ANTES de tentar carregar a imagem.
        # Garante que o usuário sempre veja qual câmera está em foco.
        self.counter_label.setText(
            f"{self._idx + 1}/{len(self._cameras)}"
        )
        self.name_label.setText(cam.nome)
        self.dvr_label.setText(cam.dvr_nome or "—")

        # Título da janela: 'Revisão Visual – PN ADM1 / C5'
        if cam.dvr_nome:
            self.setWindowTitle(f"Revisão Visual – {cam.dvr_nome} / {cam.nome}")
        else:
            self.setWindowTitle(f"Revisão Visual – {cam.nome}")

        pixmap = QPixmap(cam.imagem)

        if pixmap.isNull():
            cam.status = "ERRO_IMAGEM"
            self.image_label.clear()
            self.image_label.setStyleSheet(
                "color:#E74856; font-size:13pt; padding:24px; background:#1a1a1a;"
            )
            self.image_label.setText(
                f"⚠  Imagem não pôde ser carregada pelo Qt.\n\n"
                f"Caminho: {cam.imagem}\n\n"
                f"Pressione 1-5 para classificar ou Q/ESC para sair."
            )
            return

        self.image_label.setStyleSheet("color:#aaa;")
        self.image_label.setText("")

        target = self.image_label.size()
        if target.width() < 200 or target.height() < 200:
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
        elif key in (Qt.Key.Key_0, Qt.Key.Key_Left, Qt.Key.Key_Backspace):
            # Volta para a câmera anterior (para corrigir uma classificação).
            # Silenciosamente ignora se já estamos na primeira câmera.
            if self._idx > 0:
                self._idx -= 1
                self._show_current()
        elif key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.reject()
        else:
            super().keyPressEvent(event)
