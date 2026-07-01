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


def test_dvrs_tem_colunas_de_marca_e_tipo(tmp_path):
    db_path = str(tmp_path / "test.db")
    criar_banco(db_path)
    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(dvrs)")}
    assert {"marca", "tipo", "porta_http", "porta_rtsp", "usuario", "senha"}.issubset(cols)


def test_migracao_adiciona_colunas_em_banco_antigo(tmp_path):
    """Banco no schema v1 (sem marca/tipo) é migrado preservando os dados."""
    db_path = str(tmp_path / "antigo.db")
    # Cria um banco "antigo" só com o schema original da tabela dvrs
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE instalacoes (id INTEGER PRIMARY KEY, nome TEXT);
            CREATE TABLE dvrs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instalacao_id INTEGER,
                nome TEXT, ip TEXT, qtd_cameras INTEGER
            );
            CREATE TABLE emails (id INTEGER PRIMARY KEY, instalacao_id INTEGER, email TEXT);
            INSERT INTO instalacoes (id, nome) VALUES (1, 'Velha');
            INSERT INTO dvrs (instalacao_id, nome, ip, qtd_cameras)
                VALUES (1, 'DVR_ANTIGO', '1.2.3.4', 8);
            """
        )

    criar_banco(db_path)  # deve migrar

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(dvrs)")}
        assert "marca" in cols and "tipo" in cols
        # dado antigo preservado + defaults aplicados
        row = conn.execute(
            "SELECT nome, qtd_cameras, marca, tipo FROM dvrs WHERE nome='DVR_ANTIGO'"
        ).fetchone()
    assert row == ("DVR_ANTIGO", 8, "hikvision", "dvr")
