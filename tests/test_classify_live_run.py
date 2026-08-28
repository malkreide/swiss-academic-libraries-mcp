#!/usr/bin/env python3
"""Tests fuer scripts/classify_live_run.py — die drei Antworten eines Live-Laufs.

Die Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Genau deshalb
steht sie in einem Skript und nicht in einem `run:`-Block: So kann jemand sie
gegen die Faelle halten, aus denen sie entstanden ist.

Der wichtigste Fall ist `test_alle_uebersprungen_ist_nicht_gruen`. Gemessen am
7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY` ueberspringt die
Live-Suite alle sechs Tests und pytest endet mit 0. Ein Job, der das als gruen
bucht, schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

Nur Standardbibliothek, kein Netz.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import classify_live_run as clr  # noqa: E402


def write(tmp: Path, xml: str) -> Path:
    path = tmp / "live-report.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def suite(tests: int, failures: int = 0, errors: int = 0, skipped: int = 0) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}"></testsuite></testsuites>'
    )


class ClassifyTest(unittest.TestCase):
    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_alles_gruen_ist_clear(self):
        state, reason = self._state(suite(tests=3))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("3 von 3", reason)

    def test_ein_fehlschlag_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_ein_fehler_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, errors=1))
        self.assertEqual(state, clr.FINDING)

    def test_alle_uebersprungen_ist_nicht_gruen(self):
        """swiss-transport-mcp ohne TRANSPORT_API_KEY: 6 von 6 uebersprungen."""
        state, reason = self._state(suite(tests=6, skipped=6))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("uebersprungen", reason)

    def test_teilweise_uebersprungen_ist_gruen(self):
        """Ein einzelner Skip ist eine Entscheidung im Test, kein Ausfall."""
        state, reason = self._state(suite(tests=6, skipped=5))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("1 von 6", reason)

    def test_null_tests_ist_kein_erfolg(self):
        """Die Marke umbenannt, die Dateien verschoben — pytest meldet trotzdem 0."""
        state, reason = self._state(suite(tests=0))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("null Tests", reason)

    def test_ein_fehlschlag_schlaegt_uebersprungene(self):
        state, _ = self._state(suite(tests=6, skipped=5, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_mehrere_testsuites_werden_summiert(self):
        xml = (
            "<testsuites>"
            '<testsuite tests="2" failures="0" errors="0" skipped="2"/>'
            '<testsuite tests="3" failures="0" errors="0" skipped="0"/>'
            "</testsuites>"
        )
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)

    def test_eine_einzelne_testsuite_ohne_huelle(self):
        xml = '<testsuite tests="2" failures="0" errors="0" skipped="0"/>'
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)


class MissingReportTest(unittest.TestCase):
    """Kein Report heisst: pytest kam nicht bis zum Schreiben. Nie clear."""

    def test_fehlender_report_ist_unknown(self):
        state, reason = clr.classify(Path("/nonexistent/live-report.xml"), pytest_exit=4)
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("Exit 4", reason)

    def test_kaputtes_xml_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<testsuite tests=")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)

    def test_xml_ohne_testsuite_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<irgendwas/>")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)


class GithubOutputTest(unittest.TestCase):
    """Der Workflow liest state und reason ueber $GITHUB_OUTPUT."""

    def test_beide_werte_werden_angehaengt(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=2))
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                rc = clr.main([str(report)])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            written = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("state=clear", written)
        self.assertIn("reason=", written)


# Die Meldungstexte unten sind KEINE Erfindung: Sie stammen aus JUnit-XMLs, die
# am 19.8.2026 gegen eine haengende bzw. mit 429 antwortende Attrappe erzeugt
# wurden — durch dieselbe Fehlerbehandlung, die auch in der CI laeuft. Eine
# handgeschriebene Meldung wuerde die Annahme des Autors testen, nicht den Code.
TIMEOUT_MELDUNG = (
    "mcp.shared.exceptions.MCPError: Fehler bei emanuscripta_list_records: "
    "Zeitüberschreitung. Der Server antwortet nicht."
)
RATE_LIMIT_MELDUNG = (
    "mcp.shared.exceptions.MCPError: Fehler bei eperiodica_list_records: "
    "Rate-Limit erreicht (429). Bitte kurz warten."
)
ZUSICHERUNG_MELDUNG = "AssertionError: Vertrag verletzt\nassert 'Handschrift' in 'das steht da nicht'"


def suite_mit_fehlern(meldungen: list[str], tests: int | None = None) -> str:
    faelle = "".join(
        f'<testcase name="test_{i}"><failure message="{m}"></failure></testcase>'
        for i, m in enumerate(meldungen)
    )
    gesamt = tests if tests is not None else len(meldungen)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{gesamt}" '
        f'failures="{len(meldungen)}" errors="0" skipped="0">{faelle}</testsuite></testsuites>'
    )


class UpstreamTest(unittest.TestCase):
    """Die vierte Antwort: gelaufen, gefallen — aber nicht am Vertrag.

    `finding` hiess bis zum 19.8.2026 zweierlei, «Vertrag gebrochen» und
    «Quelle antwortet nicht». Das erste gehoert gefixt, das zweite ausgesessen.
    """

    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_nur_timeouts_sind_upstream(self):
        state, reason = self._state(suite_mit_fehlern([TIMEOUT_MELDUNG], tests=30))
        self.assertEqual(state, clr.UPSTREAM)
        self.assertIn("nicht geantwortet", reason)

    def test_nur_rate_limit_ist_upstream(self):
        state, _ = self._state(suite_mit_fehlern([RATE_LIMIT_MELDUNG], tests=30))
        self.assertEqual(state, clr.UPSTREAM)

    def test_mehrere_ausfaelle_bleiben_upstream(self):
        state, _ = self._state(suite_mit_fehlern([TIMEOUT_MELDUNG, RATE_LIMIT_MELDUNG], tests=30))
        self.assertEqual(state, clr.UPSTREAM)

    # --- die enge Seite: was NICHT upstream werden darf ------------------

    def test_gerissene_zusicherung_bleibt_finding(self):
        """Der Fall, um dessentwillen es die Live-Suite gibt."""
        state, _ = self._state(suite_mit_fehlern([ZUSICHERUNG_MELDUNG], tests=30))
        self.assertEqual(state, clr.FINDING)

    def test_gemischter_lauf_bleibt_finding(self):
        """Ein Timeout neben einem echten Befund darf den Befund nicht schlucken.

        Der Fehlermodus dieses Zustands ist nicht der falsche Alarm, sondern
        das Wegerklaeren: Ein `upstream`, das zu breit greift, verwandelt jeden
        echten Befund in ein Achselzucken.
        """
        state, reason = self._state(suite_mit_fehlern([TIMEOUT_MELDUNG, ZUSICHERUNG_MELDUNG], tests=30))
        self.assertEqual(state, clr.FINDING)
        self.assertIn("deshalb kein `upstream`", reason)

    def test_unbekannte_meldung_bleibt_finding(self):
        """Was hier niemand wiedererkennt, ist im Zweifel ein Befund."""
        state, _ = self._state(suite_mit_fehlern(["ValueError: irgendetwas ganz anderes"], tests=30))
        self.assertEqual(state, clr.FINDING)

    def test_fehlschlaege_ohne_meldungen_bleiben_finding(self):
        """Ein XML, das Fehlschlaege zaehlt, aber keine nennt.

        Darueber laesst sich nicht urteilen — und Nichturteilen heisst hier
        `finding`, nicht `upstream`.
        """
        state, _ = self._state(suite(tests=30, failures=2))
        self.assertEqual(state, clr.FINDING)

    def test_upstream_ist_nicht_clear(self):
        """Damit niemand auf die Idee kommt, den Job dafuer gruen zu machen.

        Eine Quelle, die eine Woche lang nicht antwortet, gehoert gesehen —
        auch wenn niemand sie reparieren kann.
        """
        state, _ = self._state(suite_mit_fehlern([TIMEOUT_MELDUNG], tests=30))
        self.assertNotEqual(state, clr.CLEAR)


class EchteReportsTest(unittest.TestCase):
    """Gegen aufgezeichnete JUnit-XMLs statt gegen zusammengebaute Strings.

    Die zusammengebauten Faelle oben pruefen die Logik; diese hier pruefen, dass
    die Muster auf das passen, was pytest und unsere Fehlerbehandlung wirklich
    schreiben. Ohne sie waere eine Aenderung an `handle_api_error` unbemerkt an
    der Einordnung vorbeigelaufen.
    """

    def test_aufgezeichneter_timeout_ist_upstream(self):
        pfad = Path(__file__).parent / "fixtures" / "live-report-timeout.xml"
        state, _ = clr.classify(pfad)
        self.assertEqual(state, clr.UPSTREAM)

    def test_aufgezeichnete_zusicherung_ist_finding(self):
        pfad = Path(__file__).parent / "fixtures" / "live-report-assertion.xml"
        state, _ = clr.classify(pfad)
        self.assertEqual(state, clr.FINDING)


class GithubOutputZeilenTest(unittest.TestCase):
    """Ein Grund mit Zeilenumbruch darf kein zweites Output nachschieben.

    `key=value` endet in `$GITHUB_OUTPUT` an der ersten neuen Zeile; was
    danach steht, liest der Runner als eigenen Output. Der Reportpfad kommt
    vom Aufrufer und steht woertlich im Grund — ein Umbruch darin schoebe
    sonst ein `state=clear` nach und faerbte den roten Lauf gruen.
    """

    def test_umbruch_im_grund_schiebt_kein_zweites_output_nach(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                clr.main([str(Path(tmp) / "live-report.xml") + "\nstate=clear"])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            zeilen = [z for z in out.read_text(encoding="utf-8").splitlines() if z]
        self.assertEqual([z for z in zeilen if z.startswith("state=")], ["state=unknown"])
        self.assertEqual(len(zeilen), 2)


if __name__ == "__main__":
    unittest.main()
