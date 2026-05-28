from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.domain.instalacao import Instalacao
from src.infra.instalacao_repo import InstalacaoRepository
from src.ui.instalacao_form import InstalacaoFormDialog

_ID_ROLE = Qt.ItemDataRole.UserRole


class InstalacaoSelectorWidget(QWidget):
    """
    Widget embarcável que lista todas as instalações cadastradas e
    oferece ações de Nova / Editar / Remover.

    Injete um InstalacaoRepository na construção. A lista é carregada
    automaticamente e atualizada após cada operação.
    """

    def __init__(self, repo: InstalacaoRepository, parent=None) -> None:
        super().__init__(parent)
        self._repo = repo
        self._build_ui()
        self._refresh()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Instalações cadastradas:"))

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        self._btn_nova   = QPushButton("Nova")
        self._btn_editar = QPushButton("Editar")
        self._btn_remover = QPushButton("Remover")
        self._btn_nova.clicked.connect(self._nova)
        self._btn_editar.clicked.connect(self._editar)
        self._btn_remover.clicked.connect(self._remover)
        btns.addWidget(self._btn_nova)
        btns.addWidget(self._btn_editar)
        btns.addWidget(self._btn_remover)
        btns.addStretch()
        layout.addLayout(btns)

    # ── Operações ─────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        """Recarrega a lista do banco."""
        self._list.clear()
        for inst in self._repo.listar():
            item = QListWidgetItem(inst.nome)
            item.setData(_ID_ROLE, inst.id)
            self._list.addItem(item)

    def _nova(self) -> None:
        dialog = InstalacaoFormDialog(parent=self)
        if dialog.exec() == InstalacaoFormDialog.DialogCode.Accepted:
            inst = dialog.get_instalacao()
            self._repo.salvar(inst)
            self._refresh()

    def _editar(self) -> None:
        item = self._list.currentItem()
        if item is None:
            QMessageBox.information(self, "Selecione", "Selecione uma instalação para editar.")
            return
        inst_id = item.data(_ID_ROLE)
        inst = self._repo.obter(inst_id)
        dialog = InstalacaoFormDialog(inst, parent=self)
        if dialog.exec() == InstalacaoFormDialog.DialogCode.Accepted:
            updated = dialog.get_instalacao()
            self._repo.salvar(updated)
            self._refresh()

    def _remover(self) -> None:
        item = self._list.currentItem()
        if item is None:
            QMessageBox.information(self, "Selecione", "Selecione uma instalação para remover.")
            return
        resp = QMessageBox.question(
            self,
            "Confirmar remoção",
            f'Remover "{item.text()}"?\nDVRs e e-mails vinculados serão excluídos.',
        )
        if resp == QMessageBox.StandardButton.Yes:
            self._repo.remover(item.data(_ID_ROLE))
            self._refresh()

    # ── API pública ───────────────────────────────────────────────────────────

    def atualizar_lista(self) -> None:
        """Recarrega a lista do banco (chamado externamente após importação/restauração)."""
        self._refresh()

    def selected_instalacao(self) -> Optional[Instalacao]:
        """Retorna a instalação selecionada completa (com dvrs e emails), ou None."""
        item = self._list.currentItem()
        if item is None:
            return None
        return self._repo.obter(item.data(_ID_ROLE))
