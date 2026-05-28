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
class ChecklistResult:
    """Resultado completo ao fim do pipeline."""

    dvrs: List[DVR] = field(default_factory=list)
    excel_path: str = ""
    pdf_path: str = ""
    sucesso: bool = True
    erro: str = ""
