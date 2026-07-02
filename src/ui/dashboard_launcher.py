"""Abre o dashboard como processo separado (janela nativa via pywebview).

Isolado num módulo próprio para ser reutilizado pela HomeWindow e pela
MainWindow e testável sem tocar na UI.
"""
from __future__ import annotations

import os
import subprocess
import sys


def spawn_dashboard(db_path: str = "") -> subprocess.Popen:
    """Sobe ``python -m dashboard.desktop`` em um processo à parte.

    Se ``db_path`` for informado, passa-o via CHECKCAM_DB para o dashboard
    abrir o mesmo banco do CheckCam; caso contrário, o subprocesso herda o
    ambiente do processo pai (e o dashboard cai no default ``checkcam.db``).
    """
    env = None
    if db_path:
        env = {**os.environ, "CHECKCAM_DB": db_path}
    return subprocess.Popen(
        [sys.executable, "-m", "dashboard.desktop"], env=env
    )
