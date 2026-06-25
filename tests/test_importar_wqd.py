"""Testes do importador WQD (lógica pura; rede/login não são tocados)."""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import importar_wqd as W  # noqa: E402


def _jwt(payload: dict) -> str:
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'none'})}.{b64(payload)}.sig"


class TestJWT:
    def test_decodifica_locale(self):
        tok = _jwt({"locale": "BR", "email": "x@y.com"})
        assert W._decode_jwt_payload(tok)["locale"] == "BR"

    def test_token_invalido(self):
        import pytest
        with pytest.raises(W.WQDError):
            W._decode_jwt_payload("nao-e-um-jwt")


class TestBody:
    def test_estrutura_real(self):
        b = W.montar_body("1319588", q="crase")
        assert b["locale"] == "1319588"
        assert b["q"] == "crase"
        assert b["classe"] == "concursos"
        assert b["start"] == 1
        # assinante é OBJETO (não string), formato confirmado via DevTools
        assert b["assinante"] == {"ativo": "0", "count_question": "0"}

    def test_assinante_customizado(self):
        b = W.montar_body("BR", assinante={"ativo": "1", "count_question": "5"})
        assert b["assinante"]["ativo"] == "1"


class TestAcharLista:
    def test_es_hits(self):
        resp = {"data": {"hits": {"hits": [{"_source": {"enunciado": "Q1"}}]}}}
        assert W._achar_lista_questoes(resp) == [{"enunciado": "Q1"}]

    def test_questoes_direto(self):
        resp = {"questoes": [{"enunciado": "Q1"}, {"enunciado": "Q2"}]}
        assert len(W._achar_lista_questoes(resp)) == 2

    def test_null_ou_vazio(self):
        assert W._achar_lista_questoes(None) == []
        assert W._achar_lista_questoes({"data": {}}) == []


class TestFlatten:
    def test_desembrulha_fields_array(self):
        src = {"id": "x", "fields": {"tipo": ["Multipla Escolha"], "banca": ["FUNDATEC"],
                                     "enunciado": ["O que é crase?"]}}
        flat = W._flatten_fields(src)
        assert flat["tipo"] == "Multipla Escolha"
        assert flat["banca"] == "FUNDATEC"
        assert flat["enunciado"] == "O que é crase?"
        assert flat["id"] == "x"

    def test_hit_es_via_converter(self):
        # estrutura real: _source com fields em arrays
        src = {"fields": {"enunciado": ["Pergunta?"],
                          "alternativaa": ["aa"], "alternativab": ["bb"],
                          "alternativac": ["cc"], "alternativad": ["dd"],
                          "alternativae": ["ee"], "gabarito": ["C"]}}
        q = W.converter_questao(src)
        assert q is not None
        assert q["correta"] == 2
        assert q["opcoes"][2] == "cc"


class TestConverter:
    def test_questao_valida_com_gabarito_letra(self):
        item = {"enunciado": "Qual o maior?",
                "alternativas": ["um", "dois", "três", "quatro", "cinco"],
                "gabarito": "E", "disciplina": "Matemática"}
        q = W.converter_questao(item)
        assert q["pergunta"] == "Qual o maior?"
        assert q["correta"] == 4
        assert q["opcoes"][4] == "cinco"
        assert q["origem"] == "wqd"
        assert "wqd" in q["tags"]

    def test_gabarito_indice_int(self):
        item = {"pergunta": "X?", "opcoes": ["a", "b", "c"], "correta": 1}
        assert W.converter_questao(item)["correta"] == 1

    def test_sem_gabarito_descarta(self):
        item = {"enunciado": "Sem resposta", "alternativas": ["a", "b"]}
        assert W.converter_questao(item) is None

    def test_alternativas_como_objetos(self):
        item = {"enunciado": "Y?",
                "alternativas": [{"texto": "aa"}, {"texto": "bb"}],
                "gabarito": "A"}
        q = W.converter_questao(item)
        assert q["opcoes"] == ["aa", "bb"]
