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

## Security

Please report security issues responsibly — see [SECURITY.md](SECURITY.md).

## The live suite: when it runs, and who sees a red result

**Cadence:** every Monday at 04:43 UTC, plus on demand via *Actions → Live-Tests → Run
workflow*. See [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Who sees it:** A red run opens an issue labelled `upstream` and the stable title “Live-Tests gegen api.crossref.org rot (<Datum>)”. A second red run recognises the open issue by its title prefix and appends to that same thread rather than opening a second one. Once the suite is green again, the issue closes itself.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about api.crossref.org. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the MIT License — see [LICENSE](LICENSE).

---

This project follows the conventions of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).
