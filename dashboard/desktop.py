"""Abre o dashboard numa janela nativa (sem navegador), via pywebview.

Sobe o Flask numa thread daemon e embute a página numa janela WebView2.

Modos:
  python -m dashboard.desktop            -> abre a janela
  HEADLESS=1 python -m dashboard.desktop -> só o servidor (sem janela; testes/dev)

O banco vem de CHECKCAM_DB (env) ou de ``checkcam.db`` no diretório atual —
o mesmo arquivo que o CheckCam usa para gravar os snapshots.
"""
from __future__ import annotations

import os
import socket
import threading
import time

from dashboard.app import create_app


def _db_path() -> str:
    """Caminho do banco: CHECKCAM_DB ou ``checkcam.db`` no diretório atual."""
    return os.environ.get("CHECKCAM_DB", "checkcam.db")


def _free_port(preferred: int = 5000) -> int:
    """Retorna a porta preferida se estiver livre; senão, uma porta livre qualquer."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", preferred))
        return preferred
    except OSError:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _run_server(port: int, db_path: str) -> None:
    """Sobe o Flask (bloqueante) — usado como alvo da thread daemon."""
    app = create_app(db_path)
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)


def _wait_up(port: int, timeout: float = 15.0) -> bool:
    """Espera o servidor aceitar conexões na porta (até timeout)."""
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def iniciar_servidor(db_path: str, preferred_port: int = 5000) -> int:
    """Escolhe uma porta livre, sobe o Flask em thread daemon e espera ficar up.

    Retorna a porta em que o servidor está escutando.
    """
    port = _free_port(preferred_port)
    threading.Thread(
        target=_run_server, args=(port, db_path), daemon=True
    ).start()
    _wait_up(port)
    return port


def main() -> None:
    db_path = _db_path()
    port = iniciar_servidor(db_path)
    url = f"http://127.0.0.1:{port}/overview"

    if os.getenv("HEADLESS") == "1":
        print(f"HEADLESS: servindo em {url}")
        while True:
            time.sleep(3600)

    import webview  # importado só quando vai abrir a janela

    webview.create_window(
        "Dashboard CheckCam", url,
        width=1320, height=880, min_size=(1000, 640),
    )
    webview.start()


if __name__ == "__main__":
    main()
