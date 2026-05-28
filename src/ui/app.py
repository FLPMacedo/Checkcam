from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.infra.instalacao_repo import InstalacaoRepository
from src.ui.home_window import HomeWindow


def run(db_path: str = "checkcam.db") -> int:
    """
    Ponto de entrada da aplicação.

    Inicializa a QApplication, abre (ou cria) o banco SQLite em db_path
    e exibe a janela inicial de gerenciamento de instalações.
    Retorna o código de saída do event loop Qt.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    repo = InstalacaoRepository(db_path)
    window = HomeWindow(repo)
    window.show()
    return app.exec()
