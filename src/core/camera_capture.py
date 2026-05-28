from __future__ import annotations

import os
import subprocess
from typing import Callable, List, Optional

from src.domain.models import Camera, DVR
from src.infra.app_config import AppConfig


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

    _log("\n🎥 CAPTURANDO IMAGENS DAS CÂMERAS")

    for dvr in dvrs:
        _log(f"\n📡 DVR: {dvr.nome}")

        if dvr.hd.status.startswith("OFFLINE"):
            _log("   ⛔ DVR OFFLINE – câmeras ignoradas")
            for i in range(1, dvr.qtd_cameras + 1):
                dvr.cameras.append(
                    Camera(nome=f"C{i}", imagem=config.error_img, status="NAO_ANALISADO")
                )
            continue

        pasta = os.path.join(config.base_dir, dvr.nome.replace(" ", "_"))
        os.makedirs(pasta, exist_ok=True)

        for i in range(1, dvr.qtd_cameras + 1):
            cam_nome = f"C{i}"
            img_path = os.path.join(pasta, f"{cam_nome}.jpg")
            rtsp = (
                f"rtsp://{config.usuario}:{config.senha_rtsp}"
                f"@{dvr.ip}:{config.porta_rtsp}/Streaming/Channels/{i}01"
            )

            try:
                subprocess.run(
                    [
                        config.ffmpeg_path,
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

                if os.path.exists(img_path) and os.path.getsize(img_path) > 10000:
                    dvr.cameras.append(Camera(nome=cam_nome, imagem=img_path, status="PENDENTE"))
                    _log(f"   🎥 {cam_nome} ... OK")
                else:
                    dvr.cameras.append(
                        Camera(nome=cam_nome, imagem=config.error_img, status="SEM_CONEXAO")
                    )
                    _log(f"   🎥 {cam_nome} ... SEM CONEXÃO")

            except subprocess.TimeoutExpired:
                dvr.cameras.append(
                    Camera(nome=cam_nome, imagem=config.error_img, status="SEM_CONEXAO")
                )
                _log(f"   🎥 {cam_nome} ... TIMEOUT")

    return dvrs
