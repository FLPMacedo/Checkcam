"""Rotas do dashboard, registradas sobre um app Flask já criado."""
from __future__ import annotations

from flask import Flask, abort, jsonify, redirect, render_template, url_for

from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository

from dashboard.views import historico_json, instalacao_context, overview_context


def register_routes(
    app: Flask,
    inst_repo: InstalacaoRepository,
    snap_repo: SnapshotRepository,
) -> None:
    """Registra as rotas usando os repositórios via closure."""

    @app.route("/")
    def index():
        return redirect(url_for("overview"))

    @app.route("/overview")
    def overview():
        return render_template("overview.html", **overview_context(snap_repo))

    @app.route("/instalacao/<int:instalacao_id>")
    def instalacao(instalacao_id: int):
        try:
            ctx = instalacao_context(inst_repo, snap_repo, instalacao_id)
        except KeyError:
            abort(404)
        return render_template("instalacao.html", **ctx)

    @app.route("/api/historico/<int:instalacao_id>")
    def historico(instalacao_id: int):
        return jsonify(historico_json(snap_repo, instalacao_id))
