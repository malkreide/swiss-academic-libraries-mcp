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
#
# `ci.yml` steht bewusst NICHT auf dieser Liste: Der Workflow soll gar keinen
# eigenen ruff-Pin mehr tragen. Ein solcher Schritt laeuft nach dem Install des
# dev-Extras und ueberschreibt ihn — eine Abweichung dort faellt dann in der CI
# nicht auf, sondern nur lokal, und der Gleichstands-Vergleich unten bliebe
# gruen, weil der CI-Pin ja mit den uebrigen uebereinstimmt. Sein Fehlen wird
# deshalb eigens geprueft (`_verbotene_pins`), nicht seine Version.
MIN_PINS = {PYPROJECT: 1, PRE_COMMIT: 1}
MIN_SCOPES = {CI: 3, PYPROJECT: 2, PRE_COMMIT: 2, CLAUDE_MD: 2}
MIN_CI_COMMANDS = 10
MIN_DOC_GATES = 6

# Woran ein Gate in `ci.yml` erkennbar ist, ohne die Shell zu parsen. Steht
# eine dieser Marken in einem CI-Kommando, das kein Setup ist, muss der Block
# in CLAUDE.md sie ebenfalls nennen — sonst faehrt die CI ein Gate, von dem
# die Doku nichts weiss, und wer nur die Doku liest, prueft weniger als die CI.
#
# Die Liste bleibt eine Liste: Sie kann nur melden, was auf ihr steht. Die
# Eintraege unter "faehrt dieses Repo" sind belegt, die uebrigen sind vorab
# scharf gestellt — sie kosten nichts, solange das Werkzeug nicht auftaucht,
# und melden ab dem Tag, an dem es undokumentiert auftaucht.
GATE_MARKERS = (
    # faehrt dieses Repo, in ci.yml
    "ruff check",
    "ruff format",
    "py_compile",
    "pytest",
    "pip-audit",
    "Import OK",
    # faehrt dieses Repo, in den uebrigen Workflows — waeren Gates, sobald sie
    # nach ci.yml wandern
    "python -m build",
    # verbreitete Gate-Werkzeuge, hier noch nicht im Einsatz
    "mypy",
    "pyright",
    "bandit",
    "semgrep",
    "deptry",
    "vulture",
    "black",
    "isort",
    "flake8",
    "pylint",
    "coverage",
    "twine",
    "pre-commit run",
    "hatch run",
)

# Was sich nicht aufzaehlen laesst, weil es mit dem Repo waechst: die eigenen
# Skripte. Jedes `scripts/*.py`, das die CI faehrt, muss im Block stehen — auch
# eines, das es beim Schreiben dieser Zeile noch nicht gab. Das ist der einzige
# Teil der Erkennung, der sich selbst mitzieht.
GATE_PATTERNS = (re.compile(r"\bscripts/[A-Za-z0-9_]+\.py\b"),)

# `pip install pytest ...` traegt die Marke `pytest`, ist aber kein Gate.
#
# Der Programmname endet hier auf Leerraum, nicht auf `\b`: `^pip\b` passt auch
# auf `pip-audit`, weil der Bindestrich eine Wortgrenze ist. Damit galt der
# CVE-Scan als Setup und wurde nie eingefordert — ein Gate, das sich selbst
# aus der Bewachung nimmt.
SETUP_RE = re.compile(r"^(?:pip|uv|apt|apt-get|sudo)\s|\binstall\b")

PIN_RE = re.compile(r"ruff==(\d+\.\d+\.\d+)")
REV_RE = re.compile(r"^\s*rev:\s*v?(\d+\.\d+\.\d+)\s*$")
# Der Kopf eines pre-commit-Eintrags. `rev:` und `files:` gehoeren immer dem
# zuletzt genannten `repo:` — ohne diese Zuordnung zaehlte jedes `rev:` der
# Datei als ruff-Pin, und ein zweiter, voellig gewoehnlicher Hook
# (`end-of-file-fixer` und Kollegen) faerbte den Gate rot mit «ruff-Pin weicht
# ab», obwohl am ruff-Block niemand etwas geaendert hat.
REPO_RE = re.compile(r"^\s*-\s*repo:\s*(?P<url>\S+)\s*$")
RUFF_HOOK_REPO = "ruff-pre-commit"
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

    # Der Pin steht im dev-Extra. `[tool.hatch.envs.default]` wird weiter
    # gelesen, aber nicht mehr erwartet: Die Hatch-Umgebung zieht das Extra
    # jetzt ueber `features`, statt ihre Abhaengigkeiten selbst aufzuzaehlen.
    # Traegt sie doch wieder eine eigene Liste mit ruff, faellt das hier als
    # zweite Stelle auf und muss mit der ersten uebereinstimmen.
    extra = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    pins = [
        Site(f"{PYPROJECT} [project.optional-dependencies].dev", match.group(1))
        for dep in extra
        if (match := PIN_RE.search(dep))
    ]
    pins += [
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
    im_ruff_block = False
    for number, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw)

        if match := REPO_RE.match(line):
            im_ruff_block = RUFF_HOOK_REPO in match.group("url")
            continue

        # Alles unterhalb eines fremden `repo:` gehoert nicht zum ruff-Gate —
        # weder seine Version noch sein Dateifilter.
        if not im_ruff_block:
            continue

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


STEP_RE = re.compile(r"^(?P<indent>\s*)-\s")
RUN_RE = re.compile(r"^\s*(?:-\s+)?run:\s*(?P<value>.*)$")
ENV_RE = re.compile(r"^\s*env:\s*$")
ENV_PAIR_RE = re.compile(r"^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*):\s*(?P<value>.+)$")
BLOCK_SCALARS = {"|", ">", "|-", ">-", "|+", ">+"}
SHELL_FENCES = {"```bash", "```sh", "```shell"}


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _join_continuations(block: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Mit `\\` umgebrochene Zeilen zu einem Kommando zusammenziehen.

    Der pip-audit-Aufruf steht ueber vier Zeilen. Ungejoint waere `--ignore-vuln
    PYSEC-2025-183` ein eigenes "Kommando" und der Rest ein anderes — und die
    Zeile aus CLAUDE.md passte auf keines von beiden.
    """
    joined, buffer, first = [], "", None
    for number, text in block:
        if not text:
            continue
        if first is None:
            first = number
        if text.endswith("\\"):
            buffer += text[:-1] + " "
            continue
        joined.append((first, buffer + text))
        buffer, first = "", None
    if buffer:
        joined.append((first or 0, buffer.strip()))
    return joined


def _step_lines(lines: list[str]) -> list[tuple[int, list[str]]]:
    """`ci.yml` in Steps zerlegen — jeder `- ` unterhalb eines `steps:`."""
    steps: list[tuple[int, list[str]]] = []
    current: tuple[int, list[str]] | None = None
    in_steps, steps_indent, step_indent = False, 0, None

    for number, line in enumerate(lines, start=1):
        if not line.strip():
            if current:
                current[1].append(line)
            continue

        indent = _indent(line)
        if line.strip() == "steps:":
            in_steps, steps_indent, step_indent = True, indent, None
            if current:
                steps.append(current)
                current = None
            continue

        if in_steps and indent <= steps_indent and not STEP_RE.match(line):
            in_steps, step_indent = False, None
            if current:
                steps.append(current)
                current = None
            continue

        if in_steps and STEP_RE.match(line) and step_indent in (None, indent):
            step_indent = indent
            if current:
                steps.append(current)
            current = (number, [line])
            continue

        if current:
            current[1].append(line)

    if current:
        steps.append(current)
    return steps


def ci_commands(text: str) -> list[Site]:
    """Jedes Kommando aus den `run:`-Bloecken, mit den `env:`-Variablen seines Steps.

    Die Variablen gehoeren dazu, weil CLAUDE.md sie voranstellt: Dort steht
    `PYTHONPATH=src pytest ...`, in der CI stehen Kommando und `env:` in zwei
    Bloecken. Ohne das Zusammenfuehren waere die zitierte Zeile unbelegbar.
    """
    lines = [_strip_comment(raw).rstrip() for raw in text.splitlines()]
    commands: list[Site] = []

    for start, step in _step_lines(lines):
        env: list[str] = []
        found: list[tuple[int, str]] = []
        index = 0

        while index < len(step):
            line = step[index]
            indent = _indent(line)

            if match := RUN_RE.match(line):
                value = match.group("value").strip()
                if value in BLOCK_SCALARS:
                    index += 1
                    block: list[tuple[int, str]] = []
                    while index < len(step):
                        nxt = step[index]
                        if nxt.strip() and _indent(nxt) <= indent:
                            break
                        block.append((start + index, nxt.strip()))
                        index += 1
                    found.extend(_join_continuations(block))
                    continue
                found.append((start + index, value))
                index += 1
                continue

            if ENV_RE.match(line):
                index += 1
                while index < len(step):
                    nxt = step[index]
                    if nxt.strip() and _indent(nxt) <= indent:
                        break
                    if pair := ENV_PAIR_RE.match(nxt):
                        env.append(f"{pair.group('key')}={pair.group('value').strip()}")
                    index += 1
                continue

            index += 1

        prefix = " ".join(env)
        for number, command in found:
            commands.append(Site(f"{CI}:{number}", f"{prefix} {command}".strip()))

    return commands


def doc_gates(text: str) -> list[Site]:
    """Die Zeilen des zitierten Gate-Blocks aus CLAUDE.md."""
    gates: list[Site] = []
    in_block = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("```"):
            in_block = line.strip() in SHELL_FENCES
            continue
        if in_block and line.strip() and not line.strip().startswith("#"):
            gates.append(Site(f"{CLAUDE_MD}:{number}", line.strip()))
    return gates


def _tokens(command: str) -> list[str]:
    return [token for token in command.split() if token != "\\"]


def _covers(doc: list[str], command: list[str]) -> bool:
    """Sind die Doc-Tokens eine Teilfolge des CI-Kommandos?

    Teilfolge und nicht Gleichheit, weil der Block eine Zusammenfassung ist: Er
    darf `--progress-spinner off` weglassen. Was er NICHT darf, ist etwas
    nennen, das so nicht laeuft — ein Pfad oder eine Marke, die in der CI anders
    steht, findet keine Entsprechung mehr. `<platzhalter>` passt auf ein Token,
    damit `<runtime-deps>` die erzeugte Datei vertreten kann.
    """
    position = 0
    for token in command:
        if position == len(doc):
            break
        want = doc[position]
        if want == token or (want.startswith("<") and want.endswith(">")):
            position += 1
    return position == len(doc)


def compare_gate_block(ci_text: str, md_text: str) -> list[str]:
    """Deckt sich der Block in CLAUDE.md mit dem, was `ci.yml` wirklich faehrt?"""
    commands = ci_commands(ci_text)
    gates = doc_gates(md_text)
    problems: list[str] = []

    if len(commands) < MIN_CI_COMMANDS:
        problems.append(
            f"{CI}: nur {len(commands)} von mindestens {MIN_CI_COMMANDS} erwarteten Kommandos "
            f"gelesen. Entweder ist die Datei geschrumpft, oder ihre Struktur hat sich so "
            f"geaendert, dass dieser Vergleich sie nicht mehr sieht."
        )
    if len(gates) < MIN_DOC_GATES:
        problems.append(
            f"{CLAUDE_MD}: nur {len(gates)} von mindestens {MIN_DOC_GATES} erwarteten Gate-Zeilen "
            f"im zitierten Block gefunden. Ein Block, der leerlaeuft, behauptet nichts mehr — "
            f"und faellt genau deshalb sonst nicht auf."
        )

    for gate in gates:
        wanted = _tokens(gate.value)
        if not any(_covers(wanted, _tokens(site.value)) for site in commands):
            problems.append(
                f"{gate.origin}: `{gate.value}` steht im Gate-Block, aber kein Kommando in "
                f"{CI} deckt sich damit. Entweder faehrt die CI es anders, oder gar nicht — "
                f"wer sich auf den Block verlaesst, prueft dann etwas anderes als die CI."
            )

    zitiert = "\n".join(gate.value for gate in gates)
    fehlend: dict[str, str] = {}
    for site in commands:
        if SETUP_RE.search(site.value):
            continue
        for marker in GATE_MARKERS:
            if marker in site.value and marker not in zitiert:
                fehlend.setdefault(marker, site.origin)
        for pattern in GATE_PATTERNS:
            for treffer in pattern.findall(site.value):
                if treffer not in zitiert:
                    fehlend.setdefault(treffer, site.origin)

    for marker, origin in fehlend.items():
        problems.append(
            f"{origin}: Die CI faehrt ein Gate mit `{marker}`, der Block in {CLAUDE_MD} nennt "
            f"es nicht. Wer nur die Doku faehrt, prueft weniger als die CI und faellt erst "
            f"im Pull Request darueber."
        )

    return problems


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


def _verbotene_pins(sites: list[Site]) -> list[str]:
    """Ein eigener ruff-Pin in `ci.yml` ist ein Befund, unabhaengig vom Wert.

    Gegenstueck zu `_too_few`: Dort ist zu wenig das Problem, hier ist es
    ueberhaupt etwas. Beides braucht es, weil ein zurueckgekehrter CI-Pin von
    keiner der anderen Pruefungen gesehen wuerde — er stimmt mit ihnen ueberein
    und haelt sie trotzdem aus.
    """
    if not sites:
        return []
    orte = ", ".join(f"{site.origin} = {site.value}" for site in sites)
    return [
        f"{CI}: installiert ruff selbst ({orte}). Der Schritt laeuft nach dem "
        f"Install des dev-Extras und ueberschreibt es; eine Abweichung im "
        f"deklarierten Pin faellt damit in der CI gar nicht auf. Den Schritt "
        f"entfernen — ruff kommt aus `pyproject.toml`."
    ]


def check(root: Path) -> list[str]:
    """Alle Fundstellen einsammeln und vergleichen. Rueckgabe: Liste der Befunde."""
    ci_text = _read(root, CI)
    md_text = _read(root, CLAUDE_MD)

    ci_pins, ci_scopes = collect_ci(ci_text)
    py_pins, py_scopes = collect_pyproject(_read(root, PYPROJECT))
    pc_pins, pc_scopes, problems = collect_pre_commit(_read(root, PRE_COMMIT))
    md_pins, md_scopes = collect_claude_md(md_text)
    problems += compare_gate_block(ci_text, md_text)

    pins = py_pins + pc_pins + md_pins
    scopes = ci_scopes + py_scopes + pc_scopes + md_scopes

    problems += _verbotene_pins(ci_pins)
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
        print("Pin, Scope oder Gate-Block sind auseinandergelaufen:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}\n", file=sys.stderr)
        return 1

    print(
        "ruff-Pin und Gate-Scope stimmen an allen geprueften Stellen ueberein, "
        "und der Gate-Block in CLAUDE.md deckt sich mit ci.yml."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
