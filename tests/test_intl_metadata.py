"""
Tests für die internationale Metadatenebene (intl_metadata + resolve_doi/
search_publications/search_preprints).

Netzzugriff wird mit ``respx`` gemockt; Fixtures sind gekürzte, aber echte
Antworten von Crossref (REST/JSON) und arXiv (Atom/XML).

Pflicht-Testfälle (siehe Aufgaben-Schritt 3):
  1. Happy Path je Tool
  2. Retry bei 503 (nach zweitem Versuch erfolgreich)
  3. Timeout / Netzwerkfehler → sauberer Fehler
  4. arXiv-XML-Parser
  5. Phrasen-Quotierung (build_arxiv_query)
  6. Attribution pro Quelle
"""

from __future__ import annotations

import httpx
import pytest
import respx

from swiss_academic_libraries_mcp import intl_metadata

# ─── Fixtures: gekürzte echte Upstream-Antworten ─────────────────────────────

# Crossref /works/{doi} — Journal-Artikel mit ISSN + CC-Lizenz.
CROSSREF_WORK = {
    "status": "ok",
    "message": {
        "DOI": "10.1038/nature14539",
        "title": ["Deep learning"],
        "author": [
            {"given": "Yann", "family": "LeCun"},
            {"given": "Yoshua", "family": "Bengio"},
            {"given": "Geoffrey", "family": "Hinton"},
        ],
        "issued": {"date-parts": [[2015, 5, 27]]},
        "type": "journal-article",
        "container-title": ["Nature"],
        "publisher": "Springer Science and Business Media LLC",
        "ISSN": ["0028-0836", "1476-4687"],
        "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
        "abstract": "<jats:p>Deep learning allows computational models...</jats:p>",
        "URL": "https://doi.org/10.1038/nature14539",
    },
}

# Crossref Suche — zwei Treffer, einer davon ein Buch mit ISBN.
CROSSREF_SEARCH = {
    "status": "ok",
    "message": {
        "total-results": 2,
        "items": [
            {
                "DOI": "10.5555/aiayn",
                "title": ["Attention Is All You Need"],
                "author": [{"given": "Ashish", "family": "Vaswani"}],
                "issued": {"date-parts": [[2017]]},
                "type": "proceedings-article",
                "container-title": ["NeurIPS"],
                "ISSN": [],
                "ISBN": [],
            },
            {
                "DOI": "10.1000/book",
                "title": ["Ein Buch über Transformer"],
                "author": [{"name": "Anon Collective"}],
                "issued": {"date-parts": [[2020]]},
                "type": "book",
                "ISBN": ["978-3-16-148410-0"],
            },
        ],
    },
}

# arXiv Atom-Feed — ein Eintrag mit Journal-DOI + PDF-Link.
ARXIV_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>462</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <updated>2017-12-06T03:30:00Z</updated>
    <published>2017-06-12T17:57:34Z</published>
    <title>Attention Is All You Need</title>
    <summary>  The dominant sequence transduction models are based on
    recurrent networks.  </summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <arxiv:doi>10.5555/journalref</arxiv:doi>
    <link href="http://arxiv.org/abs/1706.03762v5" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/1706.03762v5" rel="related" type="application/pdf"/>
    <arxiv:primary_category term="cs.CL"/>
    <category term="cs.CL"/>
    <category term="cs.LG"/>
  </entry>
</feed>"""


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Retries sofort (keine echten sleeps), arXiv-Throttle aus, mailto neutral."""

    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr("swiss_academic_libraries_mcp.api_client.asyncio.sleep", _no_sleep)
    monkeypatch.setattr("swiss_academic_libraries_mcp.intl_metadata.asyncio.sleep", _no_sleep)
    monkeypatch.setattr(intl_metadata, "_ARXIV_MIN_INTERVAL", 0.0)
    monkeypatch.setattr(intl_metadata, "_arxiv_last_ts", 0.0)
    monkeypatch.delenv("CROSSREF_MAILTO", raising=False)
    yield


# ─── 1. Happy Path: resolve_doi ──────────────────────────────────────────────


@respx.mock
async def test_resolve_doi_returns_full_metadata():
    respx.get(url__regex=r"https://api\.crossref\.org/works/.+").mock(
        return_value=httpx.Response(200, json=CROSSREF_WORK)
    )
    work = await intl_metadata.resolve_doi("10.1038/nature14539")
    assert work is not None
    assert work.title == "Deep learning"
    assert work.doi == "10.1038/nature14539"
    # Saubere Top-Level-Felder für die swisscovery-Verkettung:
    assert "0028-0836" in work.issn
    assert work.authors[0] == "Yann LeCun"
    assert work.year == 2015
    assert work.license == "CC BY 4.0"  # aus license-URL normalisiert
    assert work.abstract and "<jats" not in work.abstract  # JATS entfernt
    assert work.source == intl_metadata.CROSSREF_ATTRIBUTION


@respx.mock
async def test_resolve_doi_accepts_url_form():
    route = respx.get(url__regex=r"https://api\.crossref\.org/works/.+").mock(
        return_value=httpx.Response(200, json=CROSSREF_WORK)
    )
    work = await intl_metadata.resolve_doi("https://doi.org/10.1038/nature14539")
    assert work is not None
    # Die DOI-URL wurde zur blanken DOI im Pfad reduziert.
    assert "/works/10.1038/nature14539" in str(route.calls.last.request.url)


@respx.mock
async def test_resolve_doi_404_returns_none():
    respx.get(url__regex=r"https://api\.crossref\.org/works/.+").mock(
        return_value=httpx.Response(404, text="Resource not found.")
    )
    assert await intl_metadata.resolve_doi("10.0000/nonexistent") is None


# ─── 2. Happy Path: search_publications ──────────────────────────────────────


@respx.mock
async def test_search_publications_returns_results_with_doi():
    respx.get(host="api.crossref.org", path="/works").mock(
        return_value=httpx.Response(200, json=CROSSREF_SEARCH)
    )
    works = await intl_metadata.search_publications("attention transformer", limit=5)
    assert len(works) == 2
    assert all(w.doi for w in works)  # jeder Treffer trägt eine DOI
    book = [w for w in works if w.type == "book"][0]
    assert "978-3-16-148410-0" in book.isbn
    assert book.authors == ["Anon Collective"]  # 'name'-Fallback


@respx.mock
async def test_search_publications_year_filter_in_request():
    route = respx.get(host="api.crossref.org", path="/works").mock(
        return_value=httpx.Response(200, json=CROSSREF_SEARCH)
    )
    await intl_metadata.search_publications("x", year_from=2018, year_to=2020)
    url = str(route.calls.last.request.url)
    assert "from-pub-date%3A2018-01-01" in url or "from-pub-date:2018-01-01" in url
    assert "until-pub-date%3A2020-12-31" in url or "until-pub-date:2020-12-31" in url


# ─── 3. Happy Path: search_preprints + arXiv-XML-Parser ──────────────────────


@respx.mock
async def test_search_preprints_parses_atom_feed():
    respx.get(host="export.arxiv.org").mock(return_value=httpx.Response(200, text=ARXIV_FEED))
    preprints = await intl_metadata.search_preprints("attention is all you need", limit=5)
    assert len(preprints) == 1
    pre = preprints[0]
    assert pre.arxiv_id == "1706.03762v5"
    assert pre.title == "Attention Is All You Need"
    assert pre.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert pre.primary_category == "cs.CL"
    assert "cs.LG" in pre.categories
    assert pre.year == 2017
    assert pre.doi == "10.5555/journalref"  # → resolve_doi-Brücke
    assert pre.pdf_url == "http://arxiv.org/pdf/1706.03762v5"
    assert pre.source == intl_metadata.ARXIV_ATTRIBUTION


def test_arxiv_parser_unit_no_network():
    """XML-Parser isoliert (kein Netz) — Pflichttest für den Atom-Parser."""
    preprints = intl_metadata.parse_arxiv_feed(ARXIV_FEED, limit=10)
    assert len(preprints) == 1
    assert preprints[0].abs_url == "http://arxiv.org/abs/1706.03762v5"


# ─── 5. Phrasen-Quotierung ───────────────────────────────────────────────────


def test_build_arxiv_query_quotes_plain_phrase():
    # Kernfall: Leerzeichen würde arXiv als OR interpretieren → quotieren.
    assert intl_metadata.build_arxiv_query("model context protocol") == 'all:"model context protocol"'


def test_build_arxiv_query_respects_existing_field_syntax():
    assert intl_metadata.build_arxiv_query("ti:transformer") == "ti:transformer"


def test_build_arxiv_query_respects_existing_quotes():
    assert intl_metadata.build_arxiv_query('"already quoted"') == '"already quoted"'


def test_build_arxiv_query_adds_category():
    q = intl_metadata.build_arxiv_query("graph neural networks", category="cs.LG")
    assert q == '(all:"graph neural networks") AND cat:cs.LG'


# ─── 2 (bis). Retry bei 503 → nach zweitem Versuch erfolgreich ───────────────


@respx.mock
async def test_resolve_doi_retries_on_503_then_succeeds():
    respx.get(url__regex=r"https://api\.crossref\.org/works/.+").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=CROSSREF_WORK),
        ]
    )
    work = await intl_metadata.resolve_doi("10.1038/nature14539")
    assert work is not None and work.title == "Deep learning"


@respx.mock
async def test_search_preprints_retries_on_503_then_succeeds():
    respx.get(host="export.arxiv.org").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, text=ARXIV_FEED)]
    )
    preprints = await intl_metadata.search_preprints("attention", limit=1)
    assert len(preprints) == 1


# ─── 3 (bis). Timeout / Netzwerkfehler → sauberer Fehler ─────────────────────


@respx.mock
async def test_search_publications_timeout_raises_clean():
    respx.get(host="api.crossref.org", path="/works").mock(side_effect=httpx.ConnectTimeout("timed out"))
    with pytest.raises(httpx.RequestError):
        await intl_metadata.search_publications("x")


# ─── 6. Attribution pro Quelle (nicht gesammelt) ─────────────────────────────


def test_attributions_are_distinct_per_source():
    assert "Crossref" in intl_metadata.CROSSREF_ATTRIBUTION
    assert "arXiv" in intl_metadata.ARXIV_ATTRIBUTION
    assert intl_metadata.CROSSREF_ATTRIBUTION != intl_metadata.ARXIV_ATTRIBUTION


# ─── Polite pool: mailto steuert Header + Query ──────────────────────────────


@respx.mock
async def test_crossref_mailto_added_when_configured(monkeypatch):
    monkeypatch.setenv("CROSSREF_MAILTO", "team@example.org")
    route = respx.get(url__regex=r"https://api\.crossref\.org/works/.+").mock(
        return_value=httpx.Response(200, json=CROSSREF_WORK)
    )
    await intl_metadata.resolve_doi("10.1038/nature14539")
    req = route.calls.last.request
    assert "mailto:team@example.org" in req.headers["user-agent"]
    assert "mailto=team%40example.org" in str(req.url) or "mailto=team@example.org" in str(req.url)


# ─── Egress-Allow-List ───────────────────────────────────────────────────────


def test_egress_allow_list_blocks_foreign_host():
    with pytest.raises(ValueError, match="Egress-Host nicht erlaubt"):
        intl_metadata._assert_host_allowed("https://evil.example.com/works/10.1/x")


def test_egress_allow_list_permits_registry_hosts():
    intl_metadata._assert_host_allowed(intl_metadata.CROSSREF_WORKS_URL)
    intl_metadata._assert_host_allowed(intl_metadata.ARXIV_API_URL)


# ─── Live-Smoke-Tests (nur mit -m live) ──────────────────────────────────────


@pytest.mark.live
class TestLiveIntlSources:
    async def test_resolve_doi_live(self):
        work = await intl_metadata.resolve_doi("10.1145/3292500.3330701")
        assert work is not None and work.doi.startswith("10.1145")

    async def test_search_preprints_live_phrase(self):
        preprints = await intl_metadata.search_preprints("model context protocol", limit=3)
        assert isinstance(preprints, list)
