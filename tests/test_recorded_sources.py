"""Die Parser gegen aufgezeichnete Antworten der echten Quellen halten.

WARUM ES DIESE DATEI GIBT. Die uebrigen Testmodule pruefen gegen
handgeschriebene XML-Literale. Die stammen aus derselben Lektuere der Doku wie
der Produktivcode; wo beide irren, irren beide gleich, und die Suite bleibt
gruen. Genau so ist der Fehler in `_oai_list_collections` jahrelang unbemerkt
geblieben: Die erfundene ListSets-Antwort hatte keinen `resumptionToken`, also
konnte kein Test bemerken, dass niemand ihm folgt.

Die Fixtures hier sind aufgezeichnet und datiert — Quelle, Datum, Auswahlregel
und SHA-256 stehen in `fixtures/PROVENANCE.md`.

WAS SIE NICHT KOENNEN: Sie sind ein datierter Ausschnitt, kein Abonnement.
Aendert eine Quelle morgen ihre Antwortform, faellt das hier nicht auf — dafuer
ist die Live-Suite da. Erwartungen werden deshalb aus der Fixture abgeleitet
statt danebengeschrieben.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from fixture_data import payload, raw

from swiss_academic_libraries_mcp import api_client, intl_metadata, oa_legal

NS_OAI = "{http://www.openarchives.org/OAI/2.0/}"

PORTALS = ("erara", "eperiodica", "emanuscripta")


# ---------------------------------------------------------------------------
# swisscovery SRU
# ---------------------------------------------------------------------------


def test_sru_total_is_the_holdings_not_the_page():
    """`numberOfRecords` ist der Bestand, nicht die Seitenlaenge.

    Die beiden zu verwechseln ist der Gruendungsfall dieser ganzen Uebung: Eine
    Antwort, die «2 Treffer» sagt, wo die Quelle 9 899 kennt, ist nicht knapp,
    sondern falsch.
    """
    result = api_client.parse_sru_response(raw("sru_search.xml"))
    assert result["records"], "keine Datensaetze — Fixture oder Parser kaputt"
    assert result["total"] > len(result["records"]) * 100, (
        f"total={result['total']} bei {len(result['records'])} Datensaetzen — "
        "die Fixture belegt den Unterschied nicht mehr, neu aufzeichnen"
    )
    assert result["next_record_position"], "nextRecordPosition fehlt — es gibt weitere Seiten"


def test_sru_records_carry_what_the_formatter_prints():
    """Jeder Datensatz traegt Titel und Kennung — sonst ist die Ausgabe leer."""
    result = api_client.parse_sru_response(raw("sru_search.xml"))
    for rec in result["records"]:
        assert rec.get("title"), f"Datensatz ohne Titel: {rec}"
        assert rec.get("mms_id"), f"Datensatz ohne mms_id: {rec}"
        assert api_client.format_marc_record_md(rec).strip()


# ---------------------------------------------------------------------------
# Die drei Digitalportale
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("portal", PORTALS)
def test_oai_records_parse_and_report_more_pages(portal):
    """Jedes Portal liefert Datensaetze **und** sagt, dass es weitergeht."""
    result = api_client.parse_oai_response(raw(f"oai_{portal}_listrecords.xml"))
    assert result["records"], f"{portal}: keine Datensaetze geparst"
    for rec in result["records"]:
        assert rec.get("title"), f"{portal}: Datensatz ohne Titel"
        assert rec.get("oai_identifier"), f"{portal}: Datensatz ohne Identifier"
    assert result["resumption_token"], (
        f"{portal}: kein resumption_token — die Antwort saehe aus, als waere "
        "der Bestand mit dieser Seite erschoepft"
    )


def test_complete_list_size_is_not_available_everywhere():
    """Nicht jede Quelle sagt, wie gross ihr Bestand ist.

    e-rara und e-manuscripta liefern `completeListSize`, e-periodica nicht.
    Festgehalten, weil die Ausgabe «(von insgesamt N)» damit bei einer der drei
    Quellen fehlt — und das ein Unterschied in der Quelle ist, kein Fehler im
    Server. Faellt dieser Test, hat sich die Quelle geaendert und die Ausgabe
    verdient einen zweiten Blick.
    """
    totals = {
        p: api_client.parse_oai_response(raw(f"oai_{p}_listrecords.xml"))["total_size"] for p in PORTALS
    }
    assert totals["erara"] and totals["emanuscripta"], totals
    assert totals["eperiodica"] is None, (
        f"e-periodica liefert jetzt completeListSize={totals['eperiodica']} — "
        "die Ausgabe kann die Gesamtzahl nun auch dort nennen"
    )


# ---------------------------------------------------------------------------
# ListSets — der Befund
# ---------------------------------------------------------------------------


def test_listsets_is_paginated_and_says_so():
    """Die aufgezeichnete ListSets-Antwort ist eine Seite von mehreren.

    Das ist die Zusicherung, die der Fixture ihren Sinn gibt: Ohne den Token in
    der Datei koennte der Test unten nichts pruefen. Die handgeschriebene
    Vorgaengerin hatte keinen.
    """
    page = api_client.parse_oai_sets_page(raw("oai_erara_listsets.xml"))
    assert page["sets"], "keine Sets geparst"
    assert page["resumption_token"], (
        "ListSets-Fixture ohne resumptionToken — dann belegt sie die "
        "Paginierung nicht mehr und der Test darunter prueft nichts"
    )


async def test_collections_follow_every_page(monkeypatch):
    """`_oai_list_collections` liest alle Seiten, nicht die erste.

    Frueher las es genau eine. Die Antwort sagte trotzdem «10 Sammlungen» —
    gemessen sind es bei e-rara 105 —, und der Namensfilter lief ueber diese
    Reste. Eine Sammlung, die es gibt, kam als «keine Sammlungen gefunden»
    zurueck: kein Fehler, sondern eine falsche Antwort.

    Die erste Seite ist die echte, aufgezeichnete. Die zweite ist aus ihr
    gebaut, damit der Test unabhaengig von der Quelle laeuft — geprueft wird
    das Blaettern, nicht der Inhalt der Quelle.
    """
    from swiss_academic_libraries_mcp import server

    page1 = raw("oai_erara_listsets.xml")
    first = api_client.parse_oai_sets_page(page1)
    token = first["resumption_token"]

    page2 = page1.replace(
        f"<resumptionToken>{token}</resumptionToken>", "<resumptionToken></resumptionToken>"
    ).replace("<setSpec>", "<setSpec>seite2_")

    calls: list[dict] = []

    async def fake_get(url, params=None):
        calls.append(dict(params or {}))
        return page1 if "resumptionToken" not in (params or {}) else page2

    monkeypatch.setattr(server, "http_get", fake_get)
    sets = await server._oai_list_collections("https://www.e-rara.ch/oai")

    assert len(calls) == 2, f"nur {len(calls)} Abfrage(n) — dem Token wurde nicht gefolgt"
    assert calls[1].get("resumptionToken") == token
    assert len(sets) == 2 * len(first["sets"]), (
        f"{len(sets)} Sets statt {2 * len(first['sets'])} — eine Seite fehlt"
    )


async def test_a_collection_on_a_later_page_is_findable(monkeypatch):
    """Der Namensfilter darf nicht an der Seitengrenze aufhoeren.

    Das ist der Ausfall, wie ihn ein Nutzer erlebt: Er sucht eine Sammlung, die
    es gibt, und bekommt «keine Sammlungen gefunden».
    """
    from swiss_academic_libraries_mcp import server

    page1 = raw("oai_erara_listsets.xml")
    token = api_client.parse_oai_sets_page(page1)["resumption_token"]
    page2 = page1.replace(
        f"<resumptionToken>{token}</resumptionToken>", "<resumptionToken></resumptionToken>"
    ).replace("<setName>", "<setName>Nur auf Seite zwei – ", 1)

    async def fake_get(url, params=None):
        return page1 if "resumptionToken" not in (params or {}) else page2

    monkeypatch.setattr(server, "http_get", fake_get)
    hits = await server._oai_list_collections("https://www.e-rara.ch/oai", "Nur auf Seite zwei")
    assert hits, "Sammlung von Seite 2 nicht gefunden — der Filter sieht nur Seite 1"


async def test_collections_do_not_spin_on_a_repeating_token(monkeypatch):
    """Eine Quelle, die denselben Token wiederholt, darf nicht endlos drehen."""
    from swiss_academic_libraries_mcp import server

    page1 = raw("oai_erara_listsets.xml")
    calls = 0

    async def fake_get(url, params=None):
        nonlocal calls
        calls += 1
        if calls > 5:
            raise AssertionError("Endlosschleife: derselbe Token wird immer wieder verfolgt")
        return page1

    monkeypatch.setattr(server, "http_get", fake_get)
    await server._oai_list_collections("https://www.e-rara.ch/oai")
    assert calls == 2, f"{calls} Abfragen — nach dem wiederholten Token muss Schluss sein"


# ---------------------------------------------------------------------------
# Die Rechtszeitschriften
# ---------------------------------------------------------------------------


def test_ex_ante_delivers_xml_that_is_not_well_formed():
    """Die Reinigung ist tragend, nicht vorsorglich.

    ex/ante liefert ein rohes Steuerzeichen mitten in einem `dc:description`.
    Ohne `strip_invalid_xml_chars` wirft der Parser, und das Harvesting bricht
    fuer diese Quelle ab. Aufgezeichnet ist die Antwort deshalb **verbatim**;
    eine bereinigte Fixture koennte genau das nicht belegen.
    """
    text = raw("oai_ex_ante_listrecords.xml")
    control = sorted({hex(ord(c)) for c in text if ord(c) < 0x20 and c not in "\t\n\r"})
    assert control, (
        "keine Steuerzeichen mehr in der Fixture — entweder hat die Quelle "
        "aufgeraeumt oder der Zuschnitt hat den Datensatz verloren"
    )
    with pytest.raises(ET.ParseError):
        ET.fromstring(text)
    ET.fromstring(oa_legal.strip_invalid_xml_chars(text))


@pytest.mark.parametrize("key,source", [("sui_generis", "sui-generis"), ("ex_ante", "ex-ante")])
def test_legal_records_parse_into_publications(key, source):
    """Aus den aufgezeichneten Datensaetzen entstehen Publikationen.

    sui generis fuehrt seine ersten Datensaetze als `status="deleted"`. Die
    Fixture traegt deshalb ausdruecklich auch den ersten nicht geloeschten —
    eine Fixture nur aus Grabsteinen liesse den Parser korrekt nichts liefern
    und pruefte damit nichts.
    """
    cfg = oa_legal.OA_LEGAL_SOURCES[source]
    root = ET.fromstring(oa_legal.strip_invalid_xml_chars(raw(f"oai_{key}_listrecords.xml")))
    records = root.findall(f".//{NS_OAI}record")
    assert records, f"{source}: keine Datensaetze in der Fixture"

    pubs = [p for p in (oa_legal._parse_oai_legal_record(r, cfg) for r in records) if p]
    assert pubs, f"{source}: kein Datensatz wurde zu einer Publikation"
    for pub in pubs:
        assert pub.title and pub.title != "(ohne Titel)"
        assert pub.url, "Publikation ohne aufloesbare Referenz"
        assert pub.source_name == cfg["label"]


def test_deleted_records_are_skipped_not_counted():
    """Grabsteine sind keine Publikationen — und die Fixture enthaelt welche."""
    root = ET.fromstring(raw("oai_sui_generis_listrecords.xml"))
    records = root.findall(f".//{NS_OAI}record")
    deleted = [
        r for r in records if (h := r.find(f"{NS_OAI}header")) is not None and h.get("status") == "deleted"
    ]
    assert deleted, "keine geloeschten Datensaetze in der Fixture — Test ohne Gegenstand"
    cfg = oa_legal.OA_LEGAL_SOURCES["sui-generis"]
    assert all(oa_legal._parse_oai_legal_record(r, cfg) is None for r in deleted)


def test_repositorium_rows_parse():
    """Die Supabase-Zeilen ergeben Publikationen."""
    rows = payload("repositorium_rows.json")
    assert rows, "keine Zeilen aufgezeichnet"
    cfg = oa_legal.OA_LEGAL_SOURCES["repositorium"]
    pubs = [p for p in (oa_legal._parse_repositorium_row(r, cfg) for r in rows) if p]
    assert pubs, "keine Zeile wurde zu einer Publikation"
    for pub in pubs:
        assert pub.url and pub.title


# ---------------------------------------------------------------------------
# Crossref und arXiv
# ---------------------------------------------------------------------------


def test_crossref_total_is_the_corpus_not_the_page():
    """Auch hier: `total-results` ist der Bestand, `items` die Seite."""
    message = payload("crossref_works.json")["message"]
    assert message["items"], "keine Treffer aufgezeichnet"
    assert message["total-results"] > len(message["items"]) * 100, (
        f"total-results={message['total-results']} bei {len(message['items'])} "
        "Treffern — die Fixture belegt den Unterschied nicht mehr"
    )


def test_arxiv_feed_parses_into_entries():
    """Der Atom-Feed ergibt vollstaendige Eintraege."""
    entries = intl_metadata.parse_arxiv_feed(raw("arxiv_feed.xml"), 10)
    assert entries, "kein Eintrag geparst"
    for entry in entries:
        data = entry if isinstance(entry, dict) else entry.__dict__
        for field in ("arxiv_id", "title", "authors", "abs_url"):
            assert data.get(field), f"Eintrag ohne {field}: {data}"
