# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| 0.1.x | No |

## Reporting a vulnerability

Please open a GitHub issue using the bug report template, or contact the maintainers privately through the repository's security advisory form if the issue involves credentials or data exposure. Do not paste tokens, account identifiers, chat identifiers or real records into a public issue.

Include: affected version, Python version, the command you ran, a minimal reproduction, and the impact you observed. Generated artifacts under `out/`, `demo-out/`, `state/` and `dist/` are gitignored and frequently contain local data; please redact them before sharing.

## Scope and known limitations

This project is a reference runtime with deliberately bundled, credential-free adapters. Read [docs/capability-matrix.md](docs/capability-matrix.md) before assuming a safety mechanism is enforced.

- Real platform connectors are **not bundled**. Any adapter you supply is responsible for its own authentication, token storage and permission checks.
- `setup` writes `config.json` locally. Treat it as sensitive: it may contain channel identifiers, paths and webhook URLs. It is gitignored.
- The XLSX writer modifies archive parts directly. It backs up before writing and verifies that untouched parts are byte-identical, but it is not a general-purpose spreadsheet engine. Validate with a copy of your workbook first.
- The webhook adapters use `urllib` without certificate pinning or retry budgets. Do not point them at untrusted endpoints without your own hardening.
- The deduplication ledger is a plain JSON file with no file locking. Concurrent runs against the same ledger path can race. Run one instance at a time.
- Dry-run is the default for `run`, but `demo` and `run --no-dry-run` do write local artifacts and may send to a configured webhook. Review `config.json` first.
