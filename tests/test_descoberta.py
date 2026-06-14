"""Testes da descoberta automática de fontes (descoberta.py)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import descoberta as D  # noqa: E402


class TestExtrairDominio:
    def test_remove_www(self):
        assert D.extrair_dominio("https://www.jcconcursos.com.br/noticia/x") == "jcconcursos.com.br"

    def test_sem_esquema(self):
        assert D.extrair_dominio("nao-e-url") == ""


class TestRegistrar:
    def test_filtra_ruido(self):
        est = {}
        novos = D.registrar(
            ["https://www.reddit.com/r/x", "https://login.microsoft.com", "https://google.com/s"],
            estado=est, persistir=False)
        assert novos == [] and est == {}

    def test_ignora_dominios_conhecidos(self):
        est = {}
        with patch.object(D, "_dominios_conhecidos", return_value={"pciconcursos.com.br"}):
            novos = D.registrar(["https://www.pciconcursos.com.br/provas"], estado=est, persistir=False)
        assert novos == []

    def test_acumula_novos(self):
        est = {}
        with patch.object(D, "_dominios_conhecidos", return_value=set()):
            D.registrar(["https://jcconcursos.com.br/a"], contexto="noticias", estado=est, persistir=False)
            D.registrar(["https://jcconcursos.com.br/b"], contexto="editais", estado=est, persistir=False)
        reg = est["jcconcursos.com.br"]
        assert reg["ocorrencias"] == 2
        assert set(reg["contextos"]) == {"noticias", "editais"}

    def test_promove_apos_min(self):
        est = {}
        with patch.object(D, "_dominios_conhecidos", return_value=set()):
            for _ in range(D.MIN_PROMOCAO):
                D.registrar(["https://folhadirigida.com.br/x"], estado=est, persistir=False)
        assert est["folhadirigida.com.br"]["promovida"] is True


class TestPromovidas:
    def test_ordena_por_ocorrencia(self):
        est = {
            "a.com.br": {"ocorrencias": 5, "promovida": True},
            "b.com.br": {"ocorrencias": 9, "promovida": True},
            "c.com.br": {"ocorrencias": 1, "promovida": False},
        }
        assert D.promovidas(estado=est) == ["b.com.br", "a.com.br"]


class TestPersistenciaRelatorio:
    def test_round_trip(self, tmp_path):
        est = {}
        with patch.object(D, "_dominios_conhecidos", return_value=set()):
            D.registrar(["https://novosite.com.br/x"], estado=est, persistir=False)
        p = tmp_path / "f.json"
        D.salvar(est, p)
        assert "novosite.com.br" in D.carregar(p)

    def test_relatorio_vazio(self):
        assert "Nenhuma fonte nova" in D.relatorio(estado={})

    def test_relatorio_com_dados(self):
        est = {"x.com.br": {"ocorrencias": 4, "contextos": ["noticias"], "promovida": True}}
        txt = D.relatorio(estado=est)
        assert "FONTES DESCOBERTAS" in txt and "x.com.br" in txt
