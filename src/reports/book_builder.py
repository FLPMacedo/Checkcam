"""
Book PDF: gera um xlsx (depois exportado a PDF) com **uma câmera por página**
em paisagem, com a imagem em tamanho grande para inspeção detalhada.

Complementar ao Checklist (4 câmeras por linha, imagens pequenas). O book é
o "livro de imagens" — útil quando se precisa ver detalhes de uma câmera
específica em alta resolução.

Estrutura de cada página:
  ┌────────────────────────────────────────┐
  │   <DVR.nome> - <Camera.nome> - STATUS  │  ← cabeçalho
  │                                        │
  │   ┌──────────────────────────────────┐ │
  │   │                                  │ │
  │   │      IMAGEM (1000 × 625)         │ │  ← imagem grande
  │   │                                  │ │
  │   │                                  │ │
  │   └──────────────────────────────────┘ │
  └────────────────────────────────────────┘
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import List

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.pagebreak import Break

from src.domain.models import DVR
from src.infra.app_config import AppConfig
from src.reports.excel_builder import _slug_instalacao

# ── Dimensões da imagem em cada página do book (paisagem A4) ──────────────────
# A4 paisagem ≈ 1122 × 794 pixels @96 DPI.
# Imagem em 1000 × 625 deixa margens generosas pro título e respiração.
BOOK_IMG_W = 1000
BOOK_IMG_H = 625

# ── Layout de cada "página" do book em rows do Excel ──────────────────────────
TITULO_ROW          = 1     # cabeçalho da câmera
SPACER_APOS_TITULO  = 1     # linha em branco
IMG_ROW_OFFSET      = 2     # imagem começa em (page_start + 2)
LINHAS_PARA_IMAGEM  = 26    # ~26 rows × ~22 points ≈ 572 points (cabe 625 px)
ROWS_POR_PAGINA     = 30    # total reservado por câmera (com folga)

# Quantidade de colunas largas (acomoda a imagem horizontalmente)
COLS_BOOK = list("ABCDEFGHIJKLMN")  # 14 colunas

# Altura uniforme das rows da imagem
ALTURA_ROW_IMG     = 22
ALTURA_ROW_TITULO  = 28


def gerar_book_excel(dvrs: List[DVR], config: AppConfig) -> str:
    """
    Gera arquivo .xlsx com uma câmera por página, em paisagem.

    Cada câmera é precedida por um cabeçalho (DVR + nome + status) e a imagem
    aparece em tamanho cheio (1000 × 625 px). Páginas são separadas por quebras
    manuais de página — depois honradas pelo pdf_exporter (que re-aplica via COM).

    Nome do arquivo: ``Book_<slug>_<DD-MM-YYYY>_<HH-MM-SS>.xlsx``
    """
    os.makedirs(config.relatorios_dir, exist_ok=True)

    slug = _slug_instalacao(config.nome_instalacao) or "DVRs"
    agora = datetime.now()
    data_br = agora.strftime("%d-%m-%Y")
    hora    = agora.strftime("%H-%M-%S")

    book_path = os.path.join(
        config.relatorios_dir,
        f"Book_{slug}_{data_br}_{hora}.xlsx",
    )

    wb = Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Book")

    # Page setup: paisagem ajustada a 1 página de largura
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = True
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # Coleta todas as câmeras de todos os DVRs, em sequência
    cameras_planas: List[tuple] = [
        (dvr, cam) for dvr in dvrs for cam in dvr.cameras
    ]

    if not cameras_planas:
        # Nada a renderizar; salva o arquivo vazio com page setup configurado
        _aplicar_larguras(ws)
        wb.save(book_path)
        return book_path

    for n_pagina, (dvr, cam) in enumerate(cameras_planas):
        page_start = 1 + n_pagina * ROWS_POR_PAGINA
        _renderizar_pagina(ws, page_start, dvr, cam)

        # Quebra de página antes da próxima câmera (não na última)
        if n_pagina < len(cameras_planas) - 1:
            proxima_page_start = page_start + ROWS_POR_PAGINA
            ws.row_breaks.append(Break(id=proxima_page_start))

    _aplicar_larguras(ws)
    wb.save(book_path)
    return book_path


def _renderizar_pagina(ws, page_start: int, dvr: DVR, cam) -> None:
    """Desenha uma 'página' do book a partir de page_start (uma câmera)."""
    titulo_row = page_start + TITULO_ROW - 1   # row 1-indexed dentro da página
    img_row    = page_start + IMG_ROW_OFFSET

    # ── Título ──
    titulo_cell = f"A{titulo_row}"
    ws.merge_cells(f"A{titulo_row}:N{titulo_row}")
    ws[titulo_cell] = f"{dvr.nome}  -  {cam.nome}  -  {cam.status}"
    ws[titulo_cell].font = Font(size=14, bold=True)
    ws[titulo_cell].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[titulo_row].height = ALTURA_ROW_TITULO

    # ── Imagem ──
    try:
        xl_img = XLImage(cam.imagem)
        xl_img.width  = BOOK_IMG_W
        xl_img.height = BOOK_IMG_H
        ws.add_image(xl_img, f"A{img_row}")
    except (FileNotFoundError, OSError):
        # Imagem ausente/inválida: escreve um placeholder textual
        ws[f"A{img_row}"] = f"Imagem indisponivel: {cam.imagem}"

    # Altura uniforme nas rows reservadas para a imagem
    for r in range(img_row, img_row + LINHAS_PARA_IMAGEM):
        ws.row_dimensions[r].height = ALTURA_ROW_IMG


def _aplicar_larguras(ws) -> None:
    """Larguras de coluna que acomodam 1000px de imagem (≈ 14 × 12 caracteres)."""
    for col in COLS_BOOK:
        ws.column_dimensions[col].width = 12
