"""
Convenção de caminhos padrão para uma instalação CheckCam.

Quando o usuário cria uma instalação pela UI e deixa os campos de caminho
em branco, o form chama esta função para deduzir defaults sensatos a partir
do nome da instalação. Replica a mesma convenção do scripts/seed_db.py:

    base_dir       = <CheckCam>/data/<slug>/temp
    relatorios_dir = <CheckCam>/relatorios/<slug>
    logs_dir       = <CheckCam>/data/<slug>/logs
    ffmpeg_path    = <CheckCam>/assets/ffmpeg/bin/ffmpeg.exe
    playwright_path= <CheckCam>/assets/playwright_browsers
    error_img      = <CheckCam>/assets/error.jpg
"""
from __future__ import annotations

import os
from typing import Dict


def _checkcam_root() -> str:
    """Caminho absoluto para a raiz do CheckCam (onde fica main.py)."""
    # Este módulo está em src/infra/path_defaults.py → sobe 2 níveis
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )


def caminhos_padrao_para(nome_instalacao: str) -> Dict[str, str]:
    """Devolve dict com os 6 caminhos padrão para uma instalação.

    O nome é sanitizado em slug seguro (sem espaços ou chars inválidos
    do NTFS) para virar nome de pasta.
    """
    # Importação tardia para evitar ciclo com excel_builder em alguns testes
    from src.reports.excel_builder import _slug_instalacao

    root = _checkcam_root()
    slug = _slug_instalacao(nome_instalacao) or "DVRs"

    return {
        "base_dir":        os.path.join(root, "data", slug, "temp"),
        "relatorios_dir":  os.path.join(root, "relatorios", slug),
        "logs_dir":        os.path.join(root, "data", slug, "logs"),
        "ffmpeg_path":     os.path.join(root, "assets", "ffmpeg", "bin", "ffmpeg.exe"),
        "playwright_path": os.path.join(root, "assets", "playwright_browsers"),
        "error_img":       os.path.join(root, "assets", "error.jpg"),
    }
