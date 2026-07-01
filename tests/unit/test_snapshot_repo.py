"""Unit tests for src/infra/snapshot_repo.py"""
import pytest

from src.domain.events import ChecklistResult
from src.domain.instalacao import Instalacao
from src.domain.models import DVR, Camera, HDStatus
from src.domain.status import CameraStatus
from src.infra.instalacao_repo import InstalacaoRepository
from src.infra.snapshot_repo import SnapshotRepository


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def inst_repo(db_path):
    return InstalacaoRepository(db_path)


@pytest.fixture
def repo(db_path):
    return SnapshotRepository(db_path)


@pytest.fixture
def instalacao_id(inst_repo):
    """Cria uma instalação e devolve seu id (necessário pela FK dos snapshots)."""
    saved = inst_repo.salvar(Instalacao(nome="Cliente Teste"))
    return saved.id


def _dvr(nome="DVR1", ip="10.0.0.1", hd_status="ONLINE - NORMAL",
         hd_total="3000.00 GB", hd_livre="1500.00 GB", statuses=()):
    """Monta um DVR com HD e câmeras nos status informados."""
    dvr = DVR(nome=nome, ip=ip, qtd_cameras=len(statuses))
    dvr.hd = HDStatus(total=hd_total, livre=hd_livre, status=hd_status)
    dvr.cameras = [
        Camera(nome=f"C{i+1}", status=s) for i, s in enumerate(statuses)
    ]
    return dvr


def _resultado(dvrs):
    return ChecklistResult(
        dvrs=dvrs,
        excel_path="C:/rel/checklist.xlsx",
        pdf_path="C:/rel/checklist.pdf",
        book_path="C:/rel/book.pdf",
    )


def test_criar_tabelas_via_migracao(db_path):
    """Instanciar o repo cria as tabelas de snapshot sem erro."""
    import sqlite3

    SnapshotRepository(db_path)  # dispara criar_banco

    with sqlite3.connect(db_path) as conn:
        tabelas = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "snapshots" in tabelas
    assert "snapshot_dvrs" in tabelas


def test_gravar_snapshot_retorna_id(repo, instalacao_id):
    dvrs = [_dvr(statuses=[CameraStatus.OK, CameraStatus.OK])]
    snap_id = repo.gravar(instalacao_id, _resultado(dvrs))
    assert snap_id > 0


def test_ler_snapshot_por_id(repo, instalacao_id):
    """Round-trip completo: totais agregados + detalhe por DVR."""
    dvrs = [
        _dvr(
            nome="DVR_LOJA",
            ip="10.0.0.5",
            hd_status="ONLINE - ERRO (HD)",
            statuses=[
                CameraStatus.OK,
                CameraStatus.DISTORCIDA,       # alerta
                CameraStatus.SEM_CONEXAO,      # sem conexão
                CameraStatus.NAO_INSTALADA,    # não instalada
            ],
        ),
        _dvr(
            nome="DVR_OFF",
            ip="10.0.0.6",
            hd_status="OFFLINE - SEM PING",
            hd_total="-",
            hd_livre="-",
            statuses=[CameraStatus.OK, CameraStatus.OK],
        ),
    ]
    snap_id = repo.gravar(instalacao_id, _resultado(dvrs))

    snap = repo.obter(snap_id)

    assert snap.id == snap_id
    assert snap.instalacao_id == instalacao_id
    assert snap.executado_em  # ISO 8601 não vazio
    assert snap.total_dvrs == 2
    assert snap.total_cameras == 6
    assert snap.cameras_ok == 3
    assert snap.cameras_alerta == 1
    assert snap.cameras_sem_conexao == 1
    assert snap.cameras_nao_instaladas == 1
    assert snap.dvrs_hd_erro == 1       # ONLINE - ERRO (HD)
    assert snap.dvrs_offline == 1       # OFFLINE - SEM PING
    assert snap.excel_path == "C:/rel/checklist.xlsx"
    assert snap.pdf_path == "C:/rel/checklist.pdf"
    assert snap.book_path == "C:/rel/book.pdf"

    assert len(snap.dvrs) == 2
    loja = next(d for d in snap.dvrs if d.dvr_nome == "DVR_LOJA")
    assert loja.dvr_ip == "10.0.0.5"
    assert loja.hd_status == "ONLINE - ERRO (HD)"
    assert loja.cameras_ok == 1
    assert loja.cameras_alerta == 1
    assert loja.cameras_offline == 1
    assert loja.cameras_nao_instaladas == 1


def test_ultimo_snapshot_por_instalacao(repo, instalacao_id):
    """ultimo_por_instalacao devolve o snapshot mais recente."""
    repo.gravar(instalacao_id, _resultado([_dvr(statuses=[CameraStatus.OK])]))
    ultimo_id = repo.gravar(
        instalacao_id,
        _resultado([_dvr(statuses=[CameraStatus.OK, CameraStatus.OK])]),
    )

    snap = repo.ultimo_por_instalacao(instalacao_id)

    assert snap is not None
    assert snap.id == ultimo_id
    assert snap.total_cameras == 2


def test_ultimo_sem_snapshot_retorna_none(repo, instalacao_id):
    assert repo.ultimo_por_instalacao(instalacao_id) is None


def test_historico_de_snapshots_por_instalacao(repo, instalacao_id):
    """historico devolve lista ordenada da mais recente para a mais antiga."""
    ids = [
        repo.gravar(instalacao_id, _resultado([_dvr(statuses=[CameraStatus.OK])]))
        for _ in range(3)
    ]

    hist = repo.historico(instalacao_id)

    assert [s.id for s in hist] == list(reversed(ids))


def test_historico_respeita_limite(repo, instalacao_id):
    for _ in range(5):
        repo.gravar(instalacao_id, _resultado([_dvr(statuses=[CameraStatus.OK])]))

    hist = repo.historico(instalacao_id, limite=2)

    assert len(hist) == 2


def test_todos_ultimos_pareia_instalacao_com_ultimo_snapshot(
    repo, inst_repo, instalacao_id
):
    """todos_ultimos lista cada instalação com seu último snapshot (ou None)."""
    outra = inst_repo.salvar(Instalacao(nome="Sem Snapshot")).id
    ultimo_id = repo.gravar(
        instalacao_id, _resultado([_dvr(statuses=[CameraStatus.OK])])
    )

    pares = dict((inst.id, snap) for inst, snap in repo.todos_ultimos())

    assert pares[instalacao_id] is not None
    assert pares[instalacao_id].id == ultimo_id
    assert pares[outra] is None


def test_deletar_instalacao_cascateia_snapshots(repo, inst_repo, instalacao_id):
    """Remover a instalação apaga seus snapshots (FK ON DELETE CASCADE)."""
    snap_id = repo.gravar(
        instalacao_id, _resultado([_dvr(statuses=[CameraStatus.OK])])
    )
    assert repo.obter(snap_id) is not None

    inst_repo.remover(instalacao_id)

    assert repo.ultimo_por_instalacao(instalacao_id) is None
    with pytest.raises(KeyError):
        repo.obter(snap_id)
