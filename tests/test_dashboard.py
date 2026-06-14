"""Testes do módulo dashboard.

O módulo executa código top-level com streamlit, então precisa de mocks
pesados antes do carregamento. Usamos importlib para definir ``simulados``
previamente e evitar NameError (a variável só é definida na linha 375).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── Mocks de dependências gráficas ──────────────────────────────────────
_mock_st = MagicMock()
_mock_st.sidebar = MagicMock()
_mock_st.columns.side_effect = lambda n: tuple(MagicMock() for _ in range(n))
_mock_st.tabs.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())

_mock_st.form_submit_button = MagicMock(return_value=False)
for _name in ("container", "expander", "spinner"):
    _cm = MagicMock()
    _cm.__enter__.return_value = MagicMock()
    _cm.__exit__.return_value = None
    setattr(_mock_st, _name, MagicMock(return_value=_cm))

sys.modules["streamlit"] = _mock_st
sys.modules["plotly"] = MagicMock()
sys.modules["plotly.express"] = MagicMock()
sys.modules["plotly.graph_objects"] = MagicMock()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

# ── Carrega o módulo com importlib para evitar NameError ─────────────────
import importlib.util

_DASH_PATH = Path(__file__).resolve().parent.parent / "cli_python" / "dashboard.py"
_spec = importlib.util.spec_from_file_location("dashboard", _DASH_PATH)
dashboard = importlib.util.module_from_spec(_spec)
dashboard.simulados = []
sys.modules["dashboard"] = dashboard
_spec.loader.exec_module(dashboard)

_ler_json = dashboard._ler_json


class TestImport:
    """O módulo carrega sem erro com os mocks adequados."""

    def test_modulo_importado(self):
        assert dashboard.__name__ == "dashboard"

    def test_helpers_disponiveis(self):
        assert callable(_ler_json)


class TestLerJson:
    """Testes da função auxiliar _ler_json (única função pura do módulo)."""

    def test_arquivo_valido_retorna_dict(self, tmp_path):
        arquivo = tmp_path / "dados.json"
        arquivo.write_text('{"chave": "valor", "num": 42}', encoding="utf-8")
        assert _ler_json(arquivo, {}) == {"chave": "valor", "num": 42}

    def test_arquivo_valido_retorna_lista(self, tmp_path):
        arquivo = tmp_path / "lista.json"
        arquivo.write_text('[1, 2, 3]', encoding="utf-8")
        assert _ler_json(arquivo, []) == [1, 2, 3]

    def test_arquivo_inexistente_retorna_default(self, tmp_path):
        inexistente = tmp_path / "nao_existe.json"
        default = {"fallback": True}
        assert _ler_json(inexistente, default) is default

    def test_json_invalido_retorna_default(self, tmp_path):
        arquivo = tmp_path / "invalido.json"
        arquivo.write_text("não é json válido", encoding="utf-8")
        assert _ler_json(arquivo, "fallback") == "fallback"

    def test_arquivo_vazio_retorna_default(self, tmp_path):
        arquivo = tmp_path / "vazio.json"
        arquivo.write_text("", encoding="utf-8")
        assert _ler_json(arquivo, None) is None

    def test_diretorio_em_vez_de_arquivo_retorna_default(self, tmp_path):
        diretorio = tmp_path / "subdir"
        diretorio.mkdir()
        assert _ler_json(diretorio, "fallback") == "fallback"

    def test_none_como_default(self, tmp_path):
        assert _ler_json(tmp_path / "inexistente.json", None) is None

    def test_default_vazio_lista(self, tmp_path):
        assert _ler_json(tmp_path / "inexistente.json", []) == []

    def test_tipos_aninhados(self, tmp_path):
        arquivo = tmp_path / "aninhado.json"
        arquivo.write_text('{"a": {"b": [1, 2, {"c": "d"}]}}', encoding="utf-8")
        resultado = _ler_json(arquivo, {})
        assert resultado["a"]["b"][2]["c"] == "d"
