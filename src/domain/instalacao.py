from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.domain.models import DVR
from src.infra.app_config import AppConfig


@dataclass
class Instalacao:
    """
    Representa uma instalação monitorada (local/cliente).

    Armazena as configurações de credenciais, caminhos e lista de DVRs/emails.
    O campo ``id`` é 0 para registros não persistidos; após salvar no banco
    recebe o id gerado pelo SQLite.
    """

    nome: str = ""
    usuario: str = ""
    senha: str = ""
    porta_http: str = "3077"
    porta_rtsp: str = "3078"
    ffmpeg_path: str = ""
    playwright_path: str = ""
    base_dir: str = ""
    relatorios_dir: str = ""
    logs_dir: str = ""
    error_img: str = ""
    dvrs: List[DVR] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    id: int = 0

    def to_app_config(self) -> AppConfig:
        """Converte para AppConfig usado pelo pipeline de checklist."""
        return AppConfig(
            nome_instalacao=self.nome,
            usuario=self.usuario,
            senha=self.senha,
            porta_http=self.porta_http,
            porta_rtsp=self.porta_rtsp,
            ffmpeg_path=self.ffmpeg_path,
            playwright_path=self.playwright_path,
            base_dir=self.base_dir,
            relatorios_dir=self.relatorios_dir,
            logs_dir=self.logs_dir,
            error_img=self.error_img,
            emails=list(self.emails),
        )
