#!/usr/bin/env python3
"""Was hat der geplante Live-Lauf festgestellt — clear, finding oder unknown?

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
`if: failure()` kennt zwei Antworten: rot und nicht rot. Ein Live-Lauf hat
drei, und die dritte ist die, die zaehlt:

  clear    Die Suite ist gelaufen und war gruen.
  finding  Die Suite ist gelaufen und etwas ist gefallen.
  unknown  Die Suite ist NICHT gelaufen — und niemand weiss, ob der Vertrag
           mit der Quelle noch haelt.

Ein gescheitertes `pip install`, ein Timeout, eine umbenannte Marke: alles
`unknown`, alles sieht unter `if: failure()` aus wie ein gebrochener Vertrag.
Und ein Lauf, in dem jeder Test uebersprungen wurde, sieht unter jedem
Exit-Code-Check aus wie Erfolg.

Diese Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Sie in einen
`run:`-Block zu schreiben hiesse, den einzigen Teil des Workflows, der etwas
behauptet, an die einzige Stelle zu legen, an der ihn niemand testen kann.
Deshalb steht sie hier, neben ihrem Test.

DER UEBERSPRUNGENE LAUF
-----------------------
Gemessen am 7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY`
ueberspringt die Live-Suite alle sechs Tests, und pytest endet mit 0. Ein
woechentlicher Job haette gemeldet: gruen. Geprueft haette er nichts — und ein
offenes Issue haette er zugemacht, mit einem Vergleich, den es nie gab.

`tests - skipped == 0` ist deshalb `unknown` und nicht `clear`. Ein Secret, das
niemand gesetzt hat, ist kein gruener Vertrag mit der Quelle; es ist gar keiner.

DIE QUELLE IST DAS JUNIT-XML, NICHT DER EXIT-CODE
-------------------------------------------------
Der Exit-Code von pytest sagt 0 fuer «alles gruen» und fuer «alles
uebersprungen» dasselbe. Das XML zaehlt Tests, Fehler, Fehlschlaege und
Uebersprungene getrennt, also wird es gelesen. Fehlt es, ist pytest gar nicht
bis zum Schreiben gekommen — auch das ist `unknown`, und zwar mit Grund.

Aufruf:
    python scripts/classify_live_run.py live-report.xml
    python scripts/classify_live_run.py live-report.xml --pytest-exit 1

Gibt `state=...` und `reason=...` auf stdout aus und haengt beides an
`$GITHUB_OUTPUT` an, wenn die Variable gesetzt ist. Der Exit-Code ist immer 0:
Ueber rot oder gruen entscheidet der Workflow, nicht dieser Reporter.
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
UPSTREAM = "upstream"
UNKNOWN = "unknown"

# WARUM ES EINE VIERTE ANTWORT GIBT
# ---------------------------------
# `finding` hiess bis hierher zweierlei: «der Vertrag mit der Quelle ist
# gebrochen» und «die Quelle hat gerade nicht geantwortet». Das erste gehoert
# gefixt, das zweite ausgesessen — und wer sie nicht auseinanderhaelt, tut
# entweder zu viel oder gewoehnt sich das Hinsehen ab.
#
# Anlass waren zwei Ausfaelle an zwei Tagen, beide ohne Vertragsaenderung:
# arXiv mit HTTP 429 am 19.8.2026 vormittags, e-manuscripta mit einem Timeout
# am selben Abend. Beide Male antwortete die Quelle kurz darauf wieder normal.
#
# `upstream` ist NICHT gruen. Es heisst: Die Suite lief, und was fiel, fiel
# daran, dass eine Quelle nicht antwortete — geprueft wurde der Vertrag damit
# nicht. Wie `unknown` schliesst es deshalb kein Issue: Zuzumachen hiesse zu
# behaupten, der Vergleich sei gelaufen.
#
# DIE ENGE SEITE IST ABSICHT
# Der Zustand greift nur, wenn JEDER Fehlschlag eindeutig ein Ausfall ist. Ein
# gemischter Lauf — ein Timeout und eine gerissene Zusicherung — bleibt
# `finding`. Ebenso ein Fehlschlag, dessen Meldung hier nicht wiedererkannt
# wird. Der Fehlermodus dieses Zustands ist nicht der falsche Alarm, sondern
# das Wegerklaeren: Ein `upstream`, das zu breit greift, verwandelt jeden
# echten Befund in ein Achselzucken.

# Aus echten Laeufen abgelesen, nicht ausgedacht — und nach Herkunft getrennt,
# weil sich die drei Sorten unterschiedlich pruefen lassen.
#
# Die Meldungen unten stehen woertlich im Code. `scripts/check_gate_consistency.py`
# haelt sie dagegen: Formuliert jemand `handle_api_error` um, faellt das auf,
# statt dass der zugehoerige Ausfall ab da still als `finding` durchgeht.
UPSTREAM_MELDUNGEN: dict[str, str] = {
    # Muster -> Modul in `src/`, in dem es als String-Literal stehen muss
    "Zeitüberschreitung. Der Server antwortet nicht.": "api_client.py",
    "Rate-Limit erreicht (429)": "api_client.py",
    "Dienst vorübergehend nicht verfügbar (503)": "api_client.py",
    "Alle OA-Rechtsquellen sind derzeit nicht erreichbar": "oa_legal.py",
}

# Ausnahme-Typnamen. Sie stehen nirgends als fertiger Text: Sie erscheinen nur,
# weil `handle_api_error` im letzten Zweig `type(e).__name__` einbettet. Faellt
# dieser Zweig weg, erreicht kein Typname mehr eine Meldung — dann ist die ganze
# Gruppe tot, ohne dass ein einzelnes Muster falsch waere. Genau deshalb prueft
# der Guard den Zweig und nicht die Namen.
UPSTREAM_TYPEN: tuple[str, ...] = (
    "RemoteProtocolError: Server disconnected",
    "UpstreamUnavailableError",
    "ConnectTimeout",
    "ReadTimeout",
    "PoolTimeout",
    "ConnectError",
)

# Der Zweig, der die Typnamen ueberhaupt sichtbar macht.
GENERISCHER_ZWEIG = "Unerwarteter Fehler: "

UPSTREAM_MUSTER: tuple[str, ...] = tuple(UPSTREAM_MELDUNGEN) + UPSTREAM_TYPEN


def _fehlermeldungen(root: ET.Element) -> list[str]:
    """Text jedes `<failure>`/`<error>` — Attribut und Inhalt zusammen.

    Beides, weil pytest die Meldung ins `message`-Attribut schreibt, den
    Traceback aber in den Elementtext. Ein Ausfall kann in jedem von beiden
    stehen, je nachdem, ob er als Ausnahme durchschlaegt oder in einer
    Zusicherung landet.
    """
    texte = []
    for testcase in root.iter("testcase"):
        for kind in testcase:
            if kind.tag in ("failure", "error"):
                texte.append(f"{kind.get('message') or ''}\n{kind.text or ''}")
    return texte


def _ist_ausfall(meldung: str) -> bool:
    return any(muster in meldung for muster in UPSTREAM_MUSTER)


def classify(report: Path, pytest_exit: int | None = None) -> tuple[str, str]:
    """(state, reason) aus einem JUnit-XML und optional dem pytest-Exit-Code."""
    if not report.is_file():
        return (
            UNKNOWN,
            f"kein Report unter {report} — pytest ist nicht bis zum Schreiben "
            "gekommen" + (f" (Exit {pytest_exit})" if pytest_exit is not None else ""),
        )
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        return UNKNOWN, f"{report} ist nicht lesbar: {exc}"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return UNKNOWN, f"{report} enthaelt keine testsuite"

    def total(attr: str) -> int:
        return sum(int(s.get(attr) or 0) for s in suites)

    tests, failures, errors, skipped = (
        total("tests"),
        total("failures"),
        total("errors"),
        total("skipped"),
    )

    if failures or errors:
        meldungen = _fehlermeldungen(root)
        ausfaelle = [m for m in meldungen if _ist_ausfall(m)]
        # Nur wenn ALLE Fehlschlaege Ausfaelle sind — und wenn ueberhaupt
        # Meldungen im XML stehen. Ein XML ohne `<failure>`-Elemente, das
        # trotzdem Fehlschlaege zaehlt, ist nichts, worueber sich urteilen
        # laesst; das bleibt `finding`.
        if meldungen and len(ausfaelle) == len(meldungen):
            return (
                UPSTREAM,
                f"{len(ausfaelle)} von {tests} Test(s) gefallen, alle an einer "
                f"Quelle, die nicht geantwortet hat — ueber den Vertrag sagt das "
                f"nichts",
            )
        return (
            FINDING,
            f"{failures} Fehlschlag/Fehlschlaege und {errors} Fehler von {tests} Test(s)"
            + (
                f" (davon {len(ausfaelle)} durch einen Quellen-Ausfall; der Rest "
                f"nicht, deshalb kein `upstream`)"
                if ausfaelle
                else ""
            ),
        )
    if tests == 0:
        return (
            UNKNOWN,
            "null Tests eingesammelt — die Marke oder die Dateien haben sich "
            "bewegt, und ein Erfolg ohne Test ist kein Erfolg",
        )
    if tests - skipped == 0:
        return (
            UNKNOWN,
            f"alle {tests} Test(s) uebersprungen — meist ein fehlendes Secret oder "
            "eine nicht erfuellte Vorbedingung. Geprueft wurde nichts",
        )
    return CLEAR, f"{tests - skipped} von {tests} Test(s) ausgefuehrt, alle gruen"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_live_run")
    ap.add_argument("report", type=Path, help="Pfad zum JUnit-XML von pytest")
    ap.add_argument("--pytest-exit", type=int, default=None)
    args = ap.parse_args(argv)

    state, reason = classify(args.report, args.pytest_exit)
    print(f"state={state}")
    print(f"reason={reason}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus, bevor der Grund in `$GITHUB_OUTPUT` geht: Die
        # `key=value`-Form endet an der ersten neuen Zeile, und was danach
        # steht, liest der Runner als naechstes Output. Ein Grund koennte so
        # ein `state=clear` nachschieben und den roten Lauf gruen faerben.
        flat = " ".join(reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
