# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec do CheckCam — EXE único (checklist + dashboard).

O mesmo executável roda o gerenciador de checklist e, com --dashboard,
abre o painel web numa janela nativa (pywebview). Os templates e estáticos
do dashboard vão embutidos; em runtime são lidos de sys._MEIPASS/dashboard.

Build:  pyinstaller CheckCam.spec   (ou .\build_exe.ps1)
"""
from PyInstaller.utils.hooks import collect_all

# ── Recursos do dashboard (não são importados, precisam ir como datas) ──
datas = [
    ("dashboard/templates", "dashboard/templates"),
    ("dashboard/static", "dashboard/static"),
]
binaries = []
hiddenimports = [
    "dashboard.desktop",
    "dashboard.app",
    "dashboard.routes",
    "dashboard.views",
]

# ── pywebview + backend WebView2 (pythonnet/clr) ──
_web_datas, _web_bin, _web_hidden = collect_all("webview")
datas += _web_datas
binaries += _web_bin
hiddenimports += _web_hidden

# ── Outlook COM (usado pelo envio de e-mail do checklist) ──
hiddenimports += ["win32com", "win32com.client", "win32timezone"]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_qt", "pytest_mock"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CheckCam",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
