"""Exporta o banco de questões para Anki (.apkg ou CSV).

Uso:
    python exportar_anki.py                          # gera .csv
    python exportar_anki.py --formato csv            # força CSV
    python exportar_anki.py --formato apkg           # tenta .apkg (requer genanki)
    python exportar_anki.py --disciplina Legislacao  # filtra por disciplina
    python exportar_anki.py --output questoes.apkg   # caminho de saída
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from treino import BANCO_QUESTOES


def exportar_csv(caminho: Path, disciplina: str = "") -> int:
    """Exporta questões para CSV (frente=pergunta, verso=resposta+explicação).

    Formato compatível com Anki (importação direta).

    Returns:
        Número de questões exportadas.
    """
    questoes = BANCO_QUESTOES
    if disciplina:
        questoes = [q for q in questoes if q.disciplina.lower() == disciplina.lower()]

    if not questoes:
        print("Nenhuma questão encontrada para o filtro informado.")
        return 0

    with caminho.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Pergunta", "Resposta", "Disciplina", "Tags"])
        for q in questoes:
            opcoes = "\n".join(f"{i}) {o}" for i, o in enumerate(q.opcoes))
            frente = f"{q.pergunta}\n\n{opcoes}"
            verso = f"**Resposta correta:** {q.correta}) {q.opcoes[q.correta]}\n\n{q.explicacao}"
            writer.writerow([frente, verso, q.disciplina, " ".join(q.tags)])

    return len(questoes)


def exportar_apkg(caminho: Path, disciplina: str = "") -> int:
    """Exporta questões para .apkg (formato nativo Anki).

    Requer genanki: pip install genanki

    Returns:
        Número de questões exportadas.
    """
    try:
        import genanki
    except ImportError:
        print("genanki não instalado. Instale com: pip install genanki")
        print("Fallback para CSV...")
        csv_path = caminho.with_suffix(".csv")
        return exportar_csv(csv_path, disciplina)

    questoes = BANCO_QUESTOES
    if disciplina:
        questoes = [q for q in questoes if q.disciplina.lower() == disciplina.lower()]

    if not questoes:
        print("Nenhuma questão encontrada.")
        return 0

    modelo = genanki.Model(
        1607392319,
        "Questão CESGRANRIO",
        fields=[
            {"name": "Pergunta"},
            {"name": "Opcoes"},
            {"name": "Resposta"},
        ],
        templates=[
            {
                "name": "Questão",
                "qfmt": "{{Pergunta}}<br><br>{{Opcoes}}",
                "afmt": "{{FrontSide}}<hr id=answer><b>Resposta correta:</b> {{Resposta}}",
            },
        ],
    )

    deck = genanki.Deck(
        2059400110,
        f"AgentePetrobras{' - ' + disciplina if disciplina else ''}",
    )

    for i, q in enumerate(questoes):
        opcoes_html = "<br>".join(f"{j}) {o}" for j, o in enumerate(q.opcoes))
        resposta = f"{q.correta}) {q.opcoes[q.correta]}<br><br>{q.explicacao}"
        nota = genanki.Note(
            model=modelo,
            fields=[q.pergunta, opcoes_html, resposta],
            tags=q.tags,
        )
        deck.add_note(nota)

    genanki.Package(deck).write_to_file(str(caminho))
    return len(questoes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta questões para Anki")
    parser.add_argument("--formato", choices=["csv", "apkg"], default="csv",
                        help="Formato de saída (default: csv)")
    parser.add_argument("--disciplina", default="", help="Filtrar por disciplina")
    parser.add_argument("--output", default="", help="Caminho do arquivo de saída")
    args = parser.parse_args()

    if args.output:
        output = Path(args.output)
    else:
        output = Path("questoes_anki.csv" if args.formato == "csv" else "questoes_anki.apkg")

    if args.formato == "apkg":
        total = exportar_apkg(output, args.disciplina)
    else:
        total = exportar_csv(output, args.disciplina)

    if total:
        print(f"✓ {total} questões exportadas para {output}")
    else:
        print("Nenhuma questão exportada.")


if __name__ == "__main__":
    main()
