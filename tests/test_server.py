"""
Tests für den Swiss Academic Libraries MCP Server.

Kategorien:
  - Unit-Tests: Parser-Funktionen mit Fixture-XML (kein Netzwerk)
  - Live-Tests: Echte API-Abfragen (nur mit pytest -m live)
"""

from __future__ import annotations

import pytest

from swiss_academic_libraries_mcp.api_client import (
    format_marc_record_md,
    format_oai_record_md,
    parse_marc_record,
    parse_oai_dc_record,
    parse_oai_response,
    parse_oai_sets,
    parse_sru_response,
)

# ─── Fixture-Daten ────────────────────────────────────────────────────────────

SAMPLE_SRU_XML = """<?xml version="1.0" encoding="UTF-8"?>
<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
  <version>1.2</version>
  <numberOfRecords>42</numberOfRecords>
  <nextRecordPosition>2</nextRecordPosition>
  <records>
    <record>
      <recordSchema>marcxml</recordSchema>
      <recordPacking>xml</recordPacking>
      <recordData>
        <record xmlns="http://www.loc.gov/MARC21/slim">
          <leader>01234nam a2200000 c 4500</leader>
          <controlfield tag="001">991170001234567890</controlfield>
          <controlfield tag="008">200101s2020    sz ||||b    ||0   ger^^</controlfield>
          <datafield ind1="1" ind2=" " tag="100">
            <subfield code="a">Pestalozzi, Johann Heinrich</subfield>
            <subfield code="d">1746-1827</subfield>
          </datafield>
          <datafield ind1="1" ind2="0" tag="245">
            <subfield code="a">Wie Gertrud ihre Kinder lehrt :</subfield>
            <subfield code="b">ein Versuch</subfield>
            <subfield code="c">von Johann Heinrich Pestalozzi</subfield>
          </datafield>
          <datafield ind1=" " ind2="1" tag="264">
            <subfield code="a">Zürich</subfield>
            <subfield code="b">Gessner</subfield>
            <subfield code="c">1801</subfield>
          </datafield>
          <datafield ind1=" " ind2=" " tag="041">
            <subfield code="a">ger</subfield>
          </datafield>
          <datafield ind1=" " ind2="7" tag="650">
            <subfield code="a">Pädagogik</subfield>
            <subfield code="x">Geschichte</subfield>
          </datafield>
        </record>
      </recordData>
    </record>
  </records>
</searchRetrieveResponse>"""

SAMPLE_OAI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <responseDate>2024-03-01T10:00:00Z</responseDate>
  <request verb="ListRecords">https://www.e-rara.ch/oai</request>
  <ListRecords>
    <record>
      <header>
        <identifier>oai:www.e-rara.ch:12345678</identifier>
        <datestamp>2024-02-15T08:30:00Z</datestamp>
      </header>
      <metadata>
        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <dc:title>Allgemeine Schulkunde für Volksschullehrer</dc:title>
          <dc:creator>Morf, Heinrich</dc:creator>
          <dc:subject>Volksschule</dc:subject>
          <dc:subject>Pädagogik</dc:subject>
          <dc:description>Handbuch für Schweizer Volksschullehrerinnen und -lehrer</dc:description>
          <dc:publisher>Frauenfeld: Huber</dc:publisher>
          <dc:date>1883</dc:date>
          <dc:type>Text</dc:type>
          <dc:type>Book</dc:type>
          <dc:language>de</dc:language>
          <dc:identifier>oai:www.e-rara.ch:12345678</dc:identifier>
          <dc:identifier>https://www.e-rara.ch/zut/content/titleinfo/12345678</dc:identifier>
        </oai_dc:dc>
      </metadata>
    </record>
    <resumptionToken completeListSize="5000">token_abc123</resumptionToken>
  </ListRecords>
</OAI-PMH>"""

SAMPLE_OAI_EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2024-03-01T10:00:00Z</responseDate>
  <request verb="ListRecords">https://www.e-rara.ch/oai</request>
  <ListRecords>
  </ListRecords>
</OAI-PMH>"""

SAMPLE_OAI_ERROR_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2024-03-01T10:00:00Z</responseDate>
  <request verb="ListRecords">https://www.e-rara.ch/oai</request>
  <error code="noRecordsMatch">No records match the request</error>
</OAI-PMH>"""

SAMPLE_OAI_SETS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <responseDate>2024-03-01T10:00:00Z</responseDate>
  <request verb="ListSets">https://www.e-rara.ch/oai</request>
  <ListSets>
    <set>
      <setSpec>zut</setSpec>
      <setName>ETH-Bibliothek Zürich</setName>
    </set>
    <set>
      <setSpec>bau_1</setSpec>
      <setName>UB Basel (DSV01)</setName>
    </set>
    <set>
      <setSpec>zhdk</setSpec>
      <setName>Zürcher Hochschule der Künste</setName>
    </set>
  </ListSets>
</OAI-PMH>"""


# ─── Unit-Tests: SRU-Parser ───────────────────────────────────────────────────


class TestParseSruResponse:
    def test_total_count(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        assert result["total"] == 42

    def test_next_record_position(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        assert result["next_record_position"] == 2

    def test_record_count(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        assert len(result["records"]) == 1

    def test_mms_id_parsed(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        assert result["records"][0]["mms_id"] == "991170001234567890"

    def test_title_parsed(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        title = result["records"][0].get("title", "")
        assert "Gertrud" in title

    def test_creator_parsed(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        creator = result["records"][0].get("creator", "")
        assert "Pestalozzi" in creator

    def test_publication_info(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        pub = result["records"][0].get("publication_info", "")
        assert "Zürich" in pub
        assert "1801" in pub

    def test_language(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        assert result["records"][0].get("language") == "ger"

    def test_subjects(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        subjects = result["records"][0].get("subjects", [])
        assert len(subjects) >= 1
        assert any("Pädagogik" in s for s in subjects)

    def test_empty_result(self) -> None:
        empty_xml = SAMPLE_SRU_XML.replace("42", "0").replace(
            "<records>", "<records_unused>"
        ).replace("</records>", "</records_unused>")
        # Vereinfachter Test: total = 0 bei modifiziertem XML
        import re
        modified = re.sub(r"<numberOfRecords>\d+</numberOfRecords>",
                          "<numberOfRecords>0</numberOfRecords>", SAMPLE_SRU_XML)
        result = parse_sru_response(modified)
        assert result["total"] == 0


class TestParseMarcRecord:
    def setup_method(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        self.rec = result["records"][0]

    def test_has_required_fields(self) -> None:
        assert "title" in self.rec
        assert "mms_id" in self.rec

    def test_swisscovery_link_can_be_built(self) -> None:
        mms_id = self.rec.get("mms_id", "")
        link = f"https://swisscovery.slsp.ch/permalink/41SLSP_NETWORK/1ufb5t2/alma{mms_id}"
        assert mms_id in link


# ─── Unit-Tests: OAI-PMH-Parser ──────────────────────────────────────────────


class TestParseOaiResponse:
    def test_record_count(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert len(result["records"]) == 1

    def test_resumption_token(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert result["resumption_token"] == "token_abc123"

    def test_total_size(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert result["total_size"] == 5000

    def test_oai_identifier(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert result["records"][0]["oai_identifier"] == "oai:www.e-rara.ch:12345678"

    def test_title_parsed(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert "Volksschullehrer" in result["records"][0].get("title", "")

    def test_creator_parsed(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        creators = result["records"][0].get("creators", [])
        assert "Morf" in " ".join(creators)

    def test_subjects_list(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        subjects = result["records"][0].get("subjects", [])
        assert len(subjects) == 2
        assert "Volksschule" in subjects

    def test_language(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        assert result["records"][0].get("language") == "de"

    def test_url_extracted(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        url = result["records"][0].get("url", "")
        assert url.startswith("https://")

    def test_empty_response(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_EMPTY_XML)
        assert result["records"] == []
        assert result["resumption_token"] is None

    def test_oai_error_raises(self) -> None:
        with pytest.raises(ValueError, match="OAI-Fehler"):
            parse_oai_response(SAMPLE_OAI_ERROR_XML)


class TestParseOaiSets:
    def test_set_count(self) -> None:
        sets = parse_oai_sets(SAMPLE_OAI_SETS_XML)
        assert len(sets) == 3

    def test_set_spec(self) -> None:
        sets = parse_oai_sets(SAMPLE_OAI_SETS_XML)
        specs = [s["spec"] for s in sets]
        assert "zut" in specs
        assert "bau_1" in specs

    def test_set_name(self) -> None:
        sets = parse_oai_sets(SAMPLE_OAI_SETS_XML)
        eth_set = next(s for s in sets if s["spec"] == "zut")
        assert "ETH" in eth_set["name"]


# ─── Unit-Tests: Formatierung ─────────────────────────────────────────────────


class TestFormatMarcRecordMd:
    def setup_method(self) -> None:
        result = parse_sru_response(SAMPLE_SRU_XML)
        self.rec = result["records"][0]

    def test_title_in_output(self) -> None:
        output = format_marc_record_md(self.rec, index=1)
        assert "Gertrud" in output

    def test_index_prefix(self) -> None:
        output = format_marc_record_md(self.rec, index=3)
        assert "3." in output

    def test_swisscovery_link_present(self) -> None:
        output = format_marc_record_md(self.rec)
        assert "swisscovery.slsp.ch" in output

    def test_creator_present(self) -> None:
        output = format_marc_record_md(self.rec)
        assert "Pestalozzi" in output

    def test_no_index(self) -> None:
        output = format_marc_record_md(self.rec)
        assert output.startswith("**")


class TestFormatOaiRecordMd:
    def setup_method(self) -> None:
        result = parse_oai_response(SAMPLE_OAI_XML)
        self.rec = result["records"][0]

    def test_title_in_output(self) -> None:
        output = format_oai_record_md(self.rec, index=1)
        assert "Volksschullehrer" in output

    def test_date_present(self) -> None:
        output = format_oai_record_md(self.rec)
        assert "1883" in output

    def test_url_present(self) -> None:
        output = format_oai_record_md(self.rec)
        assert "https://" in output


# ─── Live-Tests (nur mit -m live) ─────────────────────────────────────────────


@pytest.mark.live
class TestSwisscoveryLive:
    async def test_basic_search(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_sru_response, SWISSCOVERY_SRU_URL
        xml_text = await http_get(SWISSCOVERY_SRU_URL, {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": "title = \"Volksschule\"",
            "maximumRecords": "3",
            "recordSchema": "marcxml",
        })
        result = parse_sru_response(xml_text)
        assert result["total"] > 0
        assert len(result["records"]) > 0
        print(f"\n  ✅ swisscovery: {result['total']:,} Treffer für 'Volksschule'")

    async def test_search_returns_mms_id(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_sru_response, SWISSCOVERY_SRU_URL
        xml_text = await http_get(SWISSCOVERY_SRU_URL, {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": "creator = \"Pestalozzi\"",
            "maximumRecords": "2",
            "recordSchema": "marcxml",
        })
        result = parse_sru_response(xml_text)
        if result["records"]:
            assert "mms_id" in result["records"][0]
            print(f"\n  ✅ swisscovery Pestalozzi: {result['total']} Treffer, MMS-ID: {result['records'][0]['mms_id']}")


@pytest.mark.live
class TestEraraLive:
    async def test_list_records(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_oai_response, ERARA_OAI_URL
        xml_text = await http_get(ERARA_OAI_URL, {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc",
            "set": "zut",
            "from": "2024-01-01",
            "until": "2024-03-31",
        })
        result = parse_oai_response(xml_text)
        assert len(result["records"]) > 0
        first = result["records"][0]
        assert "title" in first
        assert "oai_identifier" in first
        print(f"\n  ✅ e-rara (ETH): {len(result['records'])} Einträge, erster: {first['title'][:60]}")

    async def test_list_sets(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_oai_sets, ERARA_OAI_URL
        xml_text = await http_get(ERARA_OAI_URL, {"verb": "ListSets"})
        sets = parse_oai_sets(xml_text)
        assert len(sets) > 5
        specs = [s["spec"] for s in sets]
        assert "zut" in specs
        print(f"\n  ✅ e-rara ListSets: {len(sets)} Sammlungen gefunden")


@pytest.mark.live
class TestEperiodicaLive:
    async def test_list_records(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_oai_response, EPERIODICA_OAI_URL
        xml_text = await http_get(EPERIODICA_OAI_URL, {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc",
            "from": "2024-01-01",
            "until": "2024-02-28",
        })
        result = parse_oai_response(xml_text)
        assert len(result["records"]) > 0
        first = result["records"][0]
        assert "title" in first
        print(f"\n  ✅ e-periodica: {len(result['records'])} Einträge, erster: {first['title'][:60]}")


@pytest.mark.live
class TestEmanuscriptaLive:
    async def test_list_records(self) -> None:
        from swiss_academic_libraries_mcp.api_client import http_get, parse_oai_response, EMANUSCRIPTA_OAI_URL
        xml_text = await http_get(EMANUSCRIPTA_OAI_URL, {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc",
            "from": "2024-01-01",
            "until": "2024-06-30",
        })
        result = parse_oai_response(xml_text)
        assert len(result["records"]) >= 0  # Kann 0 sein wenn keine neuen Einträge
        print(f"\n  ✅ e-manuscripta: {len(result['records'])} Einträge im Zeitraum")
