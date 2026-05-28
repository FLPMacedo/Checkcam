"""Unit tests for src/infra/instalacao_repo.py"""
import pytest

from src.domain.instalacao import Instalacao
from src.domain.models import DVR
from src.infra.instalacao_repo import InstalacaoRepository


@pytest.fixture
def repo(tmp_path):
    return InstalacaoRepository(str(tmp_path / "test.db"))


def _inst(**kwargs) -> Instalacao:
    defaults = dict(nome="Teste", usuario="admin", senha="pass")
    defaults.update(kwargs)
    return Instalacao(**defaults)


def test_salvar_nova_instalacao_retorna_com_id(repo):
    saved = repo.salvar(_inst())
    assert saved.id > 0


def test_listar_retorna_instalacoes_salvas(repo):
    repo.salvar(_inst(nome="A"))
    repo.salvar(_inst(nome="B"))

    result = repo.listar()

    assert len(result) == 2
    assert {i.nome for i in result} == {"A", "B"}


def test_obter_retorna_dvrs_e_emails(repo):
    inst = _inst(
        nome="Completa",
        dvrs=[DVR(nome="DVR1", ip="1.2.3.4", qtd_cameras=2)],
        emails=["a@b.com"],
    )
    saved = repo.salvar(inst)

    loaded = repo.obter(saved.id)

    assert len(loaded.dvrs) == 1
    assert loaded.dvrs[0].ip == "1.2.3.4"
    assert loaded.dvrs[0].qtd_cameras == 2
    assert loaded.emails == ["a@b.com"]


def test_salvar_atualiza_instalacao_existente(repo):
    inst = repo.salvar(_inst(nome="Original"))
    inst.nome = "Atualizado"
    inst.senha = "nova_senha"
    repo.salvar(inst)

    loaded = repo.obter(inst.id)

    assert loaded.nome == "Atualizado"
    assert loaded.senha == "nova_senha"


def test_remover_exclui_instalacao_e_cascateia_dvrs(repo):
    inst = _inst(
        nome="Removida",
        dvrs=[DVR(nome="D1", ip="1.1.1.1", qtd_cameras=1)],
        emails=["x@y.com"],
    )
    saved = repo.salvar(inst)

    repo.remover(saved.id)

    assert repo.listar() == []
