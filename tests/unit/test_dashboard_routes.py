"""Unit tests for dashboard/routes.py — via Flask test client."""
import pytest

from dashboard.app import create_app
from src.domain.events import ChecklistResult
from src.domain.instalacao import Instalacao
from src.domain.models import DVR, Camera, HDStatus
from src.domain.status import CameraStatus
from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository


def _dvr_com_cameras(nome, ip, hd_status, statuses):
    dvr = DVR(nome=nome, ip=ip, qtd_cameras=len(statuses))
    dvr.hd = HDStatus(total="3000 GB", livre="1500 GB", status=hd_status)
    dvr.cameras = [Camera(nome=f"C{i+1}", status=s) for i, s in enumerate(statuses)]
    return dvr


@pytest.fixture
def seeded(tmp_path):
    """Banco com duas instalações; só a primeira tem snapshot."""
    db = str(tmp_path / "dash.db")
    inst_repo = InstalacaoRepository(db)
    snap_repo = SnapshotRepository(db)

    loja_a = inst_repo.salvar(
        Instalacao(nome="Loja A", dvrs=[DVR(nome="DVR1", ip="10.0.0.1", qtd_cameras=2)])
    )
    loja_b = inst_repo.salvar(Instalacao(nome="Loja B"))

    snap_repo.gravar(
        loja_a.id,
        ChecklistResult(
            dvrs=[
                _dvr_com_cameras(
                    "DVR_FRENTE", "10.0.0.1", "ONLINE - ERRO (HD)",
                    [CameraStatus.OK, CameraStatus.DISTORCIDA],
                ),
            ],
            excel_path="C:/rel/a.xlsx",
            pdf_path="C:/rel/a.pdf",
            book_path="C:/rel/a_book.pdf",
        ),
    )
    return db, loja_a.id, loja_b.id


@pytest.fixture
def client(seeded):
    db, _, _ = seeded
    app = create_app(db)
    app.config.update(TESTING=True)
    return app.test_client()


def test_index_redireciona_para_overview(client):
    resp = client.get("/")
    assert resp.status_code in (301, 302)
    assert "/overview" in resp.headers["Location"]


def test_overview_200(client):
    assert client.get("/overview").status_code == 200


def test_overview_lista_todas_instalacoes(client):
    html = client.get("/overview").get_data(as_text=True)
    assert "Loja A" in html
    assert "Loja B" in html


def test_instalacao_200(client, seeded):
    _, loja_a, _ = seeded
    assert client.get(f"/instalacao/{loja_a}").status_code == 200


def test_instalacao_mostra_dvr_do_snapshot(client, seeded):
    _, loja_a, _ = seeded
    html = client.get(f"/instalacao/{loja_a}").get_data(as_text=True)
    assert "DVR_FRENTE" in html


def test_instalacao_sem_snapshot_200(client, seeded):
    """Instalação sem checklist executado ainda renderiza (sem quebrar)."""
    _, _, loja_b = seeded
    assert client.get(f"/instalacao/{loja_b}").status_code == 200


def test_instalacao_inexistente_404(client):
    assert client.get("/instalacao/99999").status_code == 404


def test_historico_json(client, seeded):
    _, loja_a, _ = seeded
    resp = client.get(f"/api/historico/{loja_a}")
    assert resp.status_code == 200
    assert resp.is_json
    dados = resp.get_json()
    assert isinstance(dados, list)
    assert len(dados) == 1
    assert dados[0]["total_cameras"] == 2
    assert "executado_em" in dados[0]
