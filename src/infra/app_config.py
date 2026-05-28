from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from urllib.parse import quote


@dataclass
class AppConfig:
    """
    Configuração de runtime para o checklist.

    Concentra tudo que o legado espalhava em variáveis globais:
    credenciais, portas, paths de executáveis e diretórios.
    """

    usuario: str
    senha: str
    porta_http: str = "3077"
    porta_rtsp: str = "3078"
    ffmpeg_path: str = ""
    base_dir: str = ""
    error_img: str = ""
    playwright_path: str = ""
    emails: List[str] = field(default_factory=list)
    nome_instalacao: str = "DVRs"
    relatorios_dir: str = ""
    logs_dir: str = ""

    @property
    def senha_rtsp(self) -> str:
        """Senha com URL-encoding para uso em URIs RTSP."""
        return quote(self.senha)
