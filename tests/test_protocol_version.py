"""ARCH-012: die beiden Spec-Revisionen, gegen die dieser Server geprueft ist.

Das SDK bietet keinen setzbaren Pin — die Aushandlung liegt in der
Session-Schicht, weder `MCPServer.__init__` noch `Settings` nimmt den Parameter
entgegen. Ein Pin ist hier deshalb eine erklaerte Konstante plus eine
Zusicherung, die bricht, sobald ein SDK-Bump sie verschiebt. Bewusst CI-seitig
und nicht zur Laufzeit: brechen soll unser Build, nicht der Betrieb von
jemandem, der `mcp` weiter oben aktualisiert hat.

`mcp` 2.x bedient ZWEI Protokoll-Aeren ueber denselben Server; die erste
Anfrage einer Verbindung entscheidet, welche gilt:

* die **Legacy-Aera** mit `initialize`-Handshake — was heutige Clients
  sprechen. Sie deckelt bei `LATEST_HANDSHAKE_VERSION`.
* die **Modern-Aera** mit Pro-Request-Envelope, die `LATEST_MODERN_VERSION`
  erreicht.

**`LATEST_PROTOCOL_VERSION` ist ein Alias auf die MODERNE Version.** Wer nur
dagegen pinnt — die naheliegende Einzelzeile — sichert die Aera, in der heute
praktisch niemand spricht, und laesst die andere frei wandern. Beide stehen
deshalb getrennt hier.

Nachgemessen statt aus Konstantennamen geschlossen: die Aushandlung steht in
`mcp/server/runner.py::_negotiate_initialize` und lautet

    negotiated = requested if requested in HANDSHAKE_PROTOCOL_VERSIONS
                 else LATEST_HANDSHAKE_VERSION

— sie haengt an keinem Transport, gilt also fuer stdio ebenso wie fuer HTTP.

Zweiter Teil, seit diesem Commit: **gemessen statt behauptet.** Hier stand, das
Repo baue keine ASGI-App, durch die sich ein `initialize` schicken liesse, und
die Zusicherungen haengen deshalb an den SDK-Konstanten — die schwaechere Form.
Das war schon damals nur halb richtig: eine ASGI-App braucht es nicht. `Client`
verbindet sich in-process gegen dasselbe `MCPServer`-Objekt, das
`main()` ausliefert, und `mode=` waehlt die Aera. Die Tests unten oeffnen
beide und lesen die Antwort vom Draht.

Das ist die Haelfte, die ein Konstanten-Pin nicht leisten kann: Ein SDK, das
`2026-07-28` kennt, sagt nichts darueber, ob DIESER Server die Aera vollstaendig
bedient. Genau dort lag der Befund, der diesen Commit ausgeloest hat — der
`serverInfo`-Stempel, den die moderne Aera an JEDE Antwort haengt, lautete
`{"name": "swiss_academic_libraries_mcp", "version": ""}`. Beide Pins oben waren
dabei gruen.
"""

from __future__ import annotations

import pathlib
import re

import pytest
from mcp.client import Client
from mcp.types import SERVER_INFO_META_KEY
from mcp.types.version import (
    LATEST_HANDSHAKE_VERSION,
    LATEST_MODERN_VERSION,
    LATEST_PROTOCOL_VERSION,
)

from swiss_academic_libraries_mcp._version import __homepage__, __summary__, __version__
from swiss_academic_libraries_mcp.server import mcp

REPO = pathlib.Path(__file__).resolve().parents[1]

# Die Revisionen, die die READMEs nennen. Sie stehen hier und nicht im `src/`:
# das SDK bestimmt sie, der Server setzt sie nicht. Eine Konstante im
# Auslieferungspfad waere eine zweite Wahrheit, die driften kann — genau so kam
# `bag-epl-mcp` dazu, Aufrufern `2025-06-18` zu melden.
DOCUMENTED_HANDSHAKE_VERSION = "2025-11-25"
DOCUMENTED_MODERN_VERSION = "2026-07-28"

# Datei und Ueberschrift, unter der die beiden Revisionen dokumentiert stehen.
README_SECTIONS = (("README.md", "## MCP Protocol Version"), ("README.de.md", "## MCP-Protokollversion"))


def test_die_handshake_aera_steht_wo_die_readme_sie_nennt() -> None:
    """Die Aera, die bestehende Clients sprechen — der lasttragende Pin."""
    assert LATEST_HANDSHAKE_VERSION == DOCUMENTED_HANDSHAKE_VERSION, (
        f"das SDK deckelt den Handshake jetzt bei {LATEST_HANDSHAKE_VERSION}, "
        f"die READMEs sagen {DOCUMENTED_HANDSHAKE_VERSION}. Nicht blind "
        "nachziehen: erst das Spec-Changelog zwischen den beiden Revisionen "
        "lesen, dann README.md, README.de.md und CHANGELOG.md zusammen mit "
        "dieser Konstante bewegen."
    )


def test_die_moderne_aera_steht_wo_die_readme_sie_nennt() -> None:
    assert LATEST_MODERN_VERSION == DOCUMENTED_MODERN_VERSION, (
        f"das SDK erreicht modern jetzt {LATEST_MODERN_VERSION}, die READMEs "
        f"sagen {DOCUMENTED_MODERN_VERSION}"
    )


def test_latest_protocol_version_ist_der_alias_auf_die_moderne_aera() -> None:
    """Die Falle, gegen die dieses Repo abgesichert wird, benannt.

    Ohne diese Zeile liest sich der naheliegende Einzeiler
    `PIN == LATEST_PROTOCOL_VERSION` wie eine vollstaendige Zusicherung. Sie
    ist es nicht, und man sieht es dem Namen nicht an. Faellt dieser Test, hat
    das SDK die Bedeutung des Alias geaendert — dann ist die Aufteilung oben
    neu zu bewerten, nicht nur eine Zahl.
    """
    assert LATEST_PROTOCOL_VERSION == LATEST_MODERN_VERSION
    assert LATEST_PROTOCOL_VERSION != LATEST_HANDSHAKE_VERSION


def test_die_beiden_aeren_sind_verschieden() -> None:
    """Sagt, wann die Aufteilung oben wieder verschwinden darf.

    Faellt das SDK die Aeren eines Tages auf eine Revision zusammen, ist die
    doppelte Zusicherung redundant und gehoert zurueckgebaut. Dieser Test ist
    die Stelle, an der das auffaellt.
    """
    assert LATEST_MODERN_VERSION > LATEST_HANDSHAKE_VERSION


def test_der_pin_ist_eine_datierte_revision_kein_bewegliches_ziel() -> None:
    """«latest» oder eine Spanne wuerde den Zweck des Pins aufheben."""
    for value in (DOCUMENTED_HANDSHAKE_VERSION, DOCUMENTED_MODERN_VERSION):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), value


def test_beide_readmes_nennen_dieselben_beiden_revisionen() -> None:
    """Ein Pin, den die Doku anders angibt, ist kein Pin.

    Jede Sprache einzeln geprueft: im Portfolio sind EN und DE desselben Repos
    schon dreimal auseinandergelaufen, weil nur eine Fassung nachgezogen wurde
    und niemand die andere daneben gelegt hat.
    """
    for name, anchor in README_SECTIONS:
        text = (REPO / name).read_text(encoding="utf-8")
        parts = text.split(anchor, 1)
        assert len(parts) > 1, f"{name} hat keinen Abschnitt «{anchor}»"
        body = parts[1][:2500]
        for value in (DOCUMENTED_HANDSHAKE_VERSION, DOCUMENTED_MODERN_VERSION):
            assert value in body, f"{name} nennt {value} nicht im Abschnitt «{anchor}»"


# ─── Gemessen: was wirklich ueber die Verbindung geht ─────────────────────────

# Der `_meta`-Schluessel, unter dem die moderne Aera `serverInfo` fuehrt, als
# Literal — und daneben eine Zusicherung gegen die SDK-Konstante. Nur das
# Literal waere blind gegen einen Tippfehler hier; nur die Konstante waere blind
# gegen eine Umbenennung im SDK, denn dann suchte der Test brav den neuen
# Schluessel, waehrend Clients weiter den alten lesen. Zusammen faellt es in
# beide Richtungen.
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"

# Je eine Methode aus jeder Familie, die dieser Server bedient. Absichtlich
# keine Auswahl: `resultType` und der `serverInfo`-Stempel gelten der Spec nach
# fuer JEDE Antwort, und ein Test auf `tools/list` allein wuerde einen Handler
# uebersehen, der sein `_meta` selbst setzt und den Stempel damit verdraengt.
# Alle sechs kommen ohne Netz aus — `library_info` ist das einzige Tool, das
# keine Quelle abfragt.
MODERNE_AUFRUFE: dict[str, dict[str, object] | None] = {
    "tools/list": None,
    "resources/list": None,
    "prompts/list": None,
    "resources/read": {"uri": "library://sources"},
    "prompts/get": {"name": "research-workflow", "arguments": {"topic": "Volksschule"}},
    "tools/call": {"name": "library_info", "arguments": {}},
}


async def _roh(client: Client, methode: str) -> dict:
    """Die Antwort so, wie sie ueber den Draht kommt — vor jeder Typisierung.

    Der naheliegende Weg waere `await client.list_tools()` und ein
    `model_dump()`. Er taeuscht: `Result.result_type` traegt im Client-Modell
    den Vorgabewert `"complete"`, und ein Dump schreibt ihn hin, auch wenn der
    Server nichts geschickt hat. Gemessen an einer Legacy-Verbindung, die das
    Feld nachweislich NICHT sendet, lieferte der typisierte Weg fuer alle sechs
    Methoden `resultType="complete"` — ein Test darauf waere gruen geblieben,
    haette der Server das Feld nie gesetzt. Genau die Sorte Zusicherung, die
    nichts prueft.

    Deshalb die zwei nicht-oeffentlichen Zugriffe: `_stamp` ist die Stempelung
    des Clients selbst (die Aera steckt im `_meta` jeder Anfrage, ohne sie
    antwortet der Server mit «Invalid request parameters»), `_dispatcher`
    liefert das Roh-Dict. Beides hier nachzubauen waere die Alternative — und
    hiesse, die Anfrage gegen eine Kopie der Client-Logik zu pruefen statt
    gegen die Client-Logik.
    """
    params = MODERNE_AUFRUFE[methode]
    data: dict = {"method": methode, "params": dict(params) if params else {}}
    opts: dict = {}
    client.session._stamp(data, opts)
    return await client.session._dispatcher.send_raw_request(methode, data.get("params") or None, opts)


async def test_eine_moderne_verbindung_handelt_die_moderne_revision_aus() -> None:
    """Nicht «das SDK kennt 2026-07-28», sondern «dieser Server spricht sie»."""
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        assert client.protocol_version == DOCUMENTED_MODERN_VERSION


async def test_eine_legacy_verbindung_deckelt_bei_der_handshake_obergrenze() -> None:
    """Die andere Aera, am selben Objekt, ueber denselben Einstiegspunkt."""
    async with Client(mcp, mode="legacy") as client:
        assert client.protocol_version == DOCUMENTED_HANDSHAKE_VERSION


@pytest.mark.parametrize("methode", MODERNE_AUFRUFE)
async def test_jede_moderne_antwort_traegt_result_type(methode: str) -> None:
    """Spec 2026-07-28: `Result.resultType` ist Pflicht, nicht optional.

    Die Bruecke «fehlt heisst complete» gilt nur Clients alter Server
    gegenueber; als Server das Feld wegzulassen ist ein Spec-Verstoss.
    """
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        assert (await _roh(client, methode)).get("resultType") == "complete"


@pytest.mark.parametrize("methode", MODERNE_AUFRUFE)
async def test_eine_legacy_antwort_traegt_kein_result_type(methode: str) -> None:
    """Die Gegenprobe zum Test darueber, in der Suite statt im Protokoll.

    Sie haelt fest, dass `_roh` den Draht liest und nicht ein Modell mit
    Vorgabewerten: Faellt jemand auf den typisierten Weg zurueck, wird diese
    Zeile rot, waehrend der Test darueber unbemerkt gruen bliebe. Nebenbei
    zeigt sie, dass die moderne Zusicherung der Aera gilt und nicht dem Server
    an sich.
    """
    async with Client(mcp, mode="legacy") as client:
        assert (await _roh(client, methode)).get("resultType") is None


@pytest.mark.parametrize("methode", MODERNE_AUFRUFE)
async def test_jede_moderne_antwort_traegt_den_serverinfo_stempel(methode: str) -> None:
    """Spec #3002: Wo die moderne Aera kein `initialize` mehr kennt, steht die
    Identitaet des Servers im `_meta` jeder einzelnen Antwort."""
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        meta = (await _roh(client, methode)).get("_meta") or {}
    assert SERVER_INFO_KEY in meta, f"{methode} antwortet ohne serverInfo-Stempel: {sorted(meta)}"


@pytest.mark.parametrize("methode", MODERNE_AUFRUFE)
async def test_eine_legacy_antwort_traegt_keinen_stempel(methode: str) -> None:
    """Gegenprobe wie oben — der Stempel gehoert der modernen Aera."""
    async with Client(mcp, mode="legacy") as client:
        assert SERVER_INFO_KEY not in ((await _roh(client, methode)).get("_meta") or {})


def test_der_stempel_schluessel_ist_der_der_spec() -> None:
    """Faellt das, hat das SDK den Schluessel umbenannt — dann ist zu
    entscheiden, ob die Spec mitgegangen ist, statt eine Zeile nachzuziehen."""
    assert SERVER_INFO_META_KEY == SERVER_INFO_KEY


async def test_der_stempel_traegt_eine_version_und_zwar_die_des_pakets() -> None:
    """Der Befund, der diesen Abschnitt ausgeloest hat.

    Vor diesem Commit lautete der Stempel `{"name": ..., "version": ""}`: das
    SDK setzt nichts Eigenes ein, es meldet, was `MCPServer(...)` bekommen hat.
    Beide Konstanten-Pins oben blieben dabei gruen — deshalb steht hier ein
    gemessener Test und keine weitere Konstante.

    Geprueft wird gegen `__version__`, nicht gegen ein Literal: eine Zahl in
    diesem Test waere die zweite Kopie, gegen die `_version.py` geschrieben ist,
    und sie fiele bei jedem Release.
    """
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        stempel = (await _roh(client, "tools/list"))["_meta"][SERVER_INFO_KEY]
    assert stempel.get("version"), "Server meldet sich ohne Version — genau der Zustand von vorher"
    assert stempel["version"] == __version__


async def test_der_stempel_traegt_beschreibung_und_herkunft_aus_den_paket_metadaten() -> None:
    """Die uebrigen Felder des Stempels, zusammen geprueft.

    `exclude_none` laesst ein nicht uebergebenes Feld spurlos verschwinden; ein
    fehlendes faellt also nirgends auf ausser hier.
    """
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        stempel = (await _roh(client, "tools/list"))["_meta"][SERVER_INFO_KEY]
    assert stempel.get("title"), "kein Anzeigename"
    assert stempel.get("description") == __summary__
    assert stempel.get("websiteUrl") == __homepage__


def test_die_paket_metadaten_sind_im_testlauf_ueberhaupt_aufgeloest() -> None:
    """Positivkontrolle zum Test darueber.

    `__summary__` und `__homepage__` fallen ohne installierte Distribution
    bewusst auf `None`. Ein Vergleich beider Seiten gegen dieselbe Konstante
    bliebe dann gruen, waehrend der Server sich ohne Beschreibung meldete —
    `None == None`. Diese Zeile schliesst das aus.
    """
    assert __summary__ and __homepage__, (
        "Paket-Metadaten nicht aufgeloest — `pip install -e .` fehlt. Ohne sie "
        "sagt der Stempel-Test nichts aus."
    )


async def test_discover_meldet_genau_die_moderne_revision() -> None:
    """`server/discover` ist der moderne Ersatz fuer `initialize`.

    Was er als `supportedVersions` nennt, entscheidet, worauf ein Client
    einschwenkt — und ist damit die Angabe, die zum Pin oben passen muss.
    """
    async with Client(mcp, mode=DOCUMENTED_MODERN_VERSION) as client:
        payload = await client.session.send_discover(DOCUMENTED_MODERN_VERSION)
    assert payload["supportedVersions"] == [DOCUMENTED_MODERN_VERSION]


async def test_die_legacy_aera_traegt_dieselbe_identitaet() -> None:
    """Der Handshake fuellt `serverInfo` aus derselben Implementation.

    Ohne diese Zeile liesse sich die Identitaet fuer die moderne Aera reparieren
    und fuer die legacy gleichzeitig verlieren, ohne dass etwas rot wird — es
    sind zwei Pfade durch dasselbe Objekt.
    """
    async with Client(mcp, mode="legacy") as client:
        info = client.server_info
    assert info is not None
    assert info.version == __version__
    assert info.description == __summary__
    assert info.website_url == __homepage__
