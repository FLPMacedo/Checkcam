"""Unit tests for src/ui/visual_review_dialog.py"""
from PySide6.QtCore import Qt

from src.domain.models import Camera
from src.ui.visual_review_dialog import VisualReviewDialog


def _cam(imagem: str, status: str = "PENDENTE") -> Camera:
    return Camera(nome="C1", imagem=imagem, status=status)


def test_dialog_classifica_camera_com_tecla_1(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    qtbot.keyPress(dialog, Qt.Key.Key_1)

    assert cam.status == "OK"


def test_dialog_classifica_camera_com_tecla_3(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    qtbot.keyPress(dialog, Qt.Key.Key_3)

    assert cam.status == "DISTORCIDA"


def test_dialog_esc_rejeita_sem_alterar_status(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    dialog.show()

    with qtbot.waitSignal(dialog.rejected, timeout=3000):
        qtbot.keyPress(dialog, Qt.Key.Key_Escape)

    assert cam.status == "PENDENTE"


def test_dialog_ignora_cameras_com_error_img(qtbot, error_jpg):
    cam = _cam(str(error_jpg))
    dialog = VisualReviewDialog([cam], str(error_jpg))
    qtbot.addWidget(dialog)

    assert len(dialog._cameras) == 0


def test_dialog_sem_cameras_aceita_automaticamente(qtbot):
    from PySide6.QtWidgets import QDialog

    dialog = VisualReviewDialog([], "error.jpg")
    qtbot.addWidget(dialog)

    # _show_current() é deferido via QTimer; aguardamos o finished disparar.
    with qtbot.waitSignal(dialog.finished, timeout=2000):
        pass

    assert dialog._cameras == []
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_dialog_sem_cameras_dispara_finished_apos_connect(qtbot):
    """Regressão: o accept() automático precisa ocorrer depois do connect()."""
    dialog = VisualReviewDialog([], "error.jpg")
    qtbot.addWidget(dialog)

    recebido = []
    dialog.finished.connect(recebido.append)

    # Sinal chega após o evento loop processar o QTimer.
    qtbot.waitUntil(lambda: len(recebido) == 1, timeout=2000)
    assert len(recebido) == 1


def test_dialog_imagem_invalida_mostra_mensagem_visivel(qtbot, tmp_path):
    """Regressão: pixmap nulo (arquivo inexistente) → mensagem de erro
    visível na tela, em vez de pular silenciosamente para o próximo."""
    cam = _cam(str(tmp_path / "inexistente.jpg"))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    # Aguarda o QTimer disparar _show_current
    qtbot.wait(50)

    # name_label do painel lateral deve mostrar a câmera
    assert "C1" in dialog.name_label.text()
    # image_label deve mostrar texto de erro (não pixmap)
    assert "não pôde ser carregada" in dialog.image_label.text()
    # status da câmera deve ter sido marcado
    assert cam.status == "ERRO_IMAGEM"


# ─── Novo layout: info à esquerda, imagem ao centro, opções à direita ──────

def test_dialog_tem_painel_de_info_e_painel_de_opcoes(qtbot, small_camera_jpg):
    """Layout horizontal: painel de info à esquerda, opções à direita,
    imagem no centro. Resolve problema da barra inferior ficar escondida
    pela barra de tarefas do Windows."""
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    # Painéis laterais existem como widgets
    assert dialog.info_panel is not None
    assert dialog.hints_panel is not None
    # Têm largura fixa não-zero (são sidebars)
    assert dialog.info_panel.minimumWidth() > 0
    assert dialog.hints_panel.minimumWidth() > 0


def test_dialog_exibe_nome_da_camera_no_painel_lateral(qtbot, small_camera_jpg):
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    assert "C1" in dialog.name_label.text()


def test_dialog_exibe_contador_separado_do_nome(qtbot, small_camera_jpg):
    """Contador '1/N' fica em counter_label, separado de name_label."""
    cams = [_cam(str(small_camera_jpg)), _cam(str(small_camera_jpg))]
    dialog = VisualReviewDialog(cams, "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    # Contador mostra "1/2" (estamos na primeira câmera de 2)
    txt = dialog.counter_label.text()
    assert "1" in txt and "2" in txt


def test_dialog_exibe_dvr_nome_no_painel_lateral(qtbot, small_camera_jpg):
    """Painel lateral mostra o DVR a que a câmera pertence (PN ADM1)."""
    cam = Camera(nome="C5", imagem=str(small_camera_jpg), dvr_nome="PN ADM1")
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    assert "PN ADM1" in dialog.dvr_label.text()
    assert "C5" in dialog.name_label.text()


def test_dialog_titulo_da_janela_inclui_dvr_e_camera(qtbot, small_camera_jpg):
    """windowTitle: 'Revisão Visual – PN ADM1 / C5'."""
    cam = Camera(nome="C5", imagem=str(small_camera_jpg), dvr_nome="PN ADM1")
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    titulo = dialog.windowTitle()
    assert "PN ADM1" in titulo
    assert "C5" in titulo


def test_dialog_tecla_6_marca_como_nao_instalada(qtbot, small_camera_jpg):
    """Nova classificação: tecla 6 → NAO_INSTALADA (sem alerta no e-mail)."""
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    qtbot.keyPress(dialog, Qt.Key.Key_6)

    assert cam.status == "NAO_INSTALADA"


def test_dialog_painel_de_hints_lista_a_opcao_6(qtbot, small_camera_jpg):
    """A 6ª opção 'NÃO INSTALADA' deve aparecer no painel direito."""
    from PySide6.QtWidgets import QLabel

    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    # Junta todo o texto dos QLabel children do hints_panel
    todos_textos = " ".join(
        child.text() for child in dialog.hints_panel.findChildren(QLabel)
    )
    # Deve mencionar a tecla 6 e a label "NÃO INSTALADA" (acentuada ou não)
    assert "6" in todos_textos
    assert "INSTALADA" in todos_textos.upper()


# ─── Tecla 0: voltar para câmera anterior ────────────────────────────────────

def test_dialog_tecla_0_volta_para_camera_anterior(qtbot, small_camera_jpg):
    """Pressionar 0 retorna para a câmera anterior para corrigir classificação."""
    cam1 = Camera(nome="C1", imagem=str(small_camera_jpg))
    cam2 = Camera(nome="C2", imagem=str(small_camera_jpg))
    dialog = VisualReviewDialog([cam1, cam2], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    # Classifica C1 como OK e avança para C2
    qtbot.keyPress(dialog, Qt.Key.Key_1)
    assert cam1.status == "OK"
    assert "C2" in dialog.name_label.text()

    # Volta para C1 com tecla 0
    qtbot.keyPress(dialog, Qt.Key.Key_0)
    assert "C1" in dialog.name_label.text()


def test_dialog_tecla_0_na_primeira_camera_nao_quebra(qtbot, small_camera_jpg):
    """Já estamos na 1ª câmera (idx=0); pressionar 0 não deve travar."""
    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    qtbot.keyPress(dialog, Qt.Key.Key_0)

    # Continua na primeira câmera
    assert "C1" in dialog.name_label.text()


def test_dialog_voltar_permite_reclassificar(qtbot, small_camera_jpg):
    """Workflow real: classifica errado → volta → reclassifica corretamente."""
    cam1 = Camera(nome="C1", imagem=str(small_camera_jpg))
    cam2 = Camera(nome="C2", imagem=str(small_camera_jpg))
    dialog = VisualReviewDialog([cam1, cam2], "outro_error.jpg")
    qtbot.addWidget(dialog)
    qtbot.wait(50)

    # Classifica C1 errado (OK)
    qtbot.keyPress(dialog, Qt.Key.Key_1)
    assert cam1.status == "OK"

    # Volta e reclassifica como EMBAÇADA
    qtbot.keyPress(dialog, Qt.Key.Key_0)
    qtbot.keyPress(dialog, Qt.Key.Key_2)
    assert cam1.status == "EMBAÇADA_SUJA"

    # Avançou para C2 normalmente
    assert "C2" in dialog.name_label.text()


def test_dialog_painel_de_hints_lista_o_voltar(qtbot, small_camera_jpg):
    """Painel direito mostra 'VOLTAR' associado à tecla 0."""
    from PySide6.QtWidgets import QLabel

    cam = _cam(str(small_camera_jpg))
    dialog = VisualReviewDialog([cam], "outro_error.jpg")
    qtbot.addWidget(dialog)

    todos = " ".join(
        child.text() for child in dialog.hints_panel.findChildren(QLabel)
    )
    assert "0" in todos
    assert "VOLTAR" in todos.upper()
