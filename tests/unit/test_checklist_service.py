"""Unit tests for src/services/checklist_service.py"""
from src.domain.events import ChecklistResult, EmailDraft, ProgressEvent
from src.domain.models import DVR
from src.services import checklist_service
from src.services.checklist_service import ChecklistService


def _patch_pipeline(
    monkeypatch,
    excel="/fake/rel.xlsx",
    pdf="/fake/rel.pdf",
    book_excel="/fake/book.xlsx",
    book_pdf="/fake/book.pdf",
):
    """Substitui todas as dependências do pipeline por funções passthrough."""
    monkeypatch.setattr(checklist_service, "analisar_hd",
                        lambda dvrs, cfg, on_log=None: dvrs)
    monkeypatch.setattr(checklist_service, "capturar_cameras",
                        lambda dvrs, cfg, on_log=None: dvrs)
    monkeypatch.setattr(checklist_service, "analisar_visual",
                        lambda dvrs, error_img: dvrs)
    monkeypatch.setattr(checklist_service, "gerar_excel",
                        lambda dvrs, cfg: excel)
    monkeypatch.setattr(checklist_service, "gerar_book_excel",
                        lambda dvrs, cfg: book_excel)
    # exportar_pdf é chamado 2x: uma para o checklist, outra para o book
    exporta_calls = []
    def _fake_exportar(path):
        exporta_calls.append(path)
        return book_pdf if "book" in path else pdf
    monkeypatch.setattr(checklist_service, "exportar_pdf", _fake_exportar)
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="": EmailDraft())
    monkeypatch.setattr(checklist_service, "enviar_draft",
                        lambda draft, cfg: "/fake/backup.txt")
    return exporta_calls


def test_executar_retorna_checklist_result(app_config, monkeypatch):
    _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    result = ChecklistService(app_config).executar([dvr])

    assert isinstance(result, ChecklistResult)
    assert result.sucesso is True
    assert result.excel_path == "/fake/rel.xlsx"
    assert result.pdf_path == "/fake/rel.pdf"


def test_executar_gera_book_pdf_alem_do_checklist(app_config, monkeypatch):
    """O pipeline também gera o Book PDF (uma câmera por página)."""
    calls = _patch_pipeline(monkeypatch)
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)

    result = ChecklistService(app_config).executar([dvr])

    # exportar_pdf foi chamado 2x (uma para o checklist, outra para o book)
    assert len(calls) == 2
    assert any("book" in c for c in calls)
    assert result.book_path == "/fake/book.pdf"


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
    assert etapas == ["HD", "CAPTURA", "VISUAL", "RELATORIO", "BOOK", "EMAIL"]


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
    monkeypatch.setattr(checklist_service, "gerar_book_excel",
                        lambda dvrs, cfg: "/fake/book.xlsx")
    monkeypatch.setattr(checklist_service, "exportar_pdf",
                        lambda path: path.replace(".xlsx", ".pdf"))
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="": EmailDraft())
    monkeypatch.setattr(checklist_service, "enviar_draft",
                        lambda draft, cfg: "/fake/backup.txt")

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    result = ChecklistService(app_config).executar([dvr])

    assert result.dvrs[0].hd.status == "ONLINE - NORMAL"


# ─── email_review_fn (preview de e-mail) ─────────────────────────────────────

def test_email_review_fn_recebe_o_draft_composto(app_config, monkeypatch):
    """O hook recebe o EmailDraft produzido por compor_email."""
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="":
                        EmailDraft(assunto="ORIGINAL"))

    recebidos = []

    def review(draft):
        recebidos.append(draft)
        return draft

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    ChecklistService(app_config, email_review_fn=review).executar([dvr])

    assert len(recebidos) == 1
    assert recebidos[0].assunto == "ORIGINAL"


def test_email_review_fn_editado_eh_o_que_se_envia(app_config, monkeypatch):
    """O draft devolvido pelo hook (editado) é o que chega em enviar_draft."""
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="": EmailDraft())

    enviados = []
    monkeypatch.setattr(checklist_service, "enviar_draft",
                        lambda draft, cfg: enviados.append(draft) or "/fake/backup.txt")

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    result = ChecklistService(
        app_config,
        email_review_fn=lambda d: EmailDraft(assunto="EDITADO", corpo="novo"),
    ).executar([dvr])

    assert result.email_enviado is True
    assert len(enviados) == 1
    assert enviados[0].assunto == "EDITADO"


def test_email_review_fn_none_cancela_envio(app_config, monkeypatch):
    """Hook devolvendo None → não envia e result.email_enviado é False."""
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="": EmailDraft())

    enviados = []
    monkeypatch.setattr(checklist_service, "enviar_draft",
                        lambda draft, cfg: enviados.append(draft) or "/fake/backup.txt")

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    result = ChecklistService(
        app_config, email_review_fn=lambda d: None
    ).executar([dvr])

    assert result.email_enviado is False
    assert enviados == []  # enviar_draft NÃO foi chamado


def test_sem_email_review_fn_envia_por_padrao(app_config, monkeypatch):
    """Sem hook, o comportamento legado é preservado: envia o draft como está."""
    _patch_pipeline(monkeypatch)
    monkeypatch.setattr(checklist_service, "compor_email",
                        lambda dvrs, pdf_path, cfg, book_path="": EmailDraft())
    enviados = []
    monkeypatch.setattr(checklist_service, "enviar_draft",
                        lambda draft, cfg: enviados.append(draft) or "/fake/backup.txt")

    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.1", qtd_cameras=1)
    result = ChecklistService(app_config).executar([dvr])

    assert result.email_enviado is True
    assert len(enviados) == 1
