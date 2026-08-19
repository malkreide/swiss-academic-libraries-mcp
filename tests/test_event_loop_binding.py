"""Ueberlebt der modulweite httpx-Client einen Loop-Wechsel — oder reisst er?

WARUM ES DIESE TESTS GIBT
-------------------------
Am 17.8.2026 war die geplante Live-Suite rot: 13 von 30 Tests, alle mit
`RuntimeError: Event loop is closed`. Die Einordnung des Laufs lautete
`finding` — die Bedeutung, die im Workflow fuer «der Vertrag mit der Quelle
hat sich geaendert» steht. Er hatte sich nicht geaendert: swisscovery, e-rara,
e-periodica und e-manuscripta antworteten zur selben Zeit mit 200 und
unveraenderter Struktur. Der Fehler stand auf unserer Seite.

Der Grund war ein modulweiter Client, der pro *Prozess* gecacht wurde, aber pro
*Event-Loop* gueltig ist. Diese Tests halten genau diese Unterscheidung fest,
denn keiner der uebrigen Tests kann sie sehen: Sie laufen entweder gegen
Mock-Transports (die keinen Socket und keinen Loop brauchen) oder rufen von
Hand `shutdown()` auf — und raeumen damit unbeabsichtigt genau das Problem weg,
um das es hier geht.

Kein externes Netz: Der Server unten laeuft auf 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import http.server
import threading
from collections.abc import Iterator

import pytest

from swiss_academic_libraries_mcp import api_client


class _KeepAliveHandler(http.server.BaseHTTPRequestHandler):
    """Antwortet knapp und HAELT DIE VERBINDUNG OFFEN.

    Keep-alive ist hier nicht Beiwerk, sondern der Gegenstand: Nur eine im Pool
    aufbewahrte Verbindung kann in einen zweiten Loop mitgenommen werden und
    dort auf einen toten Transport treffen. Mit `Connection: close` waere jeder
    Test gruen, auch ohne die Bindung an den Loop.
    """

    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 — von BaseHTTPRequestHandler vorgegeben
        body = b"<ok/>"
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass  # Nicht in die Testausgabe schreiben.


@pytest.fixture
def lokaler_server() -> Iterator[str]:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _KeepAliveHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/x"
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.fixture(autouse=True)
def _sauberer_modulzustand() -> Iterator[None]:
    """Kein Zustand aus einem Nachbartest — und keiner in ihn hinein."""
    api_client._client = None
    api_client._client_loop = None
    api_client._semaphore = None
    api_client._semaphore_loop = None
    yield
    api_client._client = None
    api_client._client_loop = None
    api_client._semaphore = None
    api_client._semaphore_loop = None


def test_zweiter_event_loop_bekommt_einen_frischen_client() -> None:
    """Der Kern: derselbe Prozess, zwei Loops, zwei Clients."""

    async def hole() -> object:
        return api_client._get_client()

    # Referenzen halten: `id()` allein wuerde nach einem GC wiederverwendet
    # werden koennen und den Test still gruen faerben.
    erster = asyncio.run(hole())
    zweiter = asyncio.run(hole())

    assert erster is not zweiter, (
        "Der Client aus dem ersten Loop wurde in den zweiten mitgenommen. "
        "Seine Keep-alive-Sockets haengen am toten Loop."
    )


def test_innerhalb_eines_loops_bleibt_es_derselbe_client() -> None:
    """Gegenrichtung: Die Bindung darf nicht zum Neubau bei jedem Aufruf werden.

    Ohne diesen Test waere «pro Aufruf ein neuer Client» eine bestandene
    Loesung — und der Connection-Pool damit wirkungslos.
    """

    async def zweimal() -> tuple[object, object]:
        return api_client._get_client(), api_client._get_client()

    a, b = asyncio.run(zweimal())
    assert a is b


def test_semaphore_wird_pro_loop_neu_gebaut() -> None:
    """Eine Semaphore bindet ihre Warteschlange an den Loop des ersten Wartens."""

    async def hole() -> object:
        return api_client._get_semaphore()

    assert asyncio.run(hole()) is not asyncio.run(hole())


def test_zweiter_loop_kann_wirklich_abfragen(lokaler_server: str) -> None:
    """Der Regressionstest mit echtem Socket.

    Genau diese Reihenfolge — abfragen, Loop schliessen, wieder abfragen —
    hat die Live-Suite reissen lassen. Ohne Loop-Bindung wirft der zweite
    Durchgang `RuntimeError: Event loop is closed`.
    """

    async def einmal() -> str:
        return await api_client.http_get(lokaler_server)

    assert asyncio.run(einmal()) == "<ok/>"
    assert asyncio.run(einmal()) == "<ok/>", "Der zweite Loop kam nicht durch."


def test_dritter_und_vierter_loop_auch(lokaler_server: str) -> None:
    """Nicht nur der Uebergang 1->2: Der Pool darf ueber n Loops nicht auflaufen."""

    async def einmal() -> str:
        return await api_client.http_get(lokaler_server)

    for durchgang in range(4):
        assert asyncio.run(einmal()) == "<ok/>", f"Durchgang {durchgang + 1} riss."
