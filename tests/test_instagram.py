"""Testes do Radar Instagram (instagram.py) — Graph API mockada."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import instagram as ig


class TestDisponivel:
    def test_falso_sem_credenciais(self, monkeypatch):
        monkeypatch.delenv("INSTAGRAM_TOKEN", raising=False)
        monkeypatch.delenv("INSTAGRAM_IG_USER_ID", raising=False)
        assert ig.disponivel() is False
        assert ig.buscar_hashtag("concursopetrobras") == []

    def test_verdadeiro_com_credenciais(self, monkeypatch):
        monkeypatch.setenv("INSTAGRAM_TOKEN", "tok")
        monkeypatch.setenv("INSTAGRAM_IG_USER_ID", "123")
        assert ig.disponivel() is True


class TestBuscarHashtag:
    def test_busca_e_mapeia(self, monkeypatch):
        monkeypatch.setenv("INSTAGRAM_TOKEN", "tok")
        monkeypatch.setenv("INSTAGRAM_IG_USER_ID", "123")
        respostas = iter([
            {"data": [{"id": "h1"}]},
            {"data": [{
                "caption": "Edital saiu! #concursopetrobras",
                "permalink": "https://instagram.com/p/abc",
                "timestamp": "2026-06-16T10:00:00+0000",
                "media_type": "IMAGE",
            }]},
        ])
        monkeypatch.setattr(ig, "_get", lambda url, params: next(respostas))
        posts = ig.buscar_hashtag("concursopetrobras")
        assert len(posts) == 1
        assert posts[0]["permalink"].endswith("/abc")
        assert posts[0]["tag"] == "concursopetrobras"

    def test_erro_de_api_nao_quebra(self, monkeypatch):
        monkeypatch.setenv("INSTAGRAM_TOKEN", "tok")
        monkeypatch.setenv("INSTAGRAM_IG_USER_ID", "123")
        def _boom(url, params):
            raise RuntimeError("rate limit")
        monkeypatch.setattr(ig, "_get", _boom)
        out = ig.buscar_hashtag("x")
        assert out and "erro" in out[0]


class TestMonitorar:
    def test_deduplica_por_permalink(self, monkeypatch):
        monkeypatch.setenv("INSTAGRAM_TOKEN", "tok")
        monkeypatch.setenv("INSTAGRAM_IG_USER_ID", "123")
        post = {"tag": "t", "caption": "x", "permalink": "https://instagram.com/p/1", "timestamp": "", "tipo": ""}
        monkeypatch.setattr(ig, "buscar_hashtag", lambda tag, limite=10: [dict(post, tag=tag)])
        uniq = ig.monitorar(["a", "b"])  # mesmo permalink → 1
        assert len(uniq) == 1


class TestGravarRadar:
    def test_grava_nota(self, tmp_path):
        posts = [{"tag": "concursopetrobras", "caption": "Novo material!", "permalink": "https://instagram.com/p/z", "timestamp": "2026-06-16T00:00:00+0000", "tipo": "IMAGE"}]
        nome = ig.gravar_radar(posts, vault=tmp_path)
        assert nome.exists()
        texto = nome.read_text(encoding="utf-8")
        assert "Radar Instagram" in texto
        assert "instagram.com/p/z" in texto
