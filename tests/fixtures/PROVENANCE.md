# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-07**.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus.

**Aufgezeichnet mit den Parametern, die der Produktivcode sendet.** Eine
Fixture, die eine andere Frage beantwortet als die, die der Server stellt,
belegt die falsche Antwort — und zwar unauffaellig, weil sie plausibel
aussieht.

**Es sind Ausschnitte, keine Vollabzuege.** Wo gekuerzt wurde, bleiben die
Zaehlfelder (`numberOfRecords`, `completeListSize`, `total-results`) und die
`resumptionToken` auf dem echten Wert. Sie sagen, wie viel **nicht** in der
Datei steht; sie mitzukuerzen waere genau der Fehler, gegen den diese
Aufzeichnung angeht.

**Die drei Digitalportale sind einzeln aufgezeichnet.** e-rara,
e-periodica und e-manuscripta sprechen alle OAI-PMH, laufen aber nicht auf
derselben Software. Eines stellvertretend fuer alle drei zu nehmen hiesse,
genau die Unterschiede wegzulassen, wegen derer es drei Fixtures braucht.

## `sru_search.xml`

- **Quelle:** `https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK?version=1.2&operation=searchRetrieve&query=alma.all_for_ui%3DPestalozzi&maximumRecords=2&recordSchema=marcxml`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** unveraendert; 2 von 9899 Treffern, wie die Quelle sie bei maximumRecords=2 liefert. `numberOfRecords` ist der echte Gesamtbestand der Suche
- **Groesse:** 6988 B
- **SHA-256:** `2749bc4b4ab9423095c355e97f15c2b546c87a2b81d7912de987641da19004bc`

## `oai_erara_listrecords.xml`

- **Quelle:** `https://www.e-rara.ch/oai?verb=ListRecords&metadataPrefix=oai_dc`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** die ersten 2 von 10 Datensaetzen der ersten Seite; `resumptionToken` und `completeListSize` (163709) unveraendert — sie sagen, wie viel NICHT in der Datei steht
- **Groesse:** 3711 B
- **SHA-256:** `4026d73f75fbea585cfa6cee1ed5d996e26d981f9c86930355878a6bbfc1bde5`

## `oai_eperiodica_listrecords.xml`

- **Quelle:** `https://www.e-periodica.ch/oai/dataprovider?verb=ListRecords&metadataPrefix=oai_dc`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** die ersten 2 von 100 Datensaetzen der ersten Seite; `resumptionToken` und `completeListSize` (None) unveraendert — sie sagen, wie viel NICHT in der Datei steht
- **Groesse:** 3949 B
- **SHA-256:** `204415ae43bae0a77d6a4822b59173a77d5ef802d9da8cf8bb52fc18e8e11f97`

## `oai_emanuscripta_listrecords.xml`

- **Quelle:** `https://www.e-manuscripta.ch/oai?verb=ListRecords&metadataPrefix=oai_dc`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** die ersten 2 von 10 Datensaetzen der ersten Seite; `resumptionToken` und `completeListSize` (218630) unveraendert — sie sagen, wie viel NICHT in der Datei steht
- **Groesse:** 2983 B
- **SHA-256:** `684651fdc767ab052826f9364d4f5067f1c781a3aa844f2fd8d0c006d9b4dcb0`

## `oai_erara_listsets.xml`

- **Quelle:** `https://www.e-rara.ch/oai?verb=ListSets`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** unveraendert, 10 Sets
- **Groesse:** 1246 B
- **SHA-256:** `16b998c2e4e300392840cc89e29e747e02ff9a36413fb19077ae90b8f8f8eddc`

## `oai_sui_generis_listrecords.xml`

- **Quelle:** `https://sui-generis.ch/oai?verb=ListRecords&metadataPrefix=oai_dc`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** 3 von 100 Datensaetzen der ersten Seite — die ersten 2, plus der erste nicht geloeschte, mit `resumptionToken`
- **Groesse:** 3105 B
- **SHA-256:** `efb3b8b112f7b85672e37c019641793777f59898bb77b14d04c0c30fdea77045`

## `oai_ex_ante_listrecords.xml`

- **Quelle:** `https://ex-ante.ch/index.php/exante/oai?verb=ListRecords&metadataPrefix=oai_dc`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** 3 von 100 Datensaetzen der ersten Seite — die ersten 2, plus der erste nicht geloeschte, plus der erste mit rohem Steuerzeichen, mit `resumptionToken`. **Enthaelt rohe Steuerzeichen (0x17)** und ist damit kein wohlgeformtes XML — verbatim aufgezeichnet, weil genau das belegt, wozu `strip_invalid_xml_chars` da ist
- **Groesse:** 9994 B
- **SHA-256:** `97f9e015766a2bc80615205fd33ae857423dd7028664df8d3600358cd8b227d6`

## `repositorium_rows.json`

- **Quelle:** `https://api.repositorium.ch/rest/v1/repo?select=%2A%2Cauthor%28full_name%2Cusername%29&public=eq.true&order=id.asc&limit=1000&offset=0`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** die ersten 2 von 31 Zeilen der ersten Seite (limit=1000). Die Zeilenzahl steht hier, weil sie in der Antwort selbst nicht steht — PostgREST zaehlt ohne `Prefer: count` nicht mit
- **Groesse:** 59319 B
- **SHA-256:** `6d39f8d89f08015e19e92252378d320ada4516f98b13aba0b8b6a64fa0c4a178`

## `crossref_works.json`

- **Quelle:** `https://api.crossref.org/works?query=glacier&rows=2`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** unveraendert; 2 Treffer, `total-results` (19680) ist der echte Gesamtbestand
- **Groesse:** 4317 B
- **SHA-256:** `b107c6414c53334fa91cb2f5b0f3215af44b6da22d03bac90327568a469c5d29`

## `arxiv_feed.xml`

- **Quelle:** `https://export.arxiv.org/api/query?search_query=all%3Aglacier&start=0&max_results=2`
- **Aufgezeichnet:** 2026-08-07
- **Auswahl:** unveraendert, 2 Eintraege; `opensearch:totalResults` unveraendert
- **Groesse:** 5126 B
- **SHA-256:** `ebc94a6e9e337023eff843e34f68787998d2b9be6a9398a02bc345337602c85b`
