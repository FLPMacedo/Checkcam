"""
Characterization tests for carregar_dvrs() and carregar_emails().
These are pure functions — they take a file path and return a list.
"""


def test_carregar_dvrs_retorna_lista_com_campos_corretos(legacy_module, tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_A;192.168.1.1;4\n", encoding="utf-8")
    result = legacy_module.carregar_dvrs(str(f))
    assert result == [{"nome": "DVR_A", "ip": "192.168.1.1", "cameras": 4}]


def test_carregar_dvrs_cameras_e_convertido_para_int(legacy_module, tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("DVR_B;10.0.0.1;8\n", encoding="utf-8")
    result = legacy_module.carregar_dvrs(str(f))
    assert isinstance(result[0]["cameras"], int)
    assert result[0]["cameras"] == 8


def test_carregar_dvrs_ignora_linhas_vazias_e_comentarios(legacy_module, tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text(
        "# comentario\n\nDVR_C;10.0.0.2;2\n\n# outro\n",
        encoding="utf-8",
    )
    result = legacy_module.carregar_dvrs(str(f))
    assert len(result) == 1
    assert result[0]["nome"] == "DVR_C"


def test_carregar_dvrs_multiplos(legacy_module, tmp_path):
    f = tmp_path / "dvrs.txt"
    f.write_text("A;1.1.1.1;4\nB;2.2.2.2;8\nC;3.3.3.3;16\n", encoding="utf-8")
    result = legacy_module.carregar_dvrs(str(f))
    assert len(result) == 3
    assert [d["nome"] for d in result] == ["A", "B", "C"]


def test_carregar_emails_retorna_lista_de_strings(legacy_module, tmp_path):
    f = tmp_path / "emails.txt"
    f.write_text("a@teste.com\nb@teste.com\n", encoding="utf-8")
    result = legacy_module.carregar_emails(str(f))
    assert result == ["a@teste.com", "b@teste.com"]


def test_carregar_emails_ignora_comentarios_e_linhas_vazias(legacy_module, tmp_path):
    f = tmp_path / "emails.txt"
    f.write_text("# lista\n\nc@teste.com\n\n# fim\n", encoding="utf-8")
    result = legacy_module.carregar_emails(str(f))
    assert result == ["c@teste.com"]
