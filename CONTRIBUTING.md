# Contributing

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in this project! Contributions are welcome.

## How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to Swiss library and education context (source research, lesson preparation, archival work, etc.).

**Contribute code:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add e-manuscripta full-text search"`
7. Create a Pull Request

## Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs

## Tests

This project requires **no API key** for unit tests:

```bash
# Unit tests (no network required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live smoke tests (internet access required)
PYTHONPATH=src pytest tests/ -m "live"
```

New tools must be covered by at least one unit test and one live smoke test. **Never** commit personal data or credentials.

### Every live test names its source

Every test marked `@pytest.mark.live` also carries `@pytest.mark.quelle("…")` —
on the function or on its class. The finer level wins, so an outlier inside an
otherwise uniform class can be attributed on its own.

```python
# In `test_20_scenarios.py` the `live` mark comes from the module-level
# `pytestmark = pytest.mark.live` at the top of the file; only the source here.
@pytest.mark.quelle("e-rara")
async def test_09_erara_list_collections():
    ...


@pytest.mark.live
@pytest.mark.quelle("swisscovery")
class TestSwisscoveryLive:
    async def test_basic_search(self): ...
```

The permitted values live in `GRUPPEN` in
[`scripts/check_gate_consistency.py`](scripts/check_gate_consistency.py) and are
at the same time the rows of the source table in the header of
[`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml):

<!-- GRUPPEN-LISTE ANFANG (checked by scripts/check_gate_consistency.py) -->
`swisscovery`, `e-rara`, `e-periodica`, `e-manuscripta`, `oa_legal`,
`intl_metadata`, `quellenuebergreifend`, `library_info`
<!-- GRUPPEN-LISTE ENDE -->

`quellenuebergreifend` is for the one test that touches several sources at once;
`library_info` for the one that queries no external source at all.

**A missing marker turns CI red**, as does a value `GRUPPEN` does not know. That
is deliberate: `check_gate_consistency.py` counts the live tests per source and
holds them against that table. A test without a marker would be counted nowhere,
and the table would stay green while understating its coverage.

Until 19 Aug 2026 the guard guessed the source from file and test names instead.
A test that was named after the wrong source moved silently into the wrong
group — and what got reported was the table, i.e. the place that was correct.
Anyone following that report would have "fixed" a right number. A name can no
longer move anything; the marker is registered in `pyproject.toml`.

## Security

Please report security issues responsibly — see [SECURITY.md](SECURITY.md).

## The live suite: when it runs, and who sees a red result

**Cadence:** every Monday at 04:43 UTC, plus on demand via *Actions → Live-Tests → Run
workflow*. See [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen die echten Quellen rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Four answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates:

| State | Means | Job | Issue |
|---|---|---|---|
| `clear` | ran, green | green | closed |
| `finding` | ran, the contract moved | red | opened |
| `upstream` | ran, but **every** failure is a source outage | red | untouched |
| `unknown` | did not run (install failed, nothing collected, all skipped) | red | untouched |

Neither `unknown` nor `upstream` closes an issue: closing would claim a
comparison that never happened. Neither opens one either — there would be
nothing to fix.

`upstream` applies **only** when every single failure is unambiguously an outage
(timeout, 429, 503, dropped connection). A timeout next to a broken assertion
stays `finding`, as does a failure whose message the script does not recognise.
The failure mode of this state is not the false alarm but the explaining-away:
an `upstream` that reaches too far turns every real finding into a shrug.

**A red live run means one of three things**, and none of them can be read off
the error message: the contract with the source has changed; the source is down;
or the bug is ours and the source is innocent. Query the source first, classify
second.

The third is not hypothetical: on 17 Aug 2026, 13 of 30 live tests were red, all
with `RuntimeError: Event loop is closed`, while every source answered perfectly.
The bug was in our own httpx client.

Please read the run before disabling the job — that is how this check dies, and
it is the only one in the repository that can contradict a wrong assumption
about any of the connected sources. Every other test asserts against a fixture,
and the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the MIT License — see [LICENSE](LICENSE).

---

This project follows the conventions of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).
