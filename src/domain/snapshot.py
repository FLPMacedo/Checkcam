from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from src.domain.events import ChecklistResult
from src.domain.models import DVR
from src.domain.status import CameraStatus


@dataclass
class SnapshotDVR:
    """Estado agregado de um único DVR dentro de um snapshot de checklist."""

    dvr_nome: str = ""
    dvr_ip: str = ""
    hd_status: str = ""
    hd_total: str = ""
    hd_livre: str = ""
    cameras_ok: int = 0
    cameras_alerta: int = 0
    cameras_offline: int = 0
    cameras_nao_instaladas: int = 0


@dataclass
class Snapshot:
    """Fotografia do resultado de um checklist, persistida para o dashboard.

    Guarda os totais agregados da instalação (para os cards do overview e o
    trend histórico) e o detalhamento por DVR (para o drill-down). As categorias
    de câmera são mutuamente exclusivas — espelham a classificação do e-mail
    (``reports.email_sender``), mas sem a sobreposição alerta/sem_conexão de lá.
    """

    instalacao_id: int = 0
    executado_em: str = ""          # ISO 8601
    total_dvrs: int = 0
    total_cameras: int = 0
    cameras_ok: int = 0
    cameras_alerta: int = 0
    cameras_sem_conexao: int = 0
    cameras_nao_instaladas: int = 0
    dvrs_hd_erro: int = 0
    dvrs_offline: int = 0
    excel_path: str = ""
    pdf_path: str = ""
    book_path: str = ""
    dvrs: List[SnapshotDVR] = field(default_factory=list)
    id: int = 0


def _classificar_dvr(dvr: DVR) -> SnapshotDVR:
    """Agrega as câmeras de um DVR nas quatro categorias exclusivas."""
    detalhe = SnapshotDVR(
        dvr_nome=dvr.nome,
        dvr_ip=dvr.ip,
        hd_status=dvr.hd.status,
        hd_total=dvr.hd.total,
        hd_livre=dvr.hd.livre,
    )
    for cam in dvr.cameras:
        if cam.status == CameraStatus.OK:
            detalhe.cameras_ok += 1
        elif cam.status == CameraStatus.NAO_INSTALADA:
            detalhe.cameras_nao_instaladas += 1
        elif cam.status in (CameraStatus.SEM_CONEXAO, CameraStatus.NAO_ANALISADO):
            # Falha de conexão (DVR mudo ou stream inacessível) — separada dos
            # defeitos de imagem para o dashboard distinguir "amarelo" de "vermelho".
            detalhe.cameras_offline += 1
        else:
            # Demais estados (defeitos visuais, PENDENTE, ERRO_IMAGEM,
            # NAO_RECONHECIDA) contam como alerta.
            detalhe.cameras_alerta += 1
    return detalhe


def snapshot_de_resultado(
    instalacao_id: int,
    resultado: ChecklistResult,
    executado_em: Optional[str] = None,
) -> Snapshot:
    """Constrói um ``Snapshot`` a partir de um ``ChecklistResult`` (função pura).

    ``executado_em`` default = agora, em ISO 8601. Não toca em banco nem disco.
    """
    quando = executado_em or datetime.now().isoformat(timespec="seconds")
    detalhes = [_classificar_dvr(dvr) for dvr in resultado.dvrs]

    snap = Snapshot(
        instalacao_id=instalacao_id,
        executado_em=quando,
        total_dvrs=len(detalhes),
        excel_path=resultado.excel_path,
        pdf_path=resultado.pdf_path,
        book_path=resultado.book_path,
        dvrs=detalhes,
    )
    for d in detalhes:
        snap.cameras_ok += d.cameras_ok
        snap.cameras_alerta += d.cameras_alerta
        snap.cameras_sem_conexao += d.cameras_offline
        snap.cameras_nao_instaladas += d.cameras_nao_instaladas
        # HD: ONLINE mas != NORMAL é erro real; OFFLINE é problema de conexão.
        if d.hd_status.startswith("ONLINE") and d.hd_status != "ONLINE - NORMAL":
            snap.dvrs_hd_erro += 1
        elif d.hd_status.startswith("OFFLINE"):
            snap.dvrs_offline += 1

    snap.total_cameras = (
        snap.cameras_ok
        + snap.cameras_alerta
        + snap.cameras_sem_conexao
        + snap.cameras_nao_instaladas
    )
    return snap
