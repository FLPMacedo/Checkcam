"""Unit tests for src/reports/excel_builder.py"""
import os

from openpyxl import load_workbook

from src.domain.models import Camera, DVR
from src.reports import excel_builder


def _dvr_com_camera(imagem: str) -> DVR:
    dvr = DVR(nome="DVR_TESTE", ip="192.168.1.100", qtd_cameras=1)
    dvr.cameras = [Camera(nome="C1", imagem=imagem, status="OK")]
    return dvr


def test_gerar_excel_retorna_caminho_xlsx(app_config, error_jpg):
    result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)

    assert result.endswith(".xlsx")


def test_gerar_excel_cria_arquivo_no_relatorios_dir(app_config, error_jpg):
    result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)

    assert os.path.exists(result)
    assert result.startswith(app_config.relatorios_dir)


def test_gerar_excel_uma_aba_por_dvr(app_config, error_jpg):
    dvr1 = DVR(nome="DVR_A", ip="192.168.1.1", qtd_cameras=1)
    dvr1.cameras = [Camera(nome="C1", imagem=str(error_jpg), status="OK")]
    dvr2 = DVR(nome="DVR_B", ip="192.168.1.2", qtd_cameras=1)
    dvr2.cameras = [Camera(nome="C1", imagem=str(error_jpg), status="PENDENTE")]

    result = excel_builder.gerar_excel([dvr1, dvr2], app_config)

    wb = load_workbook(result)
    assert set(wb.sheetnames) == {"DVR_A", "DVR_B"}


def test_gerar_excel_com_dvr_offline(app_config, error_jpg):
    """DVR offline: câmeras têm error_img; deve gerar arquivo sem exceção."""
    from src.domain.models import HDStatus

    dvr = DVR(nome="DVR_OFF", ip="10.0.0.1", qtd_cameras=1)
    dvr.hd = HDStatus(status="OFFLINE - SEM PING")
    dvr.cameras = [Camera(nome="C1", imagem=str(error_jpg), status="NAO_ANALISADO")]

    result = excel_builder.gerar_excel([dvr], app_config)

    assert os.path.exists(result)


# ─── Nome de arquivo: Checklist_<slug>_<DD-MM-YYYY>_<HH-MM-SS>.xlsx ───────────

class TestNomeDoArquivo:
    def test_inclui_nome_da_instalacao(self, app_config, error_jpg):
        app_config.nome_instalacao = "101 - Ponte Nova"
        result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)
        nome = os.path.basename(result)
        assert "101_Ponte_Nova" in nome

    def test_data_em_formato_brasileiro(self, app_config, error_jpg):
        """Data deve estar como DD-MM-YYYY, não YYYY-MM-DD."""
        import re
        result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)
        nome = os.path.basename(result)
        # padrão DD-MM-YYYY: dia[01-31]-mês[01-12]-ano[2020+]
        assert re.search(r"_\d{2}-\d{2}-\d{4}_", nome), f"Nome sem data BR: {nome}"
        # NÃO deve ter formato ISO YYYY-MM-DD
        assert not re.search(r"_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xlsx$", nome), \
            f"Nome ainda no formato ISO: {nome}"

    def test_hora_no_nome(self, app_config, error_jpg):
        """Hora deve constar como HH-MM-SS no final do nome (antes do .xlsx)."""
        import re
        result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)
        nome = os.path.basename(result)
        assert re.search(r"_\d{2}-\d{2}-\d{2}\.xlsx$", nome), f"Nome sem hora: {nome}"

    def test_nome_com_caracteres_especiais_e_sanitizado(self, app_config, error_jpg):
        """Nomes como '102/Mutum:teste' viram '102_Mutum_teste' (sem chars inválidos NTFS)."""
        app_config.nome_instalacao = "102/Mutum:teste*com?ilegais"
        result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)
        nome = os.path.basename(result)
        for proibido in '/\\:*?"<>|':
            assert proibido not in nome, f"Char proibido '{proibido}' em {nome}"

    def test_formato_completo(self, app_config, error_jpg):
        """Formato final: Checklist_<slug>_<DD-MM-YYYY>_<HH-MM-SS>.xlsx"""
        import re
        app_config.nome_instalacao = "101 - Ponte Nova"
        result = excel_builder.gerar_excel([_dvr_com_camera(str(error_jpg))], app_config)
        nome = os.path.basename(result)
        # Checklist_<slug>_DD-MM-YYYY_HH-MM-SS.xlsx
        pattern = r"^Checklist_101_Ponte_Nova_\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}\.xlsx$"
        assert re.match(pattern, nome), f"Nome fora do padrao: {nome}"


# ─── Layout flexível ───────────────────────────────────────────────────────────

EMU_PER_PIXEL = 9525  # constante openpyxl: 1 pixel = 9525 EMU @ 96 DPI


def _dvr_com_n_cameras(n: int, imagem: str, nome: str = "DVR_N") -> DVR:
    dvr = DVR(nome=nome, ip="1.1.1.1", qtd_cameras=n)
    dvr.cameras = [
        Camera(nome=f"C{i}", imagem=imagem, status="OK") for i in range(1, n + 1)
    ]
    return dvr


def _img_size_px(img) -> tuple[int, int]:
    """Lê o tamanho de exibição da imagem em pixels a partir do anchor.ext (EMU).

    Depois de load_workbook, img.width devolve a dimensão real do JPEG —
    o que de fato é renderizado vem do anchor.ext em EMU.
    """
    cx = img.anchor.ext.cx
    cy = img.anchor.ext.cy
    return (cx // EMU_PER_PIXEL, cy // EMU_PER_PIXEL)


class TestLayoutFlexivel:
    """Grid 4×N padrão até 16 câmeras; 17+ vão pro grid largo 2×N abaixo."""

    def test_16_cameras_usa_tamanho_padrao(self, app_config, error_jpg):
        dvr = _dvr_com_n_cameras(16, str(error_jpg), "DVR_16")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_16"]

        assert len(ws._images) == 16
        for img in ws._images:
            w, h = _img_size_px(img)
            assert w == excel_builder.IMG_W
            assert h == excel_builder.IMG_H

    def test_18_cameras_separa_padrao_e_largo(self, app_config, error_jpg):
        """18 câmeras: 16 no grid padrão + 2 no grid largo (extras)."""
        dvr = _dvr_com_n_cameras(18, str(error_jpg), "DVR_18")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_18"]

        assert len(ws._images) == 18

        # 16 primeiras: tamanho padrão
        for img in ws._images[:16]:
            w, h = _img_size_px(img)
            assert w == excel_builder.IMG_W
            assert h == excel_builder.IMG_H

        # 2 últimas: tamanho largo (> que o padrão)
        for img in ws._images[16:]:
            w, h = _img_size_px(img)
            assert w == excel_builder.IMG_W_LARGO
            assert h == excel_builder.IMG_H_LARGO
            assert w > excel_builder.IMG_W

    def test_20_cameras_extras_em_layout_largo(self, app_config, error_jpg):
        """20 câmeras: 16 padrão + 4 largo (2 linhas de 2)."""
        dvr = _dvr_com_n_cameras(20, str(error_jpg), "DVR_20")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_20"]

        assert len(ws._images) == 20
        for img in ws._images[16:]:
            w, _ = _img_size_px(img)
            assert w == excel_builder.IMG_W_LARGO

    def test_3_cameras_linha_parcial_tem_altura_definida(self, app_config, error_jpg):
        """Regressão: 3 câmeras (linha incompleta) deve ter altura de linha
        definida — antes não tinha porque o código só atualizava a cada 4."""
        dvr = _dvr_com_n_cameras(3, str(error_jpg), "DVR_3")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_3"]

        # Linhas onde estão as 3 imagens (row 4 em diante) precisam de altura
        assert ws.row_dimensions[4].height == 32, "Linha da imagem sem altura definida"
        # Linha do nome (row 4 + NAME_OFFSET)
        assert ws.row_dimensions[4 + excel_builder.NAME_OFFSET].height == 18

    def test_8_cameras_duas_linhas_completas(self, app_config, error_jpg):
        """8 câmeras = 2 linhas completas. Ambas com altura definida."""
        dvr = _dvr_com_n_cameras(8, str(error_jpg), "DVR_8")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_8"]

        # Linha 1 (row 4) e linha 2 (row 4 + BLOCK_HEIGHT)
        assert ws.row_dimensions[4].height == 32
        assert ws.row_dimensions[4 + excel_builder.BLOCK_HEIGHT].height == 32

    def test_dvr_sem_cameras_nao_quebra(self, app_config):
        """0 câmeras: deve gerar arquivo sem exceção (caso degenerado)."""
        dvr = DVR(nome="DVR_VAZIO", ip="1.1.1.1", qtd_cameras=0)
        # Sem dvr.cameras
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_VAZIO"]
        assert len(ws._images) == 0

    def test_18_cameras_tem_quebra_de_pagina_antes_do_bloco_largo(
        self, app_config, error_jpg
    ):
        """Regressão: sem page-break explícito, o bloco largo era cortado pelo
        Excel no meio da página (parte renderizada na pág 1 + parte na pág 2).
        Forçar uma quebra de página garante que os extras saiam limpos."""
        dvr = _dvr_com_n_cameras(18, str(error_jpg), "DVR_PB")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_PB"]

        # Deve ter exatamente 1 quebra de página (entre standard e wide)
        assert len(ws.row_breaks.brk) == 1, \
            f"Esperava 1 page-break, achei {len(ws.row_breaks.brk)}"

    def test_16_cameras_sem_quebra_de_pagina(self, app_config, error_jpg):
        """16 câmeras (só layout padrão) não precisam de quebra forçada."""
        dvr = _dvr_com_n_cameras(16, str(error_jpg), "DVR_16NP")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_16NP"]

        assert len(ws.row_breaks.brk) == 0

    def test_4_cameras_sem_quebra_de_pagina(self, app_config, error_jpg):
        """DVRs pequenos não devem ganhar quebra de página."""
        dvr = _dvr_com_n_cameras(4, str(error_jpg), "DVR_4")
        result = excel_builder.gerar_excel([dvr], app_config)
        wb = load_workbook(result)
        ws = wb["DVR_4"]

        assert len(ws.row_breaks.brk) == 0
