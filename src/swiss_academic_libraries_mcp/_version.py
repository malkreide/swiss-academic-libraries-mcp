"""Die eine Stelle, an der dieses Paket seine Identitaet aufloest.

Gelesen aus den Metadaten der *installierten* Distribution, nie von Hand
geschrieben. Ein Literal ist eine zweite Kopie einer Angabe, die der Build
bestimmt, und zweite Kopien driften — `swiss-procurement-mcp` meldete
`0.4.0` an simap.ch, waehrend das Paket auf PyPI bei `0.18.3` stand,
vierzehn Minor-Versionen spaeter, aus genau so einer Konstante.

Ein eigenes Modul statt einer Aufloesung in `__init__`, damit andere Module
die Angaben importieren koennen, ohne die Paketwurzel zu laden.

Seit Spec `2026-07-28` traegt das nicht mehr nur die Version: auf einer
modernen Verbindung stempelt das SDK `serverInfo` in das `_meta` **jeder**
Antwort (Spec #3002), und dieser Stempel zieht `version`, `description` und
`websiteUrl` aus derselben `Implementation`. Sie kommen deshalb aus derselben
Quelle wie die Version — `description` aus `[project] description`,
`websiteUrl` aus `[project.urls] Homepage`.

Der Versions-Fallback markiert sich selbst als solcher: ein lokales
PEP-440-Segment nach `+` kann nie mit einem Release verwechselt werden,
anders als ein plausibel aussehendes `0.0.0`.

Fuer Beschreibung und Homepage gibt es bewusst **keinen** Fallback-Text.
Ein Literal waere hier genau die zweite Kopie, gegen die dieses Modul
geschrieben ist — und `Implementation` laesst beide Felder weg, wenn sie
`None` sind, statt etwas Falsches zu behaupten. Ohne Installation fehlt die
Angabe also, statt zu veralten. `tests/test_protocol_version.py` haelt mit
einer Positivkontrolle fest, dass im Testlauf nicht beide Seiten `None` sind.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as _pkg_metadata
from importlib.metadata import version as _pkg_version

_DIST = "swiss-academic-libraries-mcp"


def _homepage(meta: object) -> str | None:
    """Die Homepage aus den Distributionsmetadaten, oder `None`.

    `[project.urls] Homepage` landet nicht in einem eigenen Feld, sondern als
    `Project-URL: Homepage, <url>` — Label und URL durch Komma getrennt, in
    beliebiger Reihenfolge zwischen den uebrigen URLs. Das veraltete
    `Home-page` steht zuerst, weil aeltere Build-Backends nur dieses fuellen;
    hatchling fuellt es nicht, hier traegt also die zweite Haelfte.
    """
    legacy = meta.get("Home-page")  # type: ignore[attr-defined]
    if legacy:
        return str(legacy)
    for eintrag in meta.get_all("Project-URL") or ():  # type: ignore[attr-defined]
        label, _, url = str(eintrag).partition(",")
        if label.strip().casefold() == "homepage" and url.strip():
            return url.strip()
    return None


try:
    __version__ = _pkg_version(_DIST)
except PackageNotFoundError:  # Quellbaum statt Installation
    __version__ = "0.0.0+source"

try:
    _META = _pkg_metadata(_DIST)
except PackageNotFoundError:  # Quellbaum statt Installation
    __summary__: str | None = None
    __homepage__: str | None = None
else:
    __summary__ = _META.get("Summary") or None
    __homepage__ = _homepage(_META)

__all__ = ["__homepage__", "__summary__", "__version__"]
