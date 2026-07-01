from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from src.domain.device import Marca, TipoDispositivo
from src.domain.status import CameraStatus


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
    status: str = CameraStatus.PENDENTE
    dvr_nome: str = ""    # nome do DVR ao qual pertence (para exibição na UI)


@dataclass
class DVR:
    """Representa um dispositivo do checklist: um DVR/NVR ou uma câmera IP.

    O nome ``DVR`` é mantido por compatibilidade, mas o ``tipo`` distingue um
    DVR/NVR (1 IP, N canais) de uma câmera IP direta (1 IP, canal único).

    Os campos de override (``porta_http``, ``porta_rtsp``, ``usuario``,
    ``senha``) ficam vazios por padrão e, nesse caso, herdam o valor da
    instalação (AppConfig). Permitem misturar marcas/portas/credenciais
    diferentes na mesma instalação.
    """

    nome: str
    ip: str
    qtd_cameras: int
    marca: str = Marca.HIKVISION
    tipo: str = TipoDispositivo.DVR
    porta_http: str = ""    # override; vazio = herda da instalação
    porta_rtsp: str = ""    # override; vazio = herda (ou default da marca)
    usuario: str = ""       # override; vazio = herda da instalação
    senha: str = ""         # override; vazio = herda da instalação
    chave_criptografia: str = ""   # opcional — se o capture com a senha
    # normal falhar, o camera_capture refaz a tentativa com a chave aqui
    # como senha (caso comum: 'verification code' do Hikvision ativado)
    hd: HDStatus = field(default_factory=HDStatus)
    cameras: List[Camera] = field(default_factory=list)


def todas_as_cameras(dvrs: Iterable[DVR]) -> List[Camera]:
    """Achata as câmeras de todos os DVRs em uma única lista (ordem preservada)."""
    return [cam for dvr in dvrs for cam in dvr.cameras]


def cameras_para_revisar(cameras: Iterable[Camera], error_img: str) -> List[Camera]:
    """Filtra as câmeras que têm imagem válida (descarta placeholders error_img).

    São as câmeras que entram na revisão visual / no book. Usado pelo revisor
    cv2, pelo diálogo Qt e pela MainWindow — antes a comprehension estava
    repetida nos três.
    """
    return [c for c in cameras if c.imagem != error_img]
