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
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id   INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    nome            TEXT    NOT NULL,
    ip              TEXT    NOT NULL,
    qtd_cameras     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id   INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    email           TEXT    NOT NULL
);
"""


def criar_banco(db_path: str) -> None:
    """Cria o banco e as três tabelas se ainda não existirem."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)


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
