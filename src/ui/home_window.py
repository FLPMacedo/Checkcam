from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from typing import Optional

from src.infra.backup import exportar, importar, restaurar_no_repo
from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository
from src.ui.dashboard_launcher import spawn_dashboard
from src.ui.instalacao_selector import InstalacaoSelectorWidget
from src.ui.main_window import MainWindow


class HomeWindow(QMainWindow):
    """
    Janela inicial do CheckCam.

    Exibe o InstalacaoSelectorWidget e botões para:
      - Iniciar Checklist na instalação selecionada
      - Fazer Backup de todas as instalações (→ JSON)
      - Restaurar Backup (← JSON, merge — pula nomes já existentes)
    """

    def __init__(
        self,
        repo: InstalacaoRepository,
        parent=None,
        snapshot_repo: Optional[SnapshotRepository] = None,
        db_path: str = "",
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._snapshot_repo = snapshot_repo
        self._db_path = db_path
        self._checklist_windows: list[MainWindow] = []
        self.setWindowTitle("CheckCam – Gerenciador de Instalações")
        self.setMinimumSize(560, 460)
        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        self._selector = InstalacaoSelectorWidget(self._repo)
        layout.addWidget(self._selector, stretch=1)

        # ── botão principal ───────────────────────────────────────────────────
        self._btn_iniciar = QPushButton("▶  Iniciar Checklist")
        self._btn_iniciar.setFixedHeight(40)
        self._btn_iniciar.clicked.connect(self._iniciar)
        layout.addWidget(self._btn_iniciar)

        self.btn_dashboard = QPushButton("📊  Abrir Dashboard")
        self.btn_dashboard.setFixedHeight(36)
        self.btn_dashboard.setToolTip("Abre o painel de status das instalações")
        self.btn_dashboard.clicked.connect(self._abrir_dashboard)
        layout.addWidget(self.btn_dashboard)

        # ── linha de backup / restaurar ───────────────────────────────────────
        row = QHBoxLayout()
        row.setSpacing(8)

        self._btn_backup = QPushButton("Backup")
        self._btn_backup.setToolTip("Exporta todas as instalações para um arquivo JSON")
        self._btn_backup.clicked.connect(self._fazer_backup)

        self._btn_restaurar = QPushButton("Restaurar Backup")
        self._btn_restaurar.setToolTip(
            "Importa instalações de um arquivo JSON (pula as que já existem)"
        )
        self._btn_restaurar.clicked.connect(self._restaurar_backup)

        row.addWidget(self._btn_backup)
        row.addWidget(self._btn_restaurar)
        layout.addLayout(row)

    # ── Ações — Checklist ─────────────────────────────────────────────────────

    def _iniciar(self) -> None:
        inst = self._selector.selected_instalacao()
        if inst is None:
            QMessageBox.warning(
                self,
                "Nenhuma instalação selecionada",
                "Selecione uma instalação na lista antes de iniciar.",
            )
            return

        config = inst.to_app_config()
        win = MainWindow(
            inst.dvrs,
            config,
            parent=None,
            snapshot_repo=self._snapshot_repo,
            instalacao_id=inst.id,
            db_path=self._db_path,
        )
        win.setWindowTitle(f"CheckCam – {inst.nome}")
        win.show()
        self._checklist_windows.append(win)

    def _abrir_dashboard(self) -> None:
        """Abre o dashboard (janela nativa) em um processo separado."""
        spawn_dashboard(self._db_path)

    # ── Ações — Backup ────────────────────────────────────────────────────────

    def _fazer_backup(self) -> None:
        """Exporta todas as instalações cadastradas para um arquivo JSON."""
        instalacoes = [self._repo.obter(i.id) for i in self._repo.listar()]
        if not instalacoes:
            QMessageBox.information(
                self, "Backup", "Nenhuma instalação cadastrada para exportar."
            )
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Backup",
            "checkcam_backup.json",
            "Backup JSON (*.json)",
        )
        if not caminho:
            return  # usuário cancelou

        try:
            conteudo = exportar(instalacoes)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            QMessageBox.information(
                self,
                "Backup concluído",
                f"{len(instalacoes)} instalação(ões) exportada(s) para:\n{caminho}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro no backup", str(exc))

    def _restaurar_backup(self) -> None:
        """Importa instalações de um arquivo JSON; pula nomes já existentes."""
        caminho, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Backup",
            "",
            "Backup JSON (*.json)",
        )
        if not caminho:
            return  # usuário cancelou

        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudo = f.read()

            instalacoes = importar(conteudo)
            inseridos, pulados = restaurar_no_repo(instalacoes, self._repo)

            self._selector.atualizar_lista()  # recarrega o widget

            partes = [f"{inseridos} instalação(ões) importada(s)."]
            if pulados:
                partes.append(f"{pulados} já existia(m) e foi(ram) mantida(s).")
            QMessageBox.information(self, "Restauração concluída", "\n".join(partes))

        except ValueError as exc:
            QMessageBox.critical(
                self, "Arquivo inválido", f"Não foi possível ler o backup:\n{exc}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro na restauração", str(exc))
