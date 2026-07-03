"""Confere e (opcionalmente) corrige o horário/NTP dos DVRs de uma instalação.

Uso:
  python scripts/sincronizar_horario.py <instalacao_id>            # só confere
  python scripts/sincronizar_horario.py <instalacao_id> --aplicar  # corrige (escreve)

Sem --aplicar é seguro: apenas lê e relata a hora/NTP de cada DVR. Com
--aplicar, aponta o NTP (time1.google.com), fuso UTC-3 e força a sincronização
nos DVRs Hikvision.
"""
import os
import sys

# Console do Windows (cp1252) não engole os emojis dos logs — força UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.dvr_ntp import NTP_PADRAO, sincronizar_dvrs
from src.infra.instalacao_repo import InstalacaoRepository

DB = "checkcam.db"


def _opcao(prefixo: str, default: str) -> str:
    for a in sys.argv[1:]:
        if a.startswith(prefixo):
            return a.split("=", 1)[1]
    return default


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    aplicar = "--aplicar" in sys.argv
    servidor = _opcao("--servidor=", NTP_PADRAO)
    if not args:
        print("uso: python scripts/sincronizar_horario.py <instalacao_id> "
              "[--aplicar] [--servidor=host]")
        return 2

    inst = InstalacaoRepository(DB).obter(int(args[0]))
    modo = "CORRIGIR (escreve nos DVRs)" if aplicar else "CONFERIR (só leitura)"
    print(f"Instalação: {inst.nome}  |  {len(inst.dvrs)} DVRs  |  modo: {modo}"
          + (f"  |  NTP: {servidor}" if aplicar else ""))

    resultados = sincronizar_dvrs(inst.dvrs, inst.to_app_config(),
                                  aplicar=aplicar, host=servidor)

    ok = sum(1 for r in resultados if r.ok)
    print(f"\nResumo: {ok}/{len(resultados)} OK")
    for r in resultados:
        marca = "✅" if r.ok else "⚠️"
        hora = r.status_antes.local_time if r.status_antes else "-"
        print(f"  {marca} {r.dvr_nome:16} {r.ip:14} {hora:28} {r.mensagem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
