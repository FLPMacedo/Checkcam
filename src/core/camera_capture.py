from __future__ import annotations

import os
import subprocess
from typing import Callable, List, Optional

from src.core.rtsp import rtsp_url, rtsp_url_com_chave_criptografia
from src.domain.device import TipoDispositivo
from src.domain.models import Camera, DVR
from src.domain.status import CameraStatus
from src.infra.app_config import AppConfig

# Tamanho mínimo em bytes para considerar um capture válido.
# Frames falhados normalmente saem com cabeçalho mínimo (< 10 KB).
_TAMANHO_MIN_FRAME = 10000


def capturar_cameras(
    dvrs: List[DVR],
    config: AppConfig,
    on_log: Optional[Callable[[str], None]] = None,
) -> List[DVR]:
    """
    Captura um frame de cada câmera via FFmpeg/RTSP.

    DVRs offline recebem câmeras com ERROR_IMG e status "NAO_ANALISADO".
    Câmeras cuja captura falha recebem ERROR_IMG e status "SEM_CONEXAO".
    Câmeras capturadas com sucesso ficam com status "PENDENTE" (aguardam revisão visual).

    on_log: callback chamado para cada linha de saída.
            Se None, usa print() (comportamento legado).
    """
    _log = on_log or print

    if not config.base_dir:
        raise ValueError(
            "config.base_dir está vazio. "
            "Edite a instalação na UI e preencha 'Dir. câmeras (base)'. "
            "Sem isso, as imagens das câmeras seriam salvas no diretório "
            "atual em vez do projeto."
        )

    _log("\n🎥 CAPTURANDO IMAGENS DAS CÂMERAS")

    for dvr in dvrs:
        _log(f"\n📡 DVR: {dvr.nome}")

        # Câmera IP = 1 stream (canal único); DVR/NVR = N canais.
        n_canais = 1 if dvr.tipo == TipoDispositivo.CAMERA_IP else dvr.qtd_cameras

        if dvr.hd.status.startswith("OFFLINE"):
            _log("   ⛔ DVR OFFLINE – câmeras ignoradas")
            for i in range(1, n_canais + 1):
                dvr.cameras.append(
                    Camera(
                        nome=f"C{i}",
                        imagem=config.error_img,
                        status=CameraStatus.NAO_ANALISADO,
                        dvr_nome=dvr.nome,
                    )
                )
            continue

        pasta = os.path.join(config.base_dir, dvr.nome.replace(" ", "_"))
        os.makedirs(pasta, exist_ok=True)

        for i in range(1, n_canais + 1):
            cam_nome = f"C{i}"
            img_path = os.path.join(pasta, f"{cam_nome}.jpg")

            # 1ª tentativa: senha normal (override do DVR ou da instalação)
            sucesso, timeout = _tentar_capturar(
                rtsp_url(dvr, i, config), img_path, config.ffmpeg_path
            )

            # 2ª tentativa (se houver chave): repete com chave_criptografia
            # no lugar da senha — caso comum em Hikvision com 'verification
            # code' ativado.
            if not sucesso and not timeout and dvr.chave_criptografia:
                _log(f"   🔑 {cam_nome} ... tentando com chave de criptografia")
                sucesso, timeout = _tentar_capturar(
                    rtsp_url_com_chave_criptografia(dvr, i, config),
                    img_path,
                    config.ffmpeg_path,
                )

            if sucesso:
                dvr.cameras.append(
                    Camera(
                        nome=cam_nome,
                        imagem=img_path,
                        status=CameraStatus.PENDENTE,
                        dvr_nome=dvr.nome,
                    )
                )
                _log(f"   🎥 {cam_nome} ... OK")
            else:
                dvr.cameras.append(
                    Camera(
                        nome=cam_nome,
                        imagem=config.error_img,
                        status=CameraStatus.SEM_CONEXAO,
                        dvr_nome=dvr.nome,
                    )
                )
                _log(f"   🎥 {cam_nome} ... {'TIMEOUT' if timeout else 'SEM CONEXÃO'}")

    return dvrs


def _tentar_capturar(rtsp: str, img_path: str, ffmpeg_path: str) -> tuple[bool, bool]:
    """Tenta capturar um frame via ffmpeg.

    Retorna ``(sucesso, timeout)``:
      - sucesso=True se o arquivo existe e tem ≥ _TAMANHO_MIN_FRAME bytes
      - timeout=True se o subprocess.run estourou (não vale a pena retry)
    """
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-rtsp_transport", "tcp",
                "-i", rtsp,
                "-frames:v", "1",
                img_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        sucesso = (
            os.path.exists(img_path)
            and os.path.getsize(img_path) > _TAMANHO_MIN_FRAME
        )
        return sucesso, False
    except subprocess.TimeoutExpired:
        return False, True
