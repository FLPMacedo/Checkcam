"""Unit tests for src/domain/events.py"""
from src.domain.events import ChecklistResult, ProgressEvent


def test_progress_event_valores_padrao():
    e = ProgressEvent(etapa="HD", mensagem="Analisando...")
    assert e.etapa == "HD"
    assert e.mensagem == "Analisando..."
    assert e.total == 0
    assert e.atual == 0


def test_progress_event_com_progresso():
    e = ProgressEvent(etapa="CAPTURA", mensagem="ok", total=10, atual=3)
    assert e.total == 10
    assert e.atual == 3


def test_checklist_result_valores_padrao():
    r = ChecklistResult()
    assert r.sucesso is True
    assert r.dvrs == []
    assert r.excel_path == ""
    assert r.pdf_path == ""
    assert r.erro == ""


def test_checklist_result_com_erro():
    r = ChecklistResult(sucesso=False, erro="falha grave")
    assert r.sucesso is False
    assert r.erro == "falha grave"
