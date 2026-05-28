"""Unit tests for src/core/visual_review.py"""
from src.core import visual_review
from src.domain.models import DVR, Camera, HDStatus
from tests.fakes.fake_cv2 import FakeCv2


def test_tecla_1_define_status_ok(
    dvr_typed_with_pending_cameras, app_config, monkeypatch
):
    fake = FakeCv2(key_sequence=[ord("1"), ord("1")])
    monkeypatch.setattr(visual_review, "cv2", fake)

    result = visual_review.analisar_visual(dvr_typed_with_pending_cameras, app_config.error_img)
    cameras = result[0].cameras

    assert cameras[0].status == "OK"
    assert cameras[1].status == "OK"
    assert len(fake.shown_images) == 2


def test_teclas_2_a_5_mapeiam_status_corretos(
    dvr_typed_with_pending_cameras, app_config, monkeypatch
):
    fake = FakeCv2(key_sequence=[ord("2"), ord("3")])
    monkeypatch.setattr(visual_review, "cv2", fake)

    result = visual_review.analisar_visual(dvr_typed_with_pending_cameras, app_config.error_img)
    cameras = result[0].cameras

    assert cameras[0].status == "EMBAÇADA_SUJA"
    assert cameras[1].status == "DISTORCIDA"


def test_tecla_q_interrompe_sem_alterar_cameras_restantes(
    dvr_typed_with_pending_cameras, app_config, monkeypatch
):
    fake = FakeCv2(key_sequence=[ord("q")])
    monkeypatch.setattr(visual_review, "cv2", fake)

    result = visual_review.analisar_visual(dvr_typed_with_pending_cameras, app_config.error_img)

    assert result[0].cameras[1].status == "PENDENTE"
    assert len(fake.shown_images) == 1


def test_cameras_com_error_img_sao_ignoradas(
    dvr_typed_with_pending_cameras, app_config, monkeypatch
):
    for cam in dvr_typed_with_pending_cameras[0].cameras:
        cam.imagem = app_config.error_img

    fake = FakeCv2(key_sequence=[])
    monkeypatch.setattr(visual_review, "cv2", fake)

    visual_review.analisar_visual(dvr_typed_with_pending_cameras, app_config.error_img)

    assert len(fake.shown_images) == 0
