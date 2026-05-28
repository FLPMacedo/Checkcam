"""Unit tests for src/infra/path_defaults.py

O usuário pode criar uma instalação pela UI sem preencher os caminhos.
Em vez de obrigar o usuário a saber a convenção do projeto, deduzimos
defaults sensatos a partir do nome da instalação.
"""
import os

from src.infra import path_defaults


def test_caminhos_padrao_inclui_todos_os_campos_obrigatorios():
    """Deve devolver os 6 caminhos que o checklist precisa."""
    d = path_defaults.caminhos_padrao_para("101 - Ponte Nova")
    chaves = {"base_dir", "relatorios_dir", "logs_dir",
              "ffmpeg_path", "playwright_path", "error_img"}
    assert set(d.keys()) >= chaves


def test_base_dir_usa_slug_dentro_de_data_temp():
    """base_dir = <CheckCam>/data/<slug>/temp"""
    d = path_defaults.caminhos_padrao_para("101 - Ponte Nova")
    assert d["base_dir"].endswith(os.path.join("data", "101_Ponte_Nova", "temp"))


def test_relatorios_dir_usa_slug_em_relatorios():
    """relatorios_dir = <CheckCam>/relatorios/<slug>"""
    d = path_defaults.caminhos_padrao_para("101 - Ponte Nova")
    assert d["relatorios_dir"].endswith(os.path.join("relatorios", "101_Ponte_Nova"))


def test_logs_dir_dentro_de_data_logs():
    """logs_dir = <CheckCam>/data/<slug>/logs"""
    d = path_defaults.caminhos_padrao_para("LPA POSTOS")
    assert d["logs_dir"].endswith(os.path.join("data", "LPA_POSTOS", "logs"))


def test_assets_compartilhados_sao_caminhos_absolutos():
    """ffmpeg, playwright, error_img são iguais pra todas instalações."""
    d = path_defaults.caminhos_padrao_para("Qualquer Nome")
    assert d["ffmpeg_path"].endswith(os.path.join("assets", "ffmpeg", "bin", "ffmpeg.exe"))
    assert d["playwright_path"].endswith(os.path.join("assets", "playwright_browsers"))
    assert d["error_img"].endswith(os.path.join("assets", "error.jpg"))


def test_caminhos_sao_absolutos():
    """Todos os caminhos devem ser absolutos para evitar bugs de cwd."""
    d = path_defaults.caminhos_padrao_para("X")
    for chave, caminho in d.items():
        assert os.path.isabs(caminho), f"{chave!r} não é absoluto: {caminho!r}"


def test_nome_com_caracteres_especiais_e_sanitizado():
    """Nomes com / : * etc viram slug seguro nos caminhos."""
    d = path_defaults.caminhos_padrao_para("DVR/Teste:com?caracteres")
    for caminho in (d["base_dir"], d["relatorios_dir"], d["logs_dir"]):
        for char in '/\\:*?"<>|':
            # Após o nome do diretório raiz "data" ou "relatorios", o slug
            # não pode ter chars inválidos. Pegamos só o último componente.
            ultimo = os.path.basename(caminho.rstrip(os.sep))
            assert char not in ultimo, f"Char {char!r} ficou em {ultimo!r}"


def test_nome_vazio_devolve_caminhos_genericos():
    """Edge case: nome vazio não deve quebrar."""
    d = path_defaults.caminhos_padrao_para("")
    assert all(d.values())
