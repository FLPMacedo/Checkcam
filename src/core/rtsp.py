"""
Construção da URL RTSP por marca × tipo de dispositivo.

Cada dispositivo (DVR) pode sobrescrever credenciais e portas; quando o
override está vazio, herda da instalação (AppConfig). A porta RTSP, quando
não informada, cai no default da marca (Intelbras → 554; Hikvision → a porta
RTSP da instalação).

Esquemas suportados:
  - Hikvision : rtsp://user:senha@ip:porta/Streaming/Channels/{canal}01
  - Intelbras : rtsp://user:senha@ip:porta/cam/realmonitor?channel={canal}&subtype=0
                (Dahua-OEM; vale para NVR/DVR e câmera IP)

Para tipo ``camera_ip`` o canal é sempre 1 (1 IP = 1 câmera).
"""
from __future__ import annotations

from urllib.parse import quote

from src.domain.device import Marca, TipoDispositivo
from src.domain.models import DVR
from src.infra.app_config import AppConfig

# Stream principal (melhor qualidade) para a revisão visual.
_SUBTYPE_PRINCIPAL = 0

# Porta RTSP padrão da Intelbras/Dahua quando não há override.
_PORTA_RTSP_INTELBRAS_PADRAO = "554"


def resolver_usuario(device: DVR, config: AppConfig) -> str:
    """Credencial efetiva: override do dispositivo ou o da instalação."""
    return device.usuario or config.usuario


def resolver_senha(device: DVR, config: AppConfig) -> str:
    return device.senha or config.senha


def resolver_porta_rtsp(device: DVR, config: AppConfig) -> str:
    """Porta RTSP efetiva: override do dispositivo, senão default da marca."""
    if device.porta_rtsp:
        return device.porta_rtsp
    if device.marca == Marca.INTELBRAS:
        return _PORTA_RTSP_INTELBRAS_PADRAO
    return config.porta_rtsp


def resolver_porta_http(device: DVR, config: AppConfig) -> str:
    """Porta HTTP efetiva: override do dispositivo ou a da instalação."""
    return device.porta_http or config.porta_http


def rtsp_url(device: DVR, canal: int, config: AppConfig) -> str:
    """Monta a URL RTSP para um canal do dispositivo (usando a senha normal).

    ``canal`` é o índice 1-based da câmera no DVR; para câmera IP é sempre 1.
    """
    senha = resolver_senha(device, config)
    return _montar_url(device, canal, config, senha)


def rtsp_url_com_chave_criptografia(device: DVR, canal: int, config: AppConfig) -> str:
    """Mesma URL, mas usando ``device.chave_criptografia`` no lugar da senha.

    Hikvision com 'verification code' ativado exige a chave (não a senha do
    admin) para abrir o stream RTSP. O camera_capture chama esta versão como
    retry quando a tentativa com a senha normal falha.

    Lança ``ValueError`` se o dispositivo não tem chave configurada.
    """
    if not device.chave_criptografia:
        raise ValueError(
            f"DVR {device.nome!r} não tem chave_criptografia configurada"
        )
    return _montar_url(device, canal, config, device.chave_criptografia)


def _montar_url(device: DVR, canal: int, config: AppConfig, senha: str) -> str:
    """Internal: monta a URL RTSP com a senha fornecida (usado pelo retry)."""
    usuario = resolver_usuario(device, config)
    # safe="" encoda também '/' e ':' — usuários colocam chaves Hikvision
    # com caracteres especiais (ex.: 'a@b/c') que quebrariam a URL.
    senha_encoded = quote(senha, safe="")
    porta = resolver_porta_rtsp(device, config)
    base = f"rtsp://{usuario}:{senha_encoded}@{device.ip}:{porta}"

    if device.marca == Marca.INTELBRAS:
        canal_efetivo = 1 if device.tipo == TipoDispositivo.CAMERA_IP else canal
        return (
            f"{base}/cam/realmonitor"
            f"?channel={canal_efetivo}&subtype={_SUBTYPE_PRINCIPAL}"
        )

    # Hikvision (default). Câmera IP Hikvision = canal 1 → "101".
    canal_efetivo = 1 if device.tipo == TipoDispositivo.CAMERA_IP else canal
    return f"{base}/Streaming/Channels/{canal_efetivo}01"
