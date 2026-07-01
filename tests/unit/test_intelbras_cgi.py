"""Unit tests for src/core/intelbras_cgi.py"""
from src.core import intelbras_cgi


_GB = 1024 ** 3


def _fetch_fixo(texto):
    """Devolve um fetch que sempre retorna `texto`, ignorando a URL."""
    def _fetch(url, usuario, senha):
        return texto
    return _fetch


def test_parse_hd_normal_calcula_total_e_livre():
    total = 4 * _GB
    used = 1 * _GB
    texto = (
        "list.info[0].State=Normal\n"
        f"list.info[0].Detail[0].TotalBytes={total}\n"
        f"list.info[0].Detail[0].UsedBytes={used}\n"
    )
    hd = intelbras_cgi.ler_hd("1.2.3.4", "80", "admin", "x", fetch=_fetch_fixo(texto))

    assert hd.status == "ONLINE - NORMAL"
    assert hd.total == "4.00 GB"
    assert hd.livre == "3.00 GB"   # 4 - 1 usado


def test_parse_soma_multiplos_discos():
    texto = (
        "list.info[0].State=Normal\n"
        f"list.info[0].Detail[0].TotalBytes={2 * _GB}\n"
        f"list.info[0].Detail[0].UsedBytes={1 * _GB}\n"
        "list.info[1].State=Normal\n"
        f"list.info[1].Detail[0].TotalBytes={2 * _GB}\n"
        f"list.info[1].Detail[0].UsedBytes={0}\n"
    )
    hd = intelbras_cgi.ler_hd("1.2.3.4", "80", "a", "b", fetch=_fetch_fixo(texto))

    assert hd.total == "4.00 GB"
    assert hd.livre == "3.00 GB"


def test_estado_nao_normal_marca_erro_de_hd():
    texto = (
        "list.info[0].State=Error\n"
        f"list.info[0].Detail[0].TotalBytes={2 * _GB}\n"
        f"list.info[0].Detail[0].UsedBytes={1 * _GB}\n"
    )
    hd = intelbras_cgi.ler_hd("1.2.3.4", "80", "a", "b", fetch=_fetch_fixo(texto))

    assert hd.status == "ONLINE - ERRO (HD)"


def test_sem_dados_de_bytes_vira_erro_de_hd():
    hd = intelbras_cgi.ler_hd("1.2.3.4", "80", "a", "b", fetch=_fetch_fixo("vazio\n"))
    assert hd.status == "ONLINE - ERRO (HD)"


def test_falha_de_rede_vira_sem_resposta():
    def _fetch_explode(url, usuario, senha):
        raise OSError("connection refused")

    hd = intelbras_cgi.ler_hd("1.2.3.4", "80", "a", "b", fetch=_fetch_explode)
    assert hd.status == "OFFLINE - SEM RESPOSTA"
