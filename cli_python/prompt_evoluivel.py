"""Prompt Evoluível — Auto-tuning do system prompt.

Gerencia overlays que estendem o system prompt base (v4) com conhecimento
adquirido: estratégias comprovadas, padrões de erro do candidato, ajuste
de tom. Cada overlay é versionado com rollback.

Uso:
    from prompt_evoluivel import PromptEvoluivel

    pe = PromptEvoluivel()
    prompt_completo = pe.montar_prompt_completo(prompt_base)
    pe.evoluir_overlay("estrategias", cliente_llm, contexto)
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


AQUI = Path(__file__).resolve().parent
DADOS_EVOLUCAO = AQUI / "dados" / "evolucao"
PROMPTS_DIR = DADOS_EVOLUCAO / "prompts"
HISTORICO_PATH = PROMPTS_DIR / "historico.json"

# Overlays suportados
OVERLAYS = [
    "estrategias",      # Estratégias preferenciais para o candidato
    "armadilhas",       # Padrões de erro específicos detectados
    "tom",              # Ajuste de tom (coaching vs. direto)
    "prescricoes",      # Prescrições customizadas por disciplina
]

# Limites de segurança
MAX_OVERLAY_CHARS = 2000
MAX_OVERLAY_LINHAS = 40
MAX_VERSOES_POR_OVERLAY = 10

# Meta-prompts para evolução de cada overlay
META_PROMPTS = {
    "estrategias": """\
Você é o meta-agente de evolução do AgentePetrobras. Sua tarefa é reescrever
o overlay de ESTRATÉGIAS do system prompt com base nos dados acumulados.

DADOS DO CANDIDATO:
{contexto}

OVERLAY ATUAL:
{overlay_atual}

RANKING DE ESTRATÉGIAS (por eficácia real):
{ranking}

REGRAS:
- Mantenha o formato: bloco de texto em português, max {max_chars} caracteres
- Priorize as estratégias com maior eficácia comprovada
- Descarte estratégias com eficácia < 0.3
- Adapte as prescrições ao perfil real (fase, disciplinas fracas, erros)
- NÃO contradiga o prompt base (princípios P1–P7 são imutáveis)
- Comece com: [OVERLAY_ESTRATEGIAS]

Reescreva o overlay:""",

    "armadilhas": """\
Você é o meta-agente de evolução do AgentePetrobras. Reescreva o overlay de
ARMADILHAS com os padrões de erro específicos deste candidato.

DADOS DO CANDIDATO:
{contexto}

OVERLAY ATUAL:
{overlay_atual}

ERROS DETECTADOS:
{erros}

REGRAS:
- Formato: bloco de texto, max {max_chars} caracteres
- Liste apenas padrões reais observados (não genéricos)
- Para cada padrão, inclua: tipo [C/A/B/T], frequência, contramedida
- Comece com: [OVERLAY_ARMADILHAS]

Reescreva o overlay:""",

    "tom": """\
Você é o meta-agente de evolução do AgentePetrobras. Ajuste o overlay de
TOM de comunicação com base na resposta do candidato ao coaching.

DADOS DO CANDIDATO:
{contexto}

OVERLAY ATUAL:
{overlay_atual}

FEEDBACK INDIRETO:
{feedback}

REGRAS:
- Formato: 3-5 linhas de instrução, max {max_chars} caracteres
- Ajuste entre: mais coaching (motivacional) ↔ mais direto (cirúrgico)
- Se candidato responde bem a desafios, seja mais direto
- Se candidato mostra ansiedade, seja mais coach
- Comece com: [OVERLAY_TOM]

Reescreva o overlay:""",

    "prescricoes": """\
Você é o meta-agente de evolução do AgentePetrobras. Reescreva o overlay de
PRESCRIÇÕES customizadas para cada disciplina deste candidato.

DADOS DO CANDIDATO:
{contexto}

OVERLAY ATUAL:
{overlay_atual}

HISTÓRICO DE ACERTOS:
{historico}

REGRAS:
- Formato: uma prescrição por disciplina fraca, max {max_chars} caracteres
- Cada prescrição: técnica + tempo + material + critério de avanço
- Base nas estratégias que funcionaram (não genérico)
- Comece com: [OVERLAY_PRESCRICOES]

Reescreva o overlay:""",
}

# Overlays padrão (versão 0)
OVERLAYS_PADRAO = {
    "estrategias": (
        "[OVERLAY_ESTRATEGIAS]\n"
        "Ainda sem dados suficientes para personalizar. Use o §8 do prompt base.\n"
        "Registre sessões com /sessao para acumular dados de eficácia."
    ),
    "armadilhas": (
        "[OVERLAY_ARMADILHAS]\n"
        "Ainda sem padrões de erro detectados. Classifique erros com [C/A/B/T]\n"
        "em cada resolução para começar a detectar padrões."
    ),
    "tom": (
        "[OVERLAY_TOM]\n"
        "Tom padrão: equilibrado entre Coach e Estrategista.\n"
        "Adaptar conforme sinais do candidato ao longo das sessões."
    ),
    "prescricoes": (
        "[OVERLAY_PRESCRICOES]\n"
        "Sem prescrições customizadas. Use o currículo mínimo viável (§6)."
    ),
}


class PromptEvoluivel:
    """Gerencia overlays versionados do system prompt."""

    def __init__(self, diretorio: Path | None = None):
        self._dir = diretorio or PROMPTS_DIR
        self._historico_path = self._dir / "historico.json"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._historico = self._carregar_historico()
        self._inicializar_overlays()

    def _carregar_historico(self) -> dict[str, Any]:
        if self._historico_path.exists():
            try:
                return json.loads(self._historico_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"versoes": {}, "evolucoes": [], "_versao": 1}

    def _salvar_historico(self) -> None:
        self._historico["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        self._historico_path.write_text(
            json.dumps(self._historico, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _inicializar_overlays(self) -> None:
        """Cria overlays padrão se não existirem."""
        for nome in OVERLAYS:
            caminho = self._overlay_path(nome)
            if not caminho.exists():
                caminho.write_text(OVERLAYS_PADRAO.get(nome, ""), encoding="utf-8")
                self._historico.setdefault("versoes", {})[nome] = 0
        self._salvar_historico()

    def _overlay_path(self, nome: str, versao: int | None = None) -> Path:
        """Caminho do overlay (versão atual ou específica)."""
        if versao is not None:
            return self._dir / f"overlay_{nome}_v{versao}.md"
        v = self._historico.get("versoes", {}).get(nome, 0)
        return self._dir / f"overlay_{nome}_v{v}.md"

    def ler_overlay(self, nome: str) -> str:
        """Lê o conteúdo atual de um overlay."""
        if nome not in OVERLAYS:
            return ""
        caminho = self._overlay_path(nome)
        if caminho.exists():
            return caminho.read_text(encoding="utf-8")
        return OVERLAYS_PADRAO.get(nome, "")

    def versao_atual(self, nome: str) -> int:
        """Retorna a versão atual de um overlay."""
        return self._historico.get("versoes", {}).get(nome, 0)

    def montar_prompt_completo(self, prompt_base: str) -> str:
        """Concatena o prompt base com todos os overlays ativos.

        Args:
            prompt_base: O system prompt base (v4).

        Returns:
            Prompt completo com overlays.
        """
        partes = [prompt_base]

        partes.append("\n\n━━━ OVERLAYS EVOLUTIVOS (gerados automaticamente) ━━━\n")

        for nome in OVERLAYS:
            conteudo = self.ler_overlay(nome)
            if conteudo and "Ainda sem" not in conteudo:
                partes.append(conteudo)
                partes.append("")

        return "\n".join(partes)

    def validar_overlay(self, nome: str, conteudo: str) -> tuple[bool, str]:
        """Valida um overlay antes de aplicá-lo.

        Returns:
            (valido, mensagem_erro).
        """
        if not conteudo or not conteudo.strip():
            return False, "Overlay vazio"

        if len(conteudo) > MAX_OVERLAY_CHARS:
            return False, f"Overlay excede {MAX_OVERLAY_CHARS} caracteres ({len(conteudo)})"

        linhas = conteudo.strip().split("\n")
        if len(linhas) > MAX_OVERLAY_LINHAS:
            return False, f"Overlay excede {MAX_OVERLAY_LINHAS} linhas ({len(linhas)})"

        # Verificar que começa com o marcador correto
        marcador = f"[OVERLAY_{nome.upper()}]"
        if marcador not in conteudo[:100]:
            return False, f"Overlay deve começar com {marcador}"

        # Verificar que não contém instruções perigosas
        proibidos = [
            "ignore as instruções",
            "esqueça o sistema",
            "você é agora",
            "ignore o prompt",
            "descarte o perfil",
        ]
        conteudo_lower = conteudo.lower()
        for p in proibidos:
            if p in conteudo_lower:
                return False, f"Overlay contém instrução proibida: '{p}'"

        return True, "OK"

    def aplicar_overlay(self, nome: str, conteudo: str, motivo: str = "") -> bool:
        """Aplica um novo overlay, versionando o anterior.

        Args:
            nome: Nome do overlay.
            conteudo: Novo conteúdo.
            motivo: Motivo da evolução.

        Returns:
            True se aplicado com sucesso.
        """
        valido, erro = self.validar_overlay(nome, conteudo)
        if not valido:
            return False

        versao_atual = self.versao_atual(nome)
        nova_versao = versao_atual + 1

        # Limitar número de versões
        if nova_versao > MAX_VERSOES_POR_OVERLAY:
            # Remover versões antigas (manter última e a nova)
            for v in range(nova_versao - MAX_VERSOES_POR_OVERLAY):
                old = self._overlay_path(nome, v)
                if old.exists():
                    old.unlink()

        # Salvar nova versão
        novo_path = self._dir / f"overlay_{nome}_v{nova_versao}.md"
        novo_path.write_text(conteudo, encoding="utf-8")

        # Atualizar histórico
        self._historico.setdefault("versoes", {})[nome] = nova_versao
        self._historico.setdefault("evolucoes", []).append({
            "overlay": nome,
            "versao_anterior": versao_atual,
            "versao_nova": nova_versao,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "motivo": motivo,
            "chars": len(conteudo),
        })
        self._salvar_historico()
        return True

    def rollback(self, nome: str) -> bool:
        """Reverte um overlay para a versão anterior.

        Returns:
            True se revertido com sucesso.
        """
        versao_atual = self.versao_atual(nome)
        if versao_atual <= 0:
            return False  # Já na versão base

        versao_anterior = versao_atual - 1
        caminho_anterior = self._overlay_path(nome, versao_anterior)

        if not caminho_anterior.exists():
            # Se não temos a versão anterior, voltar ao padrão
            self._historico["versoes"][nome] = 0
            caminho_padrao = self._overlay_path(nome, 0)
            caminho_padrao.write_text(OVERLAYS_PADRAO.get(nome, ""), encoding="utf-8")
        else:
            self._historico["versoes"][nome] = versao_anterior

        self._historico.setdefault("evolucoes", []).append({
            "overlay": nome,
            "versao_anterior": versao_atual,
            "versao_nova": versao_anterior,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "motivo": "ROLLBACK",
        })
        self._salvar_historico()
        return True

    def evoluir_overlay(
        self,
        nome: str,
        cliente_llm: Any,
        contexto: str,
        dados_extra: dict | None = None,
    ) -> tuple[bool, str]:
        """Usa o LLM como meta-agente para reescrever um overlay.

        Args:
            nome: Nome do overlay a evoluir.
            cliente_llm: Instância de LocalLLM.
            contexto: Contexto do candidato serializado.
            dados_extra: Dados adicionais (ranking, erros, etc.).

        Returns:
            (sucesso, mensagem).
        """
        if nome not in META_PROMPTS:
            return False, f"Overlay '{nome}' não suporta evolução automática"

        overlay_atual = self.ler_overlay(nome)
        extra = dados_extra or {}

        prompt = META_PROMPTS[nome].format(
            contexto=contexto[:1500],
            overlay_atual=overlay_atual,
            max_chars=MAX_OVERLAY_CHARS,
            ranking=extra.get("ranking", "(sem dados)"),
            erros=extra.get("erros", "(sem dados)"),
            feedback=extra.get("feedback", "(sem dados)"),
            historico=extra.get("historico", "(sem dados)"),
        )

        try:
            novo_overlay = cliente_llm.chat(
                system="Você é um meta-agente que otimiza prompts. Responda APENAS com o overlay reescrito, sem cercas de código.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
        except Exception as e:
            return False, f"Erro ao chamar LLM: {e}"

        if not novo_overlay or len(novo_overlay.strip()) < 20:
            return False, "LLM retornou overlay vazio ou muito curto"

        # Limpar formatação
        novo_overlay = novo_overlay.strip()
        novo_overlay = re.sub(r"^```[\w]*\n", "", novo_overlay)
        novo_overlay = re.sub(r"\n```\s*$", "", novo_overlay)

        # Validar
        valido, erro = self.validar_overlay(nome, novo_overlay)
        if not valido:
            return False, f"Overlay gerado inválido: {erro}"

        # Aplicar
        sucesso = self.aplicar_overlay(
            nome, novo_overlay,
            motivo=f"Evolução automática (v{self.versao_atual(nome)} → v{self.versao_atual(nome) + 1})"
        )

        if sucesso:
            return True, f"Overlay '{nome}' evoluído para v{self.versao_atual(nome)}"
        return False, "Falha ao aplicar overlay"

    def estatisticas(self) -> dict[str, Any]:
        """Estatísticas do sistema de prompts evoluíveis."""
        versoes = self._historico.get("versoes", {})
        evolucoes = self._historico.get("evolucoes", [])
        return {
            "overlays": {nome: versoes.get(nome, 0) for nome in OVERLAYS},
            "total_evolucoes": len(evolucoes),
            "ultima_evolucao": evolucoes[-1]["timestamp"] if evolucoes else None,
            "rollbacks": sum(1 for e in evolucoes if e.get("motivo") == "ROLLBACK"),
        }
