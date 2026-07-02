from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS instalacoes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT    NOT NULL UNIQUE,
    usuario         TEXT    NOT NULL DEFAULT '',
    senha           TEXT    NOT NULL DEFAULT '',
    porta_http      TEXT    NOT NULL DEFAULT '3077',
    porta_rtsp      TEXT    NOT NULL DEFAULT '3078',
    ffmpeg_path     TEXT    NOT NULL DEFAULT '',
    playwright_path TEXT    NOT NULL DEFAULT '',
    base_dir        TEXT    NOT NULL DEFAULT '',
    relatorios_dir  TEXT    NOT NULL DEFAULT '',
    logs_dir        TEXT    NOT NULL DEFAULT '',
    error_img       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS dvrs (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id      INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    nome               TEXT    NOT NULL,
    ip                 TEXT    NOT NULL,
    qtd_cameras        INTEGER NOT NULL DEFAULT 1,
    marca              TEXT    NOT NULL DEFAULT 'hikvision',
    tipo               TEXT    NOT NULL DEFAULT 'dvr',
    porta_http         TEXT    NOT NULL DEFAULT '',
    porta_rtsp         TEXT    NOT NULL DEFAULT '',
    usuario            TEXT    NOT NULL DEFAULT '',
    senha              TEXT    NOT NULL DEFAULT '',
    chave_criptografia   TEXT    NOT NULL DEFAULT '',
    chave_criptografia_2 TEXT    NOT NULL DEFAULT '',
    chave_criptografia_3 TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id   INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    email           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id          INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    executado_em           TEXT    NOT NULL,
    total_dvrs             INTEGER NOT NULL DEFAULT 0,
    total_cameras          INTEGER NOT NULL DEFAULT 0,
    cameras_ok             INTEGER NOT NULL DEFAULT 0,
    cameras_alerta         INTEGER NOT NULL DEFAULT 0,
    cameras_sem_conexao    INTEGER NOT NULL DEFAULT 0,
    cameras_nao_instaladas INTEGER NOT NULL DEFAULT 0,
    dvrs_hd_erro           INTEGER NOT NULL DEFAULT 0,
    dvrs_offline           INTEGER NOT NULL DEFAULT 0,
    excel_path             TEXT    NOT NULL DEFAULT '',
    pdf_path               TEXT    NOT NULL DEFAULT '',
    book_path              TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS snapshot_dvrs (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id            INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    dvr_nome               TEXT    NOT NULL,
    dvr_ip                 TEXT    NOT NULL,
    hd_status              TEXT    NOT NULL,
    hd_total               TEXT    NOT NULL DEFAULT '',
    hd_livre               TEXT    NOT NULL DEFAULT '',
    cameras_ok             INTEGER NOT NULL DEFAULT 0,
    cameras_alerta         INTEGER NOT NULL DEFAULT 0,
    cameras_offline        INTEGER NOT NULL DEFAULT 0,
    cameras_nao_instaladas INTEGER NOT NULL DEFAULT 0
);
"""


# Colunas adicionadas à tabela dvrs depois da v1 (marca/tipo + overrides).
# Bancos antigos ganham essas colunas via ALTER TABLE, preservando os dados.
_COLUNAS_DVR_NOVAS = {
    "marca":              "TEXT NOT NULL DEFAULT 'hikvision'",
    "tipo":               "TEXT NOT NULL DEFAULT 'dvr'",
    "porta_http":         "TEXT NOT NULL DEFAULT ''",
    "porta_rtsp":         "TEXT NOT NULL DEFAULT ''",
    "usuario":            "TEXT NOT NULL DEFAULT ''",
    "senha":              "TEXT NOT NULL DEFAULT ''",
    "chave_criptografia":   "TEXT NOT NULL DEFAULT ''",
    "chave_criptografia_2": "TEXT NOT NULL DEFAULT ''",
    "chave_criptografia_3": "TEXT NOT NULL DEFAULT ''",
}


def _migrar_dvrs(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas à tabela dvrs em bancos pré-existentes.

    ALTER TABLE ADD COLUMN com DEFAULT é não-destrutivo: linhas antigas
    recebem o default (hikvision/dvr + overrides vazios), preservando o
    comportamento atual.
    """
    existentes = {row[1] for row in conn.execute("PRAGMA table_info(dvrs)").fetchall()}
    for coluna, ddl in _COLUNAS_DVR_NOVAS.items():
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE dvrs ADD COLUMN {coluna} {ddl}")


def criar_banco(db_path: str) -> None:
    """Cria o banco e as três tabelas se ainda não existirem; migra se preciso."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        _migrar_dvrs(conn)


@contextmanager
def get_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager que fornece uma conexão com:
      - foreign keys habilitadas
      - row_factory = sqlite3.Row (acesso por nome de coluna)
      - commit automático ao sair sem exceção; rollback em caso de erro
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
