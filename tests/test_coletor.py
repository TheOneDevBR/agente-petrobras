"""Testes do coletor de inteligência."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_COLETOR_PATH = Path(__file__).resolve().parent.parent / "cli_python" / "coletor" / "coletor.py"

def _load_coletor():
    """Load coletor.coletor as a module using importlib (avoids package path issues with xdist)."""
    spec = importlib.util.spec_from_file_location("coletor_mod", str(_COLETOR_PATH))
    mod = importlib.util.module_from_spec(spec)
    # Preserve original sys.path for sub-imports
    _old_path = sys.path.copy()
    sys.path.insert(0, str(_COLETOR_PATH.parent.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path = _old_path
    return mod


@pytest.fixture(scope="session")
def C():
    """Cached coletor module singleton."""
    return _load_coletor()


@pytest.fixture
def fontes_json(tmp_path):
    fontes = {
        "cargo_foco": "Engenheiro de Petróleo Júnior",
        "beats": [
            {"id": "editais", "titulo": "Editais", "tags": ["edital"], "instrucao": "Procure editais", "dominios_sugeridos": ["petrobras.com.br"]},
            {"id": "provas", "titulo": "Provas", "tags": ["prova"], "instrucao": "Procure provas"},
        ],
    }
    f_path = tmp_path / "fontes.json"
    f_path.write_text(json.dumps(fontes), encoding="utf-8")
    return f_path


class TestSlug:
    def test_slug_basico(self, C):
        assert C._slug("Editais e Cronogramas") == "editais-e-cronogramas"

    def test_slug_acentos(self, C):
        assert C._slug("Legislação Aplicável") == "legislacao-aplicavel"

    def test_slug_vazio(self, C):
        assert C._slug("") == "nota"


class TestExtrairResumo:
    def test_extrair_resumo_valido(self, C):
        corpo = "resumo_uma_linha: Edital publicado\n\n## Detalhes"
        assert C._extrair_resumo(corpo) == "Edital publicado"

    def test_extrair_resumo_ausente(self, C):
        assert C._extrair_resumo("## Titulo") == "(sem resumo)"


class TestFixNota:
    def test_fix_nota_adiciona_resumo(self, C):
        corpo = "Texto longo aqui com mais de 10 caracteres\n## Resumo executivo\nDetalhes"
        result = C._fix_nota(corpo)
        assert "resumo_uma_linha:" in result

    def test_fix_nota_remove_code_fences(self, C):
        corpo = "```markdown\nresumo_uma_linha: algo\n\n## Titulo\n```"
        result = C._fix_nota(corpo)
        assert result.startswith("resumo_uma_linha:")
        assert "```" not in result

    def test_fix_nota_vazio(self, C):
        assert C._fix_nota("") == ""


class TestBuscarParaBeat:
    def test_buscar_para_beat_sucesso(self, C, fontes_json):
        beat = {"id": "editais", "titulo": "Editais", "tags": ["edital"], "instrucao": "Procure", "dominios_sugeridos": ["petrobras.com.br"]}
        mock_results = [{"href": "https://exemplo.com", "title": "Noticia", "snippet": "Texto"}]

        with (
            patch.object(C, "web_search", return_value=mock_results),
            patch.object(C, "web_fetch", return_value="Conteudo extraido com mais de 200 caracteres. " * 20),
        ):
            result, _urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "Noticia" in result
        assert "Conteudo extraido" in result

    def test_buscar_usa_chave_url_do_format_result(self, C):
        # regressão: web_search/_format_result devolve a chave 'url' (não 'href'/'link').
        beat = {"id": "x", "titulo": "T", "tags": [], "instrucao": "i"}
        mock_results = [{"title": "Apostila", "url": "https://grancursosonline.com.br/x", "snippet": "s"}]
        with (
            patch.object(C, "web_search", return_value=mock_results),
            patch.object(C, "web_fetch", return_value="conteudo " * 60),
        ):
            texto, urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "https://grancursosonline.com.br/x" in urls
        assert "https://grancursosonline.com.br/x" in texto

    def test_buscar_para_beat_sem_resultados(self, C, fontes_json):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}

        with patch.object(C, "web_search", return_value=[]):
            result, _urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "Nenhum resultado encontrado" in result

    def test_buscar_para_beat_erro_rede(self, C, fontes_json):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}

        with patch.object(C, "web_search", side_effect=Exception("Timeout")):
            result, _urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "Nenhum resultado encontrado" in result

    def test_buscar_para_beat_erro_fetch_tratado(self, C, fontes_json):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        mock_results = [{"href": "https://exemplo.com", "title": "Site", "snippet": "Resumo"}]

        with (
            patch.object(C, "web_search", return_value=mock_results),
            patch.object(C, "web_fetch", side_effect=Exception("403 Forbidden")),
        ):
            result, _urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "erro ao acessar" in result

    def test_buscar_para_beat_fetch_conteudo_curto(self, C, fontes_json):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        mock_results = [{"href": "https://exemplo.com", "title": "Site", "snippet": "Curto"}]

        with (
            patch.object(C, "web_search", return_value=mock_results),
            patch.object(C, "web_fetch", return_value="curto"),
        ):
            result, _urls = C._buscar_para_beat(beat, max_resultados=2)
        assert "curto" not in result or "Conteudo extraído" not in result


class TestFetchRagContext:
    def test_fetch_rag_sucesso(self, C):
        beat = {"rag_sources": [{"url": "https://exemplo.com/lei", "descricao": "Lei 13.303"}]}

        with patch.object(C, "web_fetch", return_value="Art. 1 Esta lei... " * 200):
            result = C._fetch_rag_context(beat)
        assert "TEXTO_DA_LEI" in result
        assert "Lei 13.303" in result

    def test_fetch_rag_sem_fontes(self, C):
        assert C._fetch_rag_context({}) == ""
        assert C._fetch_rag_context({"rag_sources": []}) == ""

    def test_fetch_rag_erro(self, C):
        beat = {"rag_sources": [{"url": "https://exemplo.com", "descricao": "Fonte"}]}

        with patch.object(C, "web_fetch", side_effect=Exception("404")):
            result = C._fetch_rag_context(beat)
        assert result == ""


class TestColetarBeat:
    def test_coletar_beat_sucesso(self, C):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        cliente = MagicMock()
        cliente.chat.return_value = "resumo_uma_linha: Edital publicado\n\n## Resumo\nTexto"

        with (
            patch.object(C, "_buscar_para_beat", return_value=("resultados da busca", [])),
            patch.object(C, "_fetch_rag_context", return_value=""),
        ):
            result = C.coletar_beat(cliente, beat, "Engenheiro")
        assert result is not None
        corpo, resumo = result
        assert "resumo_uma_linha:" in corpo
        assert resumo == "Edital publicado"

    def test_coletar_beat_erro_llm(self, C):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        cliente = MagicMock()
        from local_llm import LocalLLMError
        cliente.chat.side_effect = LocalLLMError("LLM offline")

        with (
            patch.object(C, "_buscar_para_beat", return_value=("resultados", [])),
            patch.object(C, "_fetch_rag_context", return_value=""),
        ):
            result = C.coletar_beat(cliente, beat, "Engenheiro")
        assert result is None

    def test_coletar_beat_resposta_vazia(self, C):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        cliente = MagicMock()
        cliente.chat.return_value = ""

        with (
            patch.object(C, "_buscar_para_beat", return_value=("resultados", [])),
            patch.object(C, "_fetch_rag_context", return_value=""),
        ):
            result = C.coletar_beat(cliente, beat, "Engenheiro")
        assert result is None

    def test_coletar_beat_com_rag(self, C):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        cliente = MagicMock()
        cliente.chat.return_value = "resumo_uma_linha: Com legislação\n\n## Lei\nTexto da lei"

        with (
            patch.object(C, "_buscar_para_beat", return_value=("resultados", [])),
            patch.object(C, "_fetch_rag_context", return_value="[TEXTO_DA_LEI] Lei 13.303"),
        ):
            result = C.coletar_beat(cliente, beat, "Engenheiro")
        assert result is not None
        _, resumo = result
        assert resumo == "Com legislação"


class TestGravarNota:
    def test_gravar_nota_cria_arquivo(self, C, tmp_path):
        beat = {"id": "editais", "titulo": "Editais e Cronogramas", "tags": ["edital"]}

        with patch.object(C, "PASTA_INTEL", tmp_path):
            arquivo = C.gravar_nota(beat, "## Resumo\nConteudo", "Resumo do edital")
        assert arquivo.exists()
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "# Editais e Cronogramas" in conteudo
        assert "resumo_uma_linha" not in conteudo

    def test_gravar_nota_frontmatter(self, C, tmp_path):
        beat = {"id": "provas", "titulo": "Provas", "tags": ["prova", "gabarito"]}

        with patch.object(C, "PASTA_INTEL", tmp_path):
            arquivo = C.gravar_nota(beat, "resumo_uma_linha: Provas recentes\n\n## Detalhes\nProvas", "Provas recentes")
        conteudo = arquivo.read_text(encoding="utf-8")
        assert "---" in conteudo
        assert "titulo: Provas" in conteudo
        assert "tipo: inteligencia" in conteudo


class TestAtualizarMoc:
    def test_atualizar_moc_cria_novo(self, C, tmp_path):
        with patch.object(C, "RESUMO_MOC", tmp_path / "RESUMO.md"):
            arquivo = tmp_path / "nota.md"
            arquivo.write_text("conteudo", encoding="utf-8")
            registros = [{"titulo": "Editais", "resumo": "Edital publicado", "arquivo": arquivo}]
            C.atualizar_moc(registros)
        assert (tmp_path / "RESUMO.md").exists()
        conteudo = (tmp_path / "RESUMO.md").read_text(encoding="utf-8")
        assert "Editais" in conteudo
        assert "Edital publicado" in conteudo

    def test_atualizar_moc_substitui_mesma_data(self, C, tmp_path):
        from datetime import date
        hoje = date.today().isoformat()

        moc = tmp_path / "RESUMO.md"
        moc.write_text(f"# Header\n## Coleta de {hoje}\n- [[antiga]]\n", encoding="utf-8")

        with patch.object(C, "RESUMO_MOC", moc):
            arquivo = tmp_path / "nova.md"
            arquivo.write_text("conteudo", encoding="utf-8")
            registros = [{"titulo": "Novo", "resumo": "Atualizado", "arquivo": arquivo}]
            C.atualizar_moc(registros)

        conteudo = moc.read_text(encoding="utf-8")
        assert "antiga" not in conteudo
        assert "Novo" in conteudo


class TestMain:
    def test_main_listar(self, C, fontes_json, monkeypatch, capsys):
        with patch.object(C, "FONTES_PATH", fontes_json):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--listar"])
            try:
                C.main()
            except SystemExit:
                pass
        captured = capsys.readouterr()
        assert "editais" in captured.out

    def test_main_beat_inexistente(self, C, fontes_json, monkeypatch):
        with patch.object(C, "FONTES_PATH", fontes_json):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "fake"])
            with pytest.raises(SystemExit):
                C.main()

    def test_main_beat_especifico(self, C, fontes_json, monkeypatch, capsys):
        mock_cliente = MagicMock()
        mock_cliente.chat.return_value = "resumo_uma_linha: Edital\n\n## Resumo\nTexto"
        mock_cliente.model = "qwen2.5:7b"
        mock_cliente.base_url = "http://localhost:11434"

        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", return_value=mock_cliente),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
            patch.object(C, "RESUMO_MOC", fontes_json.parent / "RESUMO_MOC.md"),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "editais"])
            C.main()
        captured = capsys.readouterr()
        assert "✓" in captured.out or "Editais" in captured.out

    def test_main_todos_beats(self, C, fontes_json, monkeypatch, capsys):
        mock_cliente = MagicMock()
        mock_cliente.chat.return_value = "resumo_uma_linha: Info\n\n## Resumo\nTexto"
        mock_cliente.model = "qwen2.5:7b"
        mock_cliente.base_url = "http://localhost:11434"

        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", return_value=mock_cliente),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
            patch.object(C, "RESUMO_MOC", fontes_json.parent / "RESUMO_MOC.md"),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py"])
            C.main()

    def test_main_pdf_disponivel(self, C, fontes_json, monkeypatch, capsys):
        mock_cliente = MagicMock()
        mock_cliente.chat.return_value = "resumo_uma_linha: Info\n\n## Resumo\nTexto"
        mock_cliente.model = "qwen2.5:7b"
        mock_cliente.base_url = "http://localhost:11434"

        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", return_value=mock_cliente),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
            patch.object(C, "RESUMO_MOC", fontes_json.parent / "RESUMO_MOC.md"),
            patch.object(C, "_TEM_PDF", True),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "editais"])
            C.main()

    def test_main_sem_resultados(self, C, fontes_json, monkeypatch, capsys):
        mock_cliente = MagicMock()
        mock_cliente.chat.return_value = None
        mock_cliente.model = "qwen2.5:7b"
        mock_cliente.base_url = "http://localhost:11434"

        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", return_value=mock_cliente),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "editais"])
            C.main()
        captured = capsys.readouterr()
        assert "Nenhuma nota gerada" in captured.out

    def test_main_usa_modelo_forte_por_padrao(self, C, fontes_json, monkeypatch):
        """Sem env/flag, o coletor sintetiza com o modelo forte (anti-alucinação)."""
        monkeypatch.delenv("AGENTE_COLETOR_MODEL", raising=False)
        mock_LLM = MagicMock()
        mock_LLM.return_value.chat.return_value = "resumo_uma_linha: X\n\n## Resumo\nT"
        mock_LLM.return_value.model = "qwen2.5:latest"
        mock_LLM.return_value.base_url = "http://localhost:11434"
        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", mock_LLM),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
            patch.object(C, "RESUMO_MOC", fontes_json.parent / "RESUMO_MOC.md"),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "editais"])
            C.main()
        mock_LLM.assert_called_once_with(model="qwen2.5:latest")

    def test_main_model_override(self, C, fontes_json, monkeypatch):
        """--model sobrepõe o default."""
        mock_LLM = MagicMock()
        mock_LLM.return_value.chat.return_value = "resumo_uma_linha: X\n\n## Resumo\nT"
        mock_LLM.return_value.model = "phi3"
        mock_LLM.return_value.base_url = "http://localhost:11434"
        with (
            patch.object(C, "FONTES_PATH", fontes_json),
            patch.object(C, "LocalLLM", mock_LLM),
            patch.object(C, "PASTA_INTEL", fontes_json.parent / "intel"),
            patch.object(C, "RESUMO_MOC", fontes_json.parent / "RESUMO_MOC.md"),
        ):
            monkeypatch.setattr(sys, "argv", ["coletor.py", "--beat", "editais", "--model", "phi3"])
            C.main()
        mock_LLM.assert_called_once_with(model="phi3")


class TestConferenciaFontes:
    def test_dominio_oficial(self, C):
        assert C._dominio_oficial("https://www.cesgranrio.org.br/x")
        assert C._dominio_oficial("https://www.planalto.gov.br/lei")
        assert not C._dominio_oficial("https://blogconcurso.com/post")

    def test_url_da_busca_oficial_corroborada(self, C):
        # URL veio da busca → real, sem precisar de HTTP
        corpo = "## Fontes\n1. https://www.petrobras.com.br/carreiras\n"
        novo, conf = C._conferir_fontes(corpo, ["https://www.petrobras.com.br/carreiras"])
        assert conf["corroborado_oficial"] is True
        assert conf["quebradas"] == []
        assert "oficial" in novo.lower()

    def test_url_oficial_fora_da_busca_mas_existe(self, C):
        # CENÁRIO CHAVE: URL oficial NÃO veio na busca, mas existe de fato (HTTP 200)
        corpo = "## Fontes\n1. https://www.cesgranrio.org.br/concursos\n"
        with patch.object(C, "_url_acessivel", return_value=True) as mock_http:
            novo, conf = C._conferir_fontes(corpo, urls_reais=[])  # nada veio da busca
        mock_http.assert_called_once()  # foi verificada na prática
        assert conf["corroborado_oficial"] is True
        assert conf["quebradas"] == []

    def test_url_404_marcada_inexistente(self, C):
        corpo = "## Fontes\n1. https://www.cesgranrio.org.br/edital-fake-404\n"
        with patch.object(C, "_url_acessivel", return_value=False):
            novo, conf = C._conferir_fontes(corpo, urls_reais=[])
        assert any("edital-fake-404" in u for u in conf["quebradas"])
        assert "inexistente" in novo.lower()

    def test_url_inacessivel_nao_eh_invencao(self, C):
        corpo = "## Fontes\n1. https://site.que.nao.responde/x\n"
        with patch.object(C, "_url_acessivel", return_value=None):
            novo, conf = C._conferir_fontes(corpo, urls_reais=[])
        assert conf["inacessiveis"] and conf["quebradas"] == []
        assert "Não foi possível verificar" in novo

    def test_sem_fonte_oficial(self, C):
        corpo = "## Fontes\n1. https://pciconcursos.com.br/x\n"
        novo, conf = C._conferir_fontes(corpo, ["https://pciconcursos.com.br/x"])
        assert conf["corroborado_oficial"] is False
        assert conf["nao_oficiais"]

    def test_coletar_beat_anexa_conferencia(self, C):
        beat = {"id": "editais", "titulo": "Editais", "tags": [], "instrucao": "Procure"}
        cliente = MagicMock()
        cliente.chat.return_value = (
            "resumo_uma_linha: Sem edital\n\n## Resumo\nNada.\n\n"
            "## Fontes\n1. https://www.cesgranrio.org.br/concursos\n"
        )
        with (
            patch.object(C, "_buscar_para_beat",
                         return_value=("res", ["https://www.cesgranrio.org.br/concursos"])),
            patch.object(C, "_fetch_rag_context", return_value=""),
        ):
            corpo, resumo = C.coletar_beat(cliente, beat, "Engenheiro")
        assert "Conferência de Fontes" in corpo
        assert "oficial" in corpo.lower()


class TestImportFallbacks:
    def test_web_import_fallback(self, C):
        assert hasattr(C, "web_search") or C.web_search is None

    def test_pdf_fallback(self, C):
        assert hasattr(C, "_TEM_PDF")
