from __future__ import annotations

from typing import List

import cv2

from src.domain.models import DVR

_STATUS_KEYS = {
    ord("1"): "OK",
    ord("2"): "EMBAÇADA_SUJA",
    ord("3"): "DISTORCIDA",
    ord("4"): "TONALIDADE_CLARA_ESCURA",
    ord("5"): "NAO_RECONHECIDA",
}


def analisar_visual(dvrs: List[DVR], error_img: str) -> List[DVR]:
    """
    Exibe cada câmera em tela cheia para classificação manual pelo operador.

    Teclas:
        1 → OK
        2 → EMBAÇADA_SUJA
        3 → DISTORCIDA
        4 → TONALIDADE_CLARA_ESCURA
        5 → NAO_RECONHECIDA
        Q → interrompe e mantém status atual das câmeras restantes

    Câmeras cujo imagem é error_img são ignoradas.
    """
    pendentes = [
        cam
        for dvr in dvrs
        for cam in dvr.cameras
        if cam.imagem != error_img
    ]

    print(f"\n👁 INICIANDO ANÁLISE VISUAL ({len(pendentes)} câmeras)")

    cv2.namedWindow("Analise", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Analise", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    for idx, cam in enumerate(pendentes, 1):
        img = cv2.imread(cam.imagem)
        if img is None:
            cam.status = "ERRO_IMAGEM"
            continue

        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (img.shape[1], 150), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        textos = [
            f"Câmera {idx}/{len(pendentes)}",
            "1 OK | 2 EMBAÇADA / SUJA",
            "3 DISTORCIDA",
            "4 TONALIDADE (MUITO CLARA ou ESCURA)",
            "5 NÃO RECONHECIDA",
            "Q sair",
        ]
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
