"""
Unit tests for src/domain/models.py

Each test documents a contract that must hold throughout all future
refactoring phases.
"""
from src.domain.models import Camera, DVR, HDStatus


# ─── HDStatus ────────────────────────────────────────────────────────────────

def test_hdstatus_defaults():
    hd = HDStatus()
    assert hd.total == "-"
    assert hd.livre == "-"
    assert hd.status == "DESCONHECIDO"


def test_hdstatus_aceita_campos_customizados():
    hd = HDStatus(total="3000.00 GB", livre="1500.00 GB", status="ONLINE - NORMAL")
    assert hd.total == "3000.00 GB"
    assert hd.livre == "1500.00 GB"
    assert hd.status == "ONLINE - NORMAL"


# ─── Camera ──────────────────────────────────────────────────────────────────

def test_camera_status_padrao_e_pendente():
    cam = Camera(nome="C1", imagem="/tmp/c1.jpg")
    assert cam.status == "PENDENTE"


def test_camera_aceita_status_personalizado():
    cam = Camera(nome="C2", imagem="/tmp/c2.jpg", status="OK")
    assert cam.status == "OK"


def test_camera_imagem_padrao_e_string_vazia():
    cam = Camera(nome="C3")
    assert cam.imagem == ""


# ─── DVR ─────────────────────────────────────────────────────────────────────

def test_dvr_hd_inicializa_com_defaults():
    dvr = DVR(nome="DVR_A", ip="192.168.1.1", qtd_cameras=4)
    assert dvr.hd.total == "-"
    assert dvr.hd.livre == "-"
    assert dvr.hd.status == "DESCONHECIDO"


def test_dvr_cameras_iniciam_vazias():
    dvr = DVR(nome="DVR_A", ip="192.168.1.1", qtd_cameras=4)
    assert dvr.cameras == []


def test_dvr_cameras_nao_compartilhadas_entre_instancias():
    dvr1 = DVR(nome="A", ip="1.1.1.1", qtd_cameras=2)
    dvr2 = DVR(nome="B", ip="2.2.2.2", qtd_cameras=2)
    dvr1.cameras.append(Camera(nome="C1", imagem="x.jpg"))
    assert dvr2.cameras == []


def test_dvr_hd_nao_compartilhado_entre_instancias():
    dvr1 = DVR(nome="A", ip="1.1.1.1", qtd_cameras=2)
    dvr2 = DVR(nome="B", ip="2.2.2.2", qtd_cameras=2)
    dvr1.hd.status = "ONLINE - NORMAL"
    assert dvr2.hd.status == "DESCONHECIDO"


def test_dvr_aceita_hd_customizado():
    hd = HDStatus(total="3000.00 GB", livre="1500.00 GB", status="ONLINE - NORMAL")
    dvr = DVR(nome="DVR_B", ip="192.168.1.2", qtd_cameras=2, hd=hd)
    assert dvr.hd.status == "ONLINE - NORMAL"
