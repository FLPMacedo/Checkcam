from __future__ import annotations

from typing import List

from src.domain.instalacao import Instalacao
from src.domain.models import DVR
from src.infra.database import criar_banco, get_connection


class InstalacaoRepository:
    """
    Persiste e recupera Instalacao no banco SQLite.

    Regras:
      - salvar(inst) com inst.id == 0  → INSERT, retorna inst com id preenchido
      - salvar(inst) com inst.id  > 0  → UPDATE completo (campos + dvrs + emails)
      - listar()                       → lista leve (id + nome) para exibição
      - obter(id)                      → objeto completo com dvrs e emails
      - remover(id)                    → exclui em cascata dvrs e emails
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        criar_banco(db_path)

    # ── Leitura ───────────────────────────────────────────────────────────────

    def listar(self) -> List[Instalacao]:
        """Retorna todas as instalações ordenadas por nome (sem dvrs/emails)."""
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT id, nome FROM instalacoes ORDER BY nome"
            ).fetchall()
        return [Instalacao(id=r["id"], nome=r["nome"]) for r in rows]

    def obter(self, id: int) -> Instalacao:
        """Retorna instalação completa com dvrs e emails. Lança KeyError se não existir."""
        with get_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM instalacoes WHERE id = ?", (id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Instalação id={id} não encontrada")

            dvr_rows = conn.execute(
                "SELECT nome, ip, qtd_cameras FROM dvrs WHERE instalacao_id = ? ORDER BY id",
                (id,),
            ).fetchall()

            email_rows = conn.execute(
                "SELECT email FROM emails WHERE instalacao_id = ? ORDER BY id",
                (id,),
            ).fetchall()

        return Instalacao(
            id=row["id"],
            nome=row["nome"],
            usuario=row["usuario"],
            senha=row["senha"],
            porta_http=row["porta_http"],
            porta_rtsp=row["porta_rtsp"],
            ffmpeg_path=row["ffmpeg_path"],
            playwright_path=row["playwright_path"],
            base_dir=row["base_dir"],
            relatorios_dir=row["relatorios_dir"],
            logs_dir=row["logs_dir"],
            error_img=row["error_img"],
            dvrs=[
                DVR(nome=r["nome"], ip=r["ip"], qtd_cameras=r["qtd_cameras"])
                for r in dvr_rows
            ],
            emails=[r["email"] for r in email_rows],
        )

    # ── Escrita ───────────────────────────────────────────────────────────────

    def salvar(self, inst: Instalacao) -> Instalacao:
        """Insert ou update. Substitui completamente dvrs e emails. Retorna inst."""
        with get_connection(self._db_path) as conn:
            if inst.id == 0:
                cursor = conn.execute(
                    """INSERT INTO instalacoes
                       (nome, usuario, senha, porta_http, porta_rtsp,
                        ffmpeg_path, playwright_path, base_dir,
                        relatorios_dir, logs_dir, error_img)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        inst.nome, inst.usuario, inst.senha,
                        inst.porta_http, inst.porta_rtsp,
                        inst.ffmpeg_path, inst.playwright_path,
                        inst.base_dir, inst.relatorios_dir,
                        inst.logs_dir, inst.error_img,
                    ),
                )
                inst.id = cursor.lastrowid
            else:
                conn.execute(
                    """UPDATE instalacoes SET
                       nome=?, usuario=?, senha=?, porta_http=?, porta_rtsp=?,
                       ffmpeg_path=?, playwright_path=?, base_dir=?,
                       relatorios_dir=?, logs_dir=?, error_img=?
                       WHERE id=?""",
                    (
                        inst.nome, inst.usuario, inst.senha,
                        inst.porta_http, inst.porta_rtsp,
                        inst.ffmpeg_path, inst.playwright_path,
                        inst.base_dir, inst.relatorios_dir,
                        inst.logs_dir, inst.error_img,
                        inst.id,
                    ),
                )

            # ── DVRs: substitui completamente ──
            conn.execute("DELETE FROM dvrs WHERE instalacao_id = ?", (inst.id,))
            for dvr in inst.dvrs:
                conn.execute(
                    "INSERT INTO dvrs (instalacao_id, nome, ip, qtd_cameras) VALUES (?, ?, ?, ?)",
                    (inst.id, dvr.nome, dvr.ip, dvr.qtd_cameras),
                )

            # ── Emails: substitui completamente ──
            conn.execute("DELETE FROM emails WHERE instalacao_id = ?", (inst.id,))
            for email in inst.emails:
                conn.execute(
                    "INSERT INTO emails (instalacao_id, email) VALUES (?, ?)",
                    (inst.id, email),
                )

        return inst

    def remover(self, id: int) -> None:
        """Remove a instalação; dvrs e emails são excluídos em cascata."""
        with get_connection(self._db_path) as conn:
            conn.execute("DELETE FROM instalacoes WHERE id = ?", (id,))
