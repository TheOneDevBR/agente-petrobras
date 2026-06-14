#!/usr/bin/env python3
"""Coletor de inteligência do AgentePetrobras (local LLM).

Busca periódica em fontes PÚBLICAS (banca CESGRANRIO, carreiras Petrobras,
blogs de cursinhos, portais de concurso) usando LLM local + web_search/fetch
locais. Cada "beat" de fontes.json vira UMA nota Markdown no vault do Obsidian.

Uso:
    python coletor.py                 # roda todos os beats
    python coletor.py --beat editais  # só um beat
    python coletor.py --listar        # lista os beats configurados

Variáveis de ambiente:
    AGENTE_LLM_BASE_URL  (default: http://localhost:11434)
    AGENTE_COLETOR_MODEL (default: qwen2.5:latest — modelo de síntese do coletor;
                          forte de propósito: 1.5B alucina atos/datas/vagas)
    AGENTE_VAULT         caminho do vault Obsidian (default: <projeto>/Obsidian_Vault)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Renderização de páginas JavaScript (Chromium headless via Playwright).
# Opt-in por variável de ambiente — desligado por padrão (mantém o fetch rápido).
# Requer: pip install playwright && playwright install chromium
_RENDER_JS = os.environ.get("AGENTE_RENDER_JS", "").strip().lower() in ("1", "true", "sim", "yes")


def _map_fetch(fn, items: list) -> list:
    """Aplica ``fn`` aos itens. Paralelo por padrão; sequencial quando o render
    JS está ligado (a API síncrona do Playwright não é thread-safe)."""
    if not items:
        return []
    if _RENDER_JS:
        return [fn(x) for x in items]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(len(items), 5)) as executor:
        return list(executor.map(fn, items))

AQUI = Path(__file__).resolve().parent
PROJETO = AQUI.parents[1]
CLI_PYTHON = AQUI.parent
sys.path.insert(0, str(CLI_PYTHON))

try:
    from local_web import web_fetch, web_search
except ImportError:
    web_search = web_fetch = None  # opcional

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv()
except ImportError:
    pass

try:
    from pdf_utils import extrair_texto_pdf_para_contexto
    _TEM_PDF = True
except ImportError:
    _TEM_PDF = False

try:
    from local_llm import LocalLLM, LocalLLMError
except ImportError:
    print("Falta local_llm.py. Copie para cli_python/ e instale as dependências.")
    sys.exit(1)

FONTES_PATH = AQUI / "fontes.json"

VAULT = Path(os.environ.get("AGENTE_VAULT", PROJETO / "Obsidian_Vault"))
PASTA_PETROBRAS = VAULT / "Petrobras"
PASTA_INTEL = PASTA_PETROBRAS / "Inteligencia"
RESUMO_MOC = PASTA_PETROBRAS / "_RESUMO_INTEL.md"

SYSTEM = """\
Responda SEMPRE em português do Brasil.
Você é o braço de inteligência do AgentePetrobras — um analista que monitora
fontes públicas para preparar candidatos ao concurso da Petrobras (banca
CESGRANRIO). Sua função: ANALISAR e SINTETIZAR informações coletadas da web.

REGRAS DE INTEGRIDADE (invioláveis):
- Use EXCLUSIVAMENTE os dados em [RESULTADOS_DA_BUSCA] e [TEXTO_DA_LEI]. Nada
  fora disso existe para você.
- NUNCA invente fatos, números, datas, vagas, salários, atos normativos
  (portarias/leis/decretos) nem URLs. Não preencha lacunas com suposições.
- Em "## Fontes" liste APENAS URLs que aparecem LITERALMENTE nos resultados.
  Jamais crie, complete ou adivinhe uma URL.
- Toda afirmação factual deve ser rastreável a uma fonte listada. Se a
  informação não está nos resultados, escreva que NÃO há confirmação.
- Conferência de fontes oficiais: priorize e identifique fontes OFICIAIS
  (petrobras.com.br, cesgranrio.org.br, gov.br, in.gov.br, planalto.gov.br,
  tcu.gov.br, stf.jus.br). Marque cada item como [oficial] ou [não-oficial] e
  diga claramente quando algo NÃO é confirmado por fonte oficial.
- Honestidade clínica: sem edital/novidade/jurisprudência → diga isso. É
  preferível "não há confirmação oficial" a um detalhe inventado.
- Hoje é {hoje}. Priorize o recente e acionável para o candidato.

FORMATO DA SAÍDA — produza UMA nota Obsidian em Markdown igual ao exemplo
abaixo. Copie a ESTRUTURA (não o conteúdo). NÃO use cercas de código. NÃO
escreva texto antes ou depois.

EXEMPLO (estrutura; o conteúdo é só ilustrativo de POSTURA honesta):
resumo_uma_linha: Não há edital aberto confirmado por fonte oficial para o concurso Petrobras

## Resumo executivo
- Não foi localizado edital aberto/previsto confirmado por fonte oficial [não confirmado oficialmente]
- A informação mais recente encontrada refere-se a ciclo anterior

## Detalhes
Com base apenas nos resultados, não há ato oficial publicado confirmando novo
concurso. NÃO cite vagas, datas, salários ou portarias que não constem
literalmente nas fontes abaixo.

## O que muda para o candidato
- Acompanhar as fontes oficiais (carreiras Petrobras e CESGRANRIO)

## Disciplinas relacionadas
[[Língua Portuguesa]], [[Engenharia de Petróleo]]

## Fontes
1. (cole aqui APENAS uma URL que apareceu nos resultados, exatamente como veio)

SIGA EXATAMENTE este formato, incluindo a linha resumo_uma_linha: no topo.

Se houver [TEXTO_DA_LEI] disponível abaixo, use-o como FONTE PRIMÁRIA para a
seção de legislação. Cite artigos específicos (ex.: "Art. 17 da Lei 13.303/2016
determina que..."). NÃO contradiga o texto da lei."""

PROMPT_BEAT = """\
MISSÃO ({beat_id}): {titulo}
Cargo em foco: {cargo}

{instrucao}

[RESULTADOS_DA_BUSCA]
{resultados}

Com base APENAS nos resultados acima, produza a nota no formato definido.
Comece com a linha exata: resumo_uma_linha:"""


def _slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^\w\s-]", "", s.lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "nota"


def _extrair_resumo(corpo: str) -> str:
    m = re.search(r"resumo_uma_linha:\s*(.+)", corpo)
    return m.group(1).strip() if m else "(sem resumo)"


def _fix_nota(corpo: str) -> str:
    """Corrige formatação comum de modelos pequenos."""
    if not corpo:
        return corpo
    # remove linhas tipo "---" ou "```" que cercam a nota
    corpo = re.sub(r"^```[\w]*\n", "", corpo, flags=re.MULTILINE)
    corpo = re.sub(r"\n```\s*$", "", corpo)
    corpo = re.sub(r"^---+", "", corpo)
    # se não tem resumo_uma_linha, tenta extrair da primeira linha significativa
    if not re.search(r"^resumo_uma_linha:", corpo, re.MULTILINE):
        linhas = [ln.strip() for ln in corpo.split("\n") if ln.strip()]
        first = next((ln for ln in linhas if len(ln) > 10), "")
        if first and "## " not in first:
            corpo = f"resumo_uma_linha: {first[:140]}\n\n" + corpo
    # headers com dois pontos extras: "## Resumo executivo:" -> "## Resumo executivo"
    corpo = re.sub(r"^(#{1,6}\s+.+?):(\s|$)", r"\1\2", corpo, flags=re.MULTILINE)
    # remove linhas de separação extras
    corpo = re.sub(r"\n{3,}", "\n\n", corpo)
    return corpo.strip()


# Âncora de domínio: toda query é grudada nisto para evitar ruído (tags soltas
# como "curso"/"ebook" traziam álbuns/Wikipedia em vez de material de concurso).
_ANCORA_BUSCA = "Petrobras concurso CESGRANRIO"


def _buscar_para_beat(beat: dict, max_resultados: int = 3) -> tuple[str, list[str]]:
    """Gera queries ANCORADAS ao domínio, busca na web e retorna (texto, urls_reais)."""
    dominios = beat.get("dominios_sugeridos", [])
    tags = beat.get("tags", [])
    queries = [beat["titulo"]]
    # tags combinadas e ancoradas ao concurso (nunca termo genérico isolado)
    if tags:
        queries.append(f"{' '.join(tags[:3])} {_ANCORA_BUSCA}")
    # busca restrita ao domínio prioritário (operador site:)
    if dominios:
        queries.append(f"{beat['titulo']} site:{dominios[0]}")
    # realimentação: busca também nos SITES DESCOBERTOS (auto-aprendidos)
    try:
        from descoberta import promovidas
        for d in promovidas(limite=2):
            queries.append(f"{beat['titulo']} site:{d}")
    except Exception:
        pass

    visitados: set[str] = set()
    urls_info = []
    for q in queries[:3]:
        print(f"   ↳ buscando: {q}")
        try:
            resultados = web_search(q, max_results=max_resultados)
        except Exception as e:
            print(f"   [erro web_search: {e}]")
            continue
        for r in resultados:
            url = r.get("url") or r.get("href") or r.get("link", "")
            if not url or url in visitados:
                continue
            visitados.add(url)
            urls_info.append({
                "url": url,
                "title": r.get("title", ""),
                "snippet": r.get("snippet", r.get("body", ""))
            })

    if not urls_info:
        return "Nenhum resultado encontrado na web para as queries realizadas.", []

    def fetch_url_content(info):
        url = info["url"]
        titulo = info["title"]
        snippet = info["snippet"]
        bloco = f"### {titulo}\nURL: {url}\n{snippet}\n"
        try:
            if url.lower().endswith('.pdf') and _TEM_PDF:
                print(f"   ↳ extraindo PDF: {url}")
                conteudo = extrair_texto_pdf_para_contexto(url, max_chars=2000)
            else:
                conteudo = web_fetch(url, render=_RENDER_JS)
            if conteudo and len(conteudo) > 200:
                bloco += f"**Conteúdo extraído:**\n{conteudo[:1500]}\n"
        except Exception as e:
            bloco += f"(erro ao acessar: {e})\n"
        return bloco

    blocos = _map_fetch(fetch_url_content, urls_info)

    return "\n".join(blocos), sorted(visitados)


def _fetch_rag_context(beat: dict) -> str:
    """Busca textos-fonte oficiais (leis, decretos) para RAG."""
    sources = beat.get("rag_sources", [])
    if not sources:
        return ""

    def fetch_one(src):
        url = src["url"]
        desc = src["descricao"]
        print(f"   ↳ RAG: {desc}")
        try:
            texto = web_fetch(url, max_chars=2500, render=_RENDER_JS)
            if texto and "404" not in texto[:50] and len(texto) > 200:
                return f"[TEXTO_DA_LEI] {desc}\nFonte: {url}\n{texto[:2500]}\n"
            else:
                print(f"   ⚠ RAG vazio para {desc}")
        except Exception as e:
            print(f"   ⚠ RAG erro para {desc}: {e}")
        return None

    resultados = _map_fetch(fetch_one, sources)

    blocos = [r for r in resultados if r is not None]
    return "\n".join(blocos) if blocos else ""


# Domínios considerados FONTES OFICIAIS para a conferência.
DOMINIOS_OFICIAIS = (
    "petrobras.com.br", "transpetro.com.br", "cesgranrio.org.br",
    "gov.br", "in.gov.br", "planalto.gov.br", "tcu.gov.br", "stf.jus.br",
)

_URL_RE = re.compile(r"https?://[^\s)\]>\"'`]+")


def _dominio_oficial(url: str) -> bool:
    u = url.lower()
    return any(d in u for d in DOMINIOS_OFICIAIS)


def _url_acessivel(url: str, timeout: int = 8) -> bool | None:
    """Verifica EMPIRICAMENTE se a URL existe (responde na prática).

    Retorna:
        True  → responde 2xx/3xx (a página existe);
        False → 404/410 (link morto / inexistente);
        None  → não foi possível verificar (timeout, bloqueio, rede).
    """
    try:
        from local_web import _get_session
        sess = _get_session()
    except Exception:
        try:
            import requests
            sess = requests.Session()
        except Exception:
            return None
    try:
        try:
            resp = sess.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code in (403, 405) or resp.status_code >= 500:
                resp = sess.get(url, timeout=timeout, allow_redirects=True, stream=True)
        except Exception:
            resp = sess.get(url, timeout=timeout, allow_redirects=True, stream=True)
        code = resp.status_code
        if code in (404, 410):
            return False
        if 200 <= code < 400:
            return True
        return None
    except Exception:
        return None


def _conferir_fontes(corpo: str, urls_reais: list[str], verificar_http: bool = True) -> tuple[str, dict]:
    """Confere EMPIRICAMENTE as URLs citadas na nota.

    Uma URL é considerada real se (a) apareceu na busca OU (b) responde de fato
    via HTTP. "Não estar na busca" NÃO significa "inventada" — sites oficiais
    existem mesmo fora daquela busca. Só 404/410 conta como link morto/inventado.
    Classifica as reais em oficiais/não-oficiais e anexa "## Conferência de Fontes".
    """
    reais_norm = {u.rstrip("/").lower() for u in urls_reais}
    citadas: list[str] = []
    for u in _URL_RE.findall(corpo):
        cu = u.rstrip(".,;)").rstrip("/")
        if cu not in citadas:
            citadas.append(cu)

    oficiais: list[str] = []        # existem + domínio oficial
    nao_oficiais: list[str] = []    # existem + não-oficial
    quebradas: list[str] = []       # 404/410 → link morto / inventado
    inacessiveis: list[str] = []    # não foi possível verificar

    from concurrent.futures import ThreadPoolExecutor

    urls_a_testar = []
    for u in citadas[:10]:          # limite de segurança p/ latência
        if u.rstrip("/").lower() in reais_norm:
            (oficiais if _dominio_oficial(u) else nao_oficiais).append(u)
        elif verificar_http:
            urls_a_testar.append(u)
        else:
            inacessiveis.append(u)

    if urls_a_testar:
        with ThreadPoolExecutor(max_workers=min(len(urls_a_testar), 5)) as executor:
            futuros = [executor.submit(_url_acessivel, u) for u in urls_a_testar]
            for u, fut in zip(urls_a_testar, futuros):
                try:
                    existe = fut.result()
                except Exception:
                    existe = None
                if existe is True:
                    (oficiais if _dominio_oficial(u) else nao_oficiais).append(u)
                elif existe is False:
                    quebradas.append(u)
                else:
                    inacessiveis.append(u)

    # Fontes REAIS consultadas na busca (existem por definição) — garantem rastreio
    # mesmo quando o modelo esquece de citar as URLs no corpo.
    consultadas: list[str] = []
    for u in urls_reais:
        cu = u.rstrip("/")
        if cu not in consultadas:
            consultadas.append(cu)
    consultadas_oficiais = [u for u in consultadas if _dominio_oficial(u)]

    conf = {
        "citadas": len(citadas), "oficiais": oficiais, "nao_oficiais": nao_oficiais,
        "quebradas": quebradas, "inacessiveis": inacessiveis,
        "consultadas": consultadas, "consultadas_oficiais": consultadas_oficiais,
        "corroborado_oficial": bool(oficiais) or bool(consultadas_oficiais),
    }

    linhas = ["", "## Conferência de Fontes",
              "_Verificação empírica: fontes reais consultadas + checagem das URLs citadas._"]

    if consultadas:
        linhas.append(f"- 🔎 Fontes reais consultadas: {len(consultadas)} "
                      f"({len(consultadas_oficiais)} oficial(is)):")
        for u in consultadas[:12]:
            marca = "🏛️ " if _dominio_oficial(u) else ""
            linhas.append(f"    - {marca}{u}")
    else:
        linhas.append("- ⚠️ Nenhuma fonte foi recuperada na busca (resultado vazio).")

    if quebradas:
        linhas.append(f"- ❌ {len(quebradas)} URL(s) citada(s) inexistente(s) (404/410 — desconsidere):")
        linhas += [f"    - ~~{u}~~" for u in quebradas]

    if inacessiveis:
        linhas.append(f"- ⚠️ Não foi possível verificar {len(inacessiveis)} URL(s) citada(s):")
        linhas += [f"    - {u}" for u in inacessiveis]

    if not consultadas_oficiais and not oficiais:
        linhas.append("- ⚠️ Sem fonte **oficial** (.gov/cesgranrio/petrobras) — trate como não confirmado.")

    return corpo.rstrip() + "\n" + "\n".join(linhas) + "\n", conf


def _ler_nota_existente(caminho: Path) -> tuple[dict[str, str], str] | None:
    if not caminho.exists():
        return None
    try:
        texto = caminho.read_text(encoding="utf-8")
        if texto.startswith("---"):
            partes = texto.split("---", 2)
            if len(partes) >= 3:
                linhas_fm = partes[1].strip().split("\n")
                fm = {}
                for ln in linhas_fm:
                    if ":" in ln:
                        k, v = ln.split(":", 1)
                        fm[k.strip().lower()] = v.strip().strip('"').strip("'")
                corpo = partes[2].strip()
                
                linhas_corpo = corpo.split("\n")
                clean_lines = []
                pulo_headers = True
                for ln in linhas_corpo:
                    ln_s = ln.strip()
                    if pulo_headers:
                        if not ln_s or ln_s.startswith("#") or ln_s.startswith("## Conferência de Fontes") or ln_s.startswith("_Verificação empírica:"):
                            continue
                        pulo_headers = False
                    if ln_s.startswith("## Conferência de Fontes"):
                        break
                    clean_lines.append(ln)
                corpo_clean = "\n".join(clean_lines).strip()
                return fm, corpo_clean
    except Exception:
        pass
    return None


def coletar_beat(cliente, beat: dict, cargo: str, max_tokens: int = 12000) -> tuple[str, str] | None:
    """Executa um beat: busca web direta + síntese via LLM local. Retorna (corpo_markdown, resumo)."""
    print("   Buscando na web...")
    resultados, urls_reais = _buscar_para_beat(beat)

    rag = _fetch_rag_context(beat)
    if rag:
        resultados += "\n\n" + rag
    # URLs das fontes oficiais de RAG (leis/decretos) também são reais e verificáveis
    urls_reais = list(urls_reais) + [s["url"] for s in beat.get("rag_sources", [])]

    import hashlib
    hash_val = hashlib.md5(resultados.encode("utf-8")).hexdigest()

    hoje = date.today().isoformat()
    nome_arquivo = PASTA_INTEL / f"{hoje}_{_slug(beat['titulo'])}.md"
    nota_existente = _ler_nota_existente(nome_arquivo)
    
    corpo_cache = None
    resumo_cache = None
    
    if nota_existente:
        fm, corpo_clean = nota_existente
        if fm.get("hash_contexto") == hash_val:
            print("   ✓ cache: conteúdo de busca idêntico detectado. Pulando síntese via LLM.")
            resumo_cache = fm.get("resumo", "(sem resumo)")
            corpo_cache = corpo_clean

    try:
        from descoberta import registrar as _descobrir
        novos = _descobrir(urls_reais, contexto=beat["id"])
        if novos:
            print(f"   🛰️  {len(novos)} site(s) novo(s) observado(s)")
    except Exception:
        pass

    if corpo_cache is not None and resumo_cache is not None:
        corpo_conf, conf = _conferir_fontes(corpo_cache, urls_reais)
        if conf["oficiais"]:
            print(f"   ✓ conferência (cache): {len(conf['oficiais'])} fonte(s) oficial(is) verificada(s)")
        else:
            print("   ⚠ conferência (cache): nenhuma fonte oficial verificada")
        return f"resumo_uma_linha: {resumo_cache}\nhash_contexto: {hash_val}\n\n" + corpo_conf, resumo_cache

    prompt = PROMPT_BEAT.format(
        beat_id=beat["id"],
        titulo=beat["titulo"],
        cargo=cargo,
        instrucao=beat["instrucao"],
        resultados=resultados,
    )
    system = SYSTEM.format(hoje=date.today().isoformat())
    messages = [{"role": "user", "content": prompt}]

    try:
        corpo = cliente.chat(
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
    except LocalLLMError as e:
        print(f"   [erro no beat '{beat['id']}': {e}]")
        return None

    if not corpo:
        print(f"   [beat '{beat['id']}' não retornou texto]")
        return None
    corpo = _fix_nota(corpo)
    corpo, conf = _conferir_fontes(corpo, urls_reais)
    if conf["oficiais"]:
        print(f"   ✓ conferência: {len(conf['oficiais'])} fonte(s) oficial(is) verificada(s)")
    else:
        print("   ⚠ conferência: nenhuma fonte oficial verificada")
    if conf["quebradas"]:
        print(f"   ❌ conferência: {len(conf['quebradas'])} URL(s) inexistente(s) (404)")
    return f"hash_contexto: {hash_val}\n" + corpo, _extrair_resumo(corpo)


def gravar_nota(beat: dict, corpo: str, resumo: str) -> Path:
    PASTA_INTEL.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    nome = PASTA_INTEL / f"{hoje}_{_slug(beat['titulo'])}.md"
    tags = " ".join(f"#{t}" for t in (["petrobras", "inteligencia"] + beat.get("tags", [])))
    
    hash_val = ""
    m_hash = re.search(r"^hash_contexto:\s*(\w+)", corpo, re.MULTILINE)
    if m_hash:
        hash_val = m_hash.group(1)
        corpo = re.sub(r"^hash_contexto:\s*\w+\n*", "", corpo, flags=re.MULTILINE)
        
    frontmatter = (
        "---\n"
        f"titulo: {beat['titulo']}\n"
        f"beat: {beat['id']}\n"
        f"data: {hoje}\n"
        f"coletado_em: {datetime.now().isoformat(timespec='seconds')}\n"
        f"resumo: \"{resumo.replace(chr(34), chr(39))}\"\n"
        "tipo: inteligencia\n"
    )
    if hash_val:
        frontmatter += f"hash_contexto: {hash_val}\n"
    frontmatter += "---\n\n"
    
    corpo_limpo = re.sub(r"^\s*resumo_uma_linha:.*\n+", "", corpo, count=1)
    nome.write_text(frontmatter + f"{tags}\n\n# {beat['titulo']}\n\n" + corpo_limpo + "\n", encoding="utf-8")
    return nome


def atualizar_moc(registros: list[dict]) -> None:
    """Reescreve o _RESUMO_INTEL.md (mapa de conteúdo) com os achados do dia no topo.
    Remove bloco anterior da mesma data para evitar duplicação."""
    hoje = date.today().isoformat()
    bloco_hoje = "## Coleta de " + hoje + "\n\n"
    for r in registros:
        bloco_hoje += f"- [[{r['arquivo'].stem}|{r['titulo']}]] — {r['resumo']}\n"
    bloco_hoje += "\n"

    anterior = ""
    if RESUMO_MOC.exists():
        anterior = RESUMO_MOC.read_text(encoding="utf-8")
        anterior = re.sub(r"^---.*?---\n\n", "", anterior, count=1, flags=re.DOTALL)
        anterior = re.sub(r"^# .*?\n\n", "", anterior, count=1, flags=re.DOTALL)
        anterior = re.sub(r"^_Mapa de conteúdo.*\n?", "", anterior, flags=re.MULTILINE)
        # remove bloco da mesma data para substituir
        anterior = re.sub(
            r"\n?## Coleta de " + re.escape(hoje) + r".*?(?=\n## Coleta de|\Z)",
            "", anterior, flags=re.DOTALL
        )
        anterior = anterior.strip()

    header = (
        "---\ntitulo: Resumo de Inteligência (MOC)\ntipo: indice\n"
        f"atualizado_em: {hoje}\n---\n\n"
        "# 📡 Resumo de Inteligência — AgentePetrobras\n\n"
        "_Mapa de conteúdo gerado pela coleta automática. As notas completas "
        "estão em [[Inteligencia]]._\n\n"
    )
    RESUMO_MOC.parent.mkdir(parents=True, exist_ok=True)
    RESUMO_MOC.write_text(header + bloco_hoje + anterior + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor de inteligência AgentePetrobras")
    parser.add_argument("--beat", help="roda apenas o beat com este id")
    parser.add_argument("--all", action="store_true", help="roda todos os beats (padrão quando sem --beat)")
    parser.add_argument("--listar", action="store_true", help="lista os beats e sai")
    parser.add_argument("--max-tokens", type=int, default=12000, help="limite de tokens por síntese (padrão: 12000, use 4096 para 1.5B)")
    parser.add_argument(
        "--model",
        default=os.environ.get("AGENTE_COLETOR_MODEL", "qwen2.5:latest"),
        help="modelo de síntese (padrão: qwen2.5:latest). Um modelo forte reduz alucinação; "
             "modelos pequenos (1.5B) tendem a inventar atos/datas/vagas.",
    )
    args = parser.parse_args()

    fontes = json.loads(FONTES_PATH.read_text(encoding="utf-8"))
    beats = fontes["beats"]
    cargo = fontes.get("cargo_foco", "candidato Petrobras")

    if args.listar:
        print("Beats configurados em fontes.json:")
        for b in beats:
            print(f"  • {b['id']:20s} {b['titulo']}")
        return

    if args.beat:
        beats = [b for b in beats if b["id"] == args.beat]
        if not beats:
            print(f"Beat '{args.beat}' não encontrado. Use --listar.")
            sys.exit(1)

    cliente = LocalLLM(model=args.model)
    print(f"📡 Coleta iniciada — {date.today().isoformat()} — vault: {VAULT}")
    print(f"   {len(beats)} missão(ões) · LLM local: {cliente.model} @ {cliente.base_url}\n")

    registros = []
    for i, beat in enumerate(beats, 1):
        print(f"[{i}/{len(beats)}] {beat['titulo']} ...")
        res = coletar_beat(cliente, beat, cargo, max_tokens=args.max_tokens)
        if not res:
            continue
        corpo, resumo = res
        arquivo = gravar_nota(beat, corpo, resumo)
        registros.append({"titulo": beat["titulo"], "resumo": resumo, "arquivo": arquivo})
        print(f"   ✓ {arquivo.name} — {resumo[:80]}")

    if registros:
        atualizar_moc(registros)
        print(f"\n✓ {len(registros)} nota(s) gravada(s). MOC: {RESUMO_MOC}")
    else:
        print("\nNenhuma nota gerada nesta execução.")


if __name__ == "__main__":
    main()
