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

CI_TEMPLATE = """\
name: CI
jobs:
  test:
    steps:
      - run: uv pip install pytest "ruff=={pin}" --system
      - name: Linting mit ruff
        run: ruff check {scope}
  lint:
    steps:
      - run: pip install "ruff=={pin}"
      - run: ruff check {scope}
      # Prosa-Kommentar: hier steht `ruff check src/` und `ruff format --check src/`,
      # und beides darf NICHT als Fundstelle zaehlen.
      - run: ruff format --check {scope}
"""

PYPROJECT_TEMPLATE = """\
[project]
name = "beispiel"

[tool.hatch.envs.default]
dependencies = ["pytest>=8.0.0", "ruff=={pin}"]

[tool.hatch.envs.default.scripts]
lint = "ruff check {scope}"
fmt = "ruff format {scope}"
"""

PRE_COMMIT_TEMPLATE = """\
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v{pin}
    hooks:
      - id: ruff-check
        files: {files}
      - id: ruff-format
        files: {files}
"""

CLAUDE_TEMPLATE = """\
# CLAUDE.md

**ruff ist auf `{pin}` gepinnt** — und als `rev: v{pin}` in der pre-commit-Config.

```bash
ruff check {scope}
ruff format --check {scope}
```
"""


def schreibe_repo(
    root: Path,
    *,
    ci_pin: str = PIN,
    ci_scope: str = SCOPE,
    py_pin: str = PIN,
    py_scope: str = SCOPE,
    pc_pin: str = PIN,
    pc_files: str = "^(src|tests|scripts)/",
    md_pin: str = PIN,
    md_scope: str = SCOPE,
    ci_text: str | None = None,
) -> Path:
    """Ein in sich stimmiges Mini-Repo, an dem sich einzelne Stellen verstellen lassen."""
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    ci = ci_text if ci_text is not None else CI_TEMPLATE.format(pin=ci_pin, scope=ci_scope)
    (root / ".github" / "workflows" / "ci.yml").write_text(ci, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        PYPROJECT_TEMPLATE.format(pin=py_pin, scope=py_scope), encoding="utf-8"
    )
    (root / ".pre-commit-config.yaml").write_text(
        PRE_COMMIT_TEMPLATE.format(pin=pc_pin, files=pc_files), encoding="utf-8"
    )
    (root / "CLAUDE.md").write_text(CLAUDE_TEMPLATE.format(pin=md_pin, scope=md_scope), encoding="utf-8")
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

    def test_pin_weicht_in_ci_ab(self):
        problems = self.pruefe(ci_pin="0.16.0")
        self.assertTrue(any("ruff-Pin weicht ab" in p for p in problems), problems)
        self.assertTrue(any("0.16.0" in p for p in problems), problems)

    def test_pin_weicht_in_pyproject_ab(self):
        self.assertTrue(any("ruff-Pin weicht ab" in p for p in self.pruefe(py_pin="0.15.8")))

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
        ci = CI_TEMPLATE.format(pin=PIN, scope=SCOPE).replace(
            "      - run: ruff format --check src/ tests/ scripts/",
            "      # - run: ruff format --check src/ tests/ scripts/",
        )
        problems = self.pruefe(ci_text=ci)
        self.assertTrue(any("mindestens" in p for p in problems), problems)

    def test_unbekannte_files_regex_wird_gemeldet_nicht_uebersprungen(self):
        """Eine Regex, deren Form der Checker nicht kennt, faellt sonst still raus."""
        problems = self.pruefe(pc_files="^src/.*[.]py$")
        self.assertTrue(any("nicht vergleichen kann" in p for p in problems), problems)

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


if __name__ == "__main__":
    unittest.main()
