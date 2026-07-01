"""
Testes de unidade para src/infra/backup.py

Cobre:
  - exportar() → JSON válido com todos os campos
  - importar() → restaura objetos Instalacao/DVR/emails
  - roundtrip  → exportar → importar produz objetos equivalentes
  - erros      → JSON inválido / versão incompatível
  - merge      → restaurar_no_repo pula nomes já existentes
"""
from __future__ import annotations

import json
import pytest

from src.domain.instalacao import Instalacao
from src.domain.models import DVR


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_inst(nome: str = "TESTE", n_dvrs: int = 2) -> Instalacao:
    return Instalacao(
        nome=nome,
        usuario="admin",
        senha="1234",
        porta_http="3077",
        porta_rtsp="3078",
        ffmpeg_path="/assets/ffmpeg/bin/ffmpeg.exe",
        playwright_path="/assets/playwright_browsers",
        base_dir="/data/teste/temp",
        relatorios_dir="/data/teste/relatorios",
        logs_dir="/data/teste/logs",
        error_img="/assets/error.jpg",
        dvrs=[DVR(f"DVR_{i}", f"10.0.0.{200+i}", 16) for i in range(n_dvrs)],
        emails=["a@b.com", "c@d.com"],
    )


# ─── exportar ────────────────────────────────────────────────────────────────

class TestExportar:
    def test_retorna_string_json_valido(self):
        from src.infra.backup import exportar
        resultado = exportar([_make_inst()])
        parsed = json.loads(resultado)           # não lança exceção
        assert isinstance(parsed, dict)

    def test_tem_chave_version(self):
        from src.infra.backup import exportar
        parsed = json.loads(exportar([_make_inst()]))
        assert "version" in parsed
        assert isinstance(parsed["version"], int)

    def test_tem_chave_instalacoes(self):
        from src.infra.backup import exportar
        parsed = json.loads(exportar([_make_inst()]))
        assert "instalacoes" in parsed
        assert isinstance(parsed["instalacoes"], list)

    def test_quantidade_instalacoes_correta(self):
        from src.infra.backup import exportar
        parsed = json.loads(exportar([_make_inst("A"), _make_inst("B")]))
        assert len(parsed["instalacoes"]) == 2

    def test_lista_vazia(self):
        from src.infra.backup import exportar
        parsed = json.loads(exportar([]))
        assert parsed["instalacoes"] == []

    def test_campos_scalares_presentes(self):
        from src.infra.backup import exportar
        inst = _make_inst("CAMPOS")
        parsed = json.loads(exportar([inst]))
        d = parsed["instalacoes"][0]
        for campo in ("nome", "usuario", "senha", "porta_http", "porta_rtsp",
                      "ffmpeg_path", "playwright_path", "base_dir",
                      "relatorios_dir", "logs_dir", "error_img"):
            assert campo in d, f"Campo ausente: {campo}"

    def test_dvrs_serializados(self):
        from src.infra.backup import exportar
        inst = _make_inst(n_dvrs=3)
        parsed = json.loads(exportar([inst]))
        dvrs = parsed["instalacoes"][0]["dvrs"]
        assert len(dvrs) == 3
        assert dvrs[0]["nome"] == "DVR_0"
        assert dvrs[0]["ip"] == "10.0.0.200"
        assert dvrs[0]["qtd_cameras"] == 16

    def test_emails_serializados(self):
        from src.infra.backup import exportar
        parsed = json.loads(exportar([_make_inst()]))
        emails = parsed["instalacoes"][0]["emails"]
        assert emails == ["a@b.com", "c@d.com"]

    def test_id_nao_exportado(self):
        """id do banco não deve constar no JSON (evita conflito na restauração)."""
        from src.infra.backup import exportar
        inst = _make_inst()
        inst.id = 42
        parsed = json.loads(exportar([inst]))
        assert "id" not in parsed["instalacoes"][0]


# ─── importar ────────────────────────────────────────────────────────────────

class TestImportar:
    def _json_valido(self, nome="IMP") -> str:
        from src.infra.backup import exportar
        return exportar([_make_inst(nome)])

    def test_retorna_lista_de_instalacoes(self):
        from src.infra.backup import importar
        resultado = importar(self._json_valido())
        assert isinstance(resultado, list)
        assert len(resultado) == 1
        assert isinstance(resultado[0], Instalacao)

    def test_campos_scalares_restaurados(self):
        from src.infra.backup import importar
        inst = importar(self._json_valido("SCALAR"))[0]
        assert inst.nome == "SCALAR"
        assert inst.usuario == "admin"
        assert inst.senha == "1234"
        assert inst.porta_http == "3077"
        assert inst.porta_rtsp == "3078"

    def test_dvrs_restaurados(self):
        from src.infra.backup import importar
        inst = importar(self._json_valido())[0]
        assert len(inst.dvrs) == 2
        assert isinstance(inst.dvrs[0], DVR)
        assert inst.dvrs[0].nome == "DVR_0"
        assert inst.dvrs[0].qtd_cameras == 16

    def test_emails_restaurados(self):
        from src.infra.backup import importar
        inst = importar(self._json_valido())[0]
        assert inst.emails == ["a@b.com", "c@d.com"]

    def test_id_sempre_zero(self):
        """Instalação importada deve ter id=0 para ser INSERTed como nova."""
        from src.infra.backup import importar
        inst = importar(self._json_valido())[0]
        assert inst.id == 0

    def test_json_invalido_levanta_value_error(self):
        from src.infra.backup import importar
        with pytest.raises(ValueError, match="JSON"):
            importar("não é json {{{")

    def test_json_sem_chave_instalacoes_levanta_value_error(self):
        from src.infra.backup import importar
        with pytest.raises(ValueError):
            importar(json.dumps({"version": 1}))

    def test_versao_incompativel_levanta_value_error(self):
        from src.infra.backup import importar, VERSAO_BACKUP
        payload = json.dumps({"version": VERSAO_BACKUP + 99, "instalacoes": []})
        with pytest.raises(ValueError, match="[Vv]ers"):
            importar(payload)

    def test_lista_vazia(self):
        from src.infra.backup import importar
        resultado = importar(json.dumps({"version": 1, "instalacoes": []}))
        assert resultado == []


# ─── roundtrip ────────────────────────────────────────────────────────────────

class TestRoundtrip:
    def test_roundtrip_preserva_instalacao_completa(self):
        from src.infra.backup import exportar, importar
        original = _make_inst("ROUNDTRIP", n_dvrs=4)
        original.emails = ["x@x.com"]
        restaurado = importar(exportar([original]))[0]

        assert restaurado.nome == original.nome
        assert restaurado.usuario == original.usuario
        assert restaurado.senha == original.senha
        assert restaurado.porta_http == original.porta_http
        assert restaurado.porta_rtsp == original.porta_rtsp
        assert restaurado.ffmpeg_path == original.ffmpeg_path
        assert restaurado.playwright_path == original.playwright_path
        assert restaurado.base_dir == original.base_dir
        assert restaurado.relatorios_dir == original.relatorios_dir
        assert restaurado.logs_dir == original.logs_dir
        assert restaurado.error_img == original.error_img
        assert len(restaurado.dvrs) == len(original.dvrs)
        assert restaurado.emails == original.emails

    def test_roundtrip_multiplas_instalacoes(self):
        from src.infra.backup import exportar, importar
        originais = [_make_inst(f"INST_{i}") for i in range(3)]
        restaurados = importar(exportar(originais))
        assert [i.nome for i in restaurados] == [i.nome for i in originais]

    def test_roundtrip_preserva_chave_de_criptografia_do_dvr(self):
        """Backup/restauração mantém a chave_criptografia de cada DVR."""
        from src.infra.backup import exportar, importar

        original = Instalacao(
            nome="COM_CHAVE",
            dvrs=[
                DVR(nome="HIK1", ip="1.1.1.1", qtd_cameras=4,
                    chave_criptografia="CHAVE_ABC_123"),
                DVR(nome="HIK2", ip="2.2.2.2", qtd_cameras=8,
                    chave_criptografia=""),  # sem chave também round-trips
            ],
        )
        restaurado = importar(exportar([original]))[0]
        assert restaurado.dvrs[0].chave_criptografia == "CHAVE_ABC_123"
        assert restaurado.dvrs[1].chave_criptografia == ""


# ─── restaurar_no_repo ────────────────────────────────────────────────────────

class TestRestaurarNoRepo:
    """
    restaurar_no_repo(instalacoes, repo) → (inseridos, pulados)
    Pula instalações cujo nome já existe no banco.
    """

    def _repo(self, tmp_path):
        from src.infra.instalacao_repo import InstalacaoRepository
        return InstalacaoRepository(str(tmp_path / "bkp.db"))

    def test_insere_novas_instalacoes(self, tmp_path):
        from src.infra.backup import restaurar_no_repo
        repo = self._repo(tmp_path)
        inseridos, pulados = restaurar_no_repo([_make_inst("NOVA")], repo)
        assert inseridos == 1
        assert pulados == 0
        assert len(repo.listar()) == 1

    def test_pula_nome_ja_existente(self, tmp_path):
        from src.infra.backup import restaurar_no_repo
        repo = self._repo(tmp_path)
        repo.salvar(_make_inst("EXISTE"))
        inseridos, pulados = restaurar_no_repo([_make_inst("EXISTE")], repo)
        assert inseridos == 0
        assert pulados == 1
        assert len(repo.listar()) == 1   # não duplicou

    def test_mistura_novas_e_existentes(self, tmp_path):
        from src.infra.backup import restaurar_no_repo
        repo = self._repo(tmp_path)
        repo.salvar(_make_inst("VELHA"))
        inseridos, pulados = restaurar_no_repo(
            [_make_inst("VELHA"), _make_inst("NOVA")], repo
        )
        assert inseridos == 1
        assert pulados == 1
        assert len(repo.listar()) == 2

    def test_lista_vazia_nao_altera_banco(self, tmp_path):
        from src.infra.backup import restaurar_no_repo
        repo = self._repo(tmp_path)
        inseridos, pulados = restaurar_no_repo([], repo)
        assert inseridos == 0
        assert pulados == 0
