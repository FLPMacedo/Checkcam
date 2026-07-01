# CheckCam

Sistema de checklist visual de DVRs/NVRs e câmeras IP para laticínios (Porto
Alegre). Verifica HD, captura frames RTSP, permite classificação visual manual,
gera relatório PDF + book PDF e envia por e-mail.

Refatoração completa do legado `DVR_exe3.py` (Tkinter + globais + print no CMD)
para PySide6 com arquitetura em camadas.

- **GitHub:** https://github.com/FLPMacedo/Checkcam
- **Versão atual:** v1.1 (commit `468beb6`)
- **Testes:** 278/278 verdes

## Como rodar

```powershell
cd C:\Temp\_Projeto_Relatorio_DVRS_\CheckCam
python main.py
```

Primeira vez: rodar `python scripts/seed_db.py` para popular as instalações
padrão da produção. Depois disso, usar a UI (HomeWindow) para gerenciar.

## Rodar testes

```powershell
python -m pytest -q           # suite completa (~20s)
python -m pytest tests/unit/test_X.py -v   # arquivo específico
```

## Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — camadas, módulos, decisões
- [docs/CONVENCOES.md](docs/CONVENCOES.md) — TDD, ciclo de commit, path defaults
- [docs/HISTORICO.md](docs/HISTORICO.md) — o que já foi feito
- [docs/PROXIMOS_PASSOS.md](docs/PROXIMOS_PASSOS.md) — próximas features + prompt para sessão nova

## Estrutura mínima

```
CheckCam/
├── main.py                    (entrypoint PySide6)
├── checkcam.db                (SQLite — populado por scripts/seed_db.py)
├── requirements-dev.txt
├── pytest.ini
├── src/
│   ├── domain/    (DVR, Camera, Instalacao, enums)
│   ├── core/      (ping, hd_analyzer, camera_capture, rtsp, intelbras_cgi)
│   ├── services/  (ChecklistService — pipeline completo)
│   ├── reports/   (excel_builder, book_builder, pdf_exporter, email_sender)
│   ├── infra/     (database, instalacao_repo, backup, app_config, path_defaults)
│   └── ui/        (HomeWindow, MainWindow, InstalacaoFormDialog, dialogs)
├── scripts/       (seed_db, migrar_relatorios, etc)
├── tests/         (unit + characterization + fakes/)
├── assets/        (error.jpg, ffmpeg/, playwright_browsers/ — gitignored)
├── data/          (frames capturados, logs de e-mail — gitignored)
└── relatorios/    (PDFs gerados — gitignored)
```
