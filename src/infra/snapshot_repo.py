from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from src.domain.events import ChecklistResult
from src.domain.instalacao import Instalacao
from src.domain.snapshot import Snapshot, SnapshotDVR, snapshot_de_resultado
from src.infra.database import criar_banco, get_connection


class SnapshotRepository:
    """
    Persiste e recupera ``Snapshot`` no banco SQLite.

    Cada checklist executado vira uma linha em ``snapshots`` (totais agregados)
    mais N linhas em ``snapshot_dvrs`` (detalhe por DVR). A leitura reconstrói o
    ``Snapshot`` completo. Usado pelo dashboard para overview, drill-down e
    trend histórico.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        criar_banco(db_path)

    # ── Escrita ───────────────────────────────────────────────────────────────

    def gravar(self, instalacao_id: int, resultado: ChecklistResult) -> int:
        """Agrega o ChecklistResult num Snapshot e persiste. Retorna o id gerado."""
        snap = snapshot_de_resultado(instalacao_id, resultado)
        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO snapshots
                   (instalacao_id, executado_em, total_dvrs, total_cameras,
                    cameras_ok, cameras_alerta, cameras_sem_conexao,
                    cameras_nao_instaladas, dvrs_hd_erro, dvrs_offline,
                    excel_path, pdf_path, book_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snap.instalacao_id, snap.executado_em,
                    snap.total_dvrs, snap.total_cameras,
                    snap.cameras_ok, snap.cameras_alerta,
                    snap.cameras_sem_conexao, snap.cameras_nao_instaladas,
                    snap.dvrs_hd_erro, snap.dvrs_offline,
                    snap.excel_path, snap.pdf_path, snap.book_path,
                ),
            )
            snap_id = cursor.lastrowid

            for d in snap.dvrs:
                conn.execute(
                    """INSERT INTO snapshot_dvrs
                       (snapshot_id, dvr_nome, dvr_ip, hd_status, hd_total,
                        hd_livre, cameras_ok, cameras_alerta, cameras_offline,
                        cameras_nao_instaladas)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        snap_id, d.dvr_nome, d.dvr_ip, d.hd_status,
                        d.hd_total, d.hd_livre, d.cameras_ok, d.cameras_alerta,
                        d.cameras_offline, d.cameras_nao_instaladas,
                    ),
                )

        return snap_id

    # ── Leitura ───────────────────────────────────────────────────────────────

    def obter(self, snapshot_id: int) -> Snapshot:
        """Retorna o Snapshot completo (com detalhe por DVR). KeyError se não existir."""
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Snapshot id={snapshot_id} não encontrado")
            dvr_rows = conn.execute(
                "SELECT * FROM snapshot_dvrs WHERE snapshot_id = ? ORDER BY id",
                (snapshot_id,),
            ).fetchall()
        return _snapshot_de_rows(row, dvr_rows)

    def ultimo_por_instalacao(self, instalacao_id: int) -> Optional[Snapshot]:
        """Snapshot mais recente da instalação, ou None se ela nunca rodou."""
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """SELECT * FROM snapshots WHERE instalacao_id = ?
                   ORDER BY executado_em DESC, id DESC LIMIT 1""",
                (instalacao_id,),
            ).fetchone()
            if row is None:
                return None
            dvr_rows = conn.execute(
                "SELECT * FROM snapshot_dvrs WHERE snapshot_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
        return _snapshot_de_rows(row, dvr_rows)

    def historico(self, instalacao_id: int, limite: int = 20) -> List[Snapshot]:
        """Últimos snapshots da instalação, do mais recente para o mais antigo.

        Não carrega o detalhe por DVR (só os totais) — o histórico alimenta o
        gráfico de trend, que usa apenas os agregados.
        """
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """SELECT * FROM snapshots WHERE instalacao_id = ?
                   ORDER BY executado_em DESC, id DESC LIMIT ?""",
                (instalacao_id, limite),
            ).fetchall()
        return [_snapshot_de_rows(r, []) for r in rows]

    def todos_ultimos(self) -> List[Tuple[Instalacao, Optional[Snapshot]]]:
        """Cada instalação (id + nome) pareada com seu último snapshot (ou None).

        Base do overview: um card por instalação, mesmo as que nunca rodaram.
        """
        with get_connection(self._db_path) as conn:
            inst_rows = conn.execute(
                "SELECT id, nome FROM instalacoes ORDER BY nome"
            ).fetchall()
            pares: List[Tuple[Instalacao, Optional[Snapshot]]] = []
            for inst_row in inst_rows:
                snap_row = conn.execute(
                    """SELECT * FROM snapshots WHERE instalacao_id = ?
                       ORDER BY executado_em DESC, id DESC LIMIT 1""",
                    (inst_row["id"],),
                ).fetchone()
                inst = Instalacao(id=inst_row["id"], nome=inst_row["nome"])
                snap = _snapshot_de_rows(snap_row, []) if snap_row else None
                pares.append((inst, snap))
        return pares


# ── Reconstrução a partir das linhas do banco ────────────────────────────────

def _snapshot_de_rows(
    row: sqlite3.Row, dvr_rows: List[sqlite3.Row]
) -> Snapshot:
    return Snapshot(
        id=row["id"],
        instalacao_id=row["instalacao_id"],
        executado_em=row["executado_em"],
        total_dvrs=row["total_dvrs"],
        total_cameras=row["total_cameras"],
        cameras_ok=row["cameras_ok"],
        cameras_alerta=row["cameras_alerta"],
        cameras_sem_conexao=row["cameras_sem_conexao"],
        cameras_nao_instaladas=row["cameras_nao_instaladas"],
        dvrs_hd_erro=row["dvrs_hd_erro"],
        dvrs_offline=row["dvrs_offline"],
        excel_path=row["excel_path"],
        pdf_path=row["pdf_path"],
        book_path=row["book_path"],
        dvrs=[
            SnapshotDVR(
                dvr_nome=d["dvr_nome"],
                dvr_ip=d["dvr_ip"],
                hd_status=d["hd_status"],
                hd_total=d["hd_total"],
                hd_livre=d["hd_livre"],
                cameras_ok=d["cameras_ok"],
                cameras_alerta=d["cameras_alerta"],
                cameras_offline=d["cameras_offline"],
                cameras_nao_instaladas=d["cameras_nao_instaladas"],
            )
            for d in dvr_rows
        ],
    )
