"""Unit tests for src/infra/database.py"""
import sqlite3

from src.infra.database import criar_banco, get_connection


def test_criar_banco_cria_arquivo(tmp_path):
    db_path = str(tmp_path / "test.db")
    criar_banco(db_path)
    assert (tmp_path / "test.db").exists()


def test_criar_banco_cria_tabelas_esperadas(tmp_path):
    db_path = str(tmp_path / "test.db")
    criar_banco(db_path)
    with sqlite3.connect(db_path) as conn:
        tabelas = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"instalacoes", "dvrs", "emails"}.issubset(tabelas)


def test_get_connection_habilita_foreign_keys(tmp_path):
    db_path = str(tmp_path / "test.db")
    criar_banco(db_path)
    with get_connection(db_path) as conn:
        resultado = conn.execute("PRAGMA foreign_keys").fetchone()
    assert resultado[0] == 1
