# CheckCam

Sistema de checklist visual de DVRs/NVRs e câmeras IP para laticínios (Porto
Alegre). Verifica HD, captura frames RTSP, permite classificação visual manual,
gera relatório PDF + book PDF e envia por e-mail.

Refatoração completa do legado `DVR_exe3.py` (Tkinter + globais + print no CMD)
para PySide6 com arquitetura em camadas.

- **GitHub:** https://github.com/FLPMacedo/Checkcam
- **Versão atual:** v1.2 (dashboard web-in-window)
- **Testes:** 324/324 verdes

## Como rodar

```powershell
cd C:\Temp\_Projeto_Relatorio_DVRS_\CheckCam
python main.py
```

Primeira vez: rodar `python scripts/seed_db.py` para popular as instalações
padrão da produção. Depois disso, usar a UI (HomeWindow) para gerenciar.

## Dashboard

Painel de status por instalação (cards verde/amarelo/vermelho conforme o
último checklist) com drill-down de DVRs/câmeras e gráfico de trend histórico.
Cada checklist executado grava um snapshot no banco, que alimenta o dashboard.

Como abrir:

- **Pela UI:** botão **"📊 Abrir Dashboard"** na tela inicial, no cabeçalho da
  janela de checklist e no popup de conclusão.
- **Linha de comando (dev):**
  ```powershell
  python -m dashboard.desktop          # janela nativa (pywebview)
  flask --app dashboard.app run        # no navegador, para depurar
  ```

O banco vem de `CHECKCAM_DB` (variável de ambiente) ou de `checkcam.db` no
diretório atual — o mesmo arquivo do CheckCam.

## Build do executável

```powershell
.\build_exe.ps1        # gera dist\CheckCam.exe (EXE único: checklist + dashboard)
```

O `CheckCam.exe` roda o checklist por padrão e o dashboard com
`CheckCam.exe --dashboard` (é assim que o botão abre o painel quando empacotado).
`ffmpeg` e os browsers do Playwright **não** são embutidos — distribuir em
`assets/` ao lado do EXE.

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
├── main.py                    (entrypoint: checklist ou --dashboard)
├── CheckCam.spec              (PyInstaller — EXE único)
├── build_exe.ps1             (script de build)
├── checkcam.db                (SQLite — populado por scripts/seed_db.py)
├── requirements-dev.txt
├── pytest.ini
├── dashboard/                 (Flask + pywebview: overview, drill-down, trend)
│   ├── app.py routes.py views.py desktop.py ver.py
│   ├── templates/  (base, overview, instalacao)
│   └── static/     (style.css, charts.js)
├── src/
│   ├── domain/    (DVR, Camera, Instalacao, Snapshot, enums)
│   ├── core/      (ping, hd_analyzer, camera_capture, rtsp, intelbras_cgi)
│   ├── services/  (ChecklistService — pipeline completo)
│   ├── reports/   (excel_builder, book_builder, pdf_exporter, email_sender)
│   ├── infra/     (database, instalacao_repo, snapshot_repo, backup, app_config)
│   └── ui/        (HomeWindow, MainWindow, dashboard_launcher, dialogs)
├── scripts/       (seed_db, migrar_relatorios, etc)
├── tests/         (unit + characterization + fakes/)
├── assets/        (error.jpg, ffmpeg/, playwright_browsers/ — gitignored)
├── data/          (frames capturados, logs de e-mail — gitignored)
└── relatorios/    (PDFs gerados — gitignored)
```
