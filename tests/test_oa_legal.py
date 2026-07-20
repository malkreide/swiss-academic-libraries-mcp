"""
Tests für die OA-Rechtsliteratur-Erschliessung (oa_legal + oa_law_*-Tools).

Netzzugriff wird mit ``respx`` gemockt; Fixtures sind gekürzte, aber echte
Antworten von sui generis / ex/ante (OAI-PMH) und Repositorium.ch (PostgREST).

Pflicht-Testfälle (siehe Aufgaben-Phase 4):
  1. Suche liefert Treffer mit DOI und Lizenz
  2. Datensatz ohne Lizenzangabe → license == "unknown"  (der wichtigste Test)
  3. Datensatz ohne DOI → persistente URL vorhanden
  4. Französischsprachiger Beitrag wird gefunden und markiert
  5. Kein Volltext in irgendeinem Response-Feld
  6. Pagination / Resumption-Token über Seitengrenze
  7. Eine Quelle nicht erreichbar → übrige liefern, Ausfall ausgewiesen
  8. Alle Quellen nicht erreichbar → erklärender Fehler
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from swiss_academic_libraries_mcp import oa_legal

# ─── Fixtures: gekürzte echte Upstream-Antworten ─────────────────────────────

# sui generis — OAI-PMH oai_dc: DOI + CC-Lizenz direkt in dc:rights, DE.
SUI_OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:www.hope.uzh.ch:article/204</identifier>
        <datestamp>2022-03-01T00:00:00Z</datestamp>
        <setSpec>suigeneris:ART</setSpec>
      </header>
      <metadata>
        <oai_dc:dc>
          <dc:title xml:lang="de">Maschinelle Gesichtserkennung im oeffentlichen Raum</dc:title>
          <dc:creator>Muster, Anna</dc:creator>
          <dc:description xml:lang="de">Der Beitrag untersucht den Datenschutz bei Gesichtserkennung.</dc:description>
          <dc:publisher>sui generis</dc:publisher>
          <dc:date>2022-01-15</dc:date>
          <dc:identifier>https://sui-generis.ch/article/view/sg.204</dc:identifier>
          <dc:identifier>info:doi/10.21257/sg.204</dc:identifier>
          <dc:language>deu</dc:language>
          <dc:rights>https://creativecommons.org/licenses/by-sa/4.0</dc:rights>
        </oai_dc:dc>
      </metadata>
    </record>
    <record>
      <header>
        <identifier>oai:www.hope.uzh.ch:article/18</identifier>
        <datestamp>2016-06-20T00:00:00Z</datestamp>
      </header>
      <metadata>
        <oai_dc:dc>
          <dc:title xml:lang="de">Die Durchsetzungsinitiative</dc:title>
          <dc:creator>Raselli, Niccolo</dc:creator>
          <dc:description xml:lang="de">Analyse der Initiative.</dc:description>
          <dc:date>2016-06-20</dc:date>
          <dc:identifier>https://sui-generis.ch/article/view/sg.18</dc:identifier>
          <dc:identifier>info:doi/10.21257/sg.18</dc:identifier>
          <dc:language>deu</dc:language>
          <dc:rights>Copyright (c) 2016 Niccolo Raselli</dc:rights>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""

# ex/ante — OAI-PMH oai_dc: KEINE DOI, nur persistente URL, FR-Beitrag.
EXANTE_OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <ListRecords>
    <record>
      <header>
        <identifier>oai:ojs.ex-ante.ch:article/36</identifier>
        <datestamp>2021-02-27T18:09:38Z</datestamp>
        <setSpec>exante:ART</setSpec>
      </header>
      <metadata>
        <oai_dc:dc>
          <dc:title xml:lang="fr-FR">Le droit de l'amenagement du territoire</dc:title>
          <dc:creator xml:lang="fr-FR">Zuber-Roy, Celine</dc:creator>
          <dc:description xml:lang="fr-FR">Cette contribution analyse le droit applicable.</dc:description>
          <dc:date>2021-02-27</dc:date>
          <dc:identifier>https://ex-ante.ch/index.php/exante/article/view/36</dc:identifier>
          <dc:language>fra</dc:language>
          <dc:rights>Copyright (c) 2021 Celine Zuber-Roy</dc:rights>
        </oai_dc:dc>
      </metadata>
    </record>
  </ListRecords>
</OAI-PMH>"""

# Repositorium.ch — PostgREST JSON: license null, DOI vorhanden, datei_url (Volltext!) darf NICHT leaken.
REPO_JSON = [
    {
        "id": 66,
        "titel": "Datenschutz und Umweltschutz - ein Dilemma?",
        "author": {"full_name": "Anne-Sophie Morand", "username": "asmorand"},
        "coauthors": ["Liliane Obrecht"],
        "abstract": "Gedanken zum Verhaeltnis von Datenschutz und Umweltschutz.",
        "doi": "https://doi.org/10.21257/sg.221",
        "datei_url": "4e3af83b/public/DatenschutzGEHEIMERVOLLTEXT.pdf",
        "content": "HIER STUENDE DER GESCHUETZTE VOLLTEXT DES AUFSATZES",
        "erschienen_in": "sui generis 2022, S. 207-216",
        "sprache": "DE",
        "peer_review": "ja",
        "public": True,
        "license": None,
    }
]

# Zweite OAI-Seite für den Pagination-Test.
SUI_OAI_PAGE1 = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <ListRecords>
    <record><header><identifier>oai:x:1</identifier></header><metadata><oai_dc:dc>
      <dc:title>Beitrag Alpha ueber Datenschutz</dc:title>
      <dc:date>2020-01-01</dc:date>
      <dc:identifier>info:doi/10.21257/sg.100</dc:identifier>
      <dc:language>deu</dc:language>
    </oai_dc:dc></metadata></record>
    <resumptionToken completeListSize="2" cursor="0">TOKEN-PAGE-2</resumptionToken>
  </ListRecords>
</OAI-PMH>"""

SUI_OAI_PAGE2 = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <ListRecords>
    <record><header><identifier>oai:x:2</identifier></header><metadata><oai_dc:dc>
      <dc:title>Beitrag Beta ueber Datenschutz</dc:title>
      <dc:date>2021-01-01</dc:date>
      <dc:identifier>info:doi/10.21257/sg.101</dc:identifier>
      <dc:language>deu</dc:language>
    </oai_dc:dc></metadata></record>
    <resumptionToken completeListSize="2" cursor="1"></resumptionToken>
  </ListRecords>
</OAI-PMH>"""

EMPTY_OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords></ListRecords></OAI-PMH>"""


# ─── Test-Infrastruktur ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Cache leeren, Retries sofort (keine echten sleeps), Crossref standardmässig aus."""
    oa_legal._CACHE.clear()

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr("swiss_academic_libraries_mcp.api_client.asyncio.sleep", _no_sleep)
    monkeypatch.setenv("OA_LAW_CROSSREF_ENRICH", "0")
    yield
    oa_legal._CACHE.clear()


def _mock_sources(sui=SUI_OAI, exante=EXANTE_OAI, repo=REPO_JSON):
    """Registriert Standard-Routen für alle drei Quellen (per Host)."""
    if sui is not None:
        respx.get(host="sui-generis.ch").mock(return_value=httpx.Response(200, text=sui))
    if exante is not None:
        respx.get(host="ex-ante.ch").mock(return_value=httpx.Response(200, text=exante))
    if repo is not None:
        respx.get(host="api.repositorium.ch").mock(return_value=httpx.Response(200, json=repo))


# ─── Pflicht-Testfall 1: Treffer mit DOI und Lizenz ──────────────────────────


@respx.mock
async def test_search_returns_hit_with_doi_and_license():
    _mock_sources()
    out = await oa_legal.search_publications(query="Datenschutz Gesichtserkennung")
    hits = [p for p in out["results"] if p.doi == "10.21257/sg.204"]
    assert hits, "Erwarteter Treffer mit DOI fehlt"
    pub = hits[0]
    assert pub.doi == "10.21257/sg.204"
    assert pub.license == "CC BY-SA 4.0"  # aus dc:rights extrahiert
    assert pub.url.startswith("https://")


# ─── Pflicht-Testfall 2: Kein Lizenzfeld → "unknown" (der wichtigste Test) ───


@respx.mock
async def test_missing_license_becomes_unknown_not_dropped():
    _mock_sources()
    out = await oa_legal.search_publications(query="Datenschutz", max_records=50)

    # Repositorium-Datensatz hat license=null → muss "unknown" sein, nicht weggelassen.
    repo_hits = [p for p in out["results"] if p.source_name == "Repositorium.ch"]
    assert repo_hits, "Repositorium-Treffer wurde fälschlich weggelassen"
    assert repo_hits[0].license == "unknown"

    # license ist NIE leer.
    for p in out["results"]:
        assert p.license and p.license.strip()

    # sui-generis-Beitrag mit reinem Copyright-Statement (kein CC) → ebenfalls "unknown".
    out2 = await oa_legal.search_publications(query="Durchsetzungsinitiative", max_records=50)
    copyright_only = [p for p in out2["results"] if p.doi == "10.21257/sg.18"]
    assert copyright_only and copyright_only[0].license == "unknown"


# ─── Relevanz-Ranking: Anker-Query «Datenschutz im Bildungsbereich» ──────────

RANKING_OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
  xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <ListRecords>
    <record><header><identifier>oai:x:edu</identifier></header><metadata><oai_dc:dc>
      <dc:title xml:lang="de">Datenschutz in der Bildung</dc:title>
      <dc:date>2023-01-01</dc:date>
      <dc:identifier>info:doi/10.21257/sg.900</dc:identifier>
      <dc:language>deu</dc:language>
    </oai_dc:dc></metadata></record>
    <record><header><identifier>oai:x:only</identifier></header><metadata><oai_dc:dc>
      <dc:title xml:lang="de">Datenschutz beim Kreditscoring</dc:title>
      <dc:date>2024-01-01</dc:date>
      <dc:identifier>info:doi/10.21257/sg.901</dc:identifier>
      <dc:language>deu</dc:language>
    </oai_dc:dc></metadata></record>
    <record><header><identifier>oai:x:none</identifier></header><metadata><oai_dc:dc>
      <dc:title xml:lang="de">Rechtsschutz im Zivilprozess</dc:title>
      <dc:date>2024-01-01</dc:date>
      <dc:identifier>info:doi/10.21257/sg.902</dc:identifier>
      <dc:language>deu</dc:language>
    </oai_dc:dc></metadata></record>
  </ListRecords>
</OAI-PMH>"""


@respx.mock
async def test_anchor_query_returns_ranked_hits_not_empty():
    _mock_sources(sui=RANKING_OAI, exante=EMPTY_OAI, repo=[])
    out = await oa_legal.search_publications(query="Datenschutz im Bildungsbereich", max_records=10)

    dois = [p.doi for p in out["results"]]
    # Beide Datenschutz-Beiträge werden geliefert (nicht mehr leer bei striktem UND).
    assert "10.21257/sg.900" in dois
    assert "10.21257/sg.901" in dois
    # «Rechtsschutz» darf NICHT über «Schutz» ⊂ «Datenschutz» einsickern (Präfix-Regel).
    assert "10.21257/sg.902" not in dois
    # Der Beitrag, der BEIDE Begriffe trifft (Datenschutz + Bildung/Bildungsbereich), steht oben.
    assert dois[0] == "10.21257/sg.900"


# ─── Pflicht-Testfall 3: Kein DOI → persistente URL vorhanden ────────────────


@respx.mock
async def test_record_without_doi_has_resolvable_url():
    _mock_sources()
    out = await oa_legal.search_publications(query="droit amenagement", max_records=50)
    exante = [p for p in out["results"] if p.source_name == "ex/ante"]
    assert exante, "ex/ante-Beitrag fehlt"
    pub = exante[0]
    assert pub.doi is None
    assert pub.url == "https://ex-ante.ch/index.php/exante/article/view/36"


# ─── Pflicht-Testfall 4: Französischsprachiger Beitrag korrekt markiert ──────


@respx.mock
async def test_french_record_found_and_marked():
    _mock_sources()
    out = await oa_legal.search_publications(query="droit")
    fr = [p for p in out["results"] if p.language == "fr"]
    assert fr, "Französischsprachiger Beitrag nicht gefunden"
    assert fr[0].source_name == "ex/ante"

    # Sprachfilter FR liefert den Beitrag, Filter EN nicht.
    only_fr = await oa_legal.search_publications(query="droit", language="fr")
    assert all(p.language == "fr" for p in only_fr["results"])
    only_en = await oa_legal.search_publications(query="droit", language="en")
    assert not only_en["results"]


# ─── Pflicht-Testfall 5: Kein Volltext in irgendeinem Response-Feld ──────────


@respx.mock
async def test_no_fulltext_leaks_into_response():
    _mock_sources()
    out = await oa_legal.search_publications(query="Datenschutz", max_records=50)

    # Modell hat gar kein Volltext-Feld.
    assert "content" not in oa_legal.OaLegalPublication.model_fields
    assert "fulltext" not in oa_legal.OaLegalPublication.model_fields
    assert "datei_url" not in oa_legal.OaLegalPublication.model_fields

    # Weder der geschützte Volltext noch der PDF-Pfad tauchen serialisiert auf.
    blob = json.dumps([p.model_dump() for p in out["results"]], ensure_ascii=False)
    assert "GEHEIMERVOLLTEXT" not in blob
    assert "GESCHUETZTE VOLLTEXT" not in blob
    assert ".pdf" not in blob


# ─── Pflicht-Testfall 6: Pagination über Resumption-Token-Grenze ─────────────


@respx.mock
async def test_pagination_across_resumption_token():
    def _sui_side_effect(request):
        if "resumptionToken" in request.url.params:
            return httpx.Response(200, text=SUI_OAI_PAGE2)
        return httpx.Response(200, text=SUI_OAI_PAGE1)

    respx.get(host="sui-generis.ch").mock(side_effect=_sui_side_effect)
    _mock_sources(sui=None, exante=EMPTY_OAI, repo=[])

    out = await oa_legal.search_publications(query="Datenschutz", max_records=50)
    dois = {p.doi for p in out["results"]}
    assert "10.21257/sg.100" in dois  # von Seite 1
    assert "10.21257/sg.101" in dois  # von Seite 2 (jenseits der Token-Grenze)


# ─── Pflicht-Testfall 7: Eine Quelle down → Rest liefert, Ausfall ausgewiesen ─


@respx.mock
async def test_partial_source_failure_is_reported_not_silent():
    respx.get(host="sui-generis.ch").mock(return_value=httpx.Response(200, text=SUI_OAI))
    respx.get(host="ex-ante.ch").mock(return_value=httpx.Response(503))  # dauerhaft down
    respx.get(host="api.repositorium.ch").mock(return_value=httpx.Response(200, json=REPO_JSON))

    out = await oa_legal.search_publications(query="Datenschutz", max_records=50)
    assert out["status"]["ex-ante"] == "unreachable"
    assert out["status"]["sui-generis"] == "ok"
    # Übrige Quellen liefern trotzdem Treffer.
    assert any(p.source_name == "sui generis" for p in out["results"])
    assert any(p.source_name == "Repositorium.ch" for p in out["results"])


# ─── Pflicht-Testfall 8: Alle Quellen down → erklärender Fehler ──────────────


@respx.mock
async def test_all_sources_down_raises_explanatory_error():
    respx.get(host="sui-generis.ch").mock(return_value=httpx.Response(503))
    respx.get(host="ex-ante.ch").mock(return_value=httpx.Response(503))
    respx.get(host="api.repositorium.ch").mock(return_value=httpx.Response(503))

    with pytest.raises(RuntimeError, match="nicht erreichbar"):
        await oa_legal.search_publications(query="Datenschutz")


# ─── Crossref-Anreicherung (best-effort) ─────────────────────────────────────


@respx.mock
async def test_crossref_enrichment_upgrades_unknown_license(monkeypatch):
    monkeypatch.setenv("OA_LAW_CROSSREF_ENRICH", "1")
    _mock_sources(sui=EMPTY_OAI, exante=EMPTY_OAI)  # nur Repositorium (license null, DOI vorhanden)
    respx.get(host="api.crossref.org").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"license": [{"URL": "http://creativecommons.org/licenses/by-sa/4.0/"}]}},
        )
    )
    out = await oa_legal.search_publications(query="Datenschutz")
    repo = [p for p in out["results"] if p.source_name == "Repositorium.ch"]
    assert repo and repo[0].license == "CC BY-SA 4.0"


@respx.mock
async def test_crossref_failure_leaves_license_unknown(monkeypatch):
    monkeypatch.setenv("OA_LAW_CROSSREF_ENRICH", "1")
    _mock_sources(sui=EMPTY_OAI, exante=EMPTY_OAI)
    respx.get(host="api.crossref.org").mock(return_value=httpx.Response(500))
    out = await oa_legal.search_publications(query="Datenschutz")
    repo = [p for p in out["results"] if p.source_name == "Repositorium.ch"]
    assert repo and repo[0].license == "unknown"  # Anreicherung blockiert nie


# ─── Einheiten: Normalisierung ───────────────────────────────────────────────


class TestNormalization:
    def test_license_cc_url(self):
        assert oa_legal.normalize_license("https://creativecommons.org/licenses/by-sa/4.0") == "CC BY-SA 4.0"
        assert oa_legal.normalize_license("http://creativecommons.org/licenses/by/4.0/") == "CC BY 4.0"
        assert oa_legal.normalize_license("https://creativecommons.org/publicdomain/zero/1.0/") == "CC0 1.0"

    def test_license_copyright_statement_is_none(self):
        assert oa_legal.normalize_license("Copyright (c) 2016 Niccolo Raselli") is None
        assert oa_legal.normalize_license(None) is None

    def test_language_normalization(self):
        assert oa_legal.normalize_language("deu") == "de"
        assert oa_legal.normalize_language("fra") == "fr"
        assert oa_legal.normalize_language("ita") == "it"
        assert oa_legal.normalize_language(None) == "unknown"

    def test_doi_extraction(self):
        assert oa_legal.extract_doi("info:doi/10.21257/sg.18") == "10.21257/sg.18"
        assert oa_legal.extract_doi("https://doi.org/10.21257/sg.221") == "10.21257/sg.221"
        assert oa_legal.extract_doi("urn:issn:2297-105X") is None

    def test_year_extraction(self):
        assert oa_legal.extract_year("2022-01-15") == 2022
        assert oa_legal.extract_year("sui generis 2022, S. 207-216") == 2022
        assert oa_legal.extract_year(None, None) is None

    def test_strip_invalid_xml_chars(self):
        # 0x17 (ETB) ist in XML 1.0 unzulässig — muss entfernt werden.
        assert oa_legal.strip_invalid_xml_chars("o\x17ft") == "oft"
        assert oa_legal.strip_invalid_xml_chars("normal\ttext\n") == "normal\ttext\n"


# ─── Live-Smoke-Tests (nur mit `pytest -m live`, aus CI ausgeschlossen) ───────


@pytest.mark.live
class TestLiveOaSources:
    async def test_search_datenschutz_live(self):
        out = await oa_legal.search_publications(query="Datenschutz", max_records=10)
        assert out["results"], "Live-Suche lieferte keine Treffer"
        for p in out["results"]:
            assert p.license and p.license.strip()  # nie leer
            assert p.doi or p.url  # auflösbare Referenz
            assert "content" not in p.model_dump()

    async def test_french_records_present_live(self):
        out = await oa_legal.search_publications(query="droit", language="fr", max_records=5)
        assert out["results"], "Keine französischsprachigen Treffer — Romandie verschwunden?"
        assert all(p.language == "fr" for p in out["results"])
