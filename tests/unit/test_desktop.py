"""Unit tests for dashboard/desktop.py (helpers, sem abrir janela)."""
import socket

from dashboard import desktop


def test_free_port_retorna_int_disponivel():
    port = desktop._free_port()
    assert isinstance(port, int)
    assert 0 < port < 65536


def test_free_port_desvia_de_porta_ocupada():
    """Se a porta preferida está ocupada, devolve outra livre."""
    ocupada = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ocupada.bind(("127.0.0.1", 0))
    ocupada.listen(1)
    porta_ocupada = ocupada.getsockname()[1]
    try:
        escolhida = desktop._free_port(preferred=porta_ocupada)
        assert escolhida != porta_ocupada
    finally:
        ocupada.close()


def test_wait_up_falso_quando_nada_escuta():
    porta = desktop._free_port()
    assert desktop._wait_up(porta, timeout=0.4) is False


def test_wait_up_verdadeiro_quando_ha_servidor():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    porta = srv.getsockname()[1]
    try:
        assert desktop._wait_up(porta, timeout=2.0) is True
    finally:
        srv.close()


def test_db_path_usa_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("CHECKCAM_DB", "C:/algum/checkcam.db")
    assert desktop._db_path() == "C:/algum/checkcam.db"


def test_db_path_default_sem_variavel(monkeypatch):
    monkeypatch.delenv("CHECKCAM_DB", raising=False)
    assert desktop._db_path() == "checkcam.db"


def test_iniciar_servidor_sobe_flask_em_thread(monkeypatch, tmp_path):
    """iniciar_servidor escolhe porta livre, sobe o Flask e espera ficar up."""
    db = str(tmp_path / "checkcam.db")
    port = desktop.iniciar_servidor(db)
    try:
        # Servidor real respondendo na porta escolhida.
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
    finally:
        pass  # thread é daemon; morre com o processo de teste
