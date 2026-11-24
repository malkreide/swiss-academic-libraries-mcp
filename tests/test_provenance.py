"""Ein Neulauf von `scripts/record_fixtures.py` darf die Live-Report-Herkunft nicht loeschen.

WARUM ES DIESE DATEI GIBT. Bis November 2026 schrieb `_write_provenance` die
`PROVENANCE.md` von Grund auf neu. Das Skript kennt nur die HTTP-Fixtures;
die Eintraege der `live-report-*.xml` waren von Hand nachgetragen (6524445,
985cad8, 91d8c09, #130). Ein Neulauf haette sie ohne Meldung geloescht — fuer
`live-report-403.xml` den einzigen Beleg ihrer Herkunft, denn die e-rara-Sperre
vom September 2026 gibt es nicht mehr, und die Datei laesst sich nicht neu
aufzeichnen.

WIE ES GEPRUEFT WIRD. Nicht an den Hilfsfunktionen, sondern am Neulauf selbst:
`record()` laeuft gegen eine MockTransport, die die aufgezeichneten Fixtures
zurueckspielt, und schreibt in eine Kopie von `tests/fixtures/`. Das echte
Verzeichnis bleibt unberuehrt. Gepatcht wird der Modul-Alias `_Client`, nicht
`httpx.Client` — sonst traefe der Patch den ganzen Prozess.

Die erwarteten Eintraege werden aus der Datei gelesen, wie sie im Repo steht,
nicht aus dem markierten Abschnitt: Wer einen Eintrag aus den Markern schiebt,
soll hier rot werden und nicht still mitwandern.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import record_fixtures as rf  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _handgepflegte_namen() -> list[str]:
    """Jede Fixture, die das Skript NICHT erzeugt — unabhaengig von den Markern."""
    return sorted(
        p.name
        for p in FIXTURES.iterdir()
        if p.is_file() and p.name != "PROVENANCE.md" and p.name not in rf.AUFGEZEICHNET
    )


def _eintrag(text: str, name: str) -> str:
    """Der Block `## `name`` bis vor die naechste Ueberschrift oder den Endmarker."""
    m = re.search(rf"^## `{re.escape(name)}`\n.*?(?=^## |^<!-- |\Z)", text, re.M | re.S)
    assert m, f"kein Eintrag fuer {name} in PROVENANCE.md"
    return m.group(0).rstrip("\n")


def _antwort(request: httpx.Request) -> httpx.Response:
    """Ordnet jede Anfrage des Skripts ihrer aufgezeichneten Antwort zu."""
    url = request.url
    q = {k: v[0] for k, v in parse_qs(url.query.decode()).items()}
    host = url.host
    if host == "swisscovery.slsp.ch":
        name = "sru_search.xml"
    elif host == "www.e-rara.ch":
        name = "oai_erara_listsets.xml" if q.get("verb") == "ListSets" else "oai_erara_listrecords.xml"
    elif host == "www.e-periodica.ch":
        name = "oai_eperiodica_listrecords.xml"
    elif host == "www.e-manuscripta.ch":
        name = "oai_emanuscripta_listrecords.xml"
    elif host == "sui-generis.ch":
        name = "oai_sui_generis_listrecords.xml"
    elif host == "ex-ante.ch":
        name = "oai_ex_ante_listrecords.xml"
    elif host == "api.repositorium.ch":
        name = "repositorium_rows.json"
    elif host == "api.crossref.org":
        name = "crossref_works.json"
    elif host == "export.arxiv.org":
        name = "arxiv_feed.xml"
    else:
        raise AssertionError(f"unerwartete Anfrage: {url}")
    return httpx.Response(200, content=(FIXTURES / name).read_bytes())


@pytest.fixture
def kopie(tmp_path, monkeypatch):
    """Eine Kopie von `tests/fixtures/` als Ziel, und ein Zaehler fuer Anfragen."""
    ziel = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, ziel)
    anfragen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        anfragen.append(request)
        return _antwort(request)

    def client(**kwargs):
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(rf, "FIXTURES", ziel)
    monkeypatch.setattr(rf, "_Client", client)
    return ziel, anfragen


def test_es_gibt_handgepflegte_eintraege():
    """Ohne diese Vorbedingung pruefte der Neulauf-Test eine leere Liste."""
    namen = _handgepflegte_namen()
    assert "live-report-403.xml" in namen
    assert all(n.startswith("live-report-") for n in namen), namen


def test_neulauf_behaelt_live_report_eintraege(kopie):
    ziel, anfragen = kopie
    vorher = (FIXTURES / "PROVENANCE.md").read_text(encoding="utf-8")

    assert rf.record() == 0

    nachher = (ziel / "PROVENANCE.md").read_text(encoding="utf-8")
    assert anfragen, "der Neulauf hat nichts abgefragt — dann prueft er nichts"
    for name in _handgepflegte_namen():
        assert _eintrag(vorher, name) in nachher, f"Neulauf hat den Eintrag {name} veraendert oder geloescht"
    # Ein zweiter Lauf muss die Marker wiederfinden, sonst hielte es nur einmal.
    assert rf._read_hand_section(nachher) == rf._read_hand_section(vorher)


def test_jeder_handgepflegte_eintrag_steht_zwischen_den_markern():
    """Ausserhalb der Marker schreibt das Skript neu — dort ginge der Eintrag verloren."""
    hand = rf._read_hand_section((FIXTURES / "PROVENANCE.md").read_text(encoding="utf-8"))
    fehlend = [n for n in _handgepflegte_namen() if f"## `{n}`" not in hand]
    assert not fehlend, f"nicht im handgepflegten Abschnitt: {fehlend}"


def test_fehlende_marker_brechen_vor_der_ersten_anfrage_ab(kopie):
    ziel, anfragen = kopie
    prov = ziel / "PROVENANCE.md"
    prov.write_text(prov.read_text(encoding="utf-8").replace(rf.HAND_ENDE, ""), encoding="utf-8")
    vorher = {p.name: p.read_bytes() for p in ziel.iterdir()}

    with pytest.raises(SystemExit, match="Marker"):
        rf.record()

    assert not anfragen
    assert {p.name: p.read_bytes() for p in ziel.iterdir()} == vorher


def test_unbelegte_fixture_bricht_vor_der_ersten_anfrage_ab(kopie):
    """Ein neuer Live-Report ohne Eintrag wuerde sonst still herkunftslos."""
    ziel, anfragen = kopie
    (ziel / "live-report-neu.xml").write_text("<testsuites/>\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="live-report-neu.xml"):
        rf.record()

    assert not anfragen
