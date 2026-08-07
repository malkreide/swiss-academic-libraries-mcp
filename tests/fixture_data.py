"""Zugriff auf die aufgezeichneten Fixtures.

Ein fehlender Name ist hier ein Fehler und keine leere Struktur. Ein Loader,
der bei einem Tippfehler `""` zurueckgibt, erzeugt einen Test, der nichts mehr
prueft und trotzdem Erfolg meldet — die teuerste Sorte gruen.

Herkunft, Datum und Auswahlregel stehen in `fixtures/PROVENANCE.md`.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"


@cache
def raw(name: str) -> str:
    """Der aufgezeichnete Text, unveraendert.

    Bewusst ohne jede Reinigung: `oai_ex_ante_listrecords.xml` traegt ein rohes
    Steuerzeichen, weil die Quelle es so liefert. Wer es hier wegputzte, naehme
    dem einzigen Test, der das belegt, seinen Gegenstand.
    """
    path = FIXTURES / name
    if not path.exists():
        available = sorted(p.name for p in FIXTURES.iterdir() if p.suffix in (".xml", ".json"))
        raise FileNotFoundError(
            f"Fixture {name!r} gibt es nicht. Vorhanden: {available}. "
            "Neu aufzeichnen mit `python scripts/record_fixtures.py`."
        )
    return path.read_text(encoding="utf-8")


def payload(name: str) -> Any:
    """Eine aufgezeichnete JSON-Antwort."""
    return json.loads(raw(name))
