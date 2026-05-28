"""
Characterization tests for enviar_email().
"""
import os
from tests.fakes.fake_win32com import FakeWin32ComClient, FakeWin32ComModule


def _make_dvrs(hd_status="ONLINE - NORMAL", cam_statuses=None):
    cam_statuses = cam_statuses or ["OK", "OK"]
    return {
        "DVR_TESTE": {
            "ip": "192.168.1.100",
            "hd": {"total": "3000.00 GB", "livre": "1500.00 GB", "status": hd_status},
            "qtd_cameras": len(cam_statuses),
            "cameras": [
                {"nome": f"C{i+1}", "status": s}
                for i, s in enumerate(cam_statuses)
            ],
        }
    }


def _patch_com(monkeypatch, mod, fake_client):
    """Replaces the entire win32com reference in the legacy module."""
    monkeypatch.setattr(mod, "win32com", FakeWin32ComModule(fake_client))


def test_assunto_normal_quando_sem_problemas(legacy_module, tmp_path, monkeypatch):
    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    legacy_module.enviar_email(_make_dvrs(), pdf)

    assert fake_com.outlook.last_mail.sent is True
    assert "ATENÇÃO HD" not in fake_com.outlook.last_mail.Subject


def test_assunto_alerta_quando_hd_com_falha(legacy_module, tmp_path, monkeypatch):
    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    legacy_module.enviar_email(_make_dvrs(hd_status="OFFLINE - SEM PING"), pdf)

    assert "ATENÇÃO HD" in fake_com.outlook.last_mail.Subject


def test_corpo_inclui_cameras_com_alerta(legacy_module, tmp_path, monkeypatch):
    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    dvrs = _make_dvrs(cam_statuses=["OK", "EMBAÇADA_SUJA"])
    legacy_module.enviar_email(dvrs, pdf)

    body = fake_com.outlook.last_mail.Body
    assert "C2" in body
    assert "EMBAÇADA_SUJA" in body


def test_corpo_inclui_obs_dvr_offline(legacy_module, tmp_path, monkeypatch):
    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    dvrs = _make_dvrs(hd_status="OFFLINE - SEM PING", cam_statuses=["SEM_CONEXAO"])
    legacy_module.enviar_email(dvrs, pdf)

    body = fake_com.outlook.last_mail.Body
    assert "SEM CONEXÃO" in body.upper()


def test_pdf_e_adicionado_como_anexo(legacy_module, tmp_path, monkeypatch):
    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    legacy_module.enviar_email(_make_dvrs(), pdf)

    attachments = fake_com.outlook.last_mail.Attachments.paths
    assert len(attachments) == 1
    assert attachments[0] == os.path.abspath(pdf)


def test_backup_de_email_e_salvo_em_arquivo(legacy_module, tmp_path, monkeypatch):
    from pathlib import Path

    fake_com = FakeWin32ComClient()
    _patch_com(monkeypatch, legacy_module, fake_com)

    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()

    legacy_module.enviar_email(_make_dvrs(), pdf)

    # logs_email is created relative to legacy_module.BASE_PATH, not test tmp_path
    logs_dir = Path(legacy_module.BASE_PATH) / "logs_email"
    backups = list(logs_dir.glob("email_*.txt"))
    assert len(backups) == 1
    content = backups[0].read_text(encoding="utf-8")
    assert "ASSUNTO:" in content
    assert "CORPO DO EMAIL:" in content
