# Convenções do CheckCam

Regras que valem pra qualquer contribuição / sessão de refatoração.

## Ciclo TDD obrigatório

Toda mudança segue esse ciclo, sem exceção:

1. **Escrever teste que falha** com a mudança pretendida
2. **Rodar** e confirmar que ele falha
3. **Implementar** o mínimo pra passar
4. **Rodar suite completa** — 100% verde
5. **Commit + push**

Não pular passos. Não escrever implementação antes do teste.

## Testes

- **Pytest** em `tests/`
- **Fakes** em `tests/fakes/` isolam COM, subprocess, Playwright, cv2
- **Fixtures** em `tests/conftest.py` (fixtures de sessão + por-teste)
- **Suite completa** deve rodar em < 30s
- Nunca chamar Excel/Outlook/Playwright/rede REAL num teste

Rodar:
```powershell
python -m pytest -q                       # tudo (rápido)
python -m pytest tests/unit/test_X.py -v  # específico
python -m pytest -k "chave" -v            # filtro por nome
```

## Commits

- **Mensagens em português** (o usuário do repo é BR)
- **Título curto** na 1ª linha (≤ 72 chars)
- **Corpo explica O QUÊ + POR QUÊ**, não como (o código mostra o como)
- **Um commit por fase / feature coerente** — não misturar coisas não-relacionadas
- **Não pular hooks** (`--no-verify`) sem pedir autorização

Formato usado:
```
<tipo>: <resumo curto>

<Contexto: o que estava acontecendo / bug observado>

<Solução: o que mudou e por quê>

<Testes: quais foram adicionados / atualizados>
```

## Caminhos padrão

Todos os caminhos de instalação são deduzidos do nome via
`src/infra/path_defaults.py`:

```
base_dir       = <CheckCam>/data/<slug>/temp
relatorios_dir = <CheckCam>/relatorios/<slug>
logs_dir       = <CheckCam>/data/<slug>/logs
ffmpeg_path    = <CheckCam>/assets/ffmpeg/bin/ffmpeg.exe
playwright_path= <CheckCam>/assets/playwright_browsers
error_img      = <CheckCam>/assets/error.jpg
```

O `slug` é o nome sanitizado (sem `/`, `:`, `*`, `?`, `"`, `<`, `>`, `|`,
espaços viram `_`, hífens somem).

Se um campo de caminho ficar vazio na UI, o form preenche com o default
ao salvar. Se algum builder receber caminho vazio, levanta `ValueError`
com mensagem clara.

## Estilo de código

- **Português** em nomes e docstrings (é um projeto BR, para usuários BR)
- **Type hints** onde faz sentido, sem excesso
- **Docstrings curtas** — explicar propósito e side effects, não parafrasear código
- **Sem comentários óbvios** — `# incrementa i` é ruído

## O que NÃO commitar

`.gitignore` protege contra:
- `checkcam.db` e derivados (`*.db`, `*.db-journal`)
- `data/`, `relatorios/` (runtime)
- `__pycache__/`, `.pytest_cache/`
- `assets/ffmpeg/` (301 MB), `assets/playwright_browsers/` (394 MB)
- `*.jpg` em qualquer lugar exceto `assets/**/*.jpg`
- Pastas de captura leaked: `DVR_*/`, `PN_*/`, `CD_*/`, `CAMPO_*/`

## Interação com o usuário

- **Confirmar antes de rodar** ações destrutivas (rm, drop, force-push)
- **Não subir arquivos grandes** sem autorização
- **Não modificar `git config`** sem permissão
- **Perguntar quando ambíguo** — melhor perguntar que assumir errado
