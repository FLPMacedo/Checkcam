"""
Fonte única de verdade para os status de câmera e o mapeamento de teclas
de classificação usado na revisão visual.

Antes da Fase A esses valores viviam como strings soltas espalhadas por
core/, ui/ e reports/, e o mapa tecla→status estava DUPLICADO em dois lugares
(``core/visual_review.py`` com 5 teclas e ``ui/visual_review_dialog.py`` com 6),
que já haviam divergido. Centralizar aqui elimina a divergência e os erros
silenciosos de digitação.

``CameraStatus`` herda de ``str`` (via ``StrEnum``), então
``CameraStatus.OK == "OK"`` é ``True``. Isso mantém compatibilidade total com
o código e os testes que comparam ``cam.status == "OK"`` diretamente.
"""
from __future__ import annotations

from enum import StrEnum


class CameraStatus(StrEnum):
    """Estados possíveis de uma câmera ao longo do checklist."""

    # ── Estados de pipeline (atribuídos pelo core, não pelo operador) ──
    PENDENTE = "PENDENTE"            # capturada, aguardando revisão visual
    NAO_ANALISADO = "NAO_ANALISADO"  # DVR offline → câmera nem foi tentada
    SEM_CONEXAO = "SEM_CONEXAO"      # captura falhou (timeout / sem stream)
    ERRO_IMAGEM = "ERRO_IMAGEM"      # arquivo existe mas não pôde ser carregado

    # ── Classificações do operador na revisão visual ──
    OK = "OK"
    EMBACADA_SUJA = "EMBAÇADA_SUJA"
    DISTORCIDA = "DISTORCIDA"
    TONALIDADE_CLARA_ESCURA = "TONALIDADE_CLARA_ESCURA"
    NAO_RECONHECIDA = "NAO_RECONHECIDA"
    NAO_INSTALADA = "NAO_INSTALADA"


# Mapa ordenado dígito→status, consumido pelos dois revisores (cv2 e Qt).
# Cada revisor traduz este dict para o seu tipo de tecla nativo.
STATUS_POR_DIGITO: dict[int, CameraStatus] = {
    1: CameraStatus.OK,
    2: CameraStatus.EMBACADA_SUJA,
    3: CameraStatus.DISTORCIDA,
    4: CameraStatus.TONALIDADE_CLARA_ESCURA,
    5: CameraStatus.NAO_RECONHECIDA,
    6: CameraStatus.NAO_INSTALADA,
}

# Descrição curta de cada classificação (para overlays/painéis de ajuda).
# Mantida curta para caber na sidebar estreita do diálogo Qt (~210px).
LABEL_POR_DIGITO: dict[int, str] = {
    1: "OK",
    2: "EMBAÇADA / SUJA",
    3: "DISTORCIDA",
    4: "TONALIDADE",
    5: "NÃO RECONHECIDA",
    6: "NÃO INSTALADA",
}
