"""Flask app factory do dashboard CheckCam."""
from __future__ import annotations

from flask import Flask

from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository

from dashboard.routes import register_routes
from dashboard.ver import VERSION

DEFAULT_DB = "checkcam.db"


def create_app(db_path: str = DEFAULT_DB) -> Flask:
    """Cria e configura o app Flask do dashboard sobre o banco ``db_path``.

    Ambos os repositórios compartilham o mesmo arquivo SQLite do CheckCam,
    de onde o dashboard lê as instalações e os snapshots gravados pelo pipeline.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DB_PATH"] = db_path
    app.config["VERSION"] = VERSION

    inst_repo = InstalacaoRepository(db_path)
    snap_repo = SnapshotRepository(db_path)
    register_routes(app, inst_repo, snap_repo)

    # Disponibiliza a versão em todos os templates.
    @app.context_processor
    def _inject_version():
        return {"versao": VERSION}

    return app


# Instância padrão para `flask --app dashboard.app run`.
app = create_app()
