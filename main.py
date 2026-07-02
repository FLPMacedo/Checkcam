"""Ponto de entrada do CheckCam.

EXE único, dois modos:
  CheckCam.exe               -> abre o gerenciador de instalações (checklist)
  CheckCam.exe --dashboard   -> abre o dashboard (janela nativa)

O modo --dashboard permite que o botão "Abrir Dashboard" re-execute o próprio
executável empacotado, sem depender de Python instalado na máquina.
"""
import sys


def _run_checklist() -> int:
    from src.ui.app import run
    return run("checkcam.db")


def _run_dashboard() -> None:
    from dashboard.desktop import main as dashboard_main
    dashboard_main()


def main(argv=None) -> int:
    argv = sys.argv if argv is None else argv
    if "--dashboard" in argv:
        _run_dashboard()
        return 0
    return _run_checklist()


if __name__ == "__main__":
    sys.exit(main())
