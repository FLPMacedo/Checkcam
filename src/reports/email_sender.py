from __future__ import annotations

import os
from datetime import datetime
from typing import List, Tuple

import win32com.client

from src.domain.models import DVR
from src.infra.app_config import AppConfig


# ─── Composição ────────────────────────────────────────────────────────────────

def _compor(dvrs: List[DVR], config: AppConfig) -> Tuple[str, str]:
    """Retorna (assunto, corpo) com base nos dados dos DVRs."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    hora = datetime.now().hour
    saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

    total_dvrs = len(dvrs)
    total_cameras = 0
    cameras_ok = 0
    cameras_alerta = 0
    cameras_sem_conexao = 0
    cameras_nao_instaladas = 0

    dvrs_hd_problema: List[str] = []
    dvrs_hd_nao_verificado: List[str] = []   # DVRs offline → HD não pôde ser checado
    resumo_cameras: List[str] = []

    tem_falha_hd = False
    tem_dvr_sem_conexao = False
    tem_camera_nao_reconhecida = False

    for dvr in dvrs:
        # ── Categorização do status do HD ──
        # OFFLINE → não é problema de HD; é problema de conexão. Só registramos
        #           que o HD não pôde ser verificado.
        # ONLINE com status != NORMAL → problema REAL de HD (ATENÇÃO HD).
        if dvr.hd.status.startswith("OFFLINE"):
            tem_dvr_sem_conexao = True
            dvrs_hd_nao_verificado.append(f"- {dvr.nome}: {dvr.hd.status}")
        elif dvr.hd.status.startswith("ONLINE") and dvr.hd.status != "ONLINE - NORMAL":
            tem_falha_hd = True
            dvrs_hd_problema.append(
                f"- {dvr.nome}: {dvr.hd.status} "
                f"(Total: {dvr.hd.total} | Livre: {dvr.hd.livre})"
            )

        cams_problema: List[str] = []

        for cam in dvr.cameras:
            total_cameras += 1

            if cam.status == "OK":
                cameras_ok += 1
            elif cam.status == "NAO_INSTALADA":
                # Câmera marcada manualmente como inexistente fisicamente.
                # NÃO conta como alerta nem entra no resumo de problemas —
                # é só uma contagem informativa.
                cameras_nao_instaladas += 1
            elif cam.status == "SEM_CONEXAO":
                cameras_sem_conexao += 1
                tem_dvr_sem_conexao = True
                cameras_alerta += 1
                cams_problema.append(f"{cam.nome} (SEM CONEXÃO)")
            elif cam.status == "NAO_RECONHECIDA":
                cameras_alerta += 1
                tem_camera_nao_reconhecida = True
                cams_problema.append(f"{cam.nome} (NÃO RECONHECIDA)")
            else:
                cameras_alerta += 1
                cams_problema.append(f"{cam.nome} ({cam.status})")

        if cams_problema:
            resumo_cameras.append(
                f"\n📡 DVR: {dvr.nome}\n  " + "\n  ".join(cams_problema)
            )

    tem_hd_erro = len(dvrs_hd_problema) > 0

    assunto = (
        f"🚨 Checklist DVRs {config.nome_instalacao} – ATENÇÃO HD ({hoje})"
        if tem_hd_erro
        else f"📡 Checklist DVRs {config.nome_instalacao} – Status Geral ({hoje})"
    )

    corpo = f"""{saudacao},

Segue o checklist unificado de verificação dos DVRs {config.nome_instalacao} e câmeras
referente à data de hoje ({hoje}).

📊 RESUMO GERAL
- DVRs analisados: {total_dvrs}
- Total de câmeras: {total_cameras}
- Câmeras OK: {cameras_ok}
- Câmeras com alerta: {cameras_alerta}
- Câmeras sem conexão: {cameras_sem_conexao}
- Câmeras não instaladas: {cameras_nao_instaladas}
"""

    if dvrs_hd_problema:
        corpo += "\n⚠ DVRs COM PROBLEMA DE HD:\n"
        corpo += "\n".join(dvrs_hd_problema)
    else:
        corpo += "\n✅ Nenhum DVR com problema de HD identificado.\n"

    if dvrs_hd_nao_verificado:
        corpo += "\n\nℹ HD NÃO VERIFICADO (DVR offline):\n"
        corpo += "\n".join(dvrs_hd_nao_verificado)
        corpo += (
            "\n\n(O estado do HD desses DVRs não pôde ser verificado "
            "porque o equipamento não respondeu ao acesso remoto.)\n"
        )

    if resumo_cameras:
        corpo += "\n⚠ CÂMERAS COM ALERTA IDENTIFICADO:\n"
        corpo += "\n".join(resumo_cameras)
    else:
        corpo += "\n✅ Nenhuma câmera com problema identificada.\n"

    corpo += "\n📎 O relatório visual completo segue em anexo (PDF).\n"

    if tem_dvr_sem_conexao:
        corpo += """
⚠ DVR(s) SEM CONEXÃO IDENTIFICADO(S)

Para os DVRs listados acima sem comunicação, solicitamos verificar se o
equipamento encontra-se ligado e energizado.

Caso esteja ligado e ainda assim permaneça sem conexão, será necessário
acionar o PCM para abertura de SC e agendamento de visita da equipe
de câmeras.

Em caso de dificuldades relacionadas à rede ou conectividade, a T.I.
permanece à disposição para auxiliar.
"""

    if tem_camera_nao_reconhecida:
        corpo += """
⚠ CÂMERAS NÃO RECONHECIDAS

Para as câmeras listadas como "não reconhecidas", solicitamos a avaliação
do responsável pela área para confirmar se a câmera existe fisicamente
no local e se deveria estar em operação.

Confirmada a existência, será necessário acionar o PCM por e-mail para
requisitar a manutenção da câmera.

Caso a câmera não exista mais, pedimos que nos informem para atualização
dos registros.
"""

    if tem_falha_hd:
        corpo += """
🚨 FALHA DE HD IDENTIFICADA – AÇÃO IMEDIATA

Foi identificada falha no HD de armazenamento em um ou mais DVRs.
Nesta condição, as imagens NÃO estão sendo registradas.

Solicitamos o acionamento imediato do PCM para abertura de SC
e agendamento da equipe de câmeras para substituição ou correção do HD.

Caso seja necessário apoio técnico (rede/acesso), a T.I. permanece
à disposição.
"""

    corpo += """
Atenciosamente,

Filipe Macedo
TI
"""

    return assunto, corpo


# ─── Envio ─────────────────────────────────────────────────────────────────────

def enviar_email(
    dvrs: List[DVR],
    pdf_path: str,
    config: AppConfig,
    book_path: str = "",
) -> str:
    """
    Compõe o e-mail de checklist, grava backup em config.logs_dir e envia
    via Outlook.

    Args:
        dvrs:      DVRs do checklist (gera o corpo do e-mail)
        pdf_path:  PDF do Checklist principal (sempre anexado)
        config:    config da instalação (emails, paths)
        book_path: PDF do Book (opcional — quando passado, vai como 2º anexo)

    Retorna o caminho do arquivo de backup gravado em config.logs_dir.
    """
    assunto, corpo = _compor(dvrs, config)

    anexos = [os.path.abspath(pdf_path)]
    if book_path:
        anexos.append(os.path.abspath(book_path))

    # ── Backup em disco ──
    if not config.logs_dir:
        raise ValueError(
            "config.logs_dir está vazio. "
            "Edite a instalação na UI e preencha 'Dir. logs'."
        )
    os.makedirs(config.logs_dir, exist_ok=True)
    agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    arquivo_backup = os.path.join(config.logs_dir, f"email_{agora}.txt")

    with open(arquivo_backup, "w", encoding="utf-8") as f:
        f.write("===== BACKUP DE EMAIL =====\n\n")
        f.write("DATA/HORA:\n")
        f.write(agora + "\n\n")
        f.write("ASSUNTO:\n")
        f.write(assunto + "\n\n")
        f.write("DESTINATÁRIOS:\n")
        f.write(";".join(config.emails) + "\n\n")
        f.write("ANEXOS:\n")
        for a in anexos:
            f.write(a + "\n")
        f.write("\n")
        f.write("CORPO DO EMAIL:\n")
        f.write(corpo + "\n")

    # ── Envio via Outlook ──
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = ";".join(config.emails)
    mail.Subject = assunto
    mail.Body = corpo
    for caminho in anexos:
        mail.Attachments.Add(caminho)
    mail.Send()

    return arquivo_backup
