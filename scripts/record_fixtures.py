#!/usr/bin/env python3
"""Zeichnet die Unit-Test-Fixtures von den echten Quellen dieses Servers auf.

    python scripts/record_fixtures.py

WARUM ES DIESES SKRIPT GIBT. Ein handgeschriebener Mock kodiert die Annahme
seines Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode
und Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere der
Doku. Wo beide irren, irren beide gleich, und die Suite bleibt gruen.

Ohne Aufzeichnungsdatum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht»
nicht mehr zu unterscheiden — die Datei sieht gleich aus.

**Aufgezeichnet wird mit den Parametern, die der Produktivcode sendet.** Eine
Fixture, die eine andere Frage beantwortet als die, die der Server stellt, belegt
die falsche Antwort — und zwar unauffaellig, weil sie plausibel aussieht.

**Es sind Ausschnitte, keine Vollabzuege.** Die Auswahlregel je Datei steht in
`tests/fixtures/PROVENANCE.md`. Wo gekuerzt wird, bleiben die Zaehlfelder
(`numberOfRecords`, `completeListSize`, `total-results`) auf dem echten Wert:
Eine Fixture, die stillschweigend behauptet, der Bestand sei kleiner, waere
genau der Fehler, gegen den das hier angeht.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from swiss_academic_libraries_mcp import api_client, oa_legal  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

NS_OAI = "http://www.openarchives.org/OAI/2.0/"
NS_SRW = "http://www.loc.gov/zing/srw/"
NS_ATOM = "http://www.w3.org/2005/Atom"

# Ein Suchbegriff, der in swisscovery sicher Treffer hat und thematisch zum
# Server passt. Fest verdrahtet, damit jede Aufzeichnung dieselbe Frage stellt.
SRU_QUERY = "Pestalozzi"
SRU_MAX = 2
OAI_KEEP = 2
CROSSREF_QUERY = "glacier"
ARXIV_QUERY = "all:glacier"
REPOSITORIUM_KEEP = 2


def _has_control_char(text: str) -> bool:
    return any(ord(c) < 0x20 and c not in "\t\n\r" for c in text)


def _is_live_record(text: str) -> bool:
    """Kein Grabstein — OAI meldet geloeschte Datensaetze als `status="deleted"`."""
    return 'status="deleted"' not in text


def _trim_xml(xml_text: str, keep: int, extras: tuple = ()) -> tuple[str, int, int]:
    """Behaelt die ersten `keep` `<record>`-Elemente, laesst alles andere stehen.

    Textbasiert und nicht ueber ElementTree, weil ein Neu-Serialisieren die
    Namensraum-Praefixe umschreibt — und genau die Schreibweise ist hier Teil
    dessen, was belegt werden soll.

    `extras` sind Praedikate; vom ersten Datensatz, auf den eines zutrifft,
    kommt zusaetzlich einer mit. Der Grund ist zweimal derselbe: Ein Zuschnitt,
    der die auffaellige Zeile wegschneidet, macht aus einer belegten Eigenschaft
    eine behauptete. Bei sui generis stehen die ersten beiden Datensaetze auf
    `status="deleted"` — eine Fixture nur aus Grabsteinen liesse den Parser
    korrekt null Publikationen liefern und pruefte damit nichts.

    Liefert (Text, Gesamtzahl, Zahl der behaltenen).
    """
    matches = list(re.finditer(r"<record>.*?</record>", xml_text, re.S))
    if not matches:
        matches = list(re.finditer(r"<record\b.*?</record>", xml_text, re.S))
    if not matches:
        return xml_text, 0, 0

    wanted = set(range(min(keep, len(matches))))
    for predicate in extras:
        for i, m in enumerate(matches):
            if predicate(m.group(0)):
                wanted.add(i)
                break

    if len(wanted) >= len(matches):
        return xml_text, len(matches), len(matches)

    out = xml_text[: matches[0].start()]
    out += "".join(matches[i].group(0) + "\n" for i in sorted(wanted))
    out += xml_text[matches[-1].end() :]
    return out, len(matches), len(wanted)


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []
    skipped: list[dict] = []

    def write(name: str, text: str, url: str, rule: str) -> None:
        if not text.endswith("\n"):
            text += "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<32} {len(text.encode('utf-8')):>8} B")

    def get(
        client: httpx.Client,
        url: str,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r

    with httpx.Client(
        timeout=120.0,
        follow_redirects=True,
        headers={"User-Agent": api_client.USER_AGENT},
    ) as client:
        # 1) swisscovery SRU — dieselben Parameter wie `server.py`.
        sru_params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": f"alma.all_for_ui={SRU_QUERY}",
            "maximumRecords": str(SRU_MAX),
            "recordSchema": "marcxml",
        }
        r = get(client, api_client.SWISSCOVERY_SRU_URL, sru_params)
        root = ET.fromstring(r.text)
        total_el = root.find(f"{{{NS_SRW}}}numberOfRecords")
        total = int(total_el.text) if total_el is not None and total_el.text else 0
        n_records = len(root.findall(f".//{{{NS_SRW}}}record"))
        if not total or not n_records:
            raise SystemExit(f"SRU «{SRU_QUERY}»: {total} Treffer, {n_records} Datensaetze — leer")
        if n_records > SRU_MAX:
            raise SystemExit(
                f"SRU: {n_records} Datensaetze trotz maximumRecords={SRU_MAX} — "
                "der Parameter wirkt nicht mehr"
            )
        write(
            "sru_search.xml",
            r.text,
            str(r.request.url),
            f"unveraendert; {n_records} von {total} Treffern, wie die Quelle sie "
            f"bei maximumRecords={SRU_MAX} liefert. `numberOfRecords` ist der "
            "echte Gesamtbestand der Suche",
        )

        # 2) Die drei Digitalportale. Alle drei sprechen OAI-PMH, aber nicht
        #    dieselbe Software — deshalb wird jedes einzeln aufgezeichnet und
        #    nicht eines stellvertretend fuer alle.
        portals = {
            "erara": api_client.ERARA_OAI_URL,
            "eperiodica": api_client.EPERIODICA_OAI_URL,
            "emanuscripta": api_client.EMANUSCRIPTA_OAI_URL,
        }
        for key, base_url in portals.items():
            r = get(client, base_url, {"verb": "ListRecords", "metadataPrefix": "oai_dc"})
            root = ET.fromstring(r.text)
            rt = root.find(f".//{{{NS_OAI}}}resumptionToken")
            complete = rt.get("completeListSize") if rt is not None else None
            has_token = bool(rt is not None and rt.text and rt.text.strip())
            trimmed, seen, kept = _trim_xml(r.text, OAI_KEEP)
            if not seen:
                raise SystemExit(f"{key}: ListRecords ohne Datensaetze")
            if not has_token:
                # Ohne Token endet das Harvesting nach der ersten Seite. Waere
                # das der echte Zustand, muesste der Server das wissen — und
                # nicht dieses Skript es wegbuegeln.
                raise SystemExit(
                    f"{key}: erste Seite ohne resumptionToken bei "
                    f"completeListSize={complete} — Paginierung pruefen"
                )
            write(
                f"oai_{key}_listrecords.xml",
                trimmed,
                str(r.request.url),
                f"die ersten {kept} von {seen} Datensaetzen der ersten Seite; "
                f"`resumptionToken` und `completeListSize` ({complete}) "
                "unveraendert — sie sagen, wie viel NICHT in der Datei steht",
            )

        # 3) ListSets von e-rara, fuer den Kollektionen-Parser.
        r = get(client, api_client.ERARA_OAI_URL, {"verb": "ListSets"})
        sets_root = ET.fromstring(r.text)
        n_sets = len(sets_root.findall(f".//{{{NS_OAI}}}set"))
        if not n_sets:
            raise SystemExit("e-rara ListSets: keine Sets")
        write(
            "oai_erara_listsets.xml",
            r.text,
            str(r.request.url),
            f"unveraendert, {n_sets} Sets",
        )

        # 4) Die beiden OA-Rechtszeitschriften — Quellen von `oa_legal`.
        #
        #    ex/ante liefert XML, das nicht wohlgeformt ist: ein rohes
        #    Steuerzeichen mitten in einem `dc:description`. Der Produktivcode
        #    faengt das mit `strip_invalid_xml_chars` ab — deshalb wird zum
        #    PRUEFEN gereinigt, aber **verbatim geschrieben**. Eine bereinigte
        #    Fixture koennte nicht mehr belegen, dass die Reinigung noetig ist.
        for key in ("sui-generis", "ex-ante"):
            cfg = oa_legal.OA_LEGAL_SOURCES[key]
            r = get(client, cfg["base_url"], {"verb": "ListRecords", "metadataPrefix": "oai_dc"})
            cleaned = oa_legal.strip_invalid_xml_chars(r.text)
            control_chars = sorted({hex(ord(c)) for c in r.text if ord(c) < 0x20 and c not in "\t\n\r"})
            root = ET.fromstring(cleaned)
            n = len(root.findall(f".//{{{NS_OAI}}}record"))
            if not n:
                raise SystemExit(f"{key}: ListRecords ohne Datensaetze")
            extras = [_is_live_record]
            if control_chars:
                extras.append(_has_control_char)
            trimmed, seen, kept = _trim_xml(r.text, OAI_KEEP, tuple(extras))
            if not any(_is_live_record(m) for m in re.findall(r"<record>.*?</record>", trimmed, re.S)):
                raise SystemExit(
                    f"{key}: nur geloeschte Datensaetze behalten — der Parser "
                    "liefert daraus korrekt nichts, und die Fixture prueft nichts"
                )
            if control_chars and not _has_control_char(trimmed):
                # Das Steuerzeichen sass in einem Datensatz, den der Zuschnitt
                # weggeschnitten hat. Dann belegt die Fixture die Eigenschaft
                # nicht mehr, und ein Test darauf pruefte nichts.
                raise SystemExit(
                    f"{key}: Steuerzeichen {control_chars} in keinem behaltenen "
                    "Datensatz — Zuschnitt anpassen, sonst belegt die Fixture die "
                    "Unwohlgeformtheit nicht mehr"
                )
            rt = root.find(f".//{{{NS_OAI}}}resumptionToken")
            token_note = (
                "mit `resumptionToken`"
                if rt is not None and rt.text and rt.text.strip()
                else "ohne `resumptionToken` — eine Seite ist der ganze Bestand"
            )
            charnote = (
                f". **Enthaelt rohe Steuerzeichen ({', '.join(control_chars)})** und ist "
                "damit kein wohlgeformtes XML — verbatim aufgezeichnet, weil genau das "
                "belegt, wozu `strip_invalid_xml_chars` da ist"
                if control_chars
                else ""
            )
            write(
                f"oai_{key.replace('-', '_')}_listrecords.xml",
                trimmed,
                str(r.request.url),
                f"{kept} von {seen} Datensaetzen der ersten Seite — die ersten {OAI_KEEP}"
                + ", plus der erste nicht geloeschte"
                + (", plus der erste mit rohem Steuerzeichen" if control_chars else "")
                + f", {token_note}{charnote}",
            )

        # 5) Repositorium.ch — Supabase-REST, oeffentlicher Anon-Key.
        cfg = oa_legal.OA_LEGAL_SOURCES["repositorium"]
        rep_params = {
            "select": "*,author(full_name,username)",
            "public": "eq.true",
            "order": "id.asc",
            "limit": "1000",
            "offset": "0",
        }
        try:
            r = get(
                client,
                f"{cfg['base_url']}/{cfg['table']}",
                rep_params,
                headers={"apikey": cfg["anon_key"], "Authorization": f"Bearer {cfg['anon_key']}"},
            )
            rows = r.json()
            if not isinstance(rows, list) or not rows:
                raise SystemExit("Repositorium: leere oder unerwartete Antwort")
            kept = rows[:REPOSITORIUM_KEEP]
            write(
                "repositorium_rows.json",
                json.dumps(kept, ensure_ascii=False, indent=2),
                str(r.request.url),
                f"die ersten {REPOSITORIUM_KEEP} von {len(rows)} Zeilen der ersten "
                f"Seite (limit=1000). Die Zeilenzahl steht hier, weil sie in der "
                "Antwort selbst nicht steht — PostgREST zaehlt ohne "
                "`Prefer: count` nicht mit",
            )
        except httpx.HTTPStatusError as exc:
            skipped.append(
                {
                    "name": "repositorium_rows.json",
                    "url": f"{cfg['base_url']}/{cfg['table']}",
                    "why": f"HTTP {exc.response.status_code} mit dem oeffentlichen "
                    "Anon-Key. NICHT aufgezeichnet — der Schluessel ist ggf. rotiert.",
                }
            )
            print(f"--  repositorium_rows.json       uebersprungen (HTTP {exc.response.status_code})")

        # 6) Crossref.
        r = get(
            client,
            "https://api.crossref.org/works",
            {"query": CROSSREF_QUERY, "rows": "2"},
        )
        payload = r.json()
        msg = payload.get("message") or {}
        n_items = len(msg.get("items") or [])
        if not n_items:
            raise SystemExit("Crossref: keine Treffer")
        write(
            "crossref_works.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
            str(r.request.url),
            f"unveraendert; {n_items} Treffer, `total-results` "
            f"({msg.get('total-results')}) ist der echte Gesamtbestand",
        )

        # 7) arXiv — Atom, nicht JSON.
        r = get(
            client,
            "https://export.arxiv.org/api/query",
            {"search_query": ARXIV_QUERY, "start": "0", "max_results": "2"},
        )
        feed = ET.fromstring(r.text)
        n_entries = len(feed.findall(f"{{{NS_ATOM}}}entry"))
        if not n_entries:
            raise SystemExit("arXiv: kein <entry> — Antwortform geaendert?")
        write(
            "arxiv_feed.xml",
            r.text,
            str(r.request.url),
            f"unveraendert, {n_entries} Eintraege; `opensearch:totalResults` unveraendert",
        )

    _write_provenance(recorded_at, entries, skipped)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict], skipped: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}**.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus.",
        "",
        "**Aufgezeichnet mit den Parametern, die der Produktivcode sendet.** Eine",
        "Fixture, die eine andere Frage beantwortet als die, die der Server stellt,",
        "belegt die falsche Antwort — und zwar unauffaellig, weil sie plausibel",
        "aussieht.",
        "",
        "**Es sind Ausschnitte, keine Vollabzuege.** Wo gekuerzt wurde, bleiben die",
        "Zaehlfelder (`numberOfRecords`, `completeListSize`, `total-results`) und die",
        "`resumptionToken` auf dem echten Wert. Sie sagen, wie viel **nicht** in der",
        "Datei steht; sie mitzukuerzen waere genau der Fehler, gegen den diese",
        "Aufzeichnung angeht.",
        "",
        "**Die drei Digitalportale sind einzeln aufgezeichnet.** e-rara,",
        "e-periodica und e-manuscripta sprechen alle OAI-PMH, laufen aber nicht auf",
        "derselben Software. Eines stellvertretend fuer alle drei zu nehmen hiesse,",
        "genau die Unterschiede wegzulassen, wegen derer es drei Fixtures braucht.",
        "",
    ]
    if skipped:
        lines += ["## NICHT aufgezeichnet", ""]
        for s in skipped:
            lines += [
                f"### `{s['name']}`",
                "",
                f"- **Quelle:** `{s['url']}`",
                f"- **Grund:** {s['why']}",
                "",
            ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
