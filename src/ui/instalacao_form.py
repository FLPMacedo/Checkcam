from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.domain.device import Marca, TipoDispositivo
from src.domain.instalacao import Instalacao
from src.domain.models import DVR
from src.infra.path_defaults import caminhos_padrao_para

# Colunas da tabela de dispositivos (DVRs/câmeras).
_COL_NOME, _COL_IP, _COL_CAMERAS, _COL_MARCA, _COL_TIPO, \
    _COL_PHTTP, _COL_PRTSP, _COL_USER, _COL_SENHA, \
    _COL_CHAVE, _COL_CHAVE2, _COL_CHAVE3 = range(12)

_MARCAS = [Marca.HIKVISION, Marca.INTELBRAS]
_TIPOS = [TipoDispositivo.DVR, TipoDispositivo.CAMERA_IP]


class InstalacaoFormDialog(QDialog):
    """
    Formulário para criar ou editar uma Instalacao.

    Cobre: credenciais, portas, caminhos de executáveis e diretórios,
    tabela de DVRs e lista de e-mails de destino.

    Use get_instalacao() após exec() == Accepted para obter o objeto preenchido.
    """

    def __init__(self, instalacao: Optional[Instalacao] = None, parent=None) -> None:
        super().__init__(parent)
        self._inst = instalacao or Instalacao()
        self.setWindowTitle("Nova Instalação" if self._inst.id == 0 else "Editar Instalação")
        self.setMinimumWidth(940)
        self._build_ui()
        self._populate()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # ── Scroll com campos de configuração ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _field(attr: str, placeholder: str = "", password: bool = False) -> QLineEdit:
            le = QLineEdit()
            le.setPlaceholderText(placeholder)
            if password:
                le.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, f"_{attr}", le)
            return le

        form.addRow("Nome da instalação *", _field("nome", "ex: 107 – Antônio Carlos"))
        form.addRow("Usuário DVR *",        _field("usuario", "admin"))
        form.addRow("Senha DVR *",          _field("senha", password=True))
        form.addRow("Porta HTTP",           _field("porta_http", "3077"))
        form.addRow("Porta RTSP",           _field("porta_rtsp", "3078"))
        form.addRow("FFmpeg (caminho)",     _field("ffmpeg_path"))
        form.addRow("Playwright (dir)",     _field("playwright_path"))
        form.addRow("Dir. câmeras (base)",  _field("base_dir"))
        form.addRow("Dir. relatórios",      _field("relatorios_dir"))
        form.addRow("Dir. logs",            _field("logs_dir"))
        form.addRow("Imagem de erro",       _field("error_img"))

        scroll.setWidget(inner)
        root.addWidget(scroll)

        # ── Tabela de DVRs / câmeras ──
        dvr_box = QGroupBox("Dispositivos (DVR/NVR e câmeras IP)")
        dvr_lay = QVBoxLayout(dvr_box)

        self._dvr_table = QTableWidget(0, 12)
        self._dvr_table.setHorizontalHeaderLabels(
            ["Nome", "IP", "Câmeras", "Marca", "Tipo",
             "Porta HTTP", "Porta RTSP", "Usuário", "Senha",
             "Chave 1", "Chave 2", "Chave 3"],
        )
        header = self._dvr_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(_COL_NOME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_IP, QHeaderView.ResizeMode.Stretch)
        self._dvr_table.setToolTip(
            "Porta HTTP/RTSP, Usuário e Senha são opcionais: em branco, "
            "herdam o valor da instalação.\n"
            "Chave 1/2/3: senhas alternativas para câmeras Hikvision com\n"
            "'verification code' ativado — testadas em ordem se a senha falhar.\n"
            "Câmera IP é capturada direto pelo próprio IP (canal único)."
        )
        dvr_lay.addWidget(self._dvr_table)

        dvr_btns = QHBoxLayout()
        btn_add_dvr = QPushButton("+ Adicionar dispositivo")
        btn_add_dvr.clicked.connect(self._adicionar_dvr)
        btn_rem_dvr = QPushButton("− Remover dispositivo")
        btn_rem_dvr.clicked.connect(self._remover_dvr)
        dvr_btns.addWidget(btn_add_dvr)
        dvr_btns.addWidget(btn_rem_dvr)
        dvr_btns.addStretch()
        dvr_lay.addLayout(dvr_btns)
        root.addWidget(dvr_box)

        # ── Lista de E-mails ──
        email_box = QGroupBox("E-mails de destino")
        email_lay = QVBoxLayout(email_box)

        self._email_list = QListWidget()
        email_lay.addWidget(self._email_list)

        email_btns = QHBoxLayout()
        self._email_input = QLineEdit()
        self._email_input.setPlaceholderText("novo@email.com")
        btn_add_email = QPushButton("+ Adicionar")
        btn_add_email.clicked.connect(self._adicionar_email)
        btn_rem_email = QPushButton("− Remover")
        btn_rem_email.clicked.connect(self._remover_email)
        email_btns.addWidget(self._email_input, stretch=1)
        email_btns.addWidget(btn_add_email)
        email_btns.addWidget(btn_rem_email)
        email_lay.addLayout(email_btns)
        root.addWidget(email_box)

        # ── OK / Cancelar ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._aceitar)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── Preenchimento ─────────────────────────────────────────────────────────

    def _populate(self) -> None:
        inst = self._inst
        self._nome.setText(inst.nome)
        self._usuario.setText(inst.usuario)
        self._senha.setText(inst.senha)
        self._porta_http.setText(inst.porta_http)
        self._porta_rtsp.setText(inst.porta_rtsp)
        self._ffmpeg_path.setText(inst.ffmpeg_path)
        self._playwright_path.setText(inst.playwright_path)
        self._base_dir.setText(inst.base_dir)
        self._relatorios_dir.setText(inst.relatorios_dir)
        self._logs_dir.setText(inst.logs_dir)
        self._error_img.setText(inst.error_img)

        for dvr in inst.dvrs:
            self._inserir_linha_dvr(dvr)

        for email in inst.emails:
            self._email_list.addItem(email)

    # ── DVR helpers ───────────────────────────────────────────────────────────

    def _inserir_linha_dvr(self, dvr: DVR | None = None) -> None:
        dvr = dvr or DVR(nome="", ip="", qtd_cameras=1)
        row = self._dvr_table.rowCount()
        self._dvr_table.insertRow(row)

        self._dvr_table.setItem(row, _COL_NOME, QTableWidgetItem(dvr.nome))
        self._dvr_table.setItem(row, _COL_IP, QTableWidgetItem(dvr.ip))

        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(64)
        spin.setValue(dvr.qtd_cameras)
        self._dvr_table.setCellWidget(row, _COL_CAMERAS, spin)

        marca = QComboBox()
        marca.addItems([str(m) for m in _MARCAS])
        marca.setCurrentText(str(dvr.marca))
        self._dvr_table.setCellWidget(row, _COL_MARCA, marca)

        tipo = QComboBox()
        tipo.addItems([str(t) for t in _TIPOS])
        tipo.setCurrentText(str(dvr.tipo))
        self._dvr_table.setCellWidget(row, _COL_TIPO, tipo)

        self._dvr_table.setItem(row, _COL_PHTTP, QTableWidgetItem(dvr.porta_http))
        self._dvr_table.setItem(row, _COL_PRTSP, QTableWidgetItem(dvr.porta_rtsp))
        self._dvr_table.setItem(row, _COL_USER, QTableWidgetItem(dvr.usuario))
        self._dvr_table.setItem(row, _COL_SENHA, QTableWidgetItem(dvr.senha))
        self._dvr_table.setItem(row, _COL_CHAVE, QTableWidgetItem(dvr.chave_criptografia))
        self._dvr_table.setItem(row, _COL_CHAVE2, QTableWidgetItem(dvr.chave_criptografia_2))
        self._dvr_table.setItem(row, _COL_CHAVE3, QTableWidgetItem(dvr.chave_criptografia_3))

    def _adicionar_dvr(self) -> None:
        self._inserir_linha_dvr()

    def _remover_dvr(self) -> None:
        row = self._dvr_table.currentRow()
        if row >= 0:
            self._dvr_table.removeRow(row)

    def _texto_celula(self, row: int, col: int) -> str:
        item = self._dvr_table.item(row, col)
        return item.text().strip() if item else ""

    # ── Email helpers ─────────────────────────────────────────────────────────

    def _adicionar_email(self) -> None:
        email = self._email_input.text().strip()
        if email:
            self._email_list.addItem(email)
            self._email_input.clear()

    def _remover_email(self) -> None:
        row = self._email_list.currentRow()
        if row >= 0:
            self._email_list.takeItem(row)

    # ── Aceitar ───────────────────────────────────────────────────────────────

    def _aceitar(self) -> None:
        nome = self._nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obrigatório", "Informe o nome da instalação.")
            return

        # Auto-preenche caminhos vazios com defaults baseados no nome.
        # Evita o WinError 3 (caminho '' não existe) ao rodar o checklist.
        # Caminhos já preenchidos pelo usuário NÃO são sobrescritos.
        self._auto_preencher_caminhos_vazios(nome)

        self.accept()

    def _auto_preencher_caminhos_vazios(self, nome: str) -> None:
        defaults = caminhos_padrao_para(nome)
        pares = [
            (self._base_dir,        defaults["base_dir"]),
            (self._relatorios_dir,  defaults["relatorios_dir"]),
            (self._logs_dir,        defaults["logs_dir"]),
            (self._ffmpeg_path,     defaults["ffmpeg_path"]),
            (self._playwright_path, defaults["playwright_path"]),
            (self._error_img,       defaults["error_img"]),
        ]
        for field, padrao in pares:
            if not field.text().strip():
                field.setText(padrao)

    # ── API pública ───────────────────────────────────────────────────────────

    def get_instalacao(self) -> Instalacao:
        """Retorna o objeto Instalacao com os valores do formulário."""
        dvrs = []
        for row in range(self._dvr_table.rowCount()):
            nome = self._texto_celula(row, _COL_NOME)
            ip = self._texto_celula(row, _COL_IP)
            spin = self._dvr_table.cellWidget(row, _COL_CAMERAS)
            qtd = spin.value() if spin else 1
            marca_w = self._dvr_table.cellWidget(row, _COL_MARCA)
            tipo_w = self._dvr_table.cellWidget(row, _COL_TIPO)
            if nome and ip:
                dvrs.append(DVR(
                    nome=nome,
                    ip=ip,
                    qtd_cameras=qtd,
                    marca=marca_w.currentText() if marca_w else str(Marca.HIKVISION),
                    tipo=tipo_w.currentText() if tipo_w else str(TipoDispositivo.DVR),
                    porta_http=self._texto_celula(row, _COL_PHTTP),
                    porta_rtsp=self._texto_celula(row, _COL_PRTSP),
                    usuario=self._texto_celula(row, _COL_USER),
                    senha=self._texto_celula(row, _COL_SENHA),
                    chave_criptografia=self._texto_celula(row, _COL_CHAVE),
                    chave_criptografia_2=self._texto_celula(row, _COL_CHAVE2),
                    chave_criptografia_3=self._texto_celula(row, _COL_CHAVE3),
                ))

        emails = [
            self._email_list.item(i).text()
            for i in range(self._email_list.count())
        ]

        return Instalacao(
            id=self._inst.id,
            nome=self._nome.text().strip(),
            usuario=self._usuario.text().strip(),
            senha=self._senha.text(),
            porta_http=self._porta_http.text().strip() or "3077",
            porta_rtsp=self._porta_rtsp.text().strip() or "3078",
            ffmpeg_path=self._ffmpeg_path.text().strip(),
            playwright_path=self._playwright_path.text().strip(),
            base_dir=self._base_dir.text().strip(),
            relatorios_dir=self._relatorios_dir.text().strip(),
            logs_dir=self._logs_dir.text().strip(),
            error_img=self._error_img.text().strip(),
            dvrs=dvrs,
            emails=emails,
        )
