# Próximos passos

> **📋 Plano de execução:** o dashboard tem seu próprio arquivo com fases
> e tasks marcáveis: [PLANO_DASHBOARD.md](PLANO_DASHBOARD.md)

## 1. Dashboard web-in-window (prioridade)

**Objetivo:** dashboard que mostra estado atual por instalação, no estilo
Flask + pywebview (mesmo padrão do projeto UniFi em
`C:\Temp\_Projeto_Gerenciamento_MAC_Unifi\`).

### Estrutura proposta

```
CheckCam/
├── main.py                    (fica como está — PySide6 checklist)
├── checkcam.db                (banco atual + tabelas novas)
│
├── dashboard/                  ← MÓDULO NOVO isolado
│   ├── __init__.py
│   ├── app.py                 (Flask: /overview, /instalacao/<id>, /historico)
│   ├── desktop.py             (pywebview: janela nativa → Flask)
│   ├── snapshots.py           (grava/lê snapshot no banco)
│   ├── templates/
│   │   ├── base.html
│   │   ├── overview.html      (grid de instalações — verde/amarelo/vermelho)
│   │   └── instalacao.html    (drill-down: DVRs + câmeras)
│   └── static/
│       ├── style.css
│       └── charts.js          (Chart.js pra trend histórico)
│
└── src/
    └── infra/
        └── snapshot_repo.py    ← NOVO: salva o resultado do checklist
```

### Fluxo integrado
1. **Checklist roda normal** (`main.py` — sem mexer)
2. **Ao finalizar** o `ChecklistService.executar()`, além de PDF/e-mail,
   grava snapshot no banco (tabela nova `snapshots` + `snapshot_dvrs`)
3. **Botão novo na MainWindow** (ou no popup de conclusão):
   **"📊 Abrir Dashboard"** — executa `python -m dashboard.desktop`
4. **Dashboard** mostra:
   - Overview: card por instalação com status geral
     (verde/amarelo/vermelho baseado no último snapshot)
   - Drill-down: clica na instalação → DVRs + câmeras + trend histórico
5. **Empacotamento:** PyInstaller com spec incluindo templates/static

### Prompt sugerido para sessão nova

Cola isso numa sessão nova do Claude Code (economia de token >90% vs continuar
a sessão atual, que já carrega todo o histórico da refatoração):

```
Estou em C:\Temp\_Projeto_Relatorio_DVRS_\CheckCam\ (Python 3.12 + PySide6 + SQLite).

Quero adicionar um módulo `dashboard/` novo, no estilo Flask + pywebview
(mesmo padrão do meu outro projeto em C:\Temp\_Projeto_Gerenciamento_MAC_Unifi\,
onde tem app.py=Flask, desktop.py=pywebview wrapper, snapshot no SQLite).

Objetivo:
1. Ao final de cada checklist (src/services/checklist_service.py),
   salvar snapshot no banco (nova tabela `snapshots` + `snapshot_dvrs`
   com estado de cada DVR + contagens de câmeras por status).
2. Dashboard web-in-window (Flask + pywebview) mostrando:
   - Overview: card por instalação com status geral (verde/amarelo/vermelho)
     baseado no último snapshot
   - Drill-down: clicar em instalação → DVRs + câmeras + trend histórico
3. Botão "📊 Abrir Dashboard" na MainWindow (src/ui/main_window.py) que
   sobe o pywebview.
4. Empacotar tudo no mesmo exe (PyInstaller).

Antes de começar, leia SÓ estes arquivos:
- docs/ARQUITETURA.md
- docs/CONVENCOES.md
- src/domain/instalacao.py
- src/domain/models.py
- src/services/checklist_service.py
- src/infra/database.py
- C:\Temp\_Projeto_Gerenciamento_MAC_Unifi\desktop.py (padrão a seguir)

Repo em v1.1.0 (commit 468beb6), testes 278/278 verdes.
Trabalha em cima do que já existe, ciclo TDD obrigatório, commit por fase.
Convenções em docs/CONVENCOES.md.
```

## 2. Outras ideias que apareceram e ficaram no gelo

Coisas que foram sugeridas ou apareceram durante a refatoração e não foram
implementadas por scope:

- **Reset de senha ao trocar de instalação** — hoje as credenciais ficam
  em memória; talvez limpar ao voltar pra HomeWindow
- **Preview do e-mail antes de enviar** — já tem `EmailPreviewDialog`,
  mas não está no fluxo automático
- **Suporte a chave de criptografia via `-decryption_key` do ffmpeg**
  como fallback adicional (hoje só tenta chave-como-senha)
- **Detecção de status "Anormal" na página do Hikvision** para marcar
  `ONLINE - ERRO (HD)` mesmo com capacidades OK (foi discutido, mas o
  usuário optou por outra abordagem)
- **`hd_analyzer` como estratégia por marca** já foi separado
  (Hikvision playwright / Intelbras CGI), mas ainda dá pra ficar mais
  limpo — se surgir uma 3ª marca

## 3. Manutenção / limpeza

- **Docstrings faltando** em alguns módulos novos
- **Sanity check** dos DVRs seed nas instalações 102 e 107 (script
  original avisa que podem estar duplicados — precisa confirmar com o
  campo)
- **Migrar** as instalações antigas do BD que ficaram com paths vazios
  (usuário abrindo "Editar" + OK resolve, mas dava pra script)
