"""
Characterization tests for analisar_hd().

All tests use chromium_env (which extends legacy_module with a fake
chromium directory) because analisar_hd() discovers chromium before
entering the per-DVR loop.
"""
import pytest
from tests.fakes.fake_subprocess import make_fake_run
from tests.fakes.fake_playwright import (
    make_playwright_with_hd,
    make_playwright_timeout_on_goto,
    make_playwright_no_gb_data,
)


def test_dvr_sem_ping_fica_offline(chromium_env, monkeypatch, dvr_list_offline):
    mod = chromium_env
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=1))
    monkeypatch.setattr(mod, "sync_playwright", lambda: make_playwright_with_hd(3000, 1500))

    result = mod.analisar_hd(dvr_list_offline)

    dvr = result["DVR_OFFLINE"]
    assert dvr["hd"]["status"] == "OFFLINE - SEM PING"
    assert dvr["hd"]["total"] == "-"
    assert dvr["hd"]["livre"] == "-"
    assert dvr["cameras"] == []


def test_dvr_online_com_hd_normal_retorna_valores_parseados(
    chromium_env, monkeypatch, dvr_list_online
):
    mod = chromium_env
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    monkeypatch.setattr(mod, "sync_playwright", lambda: make_playwright_with_hd(3000.0, 1500.0))

    result = mod.analisar_hd(dvr_list_online)

    dvr = result["DVR_TESTE"]
    assert dvr["hd"]["status"] == "ONLINE - NORMAL"
    assert dvr["hd"]["total"] == "3000.00 GB"
    assert dvr["hd"]["livre"] == "1500.00 GB"


def test_dvr_online_sem_dados_gb_retorna_erro_hd(
    chromium_env, monkeypatch, dvr_list_online
):
    mod = chromium_env
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    monkeypatch.setattr(mod, "sync_playwright", lambda: make_playwright_no_gb_data())

    result = mod.analisar_hd(dvr_list_online)

    assert result["DVR_TESTE"]["hd"]["status"] == "ONLINE - ERRO (HD)"


def test_dvr_playwright_timeout_retorna_offline_sem_resposta(
    chromium_env, monkeypatch, dvr_list_online
):
    mod = chromium_env
    monkeypatch.setattr("subprocess.run", make_fake_run(returncode=0))
    monkeypatch.setattr(mod, "sync_playwright", lambda: make_playwright_timeout_on_goto())

    result = mod.analisar_hd(dvr_list_online)

    assert result["DVR_TESTE"]["hd"]["status"] == "OFFLINE - SEM RESPOSTA"
