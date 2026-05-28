from __future__ import annotations

from typing import List

from src.domain.models import DVR


def load_dvrs(path: str) -> List[DVR]:
    """
    Lê o arquivo dvrs.txt e retorna a lista de DVRs configurados.

    Formato de cada linha: nome;ip;qtd_cameras
    Linhas em branco e comentários (#) são ignorados.
    """
    dvrs: List[DVR] = []
    with open(path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            nome, ip, cams = linha.split(";")
            dvrs.append(DVR(nome=nome, ip=ip, qtd_cameras=int(cams)))
    return dvrs


def load_emails(path: str) -> List[str]:
    """
    Lê o arquivo emails.txt e retorna a lista de destinatários.

    Linhas em branco e comentários (#) são ignorados.
    """
    emails: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            emails.append(linha)
    return emails
