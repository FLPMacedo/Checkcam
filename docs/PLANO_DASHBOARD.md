# Plano — Dashboard CheckCam

Planejamento por fases para o dashboard Flask + pywebview.
Cada fase tem tasks marcáveis, critério de sucesso e commit ao final.
Ordem: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8. Só avança quando o critério da
fase anterior fecha.

> **Estimativa total:** 6-10 horas de trabalho efetivo, distribuídas em
> ~2 sessões. Cada fase = 30min a 1h.

---

## Fase 0 — Setup e leitura de contexto (30min)

**Objetivo:** entender o que já existe sem reler o repo inteiro.

- [ ] Ler `docs/ARQUITETURA.md` (5min)
- [ ] Ler `docs/CONVENCOES.md` (5min)
- [ ] Ler `src/domain/instalacao.py`, `src/domain/models.py` (10min)
- [ ] Ler `src/services/checklist_service.py` (só onde o pipeline termina) (5min)
- [ ] Ler `src/infra/database.py` (schema + migração) (5min)
- [ ] Ler `C:\Temp\_Projeto_Gerenciamento_MAC_Unifi\desktop.py` (5min)
- [ ] Escolher stack final: **Flask 3 + Jinja2 + Chart.js CDN + pywebview**

**Critério:** consegue explicar em 2 frases onde salvar o snapshot e onde
disparar o dashboard.

**Commit:** nenhum (só leitura).

---

## Fase 1 — Persistência de snapshots (1-1.5h)

**Objetivo:** capacidade de gravar/ler o estado de um checklist no banco.

### Design das tabelas

```sql
CREATE TABLE snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instalacao_id   INTEGER NOT NULL REFERENCES instalacoes(id) ON DELETE CASCADE,
    executado_em    TEXT    NOT NULL,        -- ISO 8601
    total_dvrs      INTEGER NOT NULL DEFAULT 0,
    total_cameras   INTEGER NOT NULL DEFAULT 0,
    cameras_ok      INTEGER NOT NULL DEFAULT 0,
    cameras_alerta  INTEGER NOT NULL DEFAULT 0,
    cameras_sem_conexao INTEGER NOT NULL DEFAULT 0,
    cameras_nao_instaladas INTEGER NOT NULL DEFAULT 0,
    dvrs_hd_erro    INTEGER NOT NULL DEFAULT 0,
    dvrs_offline    INTEGER NOT NULL DEFAULT 0,
    excel_path      TEXT    NOT NULL DEFAULT '',
    pdf_path        TEXT    NOT NULL DEFAULT '',
    book_path       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE snapshot_dvrs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id     INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    dvr_nome        TEXT    NOT NULL,
    dvr_ip          TEXT    NOT NULL,
    hd_status       TEXT    NOT NULL,
    hd_total        TEXT    NOT NULL DEFAULT '',
    hd_livre        TEXT    NOT NULL DEFAULT '',
    cameras_ok      INTEGER NOT NULL DEFAULT 0,
    cameras_alerta  INTEGER NOT NULL DEFAULT 0,
    cameras_offline INTEGER NOT NULL DEFAULT 0,
    cameras_nao_instaladas INTEGER NOT NULL DEFAULT 0
);
```

### Tasks

- [ ] Criar teste `tests/unit/test_snapshot_repo.py`
  - [ ] `test_criar_tabelas_via_migracao` — schema criado sem erro
  - [ ] `test_gravar_snapshot_retorna_id` — insert + id
  - [ ] `test_ler_snapshot_por_id` — round-trip completo
  - [ ] `test_ultimo_snapshot_por_instalacao` — pega o mais recente
  - [ ] `test_historico_de_snapshots_por_instalacao` — lista ordenada por data
  - [ ] `test_deletar_instalacao_cascateia_snapshots` — FK CASCADE
- [ ] Rodar → confirmar falhas
- [ ] Adicionar tabelas no `src/infra/database.py::_SCHEMA` + migração não-destrutiva
- [ ] Criar `src/infra/snapshot_repo.py` com `SnapshotRepository`
  - [ ] `gravar(instalacao_id, resultado: ChecklistResult) -> int`
  - [ ] `obter(snapshot_id: int) -> Snapshot`
  - [ ] `ultimo_por_instalacao(instalacao_id: int) -> Snapshot | None`
  - [ ] `historico(instalacao_id: int, limite: int = 20) -> List[Snapshot]`
  - [ ] `todos_ultimos() -> List[Tuple[Instalacao, Snapshot | None]]`
- [ ] Novo dataclass `Snapshot` em `src/domain/snapshot.py` (com `SnapshotDVR`)
- [ ] Rodar suite completa → 100% verde
- [ ] **Commit:** `"Snapshot repo: persiste resultado do checklist no banco"`

**Critério:** consegue gravar um `ChecklistResult` e ler de volta com
`repo.ultimo_por_instalacao(id)`.

---

## Fase 2 — Integração com ChecklistService (30min)

**Objetivo:** todo checklist gera automaticamente um snapshot.

- [ ] Teste: `test_executar_grava_snapshot_ao_final`
  - Fake `SnapshotRepository` conta calls
  - Verifica que `gravar()` é chamado após `enviar_email`
- [ ] `ChecklistResult` ganha campo `snapshot_id: int = 0`
- [ ] `ChecklistService.__init__` aceita `snapshot_repo` (Optional, default None)
- [ ] `ChecklistService.executar()`:
  - Se `snapshot_repo` presente, grava após e-mail
  - Preenche `result.snapshot_id`
- [ ] `HomeWindow._iniciar()`: passar o `SnapshotRepository` compartilhado
- [ ] Rodar suite → verde
- [ ] **Commit:** `"ChecklistService grava snapshot após enviar e-mail"`

**Critério:** rodar um checklist real → linha nova em `snapshots` no
`checkcam.db`.

---

## Fase 3 — Módulo dashboard/ + Flask app (1.5-2h)

**Objetivo:** servidor Flask servindo overview e drill-down.

### Estrutura

```
dashboard/
├── __init__.py
├── app.py              Flask app factory
├── routes.py           /overview, /instalacao/<id>, /historico/<id>
├── views.py            Agregadores de dados (Snapshot → dict para template)
└── ver.py              (versão do dashboard)
```

### Tasks

- [ ] Adicionar `flask` no `requirements-dev.txt` (Flask 3.x)
- [ ] Teste `tests/unit/test_dashboard_routes.py` com Flask test client:
  - [ ] `test_overview_200` — GET /overview retorna 200
  - [ ] `test_overview_lista_todas_instalacoes` — cards no HTML
  - [ ] `test_instalacao_200` — GET /instalacao/<id> retorna 200
  - [ ] `test_instalacao_inexistente_404` — id inválido → 404
  - [ ] `test_historico_json` — GET /api/historico/<id> retorna JSON
- [ ] Rodar → confirmar falhas
- [ ] Criar `dashboard/app.py`:
  - [ ] `create_app(db_path)` → Flask app configurado
  - [ ] Registra rotas
  - [ ] Injeta `InstalacaoRepository` + `SnapshotRepository` no config
- [ ] Criar `dashboard/routes.py`:
  - [ ] `GET /overview` — lista todas instalações com último snapshot
  - [ ] `GET /instalacao/<id>` — drill-down: DVRs + câmeras
  - [ ] `GET /api/historico/<id>` — JSON: últimos 20 snapshots (para chart)
  - [ ] `GET /` — redirect para `/overview`
- [ ] Criar `dashboard/views.py`:
  - [ ] `_classificar_saude(snapshot)` → `"verde" | "amarelo" | "vermelho"`
    - verde = 0 alertas / 0 offline / 0 hd_erro
    - amarelo = só alertas
    - vermelho = hd_erro ou offline
- [ ] Rodar suite → verde
- [ ] **Commit:** `"Dashboard: Flask app com rotas overview/drill-down/historico"`

**Critério:** rodar `flask --app dashboard.app run` e ver JSON no browser.

---

## Fase 4 — Templates + CSS (1-1.5h)

**Objetivo:** UI do dashboard bonita e funcional, inspirada no UniFi.

### Estrutura

```
dashboard/
├── templates/
│   ├── base.html          Header + layout comum
│   ├── overview.html      Grid de cards (verde/amarelo/vermelho)
│   └── instalacao.html    Drill-down: HD por DVR + câmeras por status
└── static/
    ├── style.css          Dark theme (mesmo do CheckCam terminal)
    └── charts.js          Trend histórico (Chart.js CDN)
```

### Tasks

- [ ] `base.html` com header + nav + slot de conteúdo
- [ ] `overview.html`:
  - [ ] Grid responsivo de cards (1 card por instalação)
  - [ ] Cada card: nome, cor de saúde, resumo (N DVRs, N câmeras OK/alerta)
  - [ ] Link para `/instalacao/<id>`
  - [ ] Contadores globais no topo (total DVRs, total câmeras, N problemas)
- [ ] `instalacao.html`:
  - [ ] Cabeçalho: nome + timestamp do último checklist
  - [ ] Grid de DVRs: status HD (colorido) + contagens
  - [ ] Área de trend histórico (canvas Chart.js)
- [ ] `style.css` dark theme:
  - Verde `#2ecc71`, amarelo `#f39c12`, vermelho `#e74c3c`
  - Cards com borda esquerda colorida
  - Font-family: system (sans-serif limpo)
- [ ] `charts.js` — line chart de cameras_alerta ao longo do tempo
- [ ] Teste manual: rodar Flask, abrir `/overview` no browser, ver renderizado
- [ ] **Commit:** `"Dashboard: templates HTML + CSS dark theme + charts"`

**Critério:** overview com pelo menos 2 instalações mostra cards coloridos
e conseguindo drill-down.

---

## Fase 5 — pywebview wrapper (30-45min)

**Objetivo:** dashboard abre como janela nativa, não no browser.

### Tasks

- [ ] Adicionar `pywebview` no `requirements-dev.txt`
- [ ] Criar `dashboard/desktop.py` (basear em
  `C:\Temp\_Projeto_Gerenciamento_MAC_Unifi\desktop.py`):
  - [ ] `_free_port(preferred=5000)` — pega porta livre
  - [ ] `_run_server(port, db_path)` — sobe Flask em thread daemon
  - [ ] `_wait_up(port, timeout=15)` — espera Flask ficar up
  - [ ] `main()`:
    - Pega porta livre
    - Sobe servidor em thread
    - `webview.create_window("Dashboard CheckCam", url, 1320x880)`
    - `webview.start()`
  - [ ] Modo `HEADLESS=1` (não abre webview, só server) — para dev/teste
  - [ ] Modo `--collect` (só executa uma coleta e sai) — futuro cron
- [ ] Teste manual: `python -m dashboard.desktop` abre janela nativa
- [ ] **Commit:** `"Dashboard: pywebview wrapper — janela nativa"`

**Critério:** duplo-clique no `desktop.py` (ou `python -m dashboard.desktop`)
abre uma janela do dashboard sem browser separado.

---

## Fase 6 — Integração com CheckCam UI (30min)

**Objetivo:** botão que abre o dashboard direto da MainWindow.

### Tasks

- [ ] Teste `test_main_window_botao_dashboard_spawnn_processo`
  - Mock `subprocess.Popen`
  - Clicar no botão → Popen chamado com `python -m dashboard.desktop`
- [ ] Adicionar botão **"📊 Abrir Dashboard"** na `MainWindow`:
  - [ ] Botão persistente no cabeçalho (não só após checklist)
  - [ ] `_abrir_dashboard()` faz `subprocess.Popen([sys.executable, "-m", "dashboard.desktop"])`
- [ ] Adicionar botão também no popup final (`_on_finished`):
  - [ ] `QMessageBox` com botões "OK" + "Abrir Dashboard"
- [ ] Também: botão na `HomeWindow` (dashboard independe de checklist rodado)
- [ ] Testes verdes
- [ ] **Commit:** `"UI: botão 'Abrir Dashboard' na HomeWindow e MainWindow"`

**Critério:** rodar `main.py`, clicar em "Abrir Dashboard", ver a janela
do dashboard aparecer.

---

## Fase 7 — Empacotamento (PyInstaller) (30-45min)

**Objetivo:** tudo empacotado num executável.

### Tasks

- [ ] Testar spec atual: `CheckCam.spec` compila? Se sim, adaptar.
- [ ] Criar/atualizar spec incluindo:
  - `dashboard/templates/*.html`
  - `dashboard/static/*.css`, `*.js`
  - Runtime hook do `pywebview` (WebView2)
- [ ] Escolher entre:
  - [ ] **Opção A:** Um único EXE que roda checklist E dashboard (via arg)
  - [ ] **Opção B:** Dois EXEs — `CheckCam.exe` + `CheckCamDashboard.exe`
  - [ ] Ou: EXE único com botão que spawna outro processo Python do próprio EXE
- [ ] `build_exe.ps1` (script PowerShell) — igual ao do UniFi
- [ ] Testar EXE em máquina limpa
- [ ] **Commit:** `"Build: PyInstaller spec inclui dashboard/templates+static"`

**Critério:** copiar o EXE para pasta nova (sem Python instalado) e
dashboard abre normal.

---

## Fase 8 — Docs + release v1.2 (15-30min)

**Objetivo:** documentação atualizada + tag da versão.

### Tasks

- [ ] Screenshots do dashboard (overview + drill-down) em `docs/screenshots/`
- [ ] Atualizar `README.md`: menciona dashboard + como abrir
- [ ] Atualizar `docs/ARQUITETURA.md`: nova camada dashboard/
- [ ] Atualizar `docs/HISTORICO.md`: entrada v1.2
- [ ] Marcar tasks concluídas em `docs/PROXIMOS_PASSOS.md`
- [ ] `git tag -a v1.2.0 -m "Dashboard web-in-window (Flask + pywebview)"`
- [ ] `git push origin v1.2.0`
- [ ] **Commit final:** `"Docs v1.2: dashboard integrado"`

**Critério:** repo em v1.2.0 no GitHub, README fala do dashboard.

---

## Checklist rápido de "está pronto?"

Depois de tudo:

- [ ] `python -m pytest -q` → 100% verde (esperado: ~330 testes)
- [ ] `python main.py` → CheckCam roda, botão "📊 Abrir Dashboard" funciona
- [ ] `python -m dashboard.desktop` → janela nativa abre, overview renderiza
- [ ] Rodar 1 checklist real → gera snapshot → dashboard mostra atualizado
- [ ] EXE compilado abre em máquina sem Python
- [ ] Repo em v1.2.0 com tag

## Dependências que faltam adicionar

```
# requirements-dev.txt
flask>=3.0
pywebview>=5.0
```

## Prompt sugerido para começar (sessão nova)

Copie e cole numa sessão nova do Claude Code para começar direto na Fase 0:

```
Estou em C:\Temp\_Projeto_Relatorio_DVRS_\CheckCam\ (repo em v1.1.0,
commit b237256, 278 testes verdes).

Quero implementar o Dashboard conforme docs/PLANO_DASHBOARD.md.

Comece pela Fase 0 (leia os arquivos indicados), depois execute Fase 1
seguindo o ciclo TDD do docs/CONVENCOES.md.

Pare ao final de cada fase para eu revisar antes de commit + push +
avançar pra próxima.
```
