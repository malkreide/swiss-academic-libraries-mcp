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

## License

By contributing, you agree that your contributions will be licensed under the MIT License — see [LICENSE](LICENSE).

---

This project follows the conventions of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).
