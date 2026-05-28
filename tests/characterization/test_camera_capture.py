"""
Characterization tests for capturar_cameras().
"""
import shutil
from tests.fakes.fake_subprocess import make_fake_run


def test_dvr_offline_preenche_todas_cameras_com_error_img(
    legacy_module, dvr_result_offline
):
    result = legacy_module.capturar_cameras(dvr_result_offline)
    cameras = result["DVR_OFFLINE"]["cameras"]

    assert len(cameras) == 2
    assert all(c["imagem"] == legacy_module.ERROR_IMG for c in cameras)
    assert all(c["status"] == "NAO_ANALISADO" for c in cameras)


def test_ffmpeg_sucesso_arquivo_grande_retorna_pendente(
    legacy_module, small_camera_jpg, monkeypatch
):
    from pathlib import Path

    dvr_name = "DVR_ONLINE"
    # BASE_DIR is inside the legacy_module's own tmp_path
    pasta = Path(legacy_module.BASE_DIR) / dvr_name
    pasta.mkdir(parents=True, exist_ok=True)
    expected_img = pasta / "C1.jpg"
    shutil.copy(small_camera_jpg, expected_img)  # > 10 000 bytes

    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))

    dvrs = {
        dvr_name: {
            "ip": "192.168.1.100",
            "hd": {"total": "3000 GB", "livre": "1500 GB", "status": "ONLINE - NORMAL"},
            "qtd_cameras": 1,
            "cameras": [],
        }
    }
    result = legacy_module.capturar_cameras(dvrs)
    cam = result[dvr_name]["cameras"][0]

    assert cam["status"] == "PENDENTE"
    assert cam["imagem"] == str(expected_img)


def test_ffmpeg_sucesso_arquivo_pequeno_retorna_sem_conexao(
    legacy_module, tmp_path, monkeypatch
):
    dvr_name = "DVR_SMALL"
    pasta = tmp_path / "temp" / dvr_name
    pasta.mkdir(parents=True)
    tiny_img = pasta / "C1.jpg"
    tiny_img.write_bytes(b"\xff\xd8" + b"\x00" * 100)  # well below 10 000 bytes

    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))

    dvrs = {
        dvr_name: {
            "ip": "192.168.1.100",
            "hd": {"total": "3000 GB", "livre": "1500 GB", "status": "ONLINE - NORMAL"},
            "qtd_cameras": 1,
            "cameras": [],
        }
    }
    result = legacy_module.capturar_cameras(dvrs)
    cam = result[dvr_name]["cameras"][0]

    assert cam["status"] == "SEM_CONEXAO"
    assert cam["imagem"] == legacy_module.ERROR_IMG


def test_ffmpeg_timeout_retorna_sem_conexao(legacy_module, monkeypatch):
    monkeypatch.setattr("subprocess.run", make_fake_run(raise_timeout=True))

    dvrs = {
        "DVR_TIMEOUT": {
            "ip": "192.168.1.100",
            "hd": {"total": "3000 GB", "livre": "1500 GB", "status": "ONLINE - NORMAL"},
            "qtd_cameras": 1,
            "cameras": [],
        }
    }
    result = legacy_module.capturar_cameras(dvrs)
    cam = result["DVR_TIMEOUT"]["cameras"][0]

    assert cam["status"] == "SEM_CONEXAO"
    assert cam["imagem"] == legacy_module.ERROR_IMG
