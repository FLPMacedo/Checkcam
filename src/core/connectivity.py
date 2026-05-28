from __future__ import annotations

import subprocess


def ping(ip: str) -> bool:
    """Retorna True se o host responde ao ping, False caso contrário."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False
