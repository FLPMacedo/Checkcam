"""
Popula checkcam.db com as 4 instalações lidas dos arquivos legados.

Execute UMA vez a partir da raiz do projeto:
    cd C:\\Temp\\_Projeto_Relatorio_DVRS_\\CheckCam
    python scripts/seed_db.py
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.domain.instalacao import Instalacao
from src.domain.models import DVR
from src.infra.instalacao_repo import InstalacaoRepository

DB_PATH = os.path.join(ROOT, "checkcam.db")

# ─── Caminhos dos assets (compartilhados por todas as instalações) ─────────────

ASSETS        = os.path.join(ROOT, "assets")
FFMPEG_EXE    = os.path.join(ASSETS, "ffmpeg", "bin", "ffmpeg.exe")
PLAYWRIGHT    = os.path.join(ASSETS, "playwright_browsers")
ERROR_IMG     = os.path.join(ASSETS, "error.jpg")


def _data(slug: str, subdir: str) -> str:
    """Retorna caminho absoluto para um subdiretório de dados de uma instalação."""
    return os.path.join(ROOT, "data", slug, subdir)


def _relatorios(slug: str) -> str:
    """Pasta de relatórios fica direto na raiz do CheckCam, por instalação."""
    return os.path.join(ROOT, "relatorios", slug)


# ─── Dados migrados dos arquivos legados ──────────────────────────────────────

INSTALACOES = [
    Instalacao(
        nome="101 - Ponte Nova",
        usuario="",          # preencher na UI
        senha="",            # preencher na UI
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path=FFMPEG_EXE,
        playwright_path=PLAYWRIGHT,
        base_dir=_data("101_Ponte_Nova", "temp"),
        relatorios_dir=_relatorios("101_Ponte_Nova"),
        logs_dir=_data("101_Ponte_Nova", "logs"),
        error_img=ERROR_IMG,
        dvrs=[
            DVR("PN ADM1",         "10.0.0.210", 16),
            DVR("PN ADM2",         "10.0.0.211", 16),
            DVR("PN ADM3",         "10.0.0.222", 16),
            DVR("PN ALMOXARIFADO", "10.0.0.212", 18),
            DVR("PN ARMARIOS",     "10.0.0.213",  3),
            DVR("PN FATIADOS",     "10.0.0.219", 16),
            DVR("PN MANUTENCAO",   "10.0.0.223", 16),
            DVR("PN QUALIDADE",    "10.0.0.216", 16),
            DVR("PN QUEIJO1",      "10.0.0.217", 16),
            DVR("PN QUEIJO2",      "10.0.0.218", 16),
            DVR("PN SORO1",        "10.0.0.214",  8),
            DVR("PN SORO2",        "10.0.0.215", 16),
            DVR("PN UHT1",         "10.0.0.220",  8),
            DVR("PN UHT2",         "10.0.0.221", 16),
            DVR("PN UHT3",         "10.0.0.224", 16),
            DVR("PN UHT4",         "10.0.0.225",  8),
        ],
        emails=[
            "filipe.macedo@laticiniosportoalegre.com.br",
            "rangel.goncalves@laticiniosportoalegre.com.br",
            "michele.oliveira@laticiniosportoalegre.com.br",
            "caio.silva@laticiniosportoalegre.com.br",
            "marcos.xavier@laticiniosportoalegre.com.br",
            "eduardo.vale@laticiniosportoalegre.com.br",
        ],
    ),
    Instalacao(
        nome="102 - Mutum",
        usuario="",
        senha="",
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path=FFMPEG_EXE,
        playwright_path=PLAYWRIGHT,
        base_dir=_data("102_Mutum", "temp"),
        relatorios_dir=_relatorios("102_Mutum"),
        logs_dir=_data("102_Mutum", "logs"),
        error_img=ERROR_IMG,
        # ⚠ dvrs.txt do 102 usa os mesmos IPs do 101 (PN *).
        # ALMOXARIFADO tem 16 câmeras aqui (vs 18 no 101).
        # Confirme se os DVRs de Mutum estão corretos.
        dvrs=[
            DVR("PN ADM1",         "10.0.0.210", 16),
            DVR("PN ADM2",         "10.0.0.211", 16),
            DVR("PN ADM3",         "10.0.0.222", 16),
            DVR("PN ALMOXARIFADO", "10.0.0.212", 16),
            DVR("PN ARMARIOS",     "10.0.0.213",  3),
            DVR("PN FATIADOS",     "10.0.0.219", 16),
            DVR("PN MANUTENCAO",   "10.0.0.223", 16),
            DVR("PN QUALIDADE",    "10.0.0.216", 16),
            DVR("PN QUEIJO1",      "10.0.0.217", 16),
            DVR("PN QUEIJO2",      "10.0.0.218", 16),
            DVR("PN SORO1",        "10.0.0.214",  8),
            DVR("PN SORO2",        "10.0.0.215", 16),
            DVR("PN UHT1",         "10.0.0.220",  8),
            DVR("PN UHT2",         "10.0.0.221", 16),
            DVR("PN UHT3",         "10.0.0.224", 16),
            DVR("PN UHT4",         "10.0.0.225",  8),
        ],
        emails=[
            "filipe.macedo@laticiniosportoalegre.com.br",
            "rangel.goncalves@laticiniosportoalegre.com.br",
        ],
    ),
    Instalacao(
        nome="103 - CD Contagem",
        usuario="",
        senha="",
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path=FFMPEG_EXE,
        playwright_path=PLAYWRIGHT,
        base_dir=_data("103_CD_Contagem", "temp"),
        relatorios_dir=_relatorios("103_CD_Contagem"),
        logs_dir=_data("103_CD_Contagem", "logs"),
        error_img=ERROR_IMG,
        dvrs=[
            DVR("CD CONTAGEM 1", "192.168.20.220", 16),
            DVR("CD CONTAGEM 2", "192.168.20.221", 16),
            DVR("CD CONTAGEM 3", "192.168.20.222", 16),
        ],
        emails=[
            "filipe.macedo@laticiniosportoalegre.com.br",
            "rangel.goncalves@laticiniosportoalegre.com.br",
        ],
    ),
    Instalacao(
        nome="107 - Antonio Carlos",
        usuario="",
        senha="",
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path=FFMPEG_EXE,
        playwright_path=PLAYWRIGHT,
        base_dir=_data("107_Antonio_Carlos", "temp"),
        relatorios_dir=_relatorios("107_Antonio_Carlos"),
        logs_dir=_data("107_Antonio_Carlos", "logs"),
        error_img=ERROR_IMG,
        # ⚠ dvrs.txt do 107 tem conteúdo idêntico ao 103 (CD CONTAGEM).
        # Confirme se os DVRs de Antonio Carlos estão corretos.
        dvrs=[
            DVR("CD CONTAGEM 1", "192.168.20.220", 16),
            DVR("CD CONTAGEM 2", "192.168.20.221", 16),
            DVR("CD CONTAGEM 3", "192.168.20.222", 16),
        ],
        emails=[
            "filipe.macedo@laticiniosportoalegre.com.br",
            "rangel.goncalves@laticiniosportoalegre.com.br",
        ],
    ),
]


# ─── Inserção ─────────────────────────────────────────────────────────────────

def main() -> None:
    repo = InstalacaoRepository(DB_PATH)
    existentes = {i.nome for i in repo.listar()}

    inseridos = 0
    pulados   = 0

    for inst in INSTALACOES:
        if inst.nome in existentes:
            print(f"  [PULADO]  Ja existe : {inst.nome}")
            pulados += 1
        else:
            saved = repo.salvar(inst)
            total_cam = sum(d.qtd_cameras for d in inst.dvrs)
            print(
                f"  [OK] Inserido  : {inst.nome}"
                f"  ({len(inst.dvrs)} DVRs | {total_cam} cameras | {len(inst.emails)} e-mails)"
            )
            inseridos += 1

    print(f"\n{'-'*60}")
    print(f"  {inseridos} inseridas, {pulados} ja existiam.")
    print(f"  Banco       : {DB_PATH}")
    print(f"  FFmpeg      : {FFMPEG_EXE}")
    print(f"  Playwright  : {PLAYWRIGHT}")
    print(f"  Error img   : {ERROR_IMG}")
    print(f"{'-'*60}")
    print("\n  [ATENCAO] Preencha usuario e senha de cada instalacao pela UI.")
    print("  [ATENCAO] Confirme os DVRs das instalacoes 102 e 107 (veja comentarios no script).")


if __name__ == "__main__":
    main()
