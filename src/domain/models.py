from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class HDStatus:
    """Estado do HD de armazenamento de um DVR."""

    total: str = "-"
    livre: str = "-"
    status: str = "DESCONHECIDO"


@dataclass
class Camera:
    """Representa uma câmera individual dentro de um DVR."""

    nome: str
    imagem: str = ""
    status: str = "PENDENTE"
    dvr_nome: str = ""    # nome do DVR ao qual pertence (para exibição na UI)


@dataclass
class DVR:
    """Representa um DVR com todas as informações coletadas durante o checklist."""

    nome: str
    ip: str
    qtd_cameras: int
    hd: HDStatus = field(default_factory=HDStatus)
    cameras: List[Camera] = field(default_factory=list)
