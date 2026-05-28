"""Unit tests for src/services/checklist_service.py"""
from src.domain.events import ChecklistResult, ProgressEvent
from src.domain.models import DVR
from src.services import checklist_service
from src.services.checklist_service import ChecklistService


def _patch_pipeline(monkeypatch, excel="/fake/rel.xlsx", pdf="/fake/rel.pdf"):
    """Substitui todas as dependências do pipeline por funções passthrough."""
    monkeypatch.setattr(checklist_service, "analisar_hd",
                        lambda dvrs, cfg, on_log=None: dvrs)
    monkeypatch.setattr(checklist_service, "capturar_cameras",
                        lambda dvrs, cfg, on_log=None: dvrs)
    monkeypatch.setattr(checklist_service, "analisar_visual",
                        lambda dvrs, error_img: dvrs)
    monkeypatch.setattr(checklist_service, "gerar_excel",
                        lambda dvrs, cfg: excel)
    monkeypatch.setattr(checklist_service, "exportar_pdf",
                        lambda path: pdf)
    monkeypatch.setattr(checklist_service, "enviar_email",
                        lambda dvrs, pdf_path, cfg: "/fake/backup.txt")


def test_executar_retorna_checklist_result(app_config, monkeypatch):
    _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    result = ChecklistService(app_config).executar([dvr])

    assert isinstance(result, ChecklistResult)
    assert result.sucesso is True
    assert result.excel_path == "/fake/rel.xlsx"
    assert result.pdf_path == "/fake/rel.pdf"


def test_executar_sem_callback_nao_levanta_excecao(app_config, monkeypatch):
    _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    # Nenhum on_progress passado — não deve explodir
    ChecklistService(app_config).executar([dvr])


def test_progress_callback_recebe_cinco_eventos(app_config, monkeypatch):
    _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    eventos = []
    ChecklistService(app_config, on_progress=eventos.append).executar([dvr])

    etapas = [e.etapa for e in eventos]
    assert etapas == ["HD", "CAPTURA", "VISUAL", "RELATORIO", "EMAIL"]


def test_progress_callback_recebe_progress_events(app_config, monkeypatch):
    _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    eventos = []
    ChecklistService(app_config, on_progress=eventos.append).executar([dvr])

    assert all(isinstance(e, ProgressEvent) for e in eventos)


def test_executar_preserva_dvrs_retornados(app_config, monkeypatch):
    """DVRs retornados pelas funções core chegam no ChecklistResult."""
    from src.domain.models import HDStatus

    def fake_hd(dvrs, cfg, on_log=None):
        dvrs[0].hd = HDStatus(status="ONLINE - NORMAL")
        return dvrs

    monkeypatch.setattr(checklist_service, "analisar_hd", fake_hd)
    monkeypatch.setattr(checklist_service, "capturar_cameras",
                        lambda dvrs, cfg, on_log=None: dvrs)
    monkeypatch.setattr(checklist_service, "analisar_visual",
                        lambda dvrs, error_img: dvrs)
    monkeypatch.setattr(checklist_service, "gerar_excel",
                        lambda dvrs, cfg: "/fake/rel.xlsx")
    monkeypatch.setattr(checklist_service, "exportar_pdf",
                        lambda path: "/fake/rel.pdf")
    monkeypatch.setattr(checklist_service, "enviar_email",
                        lambda dvrs, pdf_path, cfg: "/fake/backup.txt")

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    result = ChecklistService(app_config).executar([dvr])

    assert result.dvrs[0].hd.status == "ONLINE - NORMAL"
