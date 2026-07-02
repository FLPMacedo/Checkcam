"""Unit tests for dashboard/views.py — classificação de saúde."""
from dashboard.views import _classificar_saude
from src.domain.snapshot import Snapshot


def _snap(**kwargs):
    return Snapshot(**kwargs)


def test_saude_verde_sem_problemas():
    snap = _snap(cameras_ok=8)
    assert _classificar_saude(snap) == "verde"


def test_saude_amarelo_so_com_alertas():
    snap = _snap(cameras_ok=6, cameras_alerta=2)
    assert _classificar_saude(snap) == "amarelo"


def test_saude_vermelho_com_hd_erro():
    snap = _snap(cameras_ok=6, dvrs_hd_erro=1)
    assert _classificar_saude(snap) == "vermelho"


def test_saude_vermelho_com_dvr_offline():
    snap = _snap(cameras_ok=6, dvrs_offline=1)
    assert _classificar_saude(snap) == "vermelho"


def test_saude_vermelho_com_camera_sem_conexao():
    snap = _snap(cameras_ok=6, cameras_sem_conexao=1)
    assert _classificar_saude(snap) == "vermelho"


def test_hd_erro_tem_prioridade_sobre_alerta():
    """hd_erro + alerta → vermelho (o pior estado vence)."""
    snap = _snap(cameras_alerta=3, dvrs_hd_erro=1)
    assert _classificar_saude(snap) == "vermelho"
