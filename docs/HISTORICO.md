# Histórico do CheckCam

Cronologia do que foi feito, agrupado por temas. Para o log completo commit
a commit: `git log --oneline`.

## v1.0.0 — Primeira versão estável (commit `258a85a`)

Refatoração completa do legado `DVR_exe3.py` (Tkinter + globais + print no CMD)
para PySide6 em camadas.

### Estrutura
- `src/domain/` — DVR, Camera, HDStatus, Instalacao, eventos
- `src/core/` — ping, hd_analyzer, camera_capture, visual_review
- `src/services/` — ChecklistService (orquestra pipeline completo)
- `src/reports/` — excel_builder, book_builder, pdf_exporter, email_sender
- `src/infra/` — database, instalacao_repo, backup, app_config, path_defaults
- `src/ui/` — HomeWindow, MainWindow, dialogs, worker

### Pipeline
`HD → Captura → Revisão visual → Excel/PDF → Book PDF → E-mail`

### Features chave
- **Multi-instalação** em SQLite com CRUD via UI
- **Backup/Restaurar** em JSON
- **Layout flexível no Excel:** grid 4×N (≤16 câm) + grid 2×N largo (17+)
- **Nome de arquivo:** `Checklist_<slug>_<DD-MM-YYYY>_<HH-MM-SS>.{xlsx,pdf}`
- **Visual review com QDialog** (substitui `cv2.imshow`)
  - 6 classificações (tecla 1-5 + 6 NAO_INSTALADA)
  - Tecla 0 para voltar câmera anterior
  - Sidebars (info à esquerda, opções à direita)
- **Worker em QThread** isolando pipeline da UI
- **Book PDF:** 1 câmera por página em paisagem, imagem grande
- **Estratégia "1 sheet por seção"** garante N câm = N páginas
- **E-mail categorizado:**
  - OFFLINE ≠ ATENÇÃO HD (categorias separadas)
  - Seção "HD não verificado" para DVRs offline
  - `NAO_INSTALADA` não gera alerta
  - 2 anexos: Checklist + Book
- **Robustez:**
  - Caminhos padrão auto-deduzidos do nome
  - Fail-fast com mensagens claras
  - `.gitignore` estrito (sem leak de runtime)

## v1.1.0 — Chave de criptografia + Intelbras + IP (commit `468beb6`)

### Feature principal
**Chave de criptografia por DVR.** Hikvision com "verification code" ativado
exige a chave (não a senha) no RTSP. Fluxo:
1. Tenta com senha normal
2. Se falhar (não timeout) E DVR tem chave → refaz com chave
3. TIMEOUT não dispara retry (é rede, não credencial)

### Outros
- **Suporte Intelbras/Dahua:** `src/core/intelbras_cgi.py` lê HD via CGI HTTP
- **Câmera IP:** `TipoDispositivo.CAMERA_IP` = 1 IP, canal fixo em 1
- **Domain expandido:**
  - `src/domain/device.py` — `Marca` e `TipoDispositivo` (StrEnum)
  - `src/domain/status.py` — `CameraStatus` enum
- **Overrides por dispositivo:** `porta_http`, `porta_rtsp`, `usuario`, `senha`
  no DVR (vazio = herda da instalação)
- **RTSP unificado:** `src/core/rtsp.py` monta URL por marca × tipo
  - Hikvision: `rtsp://u:p@ip:porta/Streaming/Channels/{canal}01`
  - Intelbras: `rtsp://u:p@ip:554/cam/realmonitor?channel={canal}&subtype=0`
- **URL encoding:** `quote(senha, safe="")` — encoda `/` e `@` corretamente
- **UI:** coluna "Chave criptografia" na tabela de dispositivos
- **Backup JSON** serializa/desserializa todos os campos novos
- **Migração de banco** não-destrutiva (`ALTER TABLE ADD COLUMN`)
- **EmailPreviewDialog:** pré-visualização antes de enviar

### Números
- **278 testes** verdes (era 221 em v1.0)
- Novos módulos: `intelbras_cgi.py`, `rtsp.py`, `device.py`, `status.py`,
  `email_preview_dialog.py`
- Novos testes: `test_rtsp.py`, `test_intelbras_cgi.py`,
  `test_email_preview_dialog.py`

## Fases 0-7 (durante v1.0)

Sequência das fases originais da refatoração:

- **Fase 0:** Setup — conftest, fakes, characterization tests do legado
- **Fase 1:** Domain — dataclasses limpas
- **Fase 2:** Core — extração de ping/hd/captura do legado
- **Fase 3:** Reports — Excel/PDF/e-mail isolados
- **Fase 4:** Services — orquestração no ChecklistService
- **Fase 5:** UI PySide6 — HomeWindow, MainWindow, VisualReviewDialog, Worker
- **Fase 6:** Multi-instalação — SQLite + CRUD + Backup/Restaurar
- **Fase 7:** Book PDF + features solicitadas ao longo do caminho

## Bugs resolvidos que valeram commit dedicado

- Wide images cortadas entre páginas → estratégia "1 sheet por seção"
- Book PDF lento com 200+ câmeras → skip do PageSetup loop no pdf_exporter
- "NO VIDEO" cortado lateralmente → COLS_BOOK reduzido de 14 (A:N) para 12 (A:L)
- WinError 3 com caminho vazio → auto-fill + fail-fast
- JPGs de captura vazando pra raiz do repo → `.gitignore` reforçado
- OFFLINE alertando como ATENÇÃO HD → categorização separada
