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


def test_round_trip_de_marca_tipo_e_overrides(repo):
    """Os campos novos do dispositivo persistem e voltam corretos."""
    from src.domain.device import Marca, TipoDispositivo

    inst = _inst(
        nome="Valenca",
        dvrs=[
            DVR(nome="NVR", ip="10.9.130.10", qtd_cameras=16,
                marca=Marca.INTELBRAS, tipo=TipoDispositivo.DVR, porta_http="3077"),
            DVR(nome="CAM 1", ip="10.9.130.31", qtd_cameras=1,
                marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP,
                porta_http="8000", porta_rtsp="554",
                usuario="cam_user", senha="cam_pass"),
        ],
    )
    saved = repo.salvar(inst)
    loaded = repo.obter(saved.id)

    nvr, cam = loaded.dvrs
    assert nvr.marca == "intelbras" and nvr.tipo == "dvr" and nvr.porta_http == "3077"
    assert cam.tipo == "camera_ip"
    assert cam.porta_http == "8000" and cam.porta_rtsp == "554"
    assert cam.usuario == "cam_user" and cam.senha == "cam_pass"


def test_dvr_legado_usa_defaults_hikvision(repo):
    """DVR salvo sem marca/tipo explícitos volta como hikvision/dvr."""
    inst = _inst(nome="Legado", dvrs=[DVR(nome="D", ip="1.1.1.1", qtd_cameras=4)])
    saved = repo.salvar(inst)
    loaded = repo.obter(saved.id)

    assert loaded.dvrs[0].marca == "hikvision"
    assert loaded.dvrs[0].tipo == "dvr"
    assert loaded.dvrs[0].porta_rtsp == ""  # override vazio = herda


def test_remover_exclui_instalacao_e_cascateia_dvrs(repo):
    inst = _inst(
        nome="Removida",
        dvrs=[DVR(nome="D1", ip="1.1.1.1", qtd_cameras=1)],
        emails=["x@y.com"],
    )
    saved = repo.salvar(inst)

    repo.remover(saved.id)

    assert repo.listar() == []


def test_chave_de_criptografia_persiste_no_banco(repo):
    """Round-trip da chave: salvar + recuperar preserva o valor."""
    inst = _inst(
        nome="ComChave",
        dvrs=[
            DVR(nome="HIK1", ip="1.1.1.1", qtd_cameras=4,
                chave_criptografia="MINHA_CHAVE_HIKVISION_123"),
        ],
    )
    saved = repo.salvar(inst)
    loaded = repo.obter(saved.id)

    assert loaded.dvrs[0].chave_criptografia == "MINHA_CHAVE_HIKVISION_123"


def test_dvr_sem_chave_volta_string_vazia(repo):
    """DVR sem chave configurada continua com string vazia (não None)."""
    inst = _inst(
        nome="SemChave",
        dvrs=[DVR(nome="D", ip="1.1.1.1", qtd_cameras=4)],
    )
    saved = repo.salvar(inst)
    loaded = repo.obter(saved.id)

    assert loaded.dvrs[0].chave_criptografia == ""
