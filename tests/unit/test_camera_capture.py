"""Unit tests for src/core/camera_capture.py"""
import shutil

from src.core import camera_capture
from src.domain.models import DVR, HDStatus
from tests.fakes.fake_subprocess import make_fake_run


def _make_online_dvr(nome="DVR_ONLINE", qtd=1):
    dvr = DVR(nome=nome, ip="192.168.1.100", qtd_cameras=qtd)
    dvr.hd = HDStatus(total="3000 GB", livre="1500 GB", status="ONLINE - NORMAL")
    return dvr


def _make_offline_dvr(nome="DVR_OFFLINE", qtd=2):
    dvr = DVR(nome=nome, ip="192.168.1.200", qtd_cameras=qtd)
    dvr.hd = HDStatus(status="OFFLINE - SEM PING")
    return dvr


def test_dvr_offline_preenche_cameras_com_error_img(app_config, monkeypatch):
    dvrs = [_make_offline_dvr(qtd=2)]
    result = camera_capture.capturar_cameras(dvrs, app_config)

    cameras = result[0].cameras
    assert len(cameras) == 2
    assert all(c.imagem == app_config.error_img for c in cameras)
    assert all(c.status == "NAO_ANALISADO" for c in cameras)


def test_ffmpeg_sucesso_arquivo_grande_retorna_pendente(
    app_config, small_camera_jpg, monkeypatch
):
    from pathlib import Path

    dvr = _make_online_dvr()
    pasta = Path(app_config.base_dir) / dvr.nome
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.copy(small_camera_jpg, pasta / "C1.jpg")  # > 10 000 bytes

    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))

    result = camera_capture.capturar_cameras([dvr], app_config)
    cam = result[0].cameras[0]

    assert cam.status == "PENDENTE"
    assert cam.imagem == str(pasta / "C1.jpg")


def test_ffmpeg_sucesso_arquivo_pequeno_retorna_sem_conexao(
    app_config, monkeypatch, tmp_path
):
    from pathlib import Path

    dvr = _make_online_dvr(nome="DVR_SMALL")
    pasta = Path(app_config.base_dir) / dvr.nome
    pasta.mkdir(parents=True, exist_ok=True)
    tiny = pasta / "C1.jpg"
    tiny.write_bytes(b"\xff\xd8" + b"\x00" * 100)  # < 10 000 bytes

    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))

    result = camera_capture.capturar_cameras([dvr], app_config)
    cam = result[0].cameras[0]

    assert cam.status == "SEM_CONEXAO"
    assert cam.imagem == app_config.error_img


def test_ffmpeg_timeout_retorna_sem_conexao(app_config, monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(raise_timeout=True))

    dvr = _make_online_dvr(nome="DVR_TIMEOUT")
    result = camera_capture.capturar_cameras([dvr], app_config)
    cam = result[0].cameras[0]

    assert cam.status == "SEM_CONEXAO"
    assert cam.imagem == app_config.error_img
