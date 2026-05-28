"""Ponto de entrada do CheckCam."""
import sys
from src.ui.app import run

if __name__ == "__main__":
    sys.exit(run("checkcam.db"))
