"""
Migra a pasta de relatórios das instalações:
  De:   <CheckCam>/data/<slug>/relatorios/
  Para: <CheckCam>/relatorios/<slug>/

Ações:
  1. UPDATE em instalacoes.relatorios_dir no banco
  2. Cria as novas pastas
  3. Move arquivos existentes (xlsx, pdf, qualquer outro) para o novo destino
  4. Remove a pasta antiga se ficar vazia

Idempotente: pode ser rodado várias vezes sem efeito colateral.

Uso (raiz do projeto):
    python scripts/migrar_relatorios.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(ROOT, "checkcam.db")
NOVA_BASE = os.path.join(ROOT, "relatorios")


def _slug_de(caminho_antigo: str) -> str:
    """Extrai o slug a partir de '<root>/data/<slug>/relatorios'."""
    # normaliza e divide
    norm = os.path.normpath(caminho_antigo)
    partes = norm.split(os.sep)
    # procura por 'data' e devolve o componente seguinte
    if "data" in partes:
        idx = partes.index("data")
        if idx + 1 < len(partes):
            return partes[idx + 1]
    # fallback: usa o nome do diretório pai do "relatorios"
    return os.path.basename(os.path.dirname(norm))


def main() -> int:
    if not os.path.exists(DB_PATH):
        print(f"[ERRO] Banco não encontrado: {DB_PATH}")
        return 1

    os.makedirs(NOVA_BASE, exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        "SELECT id, nome, relatorios_dir FROM instalacoes ORDER BY id"
    ).fetchall()

    if not rows:
        print("[AVISO] Nenhuma instalação cadastrada.")
        return 0

    print(f"{'='*70}")
    print(f"  Migrando relatorios_dir para: {NOVA_BASE}\\<slug>")
    print(f"{'='*70}")

    atualizados = 0
    movidos_total = 0

    for row in rows:
        inst_id = row["id"]
        nome = row["nome"]
        antigo = row["relatorios_dir"] or ""

        slug = _slug_de(antigo) if antigo else nome.replace(" ", "_").replace("-", "")
        novo = os.path.join(NOVA_BASE, slug)

        # Pula se já está no novo formato
        if os.path.normpath(antigo) == os.path.normpath(novo):
            print(f"  [OK]      {nome:30s} ja esta no novo formato")
            continue

        os.makedirs(novo, exist_ok=True)

        # Move arquivos da pasta antiga, se existir
        movidos = 0
        if antigo and os.path.isdir(antigo):
            for arquivo in os.listdir(antigo):
                origem = os.path.join(antigo, arquivo)
                destino = os.path.join(novo, arquivo)
                if os.path.isfile(origem):
                    if os.path.exists(destino):
                        print(f"            ja existe no destino, pulando: {arquivo}")
                    else:
                        shutil.move(origem, destino)
                        movidos += 1

            # Remove a pasta antiga se ficou vazia
            try:
                if not os.listdir(antigo):
                    os.rmdir(antigo)
            except OSError:
                pass

        # Atualiza o banco
        con.execute(
            "UPDATE instalacoes SET relatorios_dir=? WHERE id=?",
            (novo, inst_id),
        )
        atualizados += 1
        movidos_total += movidos

        print(f"  [MIGRADO] {nome:30s} {movidos} arquivo(s) movido(s)")
        print(f"            antigo : {antigo}")
        print(f"            novo   : {novo}")

    con.commit()
    con.close()

    print(f"{'='*70}")
    print(f"  {atualizados} instalacao(oes) atualizada(s), {movidos_total} arquivo(s) movido(s).")
    print(f"  Novo destino: {NOVA_BASE}")
    print(f"{'='*70}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
