"""
Serialização / desserialização de instalações para JSON.

Funções públicas:
  exportar(instalacoes)             → str (JSON)
  importar(json_str)                → List[Instalacao]
  restaurar_no_repo(instalacoes, repo) → (inseridos: int, pulados: int)

Constante:
  VERSAO_BACKUP = 1   — incrementar se o schema mudar de forma incompatível
"""
from __future__ import annotations

import json
from typing import List, Tuple

from src.domain.instalacao import Instalacao
from src.domain.models import DVR

VERSAO_BACKUP: int = 1


# ─── Exportar ─────────────────────────────────────────────────────────────────

def exportar(instalacoes: List[Instalacao]) -> str:
    """Serializa a lista de instalações para uma string JSON."""
    payload = {
        "version": VERSAO_BACKUP,
        "instalacoes": [_inst_para_dict(i) for i in instalacoes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _inst_para_dict(inst: Instalacao) -> dict:
    return {
        "nome":            inst.nome,
        "usuario":         inst.usuario,
        "senha":           inst.senha,
        "porta_http":      inst.porta_http,
        "porta_rtsp":      inst.porta_rtsp,
        "ffmpeg_path":     inst.ffmpeg_path,
        "playwright_path": inst.playwright_path,
        "base_dir":        inst.base_dir,
        "relatorios_dir":  inst.relatorios_dir,
        "logs_dir":        inst.logs_dir,
        "error_img":       inst.error_img,
        "dvrs": [
            {"nome": d.nome, "ip": d.ip, "qtd_cameras": d.qtd_cameras}
            for d in inst.dvrs
        ],
        "emails": list(inst.emails),
    }


# ─── Importar ─────────────────────────────────────────────────────────────────

def importar(json_str: str) -> List[Instalacao]:
    """
    Desserializa uma string JSON para lista de Instalacao.

    Raises:
        ValueError: se o JSON for inválido ou incompatível.
    """
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc}") from exc

    if "instalacoes" not in payload:
        raise ValueError("Backup inválido: chave 'instalacoes' ausente.")

    versao = payload.get("version", 0)
    if versao != VERSAO_BACKUP:
        raise ValueError(
            f"Versão do backup ({versao}) incompatível com esta versão do sistema ({VERSAO_BACKUP})."
        )

    return [_dict_para_inst(d) for d in payload["instalacoes"]]


def _dict_para_inst(d: dict) -> Instalacao:
    return Instalacao(
        id=0,
        nome=            d.get("nome", ""),
        usuario=         d.get("usuario", ""),
        senha=           d.get("senha", ""),
        porta_http=      d.get("porta_http", "3077"),
        porta_rtsp=      d.get("porta_rtsp", "3078"),
        ffmpeg_path=     d.get("ffmpeg_path", ""),
        playwright_path= d.get("playwright_path", ""),
        base_dir=        d.get("base_dir", ""),
        relatorios_dir=  d.get("relatorios_dir", ""),
        logs_dir=        d.get("logs_dir", ""),
        error_img=       d.get("error_img", ""),
        dvrs=[
            DVR(
                nome=        dv.get("nome", ""),
                ip=          dv.get("ip", ""),
                qtd_cameras= int(dv.get("qtd_cameras", 0)),
            )
            for dv in d.get("dvrs", [])
        ],
        emails=list(d.get("emails", [])),
    )


# ─── Restaurar no repositório ─────────────────────────────────────────────────

def restaurar_no_repo(
    instalacoes: List[Instalacao],
    repo,  # InstalacaoRepository — sem import circular
) -> Tuple[int, int]:
    """
    Insere cada instalação no repo se o nome ainda não existir.

    Returns:
        (inseridos, pulados)
    """
    existentes = {i.nome for i in repo.listar()}
    inseridos = pulados = 0

    for inst in instalacoes:
        if inst.nome in existentes:
            pulados += 1
        else:
            inst.id = 0          # garante INSERT
            repo.salvar(inst)
            existentes.add(inst.nome)
            inseridos += 1

    return inseridos, pulados
