"""Die eine Stelle, an der dieses Paket seine Version aufloest.

Gelesen aus den Metadaten der *installierten* Distribution, nie von Hand
geschrieben. Ein Literal ist eine zweite Kopie einer Zahl, die der Build
bestimmt, und zweite Kopien driften — `swiss-procurement-mcp` meldete
`0.4.0` an simap.ch, waehrend das Paket auf PyPI bei `0.18.3` stand,
vierzehn Minor-Versionen spaeter, aus genau so einer Konstante.

Ein eigenes Modul statt einer Aufloesung in `__init__`, damit andere Module
die Version importieren koennen, ohne die Paketwurzel zu laden.

Der Fallback markiert sich selbst als solcher: ein lokales PEP-440-Segment
nach `+` kann nie mit einem Release verwechselt werden, anders als ein
plausibel aussehendes `0.0.0`.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("swiss-academic-libraries-mcp")
except PackageNotFoundError:  # Quellbaum statt Installation
    __version__ = "0.0.0+source"

__all__ = ["__version__"]
