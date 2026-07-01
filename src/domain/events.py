from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.domain.models import DVR


@dataclass
class ProgressEvent:
    """Representa o progresso de uma etapa do pipeline de checklist."""

    etapa: str      # "HD" | "CAPTURA" | "VISUAL" | "RELATORIO" | "EMAIL"
    mensagem: str
    total: int = 0
    atual: int = 0


@dataclass
class EmailDraft:
    """Rascunho do e-mail de checklist, editável antes do envio.

    Produzido por ``reports.email_sender.compor_email`` e consumido por
    ``enviar_draft``. Entre os dois, a UI pode exibir um diálogo de preview
    e devolver uma versão alterada (ou None para cancelar o envio).
    """

    assunto: str = ""
    corpo: str = ""
    destinatarios: List[str] = field(default_factory=list)
    anexos: List[str] = field(default_factory=list)


@dataclass
class ChecklistResult:
    """Resultado completo ao fim do pipeline."""

    dvrs: List[DVR] = field(default_factory=list)
    excel_path: str = ""
    pdf_path: str = ""
    book_excel_path: str = ""   # xlsx do book (1 câmera por página)
    book_path: str = ""         # PDF do book
    sucesso: bool = True
    erro: str = ""
    email_enviado: bool = True  # False se o usuário cancelou no preview
