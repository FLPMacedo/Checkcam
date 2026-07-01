# Arquitetura do CheckCam

Refatoração completa do legado monolítico em camadas isoladas. Todas as
dependências externas (COM, subprocess, Playwright, cv2) têm fakes/mocks.

## Camadas

```
┌─────────────────────────────────────────────────────────┐
│  UI (PySide6)                                           │
│  ├─ HomeWindow, MainWindow, dialogs                     │
│  └─ Worker (QThread) — isola pipeline da UI thread      │
├─────────────────────────────────────────────────────────┤
│  Services                                               │
│  └─ ChecklistService — orquestra o pipeline             │
├─────────────────────────────────────────────────────────┤
│  Core                                                   │
│  ├─ ping, hd_analyzer (Hikvision playwright)            │
│  ├─ intelbras_cgi (Intelbras via API CGI HTTP)          │
│  ├─ rtsp — monta URL por marca × tipo                   │
│  ├─ camera_capture (ffmpeg + retry com chave)           │
│  └─ visual_review (cv2, mantido para compat)            │
├─────────────────────────────────────────────────────────┤
│  Reports                                                │
│  ├─ excel_builder — Checklist xlsx (1 sheet por seção)  │
│  ├─ book_builder — Book xlsx (1 sheet por câmera)       │
│  ├─ pdf_exporter — Excel COM → PDF                      │
│  └─ email_sender — Outlook COM                          │
├─────────────────────────────────────────────────────────┤
│  Infra                                                  │
│  ├─ database (SQLite schema + migrações)                │
│  ├─ instalacao_repo (CRUD Instalação)                   │
│  ├─ backup — JSON export/import                         │
│  ├─ app_config (config em memória)                      │
│  └─ path_defaults (convenção de caminhos)               │
├─────────────────────────────────────────────────────────┤
│  Domain                                                 │
│  ├─ models (DVR, Camera, HDStatus)                      │
│  ├─ instalacao (Instalacao)                             │
│  ├─ device (Marca, TipoDispositivo — enums)             │
│  ├─ status (CameraStatus — enum)                        │
│  └─ events (ProgressEvent, ChecklistResult)             │
└─────────────────────────────────────────────────────────┘
```

## Pipeline (`ChecklistService.executar`)

```
HD (analisar_hd)         → estado do HD por DVR
  ↓
Captura (camera_capture) → frames RTSP + retry com chave
  ↓
Visual (revisão manual)  → usuário classifica câmeras
  ↓
Excel (excel_builder)    → xlsx com grid 4×4 + extras largo
  ↓
PDF (pdf_exporter)       → xlsx → pdf via Excel COM
  ↓
Book (book_builder)      → 1 câmera por página, imagem grande
  ↓
Book PDF (pdf_exporter)  → mesma conversão
  ↓
E-mail (email_sender)    → Outlook COM, anexa ambos PDFs
```

Cada etapa emite `ProgressEvent` para a UI via callback.

## Decisões de design importantes

### 1. "1 sheet por seção" no Excel
Câmeras IP e analógicas têm tamanhos diferentes → cálculo de altura
por row era frágil. Solução: cada seção lógica vira uma sheet, e Excel
garante `1 sheet = pelo menos 1 página` de PDF.

- **Checklist:** 1 sheet principal (16 câmeras) + 1 sheet extra (17+ largo)
- **Book:** 1 sheet por câmera (N câmeras = N páginas garantido)

### 2. Overrides por dispositivo
Cada DVR pode sobrescrever portas, usuário, senha da instalação. Campo
vazio herda da instalação. Permite misturar Hikvision + Intelbras + IPs
custom na mesma instalação.

### 3. Retry com chave de criptografia
Hikvision com "verification code" ativado exige a chave (não a senha) no
RTSP. `camera_capture` tenta a senha normal; se falhar (não timeout),
refaz com `dvr.chave_criptografia`.

### 4. Fail-fast em caminhos vazios
Se `base_dir`, `relatorios_dir` ou `logs_dir` chegarem vazios, os builders
levantam `ValueError` com mensagem clara em vez do críptico `WinError 3`.
O form preenche defaults automaticamente para novas instalações.

### 5. OFFLINE ≠ ATENÇÃO HD no e-mail
DVR offline é problema de conexão, não de HD. Só `ONLINE - ERRO (HD)`
dispara "ATENÇÃO HD" no assunto. OFFLINE vai em seção separada "HD NÃO
VERIFICADO".

### 6. Isolamento de deps externas em testes
Nenhum teste chama Excel COM / Outlook / Playwright reais. Fakes:
- `tests/fakes/fake_win32com.py`
- `tests/fakes/fake_playwright.py`
- `tests/fakes/fake_subprocess.py`
- `tests/fakes/fake_cv2.py`
