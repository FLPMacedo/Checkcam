from __future__ import annotations

from typing import List

import cv2

from src.domain.models import DVR, cameras_para_revisar, todas_as_cameras
from src.domain.status import CameraStatus, LABEL_POR_DIGITO, STATUS_POR_DIGITO

# Derivado da fonte única (domain.status): tecla ASCII do dígito → status.
_STATUS_KEYS = {
    ord(str(digito)): status for digito, status in STATUS_POR_DIGITO.items()
}


def analisar_visual(dvrs: List[DVR], error_img: str) -> List[DVR]:
    """
    Exibe cada câmera em tela cheia para classificação manual pelo operador.

    Teclas (mapeadas a partir de domain.status.STATUS_POR_DIGITO):
        1 → OK
        2 → EMBAÇADA_SUJA
        3 → DISTORCIDA
        4 → TONALIDADE_CLARA_ESCURA
        5 → NAO_RECONHECIDA
        6 → NAO_INSTALADA
        Q → interrompe e mantém status atual das câmeras restantes

    Câmeras cujo imagem é error_img são ignoradas.
    """
    pendentes = cameras_para_revisar(todas_as_cameras(dvrs), error_img)

    print(f"\n👁 INICIANDO ANÁLISE VISUAL ({len(pendentes)} câmeras)")

    cv2.namedWindow("Analise", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Analise", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    for idx, cam in enumerate(pendentes, 1):
        img = cv2.imread(cam.imagem)
        if img is None:
            cam.status = CameraStatus.ERRO_IMAGEM
            continue

        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (img.shape[1], 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        textos = [f"Câmera {idx}/{len(pendentes)}"]
        textos += [f"{d} {label}" for d, label in LABEL_POR_DIGITO.items()]
        textos.append("Q sair")
        y = 30
        for t in textos:
            cv2.putText(img, t, (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            y += 28

        cv2.imshow("Analise", img)
        while True:
            key = cv2.waitKey(1)
            if key != -1:
                break

        if key == ord("q"):
            break

        cam.status = _STATUS_KEYS.get(key, cam.status)

    cv2.destroyAllWindows()
    return dvrs
