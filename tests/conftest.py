import sys
import shutil
import importlib
import types
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures"

LEGACY_DVR_EXE3 = (
    Path(__file__).parents[2]
    / "___Codigo_Fonte_Atual(Producao)"
    / "107_Antonio_Carlos"
    / "DVR_exe3.py"
)


# ─── Binary fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def error_jpg(tmp_path_factory):
    """Minimal valid JPEG used as error placeholder image."""
    path = tmp_path_factory.mktemp("shared") / "error.jpg"
    from PIL import Image
    Image.new("RGB", (10, 10), color=(100, 100, 100)).save(str(path), "JPEG")
    return path


@pytest.fixture(scope="session")
def small_camera_jpg(tmp_path_factory):
    """Valid JPEG larger than 10 000 bytes (the size threshold in capturar_cameras).

    Uses random-noise pixels so JPEG compression cannot reduce the file below the
    10 000-byte threshold that capturar_cameras uses to distinguish a real frame
    from a failed capture.
    """
    import numpy as np
    from PIL import Image

    path = tmp_path_factory.mktemp("shared") / "camera.jpg"
    arr = np.random.randint(0, 255, (300, 300, 3), dtype=np.uint8)
    Image.fromarray(arr).save(str(path), "JPEG", quality=95)
    return path


# ─── Legacy module isolation ──────────────────────────────────────────────────

def _ensure_win32com_stub():
    """Injects a minimal win32com stub if pywin32 is not installed."""
    if "win32com" not in sys.modules:
        win32com_mod = types.ModuleType("win32com")
        win32com_client_mod = types.ModuleType("win32com.client")
        win32com_mod.client = win32com_client_mod
        sys.modules["win32com"] = win32com_mod
        sys.modules["win32com.client"] = win32com_client_mod


@pytest.fixture(scope="session", autouse=True)
def _win32com_stub():
    """Garante stub de win32com disponível para toda a suíte."""
    _ensure_win32com_stub()


@pytest.fixture
def legacy_module(tmp_path, error_jpg, monkeypatch):
    """
    Imports DVR_exe3 in a clean, isolated environment.

    Copies DVR_exe3.py and required support files into tmp_path so that
    BASE_PATH (computed from __file__) resolves to tmp_path. The module is
    removed from sys.modules after the test to prevent cross-test contamination.
    """
    _ensure_win32com_stub()

    shutil.copy(LEGACY_DVR_EXE3,                          tmp_path / "DVR_exe3.py")
    shutil.copy(FIXTURES_DIR / "dvrs_sample.txt",         tmp_path / "dvrs.txt")
    shutil.copy(FIXTURES_DIR / "emails_sample.txt",       tmp_path / "emails.txt")
    shutil.copy(error_jpg,                                tmp_path / "error.jpg")

    (tmp_path / "temp").mkdir(exist_ok=True)
    (tmp_path / "playwright_browsers").mkdir(exist_ok=True)

    sys.modules.pop("DVR_exe3", None)
    monkeypatch.syspath_prepend(str(tmp_path))

    mod = importlib.import_module("DVR_exe3")
    yield mod

    sys.modules.pop("DVR_exe3", None)


@pytest.fixture
def chromium_env(legacy_module, tmp_path):
    """
    Extends legacy_module with a fake chromium directory so that the chromium
    path discovery inside analisar_hd() succeeds without a real browser.
    Returns the legacy_module for convenience.
    """
    exe = (
        tmp_path
        / "playwright_browsers"
        / "chromium-1234"
        / "chrome-win64"
        / "chrome.exe"
    )
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.touch()
    return legacy_module


# ─── Shared DVR data fixtures ─────────────────────────────────────────────────

@pytest.fixture
def dvr_list_online():
    """Lista de DVRs no formato aceito por analisar_hd (list of dicts)."""
    return [{"nome": "DVR_TESTE", "ip": "192.168.1.100", "cameras": 2}]


@pytest.fixture
def dvr_list_offline():
    return [{"nome": "DVR_OFFLINE", "ip": "192.168.1.200", "cameras": 2}]


@pytest.fixture
def dvr_result_online():
    """Resultado de analisar_hd para DVR online, pronto para capturar_cameras."""
    return {
        "DVR_TESTE": {
            "ip": "192.168.1.100",
            "hd": {
                "total": "3000.00 GB",
                "livre": "1500.00 GB",
                "status": "ONLINE - NORMAL",
            },
            "qtd_cameras": 2,
            "cameras": [],
        }
    }


@pytest.fixture
def dvr_result_offline():
    return {
        "DVR_OFFLINE": {
            "ip": "192.168.1.200",
            "hd": {"total": "-", "livre": "-", "status": "OFFLINE - SEM PING"},
            "qtd_cameras": 2,
            "cameras": [],
        }
    }


@pytest.fixture
def dvr_with_pending_cameras(tmp_path, small_camera_jpg):
    """DVR result dict com câmeras prontas para revisão visual."""
    img1 = tmp_path / "C1.jpg"
    img2 = tmp_path / "C2.jpg"
    shutil.copy(small_camera_jpg, img1)
    shutil.copy(small_camera_jpg, img2)
    return {
        "DVR_TESTE": {
            "ip": "192.168.1.100",
            "hd": {
                "total": "3000.00 GB",
                "livre": "1500.00 GB",
                "status": "ONLINE - NORMAL",
            },
            "qtd_cameras": 2,
            "cameras": [
                {"nome": "C1", "imagem": str(img1), "status": "PENDENTE"},
                {"nome": "C2", "imagem": str(img2), "status": "PENDENTE"},
            ],
        }
    }


@pytest.fixture
def dvr_report_ready(tmp_path, small_camera_jpg):
    """DVR result dict com imagem válida, pronto para gerar_excel_pdf."""
    img = tmp_path / "C1_report.jpg"
    shutil.copy(small_camera_jpg, img)
    return {
        "DVR_RELATORIO": {
            "ip": "192.168.1.100",
            "hd": {
                "total": "3000.00 GB",
                "livre": "1500.00 GB",
                "status": "ONLINE - NORMAL",
            },
            "qtd_cameras": 1,
            "cameras": [{"nome": "C1", "imagem": str(img), "status": "OK"}],
        }
    }


# ─── Fixtures para módulos core/ ─────────────────────────────────────────────

@pytest.fixture
def playwright_env(tmp_path):
    """Diretório playwright_browsers com estrutura mínima de chromium falso."""
    exe = (
        tmp_path
        / "playwright_browsers"
        / "chromium-1234"
        / "chrome-win64"
        / "chrome.exe"
    )
    exe.parent.mkdir(parents=True)
    exe.touch()
    return tmp_path / "playwright_browsers"


@pytest.fixture
def app_config(tmp_path, playwright_env, error_jpg):
    """AppConfig preenchida com valores de teste."""
    from src.infra.app_config import AppConfig

    (tmp_path / "temp").mkdir(exist_ok=True)
    (tmp_path / "relatorios").mkdir(exist_ok=True)
    (tmp_path / "logs").mkdir(exist_ok=True)
    return AppConfig(
        usuario="admin",
        senha="admin123",
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path="ffmpeg.exe",
        base_dir=str(tmp_path / "temp"),
        error_img=str(error_jpg),
        playwright_path=str(playwright_env),
        emails=["teste@exemplo.com"],
        nome_instalacao="DVRs Teste",
        relatorios_dir=str(tmp_path / "relatorios"),
        logs_dir=str(tmp_path / "logs"),
    )


@pytest.fixture
def dvr_typed_online():
    """Lista de DVR objects (não dicts) com DVR online, para testes de core/."""
    from src.domain.models import DVR
    return [DVR(nome="DVR_TESTE", ip="192.168.1.100", qtd_cameras=2)]


@pytest.fixture
def dvr_typed_offline():
    from src.domain.models import DVR
    return [DVR(nome="DVR_OFFLINE", ip="192.168.1.200", qtd_cameras=2)]


@pytest.fixture
def dvr_typed_with_pending_cameras(tmp_path, small_camera_jpg):
    """DVR objects com câmeras reais prontas para revisão visual."""
    from src.domain.models import DVR, Camera

    img1 = tmp_path / "C1.jpg"
    img2 = tmp_path / "C2.jpg"
    shutil.copy(small_camera_jpg, img1)
    shutil.copy(small_camera_jpg, img2)

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.100", qtd_cameras=2)
    dvr.cameras = [
        Camera(nome="C1", imagem=str(img1), status="PENDENTE"),
        Camera(nome="C2", imagem=str(img2), status="PENDENTE"),
    ]
    return [dvr]
