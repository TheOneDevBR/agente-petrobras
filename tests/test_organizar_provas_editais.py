"""Testes do organizador de provas/editais Petrobras por cargo."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import organizar_provas_editais as OPE  # noqa: E402


class TestParseItem:
    def test_prova_cesgranrio(self):
        url = "https://x/cesgranrio-2018-petrobras-engenheiro-de-petroleo-junior-prova.pdf"
        it = OPE.parse_item_de_url(url)
        assert it is not None
        assert it.ano == "2018"
        assert it.tipo == "Provas"
        assert it.banca == "CESGRANRIO"
        assert it.cargo == "Engenheiro De Petroleo Junior"

    def test_gabarito_cebraspe(self):
        url = "https://x/cespe-cebraspe-2022-petrobras-engenharia-de-petroleo-gabarito.pdf"
        it = OPE.parse_item_de_url(url)
        assert it.tipo == "Gabaritos"
        assert it.ano == "2022"
        assert "Engenharia De Petroleo" in it.cargo

    def test_url_nao_reconhecida(self):
        assert OPE.parse_item_de_url("https://x/documento-qualquer.pdf") is None


class TestNomeArquivo:
    def test_url_direta(self):
        assert OPE.nome_arquivo_de_url("https://x/y/prova-2018.pdf") == "prova-2018.pdf"

    def test_storage_ashx_preserva_nome_original(self):
        url = ("https://inscricao.cesgranrio.com.br/storage.ashx?file=pdf%2F"
               "petrobras0118%2Fpetrobras0118_edital.pdf")
        assert OPE.nome_arquivo_de_url(url) == "petrobras0118_edital.pdf"


class TestCatalogo:
    def test_inclui_oficial_e_derivados(self):
        urls = ["https://x/cesgranrio-2018-petrobras-advogado-junior-prova.pdf"]
        cat = OPE.montar_catalogo(urls)
        fontes = {it.fonte for it in cat}
        assert "oficial" in fontes  # edital oficial do catálogo
        assert any(it.cargo == "Advogado Junior" for it in cat)
        # pendente 2023 marcado como indisponível, não omitido
        assert any(it.status == "indisponível" and it.ano == "2023" for it in cat)


class TestOrganizar:
    def test_roteia_por_cargo_e_cria_sidecar(self, tmp_path):
        itens = [OPE.Item(ano="2018", cargo="Quimico De Petroleo Junior", tipo="Provas",
                          url="https://x/cesgranrio-2018-petrobras-quimico-de-petroleo-junior-prova.pdf",
                          banca="CESGRANRIO", fonte="espelho")]

        def fake_baixar(url, destino):
            destino.write_bytes(b"%PDF-fake")
            return True

        OPE.organizar(itens, raiz=tmp_path, baixar=True, baixar_fn=fake_baixar)
        esperado = (tmp_path / "Petrobras_2018" / "Quimico De Petroleo Junior" /
                    "Provas" / "cesgranrio-2018-petrobras-quimico-de-petroleo-junior-prova.pdf")
        assert esperado.exists()
        assert itens[0].status == "concluído"
        sidecar = esperado.parent / f"{esperado.name}.fonte.txt"
        assert sidecar.exists()
        assert "url_origem: https://x/" in sidecar.read_text(encoding="utf-8")

    def test_download_falho_marca_indisponivel(self, tmp_path):
        itens = [OPE.Item(ano="2018", cargo="Contador Junior", tipo="Provas",
                          url="https://x/cesgranrio-2018-petrobras-contador-junior-prova.pdf")]
        OPE.organizar(itens, raiz=tmp_path, baixar=True, baixar_fn=lambda u, d: False)
        assert itens[0].status == "indisponível"

    def test_indisponivel_nao_baixa(self, tmp_path):
        itens = [OPE.Item(ano="2023", cargo="Geral", tipo="Editais", url="https://x",
                          status="indisponível")]
        chamou = []
        OPE.organizar(itens, raiz=tmp_path, baixar=True,
                      baixar_fn=lambda u, d: chamou.append(1) or True)
        assert chamou == []
        assert itens[0].status == "indisponível"


class TestIndice:
    def test_gera_csv_com_colunas_e_status(self, tmp_path):
        itens = [
            OPE.Item(ano="2018", cargo="Advogado Junior", tipo="Provas", url="https://x/a.pdf",
                     banca="CESGRANRIO", edital_num="PSP 1/2018", arquivo="a.pdf", status="concluído"),
            OPE.Item(ano="2023", cargo="Geral", tipo="Editais", url="https://petrobras.com.br",
                     status="indisponível"),
        ]
        csv_path = OPE.gerar_indice_csv(itens, tmp_path / "indice.csv")
        linhas = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert linhas[0]["cargo"] == "Advogado Junior"
        assert linhas[0]["status"] == "concluído"
        assert linhas[0]["url_origem"] == "https://x/a.pdf"
        assert any(l["status"] == "indisponível" for l in linhas)
