"""
Unit tests for src/infra/config_loader.py

These tests mirror the behavior already documented in
tests/characterization/test_config_loading.py (which covers the legacy
carregar_dvrs/carregar_emails). The key differences from the legacy:
- load_dvrs() returns List[DVR] instead of List[dict]
- load_emails() is identical in behavior
- Neither function has any side-effects on import
"""
import pytest
from src.domain.models import DVR
from src.infra.config_loader import load_dvrs, load_emails


# ─── load_dvrs ───────────────────────────────────────────────────────────────

def test_load_dvrs_retorna_lista_de_objetos_dvr(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_A;192.168.1.1;4\n", encoding="utf-8")
    result = load_dvrs(str(f))
    assert len(result) == 1
    assert isinstance(result[0], DVR)


def test_load_dvrs_campos_corretos(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_A;192.168.1.1;4\n", encoding="utf-8")
    dvr = load_dvrs(str(f))[0]
    assert dvr.nome == "DVR_A"
    assert dvr.ip == "192.168.1.1"
    assert dvr.qtd_cameras == 4


def test_load_dvrs_qtd_cameras_e_int(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_B;10.0.0.1;8\n", encoding="utf-8")
    dvr = load_dvrs(str(f))[0]
    assert isinstance(dvr.qtd_cameras, int)


def test_load_dvrs_ignora_comentarios_e_linhas_vazias(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("# comentario\n\nDVR_C;10.0.0.2;2\n\n# outro\n", encoding="utf-8")
    result = load_dvrs(str(f))
    assert len(result) == 1
    assert result[0].nome == "DVR_C"


def test_load_dvrs_multiplos(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("A;1.1.1.1;4\nB;2.2.2.2;8\nC;3.3.3.3;16\n", encoding="utf-8")
    result = load_dvrs(str(f))
    assert len(result) == 3
    assert [d.nome for d in result] == ["A", "B", "C"]


def test_load_dvrs_dvr_inicia_sem_hd_e_sem_cameras(tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_X;10.0.0.9;2\n", encoding="utf-8")
    dvr = load_dvrs(str(f))[0]
    assert dvr.cameras == []
    assert dvr.hd.status == "DESCONHECIDO"


# ─── load_emails ─────────────────────────────────────────────────────────────

def test_load_emails_retorna_lista_de_strings(tmp_path):
    f = tmp_path / "emails.txt"
    f.write_text("a@teste.com\nb@teste.com\n", encoding="utf-8")
    result = load_emails(str(f))
    assert result == ["a@teste.com", "b@teste.com"]


def test_load_emails_ignora_comentarios_e_linhas_vazias(tmp_path):
    f = tmp_path / "emails.txt"
    f.write_text("# lista\n\nc@teste.com\n\n# fim\n", encoding="utf-8")
    result = load_emails(str(f))
    assert result == ["c@teste.com"]
