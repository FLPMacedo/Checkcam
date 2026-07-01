"""
Marca e tipo de dispositivo — definem qual estratégia de captura (RTSP) e de
análise de HD será usada para cada equipamento.

Antes só existia o caso Hikvision/DVR (hardcoded em core/). Com a chegada dos
equipamentos Intelbras (Dahua-OEM) e a captura direta de câmeras IP, cada
dispositivo passa a declarar marca × tipo, e o core despacha a estratégia certa.

Como ``StrEnum``, ``Marca.HIKVISION == "hikvision"`` é ``True`` — compatível com
valores em texto vindos do banco e dos backups JSON.
"""
from __future__ import annotations

from enum import StrEnum


class Marca(StrEnum):
    """Fabricante do equipamento (define o esquema de RTSP e a leitura de HD)."""

    HIKVISION = "hikvision"
    INTELBRAS = "intelbras"


class TipoDispositivo(StrEnum):
    """Como o dispositivo é acessado para captura."""

    DVR = "dvr"              # 1 IP, N canais (DVR/NVR)
    CAMERA_IP = "camera_ip"  # 1 IP = 1 câmera, canal único
