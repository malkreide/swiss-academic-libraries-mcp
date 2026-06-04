# Security Policy

[🇩🇪 Deutsche Version](SECURITY.de.md)

## Supported Versions

Security fixes are provided for the latest released version on
[PyPI](https://pypi.org/project/swiss-academic-libraries-mcp/). Please always
upgrade to the most recent version before reporting an issue.

## Reporting a Vulnerability

Please report security vulnerabilities **privately** — do not open a public
issue for security-sensitive reports.

- Use [GitHub Security Advisories](../../security/advisories/new) to report
  privately, **or**
- Contact the maintainer at [github.com/malkreide](https://github.com/malkreide).

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept, affected tool/endpoint)
- The version affected and your environment (OS, Python version, transport)

You can expect an initial response within **7 days**. Once a fix is released,
we will credit you in the changelog unless you prefer to remain anonymous.

## Security Model

This server is **read-only** and requires **no API key**:

- All tools perform HTTP `GET` requests against public SRU and OAI-PMH
  endpoints — no data is written, modified, or deleted upstream.
- No personally identifiable information (PII) about library users is
  processed or stored. The APIs return public bibliographic metadata only.
- The server enforces a 30 s timeout per request.

### Deployment Hardening

- **Default binding is `127.0.0.1`** (loopback only). The server has **no
  built-in authentication**.
- Use `--host 0.0.0.0` only when running **behind a reverse proxy that
  provides authentication and per-IP rate limits** (e.g. nginx with
  `limit_req` + OAuth2-Proxy). Non-loopback bindings emit a `WARN` log.
- Logs go to **stderr**; set verbosity with
  `MCP_LOG_LEVEL=DEBUG|INFO|WARNING`. Review your retention policy before
  enabling `DEBUG`.

## Scope

In-scope: the code in this repository (the MCP server, parsers, and
transport layer). Out of scope: vulnerabilities in upstream services
(SLSP / swisscovery, ETH Library e-rara / e-periodica / e-manuscripta) —
please report those directly to the respective providers.

---

This project follows the conventions of the
[Swiss Public Data MCP Portfolio](https://github.com/malkreide).
