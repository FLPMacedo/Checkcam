"""Unit tests for src/core/camera_capture.py"""
import shutil
import subprocess

from src.core import camera_capture
from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR, HDStatus
from tests.fakes.fake_subprocess import make_fake_run


def _capturando_comandos(comandos, returncode=0):
    """Fake subprocess.run que registra cada cmd recebido em `comandos`."""
    def fake_run(cmd, **kwargs):
        comandos.append(cmd)
        from tests.fakes.fake_subprocess import FakeCompletedProcess
        return FakeCompletedProcess(returncode=returncode)
    return fake_run


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


def test_cada_camera_capturada_sabe_seu_dvr_nome(app_config, small_camera_jpg, monkeypatch):
    """Regressão: a câmera precisa carregar o nome do DVR a que pertence
    para o VisualReviewDialog poder exibir 'DVR PN_ADM1 / C5'."""
    from pathlib import Path
    import shutil

    dvr = _make_online_dvr(nome="PN_ADM1", qtd=2)
    pasta = Path(app_config.base_dir) / dvr.nome
    pasta.mkdir(parents=True, exist_ok=True)
    shutil.copy(small_camera_jpg, pasta / "C1.jpg")
    shutil.copy(small_camera_jpg, pasta / "C2.jpg")

    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    result = camera_capture.capturar_cameras([dvr], app_config)

    for cam in result[0].cameras:
        assert cam.dvr_nome == "PN_ADM1", f"Camera {cam.nome} sem dvr_nome"


def test_dvr_offline_cameras_tambem_tem_dvr_nome(app_config):
    """Mesmo em DVR offline, as câmeras placeholder devem ter dvr_nome
    (caso o usuário ainda queira ver de qual DVR são no diálogo)."""
    dvrs = [_make_offline_dvr(nome="DVR_OFF_X", qtd=3)]
    result = camera_capture.capturar_cameras(dvrs, app_config)
    for cam in result[0].cameras:
        assert cam.dvr_nome == "DVR_OFF_X"


# ─── Câmera IP / Intelbras ───────────────────────────────────────────────────

def test_camera_ip_captura_apenas_um_canal(app_config, monkeypatch):
    """Câmera IP = 1 stream, mesmo que qtd_cameras venha > 1."""
    comandos = []
    monkeypatch.setattr("subprocess.run", _capturando_comandos(comandos))

    cam = DVR(nome="CAM 1", ip="10.9.130.31", qtd_cameras=5,
              marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP)
    cam.hd = HDStatus(status="N/A - CÂMERA IP")

    result = camera_capture.capturar_cameras([cam], app_config)

    # apenas 1 câmera criada (canal único), apesar de qtd_cameras=5
    assert len(result[0].cameras) == 1
    assert len(comandos) == 1


def test_camera_ip_intelbras_usa_url_realmonitor(app_config, monkeypatch):
    comandos = []
    monkeypatch.setattr("subprocess.run", _capturando_comandos(comandos))

    cam = DVR(nome="CAM 1", ip="10.9.130.31", qtd_cameras=1,
              marca=Marca.INTELBRAS, tipo=TipoDispositivo.CAMERA_IP)
    cam.hd = HDStatus(status="N/A - CÂMERA IP")

    camera_capture.capturar_cameras([cam], app_config)

    # A URL RTSP está no cmd, logo após "-i"
    cmd = comandos[0]
    rtsp = cmd[cmd.index("-i") + 1]
    assert "10.9.130.31:554/cam/realmonitor?channel=1&subtype=0" in rtsp


def test_nvr_intelbras_captura_todos_os_canais(app_config, monkeypatch):
    comandos = []
    monkeypatch.setattr("subprocess.run", _capturando_comandos(comandos))

    nvr = DVR(nome="NVR", ip="10.9.130.10", qtd_cameras=4,
              marca=Marca.INTELBRAS, tipo=TipoDispositivo.DVR)
    nvr.hd = HDStatus(status="ONLINE - NORMAL")

    result = camera_capture.capturar_cameras([nvr], app_config)

    assert len(result[0].cameras) == 4
    canais = [
        cmd[cmd.index("-i") + 1].split("channel=")[1].split("&")[0]
        for cmd in comandos
    ]
    assert canais == ["1", "2", "3", "4"]


# ─── Retry com chave de criptografia ─────────────────────────────────────────

def _fake_run_que_falha_com_senha_normal(senha_normal: str, comandos: list):
    """Fake subprocess.run: cria arquivo PEQUENO (< 10KB) se a senha normal
    está na URL, ou GRANDE se a chave de criptografia está. Permite simular
    o caso real onde a senha falha mas a chave funciona."""
    def _run(cmd, **kwargs):
        comandos.append(cmd)
        from tests.fakes.fake_subprocess import FakeCompletedProcess
        rtsp = cmd[cmd.index("-i") + 1]
        img = cmd[-1]
        # Se a URL ainda usa a senha normal, "falha" (arquivo pequeno)
        if senha_normal in rtsp:
            with open(img, "wb") as f:
                f.write(b"\xff\xd8" + b"\x00" * 100)  # < 10 KB
        else:
            # URL com chave de criptografia → arquivo grande (sucesso)
            with open(img, "wb") as f:
                f.write(b"\xff\xd8" + b"\x00" * 20000)
        return FakeCompletedProcess(returncode=0)
    return _run


def test_chave_de_criptografia_e_usada_quando_senha_normal_falha(
    app_config, monkeypatch, small_camera_jpg
):
    """Cenário Hikvision com 'verification code': a senha do admin não abre
    o stream, mas a chave abre. O capture deve refazer com a chave."""
    comandos = []
    monkeypatch.setattr(
        "subprocess.run",
        _fake_run_que_falha_com_senha_normal("admin123", comandos),
    )

    dvr = _make_online_dvr(nome="DVR_CRIPT", qtd=1)
    dvr.chave_criptografia = "MINHA_CHAVE_HIK"
    from pathlib import Path
    pasta = Path(app_config.base_dir) / dvr.nome
    pasta.mkdir(parents=True, exist_ok=True)

    result = camera_capture.capturar_cameras([dvr], app_config)

    # 2 chamadas ao ffmpeg: tentou senha, falhou; tentou chave, sucesso
    assert len(comandos) == 2
    # Primeira chamada usou a senha normal
    assert "admin123" in comandos[0][comandos[0].index("-i") + 1]
    # Segunda chamada usou a chave
    assert "MINHA_CHAVE_HIK" in comandos[1][comandos[1].index("-i") + 1]
    # Câmera ficou PENDENTE (capture bem-sucedido)
    assert result[0].cameras[0].status == "PENDENTE"


def test_sem_chave_configurada_so_tenta_uma_vez(app_config, monkeypatch):
    """Sem chave_criptografia: nenhuma chamada extra; falha = SEM_CONEXAO."""
    comandos = []
    monkeypatch.setattr(
        "subprocess.run",
        _fake_run_que_falha_com_senha_normal("admin123", comandos),
    )

    dvr = _make_online_dvr(nome="DVR_NO_KEY", qtd=1)
    # dvr.chave_criptografia = "" (default)
    from pathlib import Path
    (Path(app_config.base_dir) / dvr.nome).mkdir(parents=True, exist_ok=True)

    result = camera_capture.capturar_cameras([dvr], app_config)

    # Só 1 tentativa (sem retry porque não tem chave)
    assert len(comandos) == 1
    assert result[0].cameras[0].status == "SEM_CONEXAO"


def test_chave_nao_e_usada_quando_senha_normal_funciona(
    app_config, monkeypatch, small_camera_jpg
):
    """Se a 1ª tentativa já funciona, não precisa do retry."""
    import shutil
    from pathlib import Path

    comandos = []
    def _run(cmd, **kwargs):
        comandos.append(cmd)
        from tests.fakes.fake_subprocess import FakeCompletedProcess
        # Sempre cria arquivo grande (sucesso)
        img = cmd[-1]
        shutil.copy(small_camera_jpg, img)
        return FakeCompletedProcess(returncode=0)
    monkeypatch.setattr("subprocess.run", _run)

    dvr = _make_online_dvr(nome="DVR_OK", qtd=1)
    dvr.chave_criptografia = "CHAVE_QUE_NAO_VAI_SER_USADA"
    (Path(app_config.base_dir) / dvr.nome).mkdir(parents=True, exist_ok=True)

    result = camera_capture.capturar_cameras([dvr], app_config)

    # Só 1 tentativa (sucesso de primeira)
    assert len(comandos) == 1
    assert "CHAVE_QUE_NAO_VAI_SER_USADA" not in comandos[0][comandos[0].index("-i") + 1]
    assert result[0].cameras[0].status == "PENDENTE"


def test_timeout_nao_dispara_retry_com_chave(app_config, monkeypatch):
    """TIMEOUT é problema de rede, não de credencial. Retry seria desperdício."""
    comandos = []
    def _run(cmd, **kwargs):
        comandos.append(cmd)
        raise subprocess.TimeoutExpired(cmd, 60)
    monkeypatch.setattr("subprocess.run", _run)

    dvr = _make_online_dvr(nome="DVR_TO", qtd=1)
    dvr.chave_criptografia = "CHAVE"
    from pathlib import Path
    (Path(app_config.base_dir) / dvr.nome).mkdir(parents=True, exist_ok=True)

    result = camera_capture.capturar_cameras([dvr], app_config)

    # Só 1 tentativa — TIMEOUT não justifica retry
    assert len(comandos) == 1
    assert result[0].cameras[0].status == "SEM_CONEXAO"
