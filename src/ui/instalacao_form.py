from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from src.domain.instalacao import Instalacao
from src.domain.models import DVR
from src.infra.path_defaults import caminhos_padrao_para


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
        self.setMinimumWidth(640)
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

        # ── Tabela de DVRs ──
        dvr_box = QGroupBox("DVRs")
        dvr_lay = QVBoxLayout(dvr_box)

        self._dvr_table = QTableWidget(0, 3)
        self._dvr_table.setHorizontalHeaderLabels(["Nome", "IP", "Câmeras"])
        self._dvr_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        dvr_lay.addWidget(self._dvr_table)

        dvr_btns = QHBoxLayout()
        btn_add_dvr = QPushButton("+ Adicionar DVR")
        btn_add_dvr.clicked.connect(self._adicionar_dvr)
        btn_rem_dvr = QPushButton("− Remover DVR")
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
            self._inserir_linha_dvr(dvr.nome, dvr.ip, dvr.qtd_cameras)

        for email in inst.emails:
            self._email_list.addItem(email)

    # ── DVR helpers ───────────────────────────────────────────────────────────

    def _inserir_linha_dvr(self, nome: str = "", ip: str = "", qtd: int = 1) -> None:
        row = self._dvr_table.rowCount()
        self._dvr_table.insertRow(row)
        self._dvr_table.setItem(row, 0, QTableWidgetItem(nome))
        self._dvr_table.setItem(row, 1, QTableWidgetItem(ip))
        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(64)
        spin.setValue(qtd)
        self._dvr_table.setCellWidget(row, 2, spin)

    def _adicionar_dvr(self) -> None:
        self._inserir_linha_dvr()

    def _remover_dvr(self) -> None:
        row = self._dvr_table.currentRow()
        if row >= 0:
            self._dvr_table.removeRow(row)

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
            nome_item = self._dvr_table.item(row, 0)
            ip_item = self._dvr_table.item(row, 1)
            spin = self._dvr_table.cellWidget(row, 2)
            nome = nome_item.text().strip() if nome_item else ""
            ip = ip_item.text().strip() if ip_item else ""
            qtd = spin.value() if spin else 1
            if nome and ip:
                dvrs.append(DVR(nome=nome, ip=ip, qtd_cameras=qtd))

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
