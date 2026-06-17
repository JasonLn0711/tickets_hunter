# Security Policy

Tickets Hunter is maintained as a local desktop automation tool for personal lawful use with user-owned accounts and platform-term-aware operation. The security process focuses on local control-plane safety, secret lifecycle protection, dependency visibility, release artifact verification, and clear abuse-resistance scope controls.

## Supported Scope

Security reports are in scope when they affect:

- Local settings API authorization, loopback binding, browser-launch controls, or file-write boundaries.
- Stored credentials, cookies, webhook URLs, Telegram bot tokens, runtime tokens, logs, screenshots, or generated artifacts.
- Release artifacts, bundled browser downloads, model or charset assets, dependency pins, SBOM output, or integrity manifests.
- Platform adapter behavior that can change automation rate, login handling, checkout safety, captcha/OCR handling, or user-owned credential handling.

## Reporting

Please report security concerns through a private maintainer channel when available, or open a GitHub issue with a minimal non-sensitive reproduction if no private channel is available. Include the affected version or commit, operating system, reproduction steps, expected security boundary, and observed behavior.

Do not include real passwords, cookies, account identifiers, webhook URLs, Telegram tokens, screenshots containing credentials, or ticketing-session data in public reports. Use synthetic values and local/mock-only examples.

## Security Validation Baseline

Maintainers should keep the following checks passing before release-oriented changes:

- `python -m compileall src tests`
- `python -m pytest`
- `python -m bandit -q -r src -x src/assets,src/www/dist --severity-level high --confidence-level high`
- `python -m pip_audit -r requirement.txt`
- `detect-secrets scan src scripts tests docs/security .github SECURITY.md requirement.txt requirements-dev.txt pyproject.toml --exclude-files '(^|/)(src/assets|src/www/dist)/|.*\.(png|gif|ico|ttf|mp3|wav|onnx)$'`

Release builds should also generate and publish `release-manifest.json` and `sbom.cdx.json` with the packaged ZIP or executable artifacts.
