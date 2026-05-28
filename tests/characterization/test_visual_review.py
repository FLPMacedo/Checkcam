"""
Characterization tests for analisar_visual().
"""
from tests.fakes.fake_cv2 import FakeCv2


def test_tecla_1_define_status_ok(legacy_module, dvr_with_pending_cameras, monkeypatch):
    fake = FakeCv2(key_sequence=[ord("1"), ord("1")])
    monkeypatch.setattr(legacy_module, "cv2", fake)

    result = legacy_module.analisar_visual(dvr_with_pending_cameras)
    cameras = result["DVR_TESTE"]["cameras"]

    assert cameras[0]["status"] == "OK"
    assert cameras[1]["status"] == "OK"
    assert len(fake.shown_images) == 2


def test_teclas_2_a_5_mapeiam_status_corretos(
    legacy_module, dvr_with_pending_cameras, monkeypatch
):
    # Two cameras: first gets key '2', second gets key '3'
    fake = FakeCv2(key_sequence=[ord("2"), ord("3")])
    monkeypatch.setattr(legacy_module, "cv2", fake)

    result = legacy_module.analisar_visual(dvr_with_pending_cameras)
    cameras = result["DVR_TESTE"]["cameras"]

    assert cameras[0]["status"] == "EMBAÇADA_SUJA"
    assert cameras[1]["status"] == "DISTORCIDA"


def test_tecla_q_interrompe_sem_alterar_cameras_restantes(
    legacy_module, dvr_with_pending_cameras, monkeypatch
):
    # First camera gets 'q' — second camera should keep its original status
    fake = FakeCv2(key_sequence=[ord("q")])
    monkeypatch.setattr(legacy_module, "cv2", fake)

    result = legacy_module.analisar_visual(dvr_with_pending_cameras)
    cameras = result["DVR_TESTE"]["cameras"]

    assert cameras[1]["status"] == "PENDENTE"
    assert len(fake.shown_images) == 1


def test_cameras_com_error_img_sao_ignoradas(
    legacy_module, dvr_with_pending_cameras, monkeypatch, error_jpg
):
    # Replace all camera images with ERROR_IMG path
    for cam in dvr_with_pending_cameras["DVR_TESTE"]["cameras"]:
        cam["imagem"] = legacy_module.ERROR_IMG

    fake = FakeCv2(key_sequence=[])
    monkeypatch.setattr(legacy_module, "cv2", fake)

    legacy_module.analisar_visual(dvr_with_pending_cameras)

    assert len(fake.shown_images) == 0
