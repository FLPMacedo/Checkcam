"""Unit tests for src/reports/book_builder.py

O "book" é um PDF complementar ao Checklist principal: cada câmera ocupa
uma página inteira em paisagem, com a imagem em tamanho cheio (vs. as
imagens pequenas/divididas do checklist 4×N).
"""
import os
import re

from openpyxl import load_workbook

from src.domain.models import Camera, DVR, HDStatus
from src.reports import book_builder


def _dvr_com_cameras(nome: str, imagem: str, n: int) -> DVR:
    dvr = DVR(nome=nome, ip="1.1.1.1", qtd_cameras=n)
    dvr.hd = HDStatus(total="3000 GB", livre="1500 GB", status="ONLINE - NORMAL")
    dvr.cameras = [
        Camera(nome=f"C{i}", imagem=imagem, status="OK") for i in range(1, n + 1)
    ]
    return dvr


# ─── filename ────────────────────────────────────────────────────────────────

def test_book_arquivo_tem_prefixo_book(app_config, error_jpg):
    dvr = _dvr_com_cameras("DVR_A", str(error_jpg), 1)
    result = book_builder.gerar_book_excel([dvr], app_config)
    nome = os.path.basename(result)
    assert nome.startswith("Book_")
    assert nome.endswith(".xlsx")


def test_book_arquivo_segue_padrao_de_nome_do_checklist(app_config, error_jpg):
    """Mesmo formato do Checklist: Book_<slug>_DD-MM-YYYY_HH-MM-SS.xlsx"""
    app_config.nome_instalacao = "101 - Ponte Nova"
    dvr = _dvr_com_cameras("DVR_A", str(error_jpg), 1)
    result = book_builder.gerar_book_excel([dvr], app_config)
    nome = os.path.basename(result)
    pattern = r"^Book_101_Ponte_Nova_\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}\.xlsx$"
    assert re.match(pattern, nome), f"Nome fora do padrao: {nome}"


def test_book_arquivo_e_salvo_em_relatorios_dir(app_config, error_jpg):
    dvr = _dvr_com_cameras("DVR_A", str(error_jpg), 1)
    result = book_builder.gerar_book_excel([dvr], app_config)
    assert os.path.exists(result)
    assert result.startswith(app_config.relatorios_dir)


# ─── conteúdo: uma câmera por página ─────────────────────────────────────────

def test_book_tem_uma_imagem_por_camera(app_config, error_jpg):
    """3 câmeras → 3 imagens no book."""
    dvr = _dvr_com_cameras("DVR_X", str(error_jpg), 3)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    assert len(ws._images) == 3


def test_book_tem_quebra_de_pagina_entre_cameras(app_config, error_jpg):
    """N câmeras geram N-1 quebras de página (uma entre cada par)."""
    dvr = _dvr_com_cameras("DVR_Y", str(error_jpg), 4)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    # 4 câmeras: 3 quebras de página entre elas (1→2, 2→3, 3→4)
    assert len(ws.row_breaks.brk) == 3


def test_book_imagem_em_tamanho_grande(app_config, error_jpg):
    """Imagem do book é claramente maior que a do Checklist (310×194)."""
    EMU_PER_PIXEL = 9525
    dvr = _dvr_com_cameras("DVR_Z", str(error_jpg), 1)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    img = ws._images[0]
    w_px = img.anchor.ext.cx // EMU_PER_PIXEL
    h_px = img.anchor.ext.cy // EMU_PER_PIXEL
    # Pelo menos 2× a largura do checklist padrão
    assert w_px >= 620, f"Imagem book muito pequena: {w_px}px"
    assert h_px >= 400, f"Imagem book muito pequena: {h_px}px"


def test_book_inclui_nome_do_dvr_e_camera_no_titulo(app_config, error_jpg):
    """Cada página tem um cabeçalho com nome do DVR e nome da câmera."""
    dvr = _dvr_com_cameras("PN_ALMOXARIFADO", str(error_jpg), 2)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    # Concatena todo o texto da planilha
    todos_textos = []
    for row in ws.iter_rows(values_only=True):
        for valor in row:
            if isinstance(valor, str):
                todos_textos.append(valor)
    texto = " | ".join(todos_textos)

    assert "PN_ALMOXARIFADO" in texto
    assert "C1" in texto
    assert "C2" in texto


def test_book_combina_cameras_de_multiplos_dvrs(app_config, error_jpg):
    """Várias instalações vão no mesmo book, em sequência."""
    dvr1 = _dvr_com_cameras("DVR_1", str(error_jpg), 2)
    dvr2 = _dvr_com_cameras("DVR_2", str(error_jpg), 3)
    result = book_builder.gerar_book_excel([dvr1, dvr2], app_config)
    wb = load_workbook(result)
    ws = wb.active

    # 2 + 3 = 5 câmeras = 5 imagens; 4 quebras entre elas
    assert len(ws._images) == 5
    assert len(ws.row_breaks.brk) == 4


def test_book_dvrs_sem_cameras_nao_quebra(app_config):
    """Edge case: DVR sem câmeras (offline) não gera páginas, mas o book existe."""
    dvr = DVR(nome="DVR_VAZIO", ip="1.1.1.1", qtd_cameras=0)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active
    assert len(ws._images) == 0


def test_book_orientacao_paisagem(app_config, error_jpg):
    """Page setup configurado como paisagem (mesma do checklist)."""
    dvr = _dvr_com_cameras("DVR_O", str(error_jpg), 1)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    assert ws.page_setup.orientation == "landscape"


def test_book_altura_de_cada_pagina_cabe_em_landscape_a4(app_config, error_jpg):
    """Regressão: o conteúdo alocado para UMA câmera precisa caber em
    uma página landscape A4 (~487pt depois das margens default).

    Sem isso, o Excel quebra a página AUTOMATICAMENTE no meio do conteúdo,
    cortando a imagem e empurrando o resto para a página seguinte —
    independente das quebras manuais que adicionarmos."""
    # Espaço útil em landscape A4 com margens default (0.75" × 2 = 108pt)
    MAX_HEIGHT_PT = 487

    dvr = _dvr_com_cameras("DVR_HT", str(error_jpg), 2)
    result = book_builder.gerar_book_excel([dvr], app_config)
    wb = load_workbook(result)
    ws = wb.active

    # Pega a primeira quebra (delimita o fim da página 1)
    assert ws.row_breaks.brk, "Não há quebra de página para delimitar"
    primeira_quebra = min(b.id for b in ws.row_breaks.brk)

    total_pt = 0.0
    for row_num in range(1, primeira_quebra):
        altura = ws.row_dimensions[row_num].height
        if altura is None:
            altura = 15  # default do openpyxl
        total_pt += altura

    assert total_pt <= MAX_HEIGHT_PT, (
        f"Conteúdo de uma página ({total_pt:.0f}pt) excede landscape A4 "
        f"({MAX_HEIGHT_PT}pt) — Excel vai quebrar no meio da imagem"
    )
