#!/usr/bin/env python3
"""Stehen ruff-Pin und Gate-Scope ueberall gleich — oder ist eine Stelle zurueckgeblieben?

WARUM ES DIESEN GATE GIBT
-------------------------
Der ruff-Pin steht an vier Stellen, der Gate-Scope an neun. Dass sie
uebereinstimmen, stand bis hierher nur in CLAUDE.md. Eine Zusicherung, die
niemand prueft, ist eine Absichtserklaerung: Sie haelt, bis jemand es eilig hat.

Beide Abweichungen sind unauffaellig, und das ist das Problem:

  Pin gedriftet    Eine andere ruff-Version meldet Abweichungen, die niemand
                   verursacht hat. Wer sie sucht, sucht im Diff — dort steht
                   sie nicht.
  Scope gedriftet  Das schmalere Gate laesst durch, was das breitere ablehnt.
                   Lokal gruen, in der CI rot — oder umgekehrt, was schlimmer
                   ist: ein Hook, der Commits wegen Befunden blockiert, die
                   keine Pipeline je meldet.

NICHTS GEFUNDEN IST NICHT DASSELBE WIE NICHTS ZU BEANSTANDEN
------------------------------------------------------------
Der Fehlermodus dieses Skripts ist nicht der falsche Alarm, sondern das
Schweigen. Ein Checker, der seine Stellen nicht mehr findet — weil ein Job
umbenannt, ein Block verschoben, eine Datei umstrukturiert wurde — meldet
ohne Gegenmassnahme froehlich "alles konsistent" und bewacht ab da nichts
mehr. Deshalb hat jede Datei eine Mindestzahl erwarteter Fundstellen, und
Unterschreiten ist ein Befund wie jeder andere.

Aus demselben Grund wird eine `files:`-Regex, deren Form dieses Skript nicht
kennt, gemeldet statt uebersprungen. Lieber ein Befund zu viel als eine
Stelle, die still aus der Bewachung faellt.

Nur Standardbibliothek: `tomllib` liest pyproject.toml, YAML wird zeilenweise
nach genau den Tokens abgesucht, um die es geht. PyYAML waere hier die fuenfte
Stelle, an der eine Version gepflegt werden muss — und damit ein Beitrag zu
dem Problem, gegen das dieses Skript steht.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

CI = ".github/workflows/ci.yml"
PYPROJECT = "pyproject.toml"
PRE_COMMIT = ".pre-commit-config.yaml"
CLAUDE_MD = "CLAUDE.md"

# Unterschreitet eine Datei ihre Zahl, ist die Bewachung loechrig geworden —
# unabhaengig davon, ob das Gefundene untereinander stimmt.
MIN_PINS = {CI: 2, PYPROJECT: 1, PRE_COMMIT: 1}
MIN_SCOPES = {CI: 3, PYPROJECT: 2, PRE_COMMIT: 2, CLAUDE_MD: 2}

PIN_RE = re.compile(r"ruff==(\d+\.\d+\.\d+)")
REV_RE = re.compile(r"^\s*rev:\s*v?(\d+\.\d+\.\d+)\s*$")
FILES_RE = re.compile(r"^\s*files:\s*(?P<regex>\S+)\s*$")
FILES_SHAPE_RE = re.compile(r"^\^\((?P<dirs>[A-Za-z0-9_|-]+)\)/$")
RUFF_CMD_RE = re.compile(r"\bruff\s+(?:check|format)\b(?P<rest>[^\n]*)")
MD_VERSION_RE = re.compile(r"`v?(\d+\.\d+\.\d+)`")
MD_REV_RE = re.compile(r"rev:\s*v?(\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class Site:
    """Eine Fundstelle, mit Herkunft — damit ein Befund sagt, wo zu greifen ist."""

    origin: str
    value: str


class GateError(Exception):
    """Eine Datei fehlt oder ist nicht lesbar. Kein Befund, sondern ein Abbruch."""


def _strip_comment(line: str) -> str:
    """Kommentar ab `#` entfernen, Anfuehrungszeichen respektieren.

    Ohne das zaehlten die erklaerenden Kommentare in `ci.yml` als Fundstellen —
    dort steht `ruff check` mehrfach in Prosa, und ein Checker, der Prosa fuer
    ein Gate haelt, vergleicht Kommentare mit Kommandos.
    """
    quote: str | None = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _scope_from_args(rest: str) -> frozenset[str]:
    """Pfad-Argumente eines ruff-Aufrufs zu Verzeichnisnamen normalisieren."""
    dirs = set()
    for token in rest.split():
        if token.startswith("-"):
            continue
        dirs.add(token.rstrip("/"))
    return frozenset(dirs)


def _fmt_scope(scope: frozenset[str]) -> str:
    return " ".join(sorted(scope)) or "(leer)"


def _read(root: Path, name: str) -> str:
    path = root / name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateError(f"{name}: nicht lesbar ({exc})") from exc


def collect_ci(text: str) -> tuple[list[Site], list[Site]]:
    pins, scopes = [], []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)
        for match in PIN_RE.finditer(line):
            pins.append(Site(f"{CI}:{number}", match.group(1)))
        for match in RUFF_CMD_RE.finditer(line):
            scope = _scope_from_args(match.group("rest"))
            if scope:
                scopes.append(Site(f"{CI}:{number}", _fmt_scope(scope)))
    return pins, scopes


def collect_pyproject(text: str) -> tuple[list[Site], list[Site]]:
    data = tomllib.loads(text)
    env = data.get("tool", {}).get("hatch", {}).get("envs", {}).get("default", {})

    pins = [
        Site(f"{PYPROJECT} [tool.hatch.envs.default]", match.group(1))
        for dep in env.get("dependencies", [])
        if (match := PIN_RE.search(dep))
    ]
    scopes = [
        Site(f"{PYPROJECT} scripts.{name}", _fmt_scope(scope))
        for name, command in sorted(env.get("scripts", {}).items())
        if (match := RUFF_CMD_RE.search(str(command))) and (scope := _scope_from_args(match.group("rest")))
    ]
    return pins, scopes


def collect_pre_commit(text: str) -> tuple[list[Site], list[Site], list[str]]:
    pins, scopes, problems = [], [], []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)

        if match := REV_RE.match(line):
            pins.append(Site(f"{PRE_COMMIT}:{number} rev", match.group(1)))

        if match := FILES_RE.match(line):
            regex = match.group("regex")
            shape = FILES_SHAPE_RE.match(regex)
            if not shape:
                # Nicht ueberspringen: Eine Regex, deren Form hier unbekannt ist,
                # faellt sonst still aus der Bewachung — und niemand merkt es.
                problems.append(
                    f"{PRE_COMMIT}:{number}: `files: {regex}` hat eine Form, die dieses Skript "
                    f"nicht vergleichen kann. Erwartet wird `^(a|b|c)/`. Entweder die Regex "
                    f"anpassen oder FILES_SHAPE_RE in {Path(__file__).name} erweitern."
                )
                continue
            dirs = frozenset(shape.group("dirs").split("|"))
            scopes.append(Site(f"{PRE_COMMIT}:{number} files", _fmt_scope(dirs)))
    return pins, scopes, problems


def collect_claude_md(text: str) -> tuple[list[Site], list[Site]]:
    """Der zitierte Gate-Block und jede ruff-Version, die die Doku nennt.

    Die Doku ist kein Nebenschauplatz: Wer sie liest, faehrt die Gates, die dort
    stehen. Nennt sie einen Scope, den die CI nicht faehrt, schickt sie jeden
    Leser an einem Gate vorbei.
    """
    pins, scopes = [], []
    in_block = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("```"):
            in_block = not in_block
            continue

        if in_block:
            if match := RUFF_CMD_RE.search(line):
                if scope := _scope_from_args(match.group("rest")):
                    scopes.append(Site(f"{CLAUDE_MD}:{number}", _fmt_scope(scope)))
            continue

        if "ruff" in line.lower() or "rev:" in line:
            # Beide Schreibweisen: `0.16.1` in Prosa und `rev: v0.16.1` als Zitat
            # aus der pre-commit-Config. Nur die erste zu kennen hiesse, die
            # Stelle zu uebersehen, an der die Doku am ehesten veraltet.
            for pattern in (MD_VERSION_RE, MD_REV_RE):
                for match in pattern.finditer(line):
                    pins.append(Site(f"{CLAUDE_MD}:{number}", match.group(1)))
    return pins, scopes


def _disagreements(kind: str, sites: list[Site]) -> list[str]:
    values = {site.value for site in sites}
    if len(values) <= 1:
        return []
    lines = [f"{kind} weicht ab — {len(values)} verschiedene Werte:"]
    for site in sites:
        lines.append(f"    {site.value:<28} {site.origin}")
    return ["\n".join(lines)]


def _too_few(kind: str, sites: list[Site], minimum: dict[str, int]) -> list[str]:
    problems = []
    for name, expected in sorted(minimum.items()):
        found = sum(1 for site in sites if site.origin.startswith(name))
        if found < expected:
            problems.append(
                f"{name}: nur {found} von mindestens {expected} erwarteten {kind}-Stellen "
                f"gefunden. Entweder ist eine Stelle verschwunden, oder die Datei ist so "
                f"umgebaut, dass dieser Gate sie nicht mehr sieht — beides gehoert angesehen, "
                f"bevor hier wieder gruen steht."
            )
    return problems


def check(root: Path) -> list[str]:
    """Alle Fundstellen einsammeln und vergleichen. Rueckgabe: Liste der Befunde."""
    ci_pins, ci_scopes = collect_ci(_read(root, CI))
    py_pins, py_scopes = collect_pyproject(_read(root, PYPROJECT))
    pc_pins, pc_scopes, problems = collect_pre_commit(_read(root, PRE_COMMIT))
    md_pins, md_scopes = collect_claude_md(_read(root, CLAUDE_MD))

    pins = ci_pins + py_pins + pc_pins + md_pins
    scopes = ci_scopes + py_scopes + pc_scopes + md_scopes

    problems += _too_few("Pin", pins, MIN_PINS)
    problems += _too_few("Scope", scopes, MIN_SCOPES)
    problems += _disagreements("ruff-Pin", pins)
    problems += _disagreements("Gate-Scope", scopes)
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="check_gate_consistency")
    ap.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Wurzel des Repos (Vorgabe: das Repo, in dem dieses Skript liegt)",
    )
    args = ap.parse_args(argv)

    try:
        problems = check(args.root)
    except GateError as exc:
        print(f"Abbruch: {exc}", file=sys.stderr)
        return 2

    if problems:
        print("Pin oder Scope sind auseinandergelaufen:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}\n", file=sys.stderr)
        return 1

    print("ruff-Pin und Gate-Scope stimmen an allen geprueften Stellen ueberein.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
