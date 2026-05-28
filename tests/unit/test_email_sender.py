"""Unit tests for src/reports/email_sender.py"""
import os
from pathlib import Path

from tests.fakes.fake_win32com import FakeWin32ComClient, FakeWin32ComModule
from src.domain.models import Camera, DVR, HDStatus
from src.reports import email_sender


def _patch_com(monkeypatch, fake_client):
    monkeypatch.setattr(email_sender, "win32com", FakeWin32ComModule(fake_client))


def _make_dvrs(hd_status="ONLINE - NORMAL", cam_statuses=None):
    cam_statuses = cam_statuses or ["OK", "OK"]
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.100", qtd_cameras=len(cam_statuses))
    dvr.hd = HDStatus(total="3000.00 GB", livre="1500.00 GB", status=hd_status)
    dvr.cameras = [
        Camera(nome=f"C{i+1}", status=s) for i, s in enumerate(cam_statuses)
    ]
    return [dvr]


def _make_pdf(tmp_path) -> str:
    pdf = str(tmp_path / "relatorio.pdf")
    open(pdf, "wb").close()
    return pdf


def test_enviar_email_chama_send(tmp_path, app_config, monkeypatch):
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    email_sender.enviar_email(_make_dvrs(), _make_pdf(tmp_path), app_config)

    assert fake_client.outlook.last_mail.sent is True


def test_enviar_email_destinatarios_corretos(tmp_path, app_config, monkeypatch):
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    email_sender.enviar_email(_make_dvrs(), _make_pdf(tmp_path), app_config)

    assert "teste@exemplo.com" in fake_client.outlook.last_mail.To


def test_enviar_email_assunto_alerta_hd_quando_offline(tmp_path, app_config, monkeypatch):
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    email_sender.enviar_email(
        _make_dvrs(hd_status="OFFLINE - SEM PING"), _make_pdf(tmp_path), app_config
    )

    assert "ATENÇÃO HD" in fake_client.outlook.last_mail.Subject


def test_enviar_email_salva_backup_em_logs_dir(tmp_path, app_config, monkeypatch):
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    backup_path = email_sender.enviar_email(
        _make_dvrs(), _make_pdf(tmp_path), app_config
    )

    assert os.path.exists(backup_path)
    assert backup_path.startswith(app_config.logs_dir)
    content = Path(backup_path).read_text(encoding="utf-8")
    assert "ASSUNTO:" in content
    assert "CORPO DO EMAIL:" in content


def test_enviar_email_anexa_book_pdf_quando_fornecido(tmp_path, app_config, monkeypatch):
    """Quando book_path é passado, ambos PDFs vão no anexo."""
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    pdf = _make_pdf(tmp_path)
    book = str(tmp_path / "book.pdf")
    open(book, "wb").close()

    email_sender.enviar_email(_make_dvrs(), pdf, app_config, book_path=book)

    anexos = fake_client.outlook.last_mail.Attachments.paths
    assert len(anexos) == 2
    assert any("relatorio.pdf" in a for a in anexos)
    assert any("book.pdf" in a for a in anexos)


def test_enviar_email_sem_book_anexa_so_o_pdf_principal(tmp_path, app_config, monkeypatch):
    """Backwards compat: chamar sem book_path mantém só 1 anexo."""
    fake_client = FakeWin32ComClient()
    _patch_com(monkeypatch, fake_client)

    email_sender.enviar_email(_make_dvrs(), _make_pdf(tmp_path), app_config)

    anexos = fake_client.outlook.last_mail.Attachments.paths
    assert len(anexos) == 1
