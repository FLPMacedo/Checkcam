"""Agregadores de dados: transformam Snapshot em contexto para os templates.

Não tocam em Flask nem em banco diretamente — recebem os repositórios já
construídos, para serem testáveis de forma isolada.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.snapshot import Snapshot
from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository

# Instalação que nunca rodou um checklist — sem dados para classificar.
SEM_DADOS = "sem_dados"


def _classificar_saude(snapshot: Snapshot) -> str:
    """Classifica a saúde de uma instalação a partir do seu último snapshot.

    - vermelho: HD com erro, DVR offline ou câmera sem conexão (imagem não
      está sendo gravada — problema crítico).
    - amarelo:  apenas alertas de imagem (embaçada, distorcida, etc.).
    - verde:    nenhum problema.
    """
    if snapshot.dvrs_hd_erro or snapshot.dvrs_offline or snapshot.cameras_sem_conexao:
        return "vermelho"
    if snapshot.cameras_alerta:
        return "amarelo"
    return "verde"


def _saude(snapshot: Optional[Snapshot]) -> str:
    return _classificar_saude(snapshot) if snapshot is not None else SEM_DADOS


def overview_context(snap_repo: SnapshotRepository) -> Dict:
    """Monta o contexto do overview: um item por instalação + totais globais."""
    instalacoes: List[Dict] = []
    total_dvrs = 0
    total_cameras = 0
    instalacoes_problema = 0

    for inst, snap in snap_repo.todos_ultimos():
        saude = _saude(snap)
        instalacoes.append({"instalacao": inst, "snapshot": snap, "saude": saude})
        if snap is not None:
            total_dvrs += snap.total_dvrs
            total_cameras += snap.total_cameras
            if saude != "verde":
                instalacoes_problema += 1

    return {
        "instalacoes": instalacoes,
        "totais": {
            "total_dvrs": total_dvrs,
            "total_cameras": total_cameras,
            "instalacoes_problema": instalacoes_problema,
        },
    }


def instalacao_context(
    inst_repo: InstalacaoRepository,
    snap_repo: SnapshotRepository,
    instalacao_id: int,
) -> Dict:
    """Contexto do drill-down. Lança KeyError se a instalação não existir."""
    inst = inst_repo.obter(instalacao_id)  # KeyError → rota devolve 404
    snap = snap_repo.ultimo_por_instalacao(instalacao_id)
    return {"instalacao": inst, "snapshot": snap, "saude": _saude(snap)}


def historico_json(
    snap_repo: SnapshotRepository, instalacao_id: int, limite: int = 20
) -> List[Dict]:
    """Série histórica (mais antigo → mais recente) para o gráfico de trend."""
    hist = snap_repo.historico(instalacao_id, limite=limite)
    return [
        {
            "executado_em": s.executado_em,
            "total_cameras": s.total_cameras,
            "cameras_ok": s.cameras_ok,
            "cameras_alerta": s.cameras_alerta,
            "cameras_sem_conexao": s.cameras_sem_conexao,
            "cameras_nao_instaladas": s.cameras_nao_instaladas,
            "dvrs_hd_erro": s.dvrs_hd_erro,
            "dvrs_offline": s.dvrs_offline,
        }
        for s in reversed(hist)
    ]
