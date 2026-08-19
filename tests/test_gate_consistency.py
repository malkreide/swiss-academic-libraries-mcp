#!/usr/bin/env python3
"""Tests fuer scripts/check_gate_consistency.py — faellt der Gate, wenn er soll?

Ein Konsistenz-Checker ist die Sorte Code, die am leichtesten unbemerkt
aufhoert zu arbeiten. Er hat keinen sichtbaren Effekt, solange alles stimmt,
und "alles stimmt" sieht genauso aus wie "ich finde meine Stellen nicht mehr".
Ein Test, der nur den gruenen Fall prueft, kann diesen Unterschied nicht sehen
— er bliebe gruen, wenn man `check()` durch `return []` ersetzte.

Deshalb wird hier jede Zusicherung einzeln neutralisiert: pro Datei eine
abweichende Version, pro Datei ein abweichender Scope, und der Fall, auf den
es am meisten ankommt — eine Datei, in der die erwarteten Stellen gar nicht
mehr vorkommen (`test_verschwundene_stellen_*`). Genau dort muss ein Befund
stehen und nicht Schweigen.

Nur Standardbibliothek, kein Netz.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_gate_consistency as cgc  # noqa: E402

PIN = "0.16.1"
SCOPE = "src/ tests/ scripts/"

# Ein Mini-`src/` mit denselben zwei Schreibweisen wie das echte: Quellen stehen
# als Modulkonstante UND als `base_url` in einer Tabelle. Wer nur die eine Form
# nachbaut, testet einen Checker, der die andere uebersieht. Die Doku-Links darin
# sind Absicht — sie duerfen NICHT als Quelle zaehlen.
SRC_MODUL = """\
SWISSCOVERY_SRU_URL = "https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK"
ERARA_OAI_URL = "https://www.e-rara.ch/oai"
EPERIODICA_OAI_URL = "https://www.e-periodica.ch/oai/dataprovider"
EMANUSCRIPTA_OAI_URL = "https://www.e-manuscripta.ch/oai"
CROSSREF_BASE = "https://api.crossref.org"
ARXIV_API_URL = "https://export.arxiv.org/api/query"

# Doku-Links: siehe https://www.crossref.org und https://github.com/malkreide/x
REPOSITORIEN = {
    "sui": {"base_url": "https://sui-generis.ch/oai", "homepage": "https://sui-generis.ch"},
    "exa": {"base_url": "https://ex-ante.ch/index.php/exante/oai"},
}
"""

LIVE_HOSTS = """\
#   swisscovery.slsp.ch (SRU)                           10
#   www.e-rara.ch (OAI)                                  7
#   www.e-manuscripta.ch (OAI)                           4
#   www.e-periodica.ch (OAI)                             3
#   sui-generis.ch, ex-ante.ch                           2
#   api.crossref.org, export.arxiv.org                   2
"""

LIVE_TEMPLATE = """\
# Geplante Live-Tests gegen die echten Quellen (DRIFT-005).
#
{hosts}#
# Wer hier eine Quelle ergaenzt, aendert den Namen NICHT mit.

name: Live-Tests
on:
  schedule:
    - cron: "43 4 * * 1"
jobs:
  live:
    name: {job_name}
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            const PREFIX = '{prefix}';
"""

LIVE_JOB_NAME = "Live-Suite gegen die echten Quellen"
LIVE_PREFIX = "Live-Tests gegen die echten Quellen rot"

CI_TEMPLATE = """\
name: CI
jobs:
  test:
    steps:
      - run: pip install uv
      - run: uv pip install -e ".[dev]" --system
      - name: Linting mit ruff
        run: ruff check {scope}
      - name: Syntax-Pruefung
        run: |
          python -m py_compile src/paket/server.py
          python -m py_compile src/paket/{modul}.py
      - name: Import-Test
        run: python -c "from paket.server import mcp; print('Import OK')"
      - name: Unit-Tests
        run: pytest tests/ -v -m "not live"
{env_block}
  lint:
    steps:
      - run: pip install -e ".[dev]"
      - run: ruff check {scope}
      # Prosa-Kommentar: hier steht `ruff check src/` und `ruff format --check src/`,
      # und beides darf NICHT als Fundstelle zaehlen.
      - run: ruff format --check {scope}
      - run: python scripts/check_gate_consistency.py
  security:
    steps:
      - run: pip install pip-audit
{audit_block}
"""

ENV_BLOCK = """\
        env:
          PYTHONPATH: src
"""

AUDIT_BLOCK = """\
      - run: |
          pip-audit --strict --progress-spinner off \\
            -r /tmp/requirements-runtime.txt \\
            --ignore-vuln PYSEC-2025-183
"""

DOC_BLOCK = """\
ruff check {scope}
ruff format --check {scope}
python -m py_compile src/paket/server.py
python -m py_compile src/paket/{modul}.py
python -c "from paket.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -v -m "not live"
python scripts/check_gate_consistency.py
pip-audit --strict -r <runtime-deps> --ignore-vuln PYSEC-2025-183
"""

PYPROJECT_TEMPLATE = """\
[project]
name = "beispiel"

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff=={pin}"]

[tool.hatch.envs.default]
features = ["dev"]

[tool.hatch.envs.default.scripts]
lint = "ruff check {scope}"
fmt = "ruff format {scope}"
"""

PRE_COMMIT_TEMPLATE = """\
repos:
{fremd}\
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v{pin}
    hooks:
      - id: ruff-check
        files: {files}
      - id: ruff-format
        files: {files}
"""

# Ein voellig gewoehnlicher zweiter Hook — eigene `rev`, eigener Dateifilter,
# und mit ruff hat er nichts zu tun.
FREMDER_HOOK = """\
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v9.9.9
    hooks:
      - id: end-of-file-fixer
        files: ^(docs)/
"""

CLAUDE_TEMPLATE = """\
# CLAUDE.md

**ruff ist auf `{pin}` gepinnt** — und als `rev: v{pin}` in der pre-commit-Config.

```bash
{block}```
"""


EXTRA_JOB = """\
  zusatz:
    steps:
      - run: {command}
"""


def baue_ci(
    *,
    pin: str | None = None,
    scope: str = SCOPE,
    modul: str = "api_client",
    env_block: str = ENV_BLOCK,
    audit_block: str = AUDIT_BLOCK,
    extra: str = "",
) -> str:
    ci = CI_TEMPLATE.format(scope=scope, modul=modul, env_block=env_block, audit_block=audit_block)
    if pin is not None:
        # Ein eigener ruff-Install im Workflow — soll es nicht mehr geben,
        # laesst sich fuer die Gegenprobe aber gezielt einschleusen.
        ci += EXTRA_JOB.format(command=f'pip install "ruff=={pin}"')
    return ci + (EXTRA_JOB.format(command=extra) if extra else "")


def schreibe_repo(
    root: Path,
    *,
    ci_pin: str | None = None,
    ci_scope: str = SCOPE,
    py_pin: str = PIN,
    py_scope: str = SCOPE,
    pc_pin: str = PIN,
    pc_files: str = "^(src|tests|scripts)/",
    pc_fremder_hook: bool = False,
    md_pin: str = PIN,
    md_scope: str = SCOPE,
    md_block: str | None = None,
    ci_text: str | None = None,
    src_modul: str = SRC_MODUL,
    live_hosts: str = LIVE_HOSTS,
    live_job_name: str = LIVE_JOB_NAME,
    live_prefix: str = LIVE_PREFIX,
) -> Path:
    """Ein in sich stimmiges Mini-Repo, an dem sich einzelne Stellen verstellen lassen."""
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    ci = ci_text if ci_text is not None else baue_ci(pin=ci_pin, scope=ci_scope)
    (root / ".github" / "workflows" / "ci.yml").write_text(ci, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(pin=py_pin, scope=py_scope), encoding="utf-8"
    )
    fremd = FREMDER_HOOK if pc_fremder_hook else ""
    (root / ".pre-commit-config.yaml").write_text(
        PRE_COMMIT_TEMPLATE.format(pin=pc_pin, files=pc_files, fremd=fremd), encoding="utf-8"
    )
    block = md_block if md_block is not None else DOC_BLOCK.format(scope=md_scope, modul="api_client")
    (root / "CLAUDE.md").write_text(CLAUDE_TEMPLATE.format(pin=md_pin, block=block), encoding="utf-8")
    paket = root / "src" / "paket"
    paket.mkdir(parents=True, exist_ok=True)
    (paket / "quellen.py").write_text(src_modul, encoding="utf-8")
    (root / ".github" / "workflows" / "live-tests.yml").write_text(
        LIVE_TEMPLATE.format(hosts=live_hosts, job_name=live_job_name, prefix=live_prefix),
        encoding="utf-8",
    )
    return root


class GateKonsistenzTest(unittest.TestCase):
    def pruefe(self, **kwargs) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            return cgc.check(schreibe_repo(Path(tmp), **kwargs))

    # --- der gruene Fall, als Bezugspunkt --------------------------------

    def test_stimmiges_repo_ist_still(self):
        self.assertEqual(self.pruefe(), [])

    def test_echtes_repo_ist_konsistent(self):
        """Der Gate laeuft gegen dieses Repo, nicht nur gegen Attrappen."""
        self.assertEqual(cgc.check(Path(__file__).resolve().parents[1]), [])

    # --- Pin einzeln neutralisieren, Datei fuer Datei ---------------------

    def test_abweichender_pin_in_der_ci_ist_ein_befund(self):
        problems = self.pruefe(ci_pin="0.16.0")
        self.assertTrue(any("installiert ruff selbst" in p for p in problems), problems)
        self.assertTrue(any("0.16.0" in p for p in problems), problems)

    def test_uebereinstimmender_pin_in_der_ci_ist_auch_ein_befund(self):
        """Die Gegenprobe, ohne die die neue Zusicherung nicht widerlegbar waere.

        Frueher war ein CI-Pin eine von drei Stellen, und gemeldet wurde nur,
        wenn er abwich. Ein Pin, der mit den uebrigen uebereinstimmt, ist aber
        genau der gefaehrliche Fall: Er faellt keinem Gleichstands-Vergleich
        auf und ueberschreibt das dev-Extra trotzdem — eine Anhebung dort
        bliebe in der CI wirkungslos, und niemand saehe warum.
        """
        problems = self.pruefe(ci_pin=PIN)
        self.assertTrue(any("installiert ruff selbst" in p for p in problems), problems)

    def test_ohne_ci_pin_meldet_der_gate_nichts_dazu(self):
        """Damit der Befund oben nicht bloss immer anschlaegt."""
        problems = self.pruefe()
        self.assertFalse(any("installiert ruff selbst" in p for p in problems), problems)

    def test_pin_weicht_in_pyproject_ab(self):
        self.assertTrue(any("ruff-Pin weicht ab" in p for p in self.pruefe(py_pin="0.15.8")))

    def test_fremder_hook_bringt_weder_pin_noch_scope_ein(self):
        """Ein zweiter Hook ist kein ruff-Befund.

        `rev:` und `files:` wurden zeilenweise eingesammelt, ohne zu fragen, zu
        welchem `repo:` sie gehoeren. Ein `end-of-file-fixer` mit eigener `rev`
        — der gewoehnlichste Zusatz ueberhaupt — faerbte den Gate damit rot
        mit «ruff-Pin weicht ab: 9.9.9», obwohl am ruff-Block niemand etwas
        geaendert hat. Sein `files:` haette denselben Effekt auf den Scope.
        """
        self.assertEqual(self.pruefe(pc_fremder_hook=True), [])

    def test_der_ruff_block_wird_trotz_fremdem_hook_weiter_gelesen(self):
        """Die Gegenprobe zum Test darueber.

        Ein Filter, der den fremden Hook uebergeht, koennte genauso gut den
        ganzen Rest uebergehen — dann waere oben gruen, weil gar nichts mehr
        geprueft wird. Hier steht der fremde Hook davor UND der ruff-Pin ist
        verstellt: Gemeldet werden muss er trotzdem.
        """
        problems = self.pruefe(pc_fremder_hook=True, pc_pin="0.16.0")
        self.assertTrue(problems, "verstellter ruff-Pin blieb hinter dem fremden Hook unsichtbar")
        self.assertIn("0.16.0", " ".join(problems))

    def test_pin_weicht_in_pre_commit_ab(self):
        self.assertTrue(any("ruff-Pin weicht ab" in p for p in self.pruefe(pc_pin="0.17.0")))

    def test_pin_weicht_in_der_doku_ab(self):
        """Die Doku zaehlt mit: Wer sie liest, installiert die Version, die dort steht."""
        self.assertTrue(any("ruff-Pin weicht ab" in p for p in self.pruefe(md_pin="0.14.0")))

    # --- Scope einzeln neutralisieren ------------------------------------

    def test_scope_weicht_in_ci_ab(self):
        problems = self.pruefe(ci_scope="src/ tests/")
        self.assertTrue(any("Gate-Scope weicht ab" in p for p in problems), problems)

    def test_scope_weicht_in_pyproject_ab(self):
        self.assertTrue(any("Gate-Scope weicht ab" in p for p in self.pruefe(py_scope="src/")))

    def test_scope_weicht_im_hook_ab(self):
        problems = self.pruefe(pc_files="^(src|tests)/")
        self.assertTrue(any("Gate-Scope weicht ab" in p for p in problems), problems)

    def test_scope_weicht_in_der_doku_ab(self):
        problems = self.pruefe(md_scope="src/ tests/")
        self.assertTrue(any("Gate-Scope weicht ab" in p for p in problems), problems)

    # --- der Fall, auf den es ankommt: die Stelle ist weg -----------------

    def test_verschwundene_stellen_sind_ein_befund_kein_schweigen(self):
        """Eine ci.yml ohne ruff-Aufrufe darf nicht als konsistent durchgehen.

        Das ist der Unterschied zwischen "nichts zu beanstanden" und "ich sehe
        nichts mehr". Ohne diesen Test wuerde ein Umbau der CI den Gate still
        entwaffnen: Was er nicht findet, kann er nicht als abweichend melden.
        """
        problems = self.pruefe(ci_text="name: CI\njobs:\n  test:\n    steps:\n      - run: echo hi\n")
        self.assertTrue(any("mindestens" in p for p in problems), problems)
        self.assertTrue(any(cgc.CI in p for p in problems), problems)

    def test_auskommentierte_gates_zaehlen_nicht_als_stellen(self):
        """Ein auskommentiertes Gate ist kein Gate — sonst bewacht der Checker Prosa."""
        ci = baue_ci().replace(
            "      - run: ruff format --check src/ tests/ scripts/",
            "      # - run: ruff format --check src/ tests/ scripts/",
        )
        problems = self.pruefe(ci_text=ci)
        self.assertTrue(any("mindestens" in p for p in problems), problems)

    def test_unbekannte_files_regex_wird_gemeldet_nicht_uebersprungen(self):
        """Eine Regex, deren Form der Checker nicht kennt, faellt sonst still raus."""
        problems = self.pruefe(pc_files="^src/.*[.]py$")
        self.assertTrue(any("nicht vergleichen kann" in p for p in problems), problems)

    # --- der Gate-Block gegen ci.yml -------------------------------------

    def test_doku_nennt_ein_gate_das_die_ci_so_nicht_faehrt(self):
        """Ein Block, der eine andere Marke behauptet, schickt jeden Leser daneben."""
        block = DOC_BLOCK.format(scope=SCOPE, modul="api_client").replace('-m "not live"', '-m "not slow"')
        problems = self.pruefe(md_block=block)
        self.assertTrue(any("deckt sich damit" in p for p in problems), problems)

    def test_geaenderter_pfad_in_der_ci_laesst_die_doku_auffliegen(self):
        """Die CI kompiliert ein anderes Modul, die Doku nennt weiter das alte."""
        problems = self.pruefe(ci_text=baue_ci(modul="klient"))
        self.assertTrue(any("deckt sich damit" in p for p in problems), problems)
        self.assertTrue(any("api_client" in p for p in problems), problems)

    def test_doku_verschweigt_ein_gate_der_ci(self):
        """Die CI faehrt pip-audit, der Block nennt es nicht — wer ihn faehrt, prueft weniger."""
        block = "".join(
            zeile + "\n"
            for zeile in DOC_BLOCK.format(scope=SCOPE, modul="api_client").splitlines()
            if "pip-audit" not in zeile
        )
        problems = self.pruefe(md_block=block)
        self.assertTrue(any("pip-audit" in p for p in problems), problems)

    def test_bindestrich_macht_aus_einem_gate_kein_setup(self):
        """`^pip\\b` passte auch auf `pip-audit` — der CVE-Scan galt als Setup.

        Beim Bauen dieses Tests gefunden: Die Marke wurde nie eingefordert, und
        der gruene Lauf sah genauso aus wie einer, in dem sie geprueft wird.
        """
        self.assertFalse(cgc.SETUP_RE.search("pip-audit --strict -r /tmp/x.txt"))
        self.assertTrue(cgc.SETUP_RE.search("pip install pip-audit"))

    def test_env_variable_zaehlt_zum_kommando(self):
        """`PYTHONPATH=src pytest ...` ist nur belegt, weil `env:` mitgelesen wird."""
        self.assertEqual(self.pruefe(), [])
        problems = self.pruefe(ci_text=baue_ci(env_block=""))
        self.assertTrue(any("PYTHONPATH" in p for p in problems), problems)

    def test_platzhalter_deckt_die_gekuerzte_stelle(self):
        """`<runtime-deps>` vertritt den erzeugten Pfad — sonst waere die Zeile unbelegbar."""
        problems = self.pruefe()
        self.assertFalse(any("pip-audit" in p for p in problems), problems)

    def test_setup_schritte_verlangen_keinen_eintrag_im_block(self):
        """`pip install pip-audit` traegt die Marke, ist aber kein Gate."""
        block = "".join(
            zeile + "\n"
            for zeile in DOC_BLOCK.format(scope=SCOPE, modul="api_client").splitlines()
            if "pip-audit" not in zeile
        )
        self.assertEqual(self.pruefe(ci_text=baue_ci(audit_block=""), md_block=block), [])

    # --- die Marken-Liste, Eintrag fuer Eintrag --------------------------

    def test_jede_marke_der_liste_wird_wirklich_eingefordert(self):
        """Fuer JEDEN Eintrag in GATE_MARKERS: taucht er in der CI auf, muss die Doku ihn nennen.

        Der Test laeuft ueber die Liste selbst, nicht ueber eine Kopie davon.
        Wer eine Marke ergaenzt, bekommt die Pruefung dafuer ohne Zutun — und
        wer eine ergaenzt, die nirgends ausgewertet wird, faellt hier auf.
        """
        block = DOC_BLOCK.format(scope=SCOPE, modul="api_client")
        ungenannt = [marker for marker in cgc.GATE_MARKERS if marker not in block]
        self.assertGreater(len(ungenannt), 5, "Die Liste sollte mehr als eine Handvoll fuehren")

        for marker in ungenannt:
            with self.subTest(marker=marker):
                problems = self.pruefe(ci_text=baue_ci(extra=f"{marker} src/"))
                self.assertTrue(any(marker in p for p in problems), (marker, problems))

    def test_neues_skript_der_ci_muss_in_die_doku(self):
        """Das Muster zieht sich mit: auch ein Skript, das es hier noch nicht gibt."""
        problems = self.pruefe(ci_text=baue_ci(extra="python scripts/frisch_erfunden.py --strict"))
        self.assertTrue(any("scripts/frisch_erfunden.py" in p for p in problems), problems)

    def test_bekanntes_skript_im_block_verlangt_nichts(self):
        """Gegenstueck: Was im Block steht, loest keinen Befund aus."""
        self.assertEqual(self.pruefe(ci_text=baue_ci(extra="python scripts/check_gate_consistency.py")), [])

    def test_werkzeugname_im_setup_ist_kein_gate(self):
        """`pip install mypy` traegt die Marke, prueft aber nichts."""
        self.assertEqual(self.pruefe(ci_text=baue_ci(extra="pip install mypy bandit")), [])

    def test_leerer_gate_block_ist_ein_befund(self):
        problems = self.pruefe(md_block="")
        self.assertTrue(any("Gate-Zeilen" in p for p in problems), problems)

    def test_fehlende_datei_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cgc.GateError):
                cgc.check(Path(tmp))

    # --- Rueckgabewerte des Kommandozeilen-Einstiegs ----------------------

    def test_exitcode_eins_bei_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            schreibe_repo(Path(tmp), ci_pin="0.1.0")
            self.assertEqual(cgc.main(["--root", tmp]), 1)

    def test_exitcode_zwei_wenn_dateien_fehlen(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cgc.main(["--root", tmp]), 2)

    def test_exitcode_null_wenn_alles_stimmt(self):
        with tempfile.TemporaryDirectory() as tmp:
            schreibe_repo(Path(tmp))
            self.assertEqual(cgc.main(["--root", tmp]), 0)

    # --- Quellen-Aufzaehlung in live-tests.yml ---------------------------
    #
    # Der Workflow hiess bis zum 19.8.2026 «Live-Suite gegen api.crossref.org»,
    # obwohl er neun Hosts abfragt. Wer den roten Lauf vom 17.8.2026 sah, las
    # den Titel und suchte bei crossref; gerissen waren swisscovery, e-rara,
    # e-periodica und e-manuscripta — genau die vier, die im Titel fehlten.

    def test_angebundene_quelle_fehlt_in_der_aufzaehlung(self):
        problems = self.pruefe(
            src_modul=SRC_MODUL + '\nZENTRALGUT_OAI_URL = "https://www.zentralgut.ch/oai"\n'
        )
        self.assertTrue(any("www.zentralgut.ch" in p for p in problems), problems)

    def test_quelle_aus_der_tabelle_zaehlt_auch(self):
        """`base_url` in einer Tabelle ist so sehr eine Quelle wie eine Konstante.

        Ohne diesen Fall waere ein Checker gruen, der nur Modulkonstanten liest —
        und uebersaehe im echten Repo sui-generis, ex/ante und repositorium,
        also drei von neun.
        """
        modul = SRC_MODUL.replace(
            '"exa": {"base_url": "https://ex-ante.ch/index.php/exante/oai"},',
            '"exa": {"base_url": "https://ex-ante.ch/index.php/exante/oai"},\n'
            '    "neu": {"base_url": "https://neue-quelle.ch/oai"},',
        )
        problems = self.pruefe(src_modul=modul)
        self.assertTrue(any("neue-quelle.ch" in p for p in problems), problems)

    def test_aufzaehlung_nennt_host_den_es_nicht_mehr_gibt(self):
        problems = self.pruefe(
            src_modul=SRC_MODUL.replace('ARXIV_API_URL = "https://export.arxiv.org/api/query"', "")
        )
        self.assertTrue(any("export.arxiv.org" in p for p in problems), problems)
        self.assertTrue(any("nicht mehr anbindet" in p for p in problems), problems)

    def test_doku_links_zaehlen_nicht_als_quelle(self):
        """Die Gegenprobe gegen zu breite Extraktion.

        `https://www.crossref.org`, `https://github.com/...` und die `homepage`
        eines Repositoriums stehen in der Attrappe. Wuerden sie als Quelle
        zaehlen, verlangte der Gate, Doku-Links in die Workflow-Liste zu
        schreiben — ein Gate, das zum Eintragen von Unwahrheiten noetigt, wird
        umgangen. Der stimmige Fall oben ist still; hier steht, warum.
        """
        self.assertEqual(self.pruefe(), [])

    def test_job_name_der_eine_quelle_herausgreift_ist_ein_befund(self):
        problems = self.pruefe(live_job_name="Live-Suite gegen api.crossref.org")
        self.assertTrue(any("Job-Name" in p and "api.crossref.org" in p for p in problems), problems)

    def test_issue_praefix_der_eine_quelle_herausgreift_ist_ein_befund(self):
        """Die vollstaendige Liste im Kommentar nuetzt nichts, wenn das Issue
        weiter nach einem Host heisst — im Posteingang steht der Titel."""
        problems = self.pruefe(live_prefix="Live-Tests gegen swisscovery.slsp.ch rot")
        self.assertTrue(any("Issue-Praefix" in p for p in problems), problems)

    def test_umzug_auf_beiden_seiten_ist_kein_befund(self):
        """Kein Fehlalarm, wenn Quelle und Aufzaehlung zusammen umziehen."""
        problems = self.pruefe(
            src_modul=SRC_MODUL.replace("export.arxiv.org", "arxiv-neu.example.org"),
            live_hosts=LIVE_HOSTS.replace("export.arxiv.org", "arxiv-neu.example.org"),
        )
        self.assertEqual(problems, [])

    def test_leergelaufene_extraktion_ist_ein_befund(self):
        """Nichts gefunden ist nicht dasselbe wie nichts zu beanstanden.

        Laufen die Regexes an einem Umbau vorbei, vergleicht der Gate zwei
        leere Mengen und bliebe still gruen — der gefaehrlichste Zustand, weil
        er wie Zustimmung aussieht.
        """
        problems = self.pruefe(src_modul="# hier stand einmal etwas\n")
        self.assertTrue(any("mindestens" in p and "Quell-Hosts" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
