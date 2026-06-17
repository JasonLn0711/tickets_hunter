---
goal_id: tickets-hunter-security-followup
version: 0.2.0
status: implemented-and-verified
created_at: 2026-06-17
timezone: Asia/Taipei
repo: tickets_hunter
branch_at_creation: main
baseline_commit_at_creation: 3ae0376
source_report: docs/security/security-audit-2026-06-17.md
current_security_work_state: follow-up-implemented-in-working-tree-before-commit
owner: Tickets Hunter maintainers
execution_mode: local-and-mock-only
---

# Codex Goal Prompt: Tickets Hunter Security Follow-up

## Version Trace

| Version | Date | Change | Source |
|---|---|---|---|
| 0.1.0 | 2026-06-17 | Initial follow-up goal prompt after the first OWASP/NIST security hardening pass. | `docs/security/security-audit-2026-06-17.md`, current working tree based on `3ae0376` |
| 0.2.0 | 2026-06-17 | Follow-up implementation completed: runtime integration evidence, secret lifecycle migration, release manifest/SBOM tooling, POST migration, redaction, static-analysis triage, scope-control UX, iBon helper refactor, and governance docs. | `docs/security/local-runtime-evidence-2026-06-17.md`, `docs/security/static-analysis-triage-2026-06-17.md`, `docs/security/security-audit-2026-06-17.md` |

## Prompt To Give Codex

You are Codex working in the `tickets_hunter` repository. Continue the security hardening program from the existing security audit and implementation pass.

Use `docs/security/security-audit-2026-06-17.md` as the source report. Treat the current working tree security implementation as the immediate baseline: local-only settings API, local API token, schema validation, hardened Chrome downloader, removed global TLS bypass, security pytest coverage, dependency pin upgrades, security CI, and release security gates.

Your goal is to complete the next security maturity layer for Tickets Hunter while preserving the product’s correct operating scope: a user-owned local desktop automation tool with explicit legal-use boundaries, local/mock-only tests, and a verifiable release path.

## Operating Scope Controls

- Keep all tests local or mocked unless a maintainer explicitly provides a sandbox service and written test boundary.
- Do not connect to real ticketing platforms for security tests.
- Do not send real Discord or Telegram notifications.
- Do not use real user accounts, real session cookies, real webhook URLs, real Telegram bot tokens, or real payment information.
- Do not weaken TLS verification, dependency audit gates, local-only server binding, or the local API token gate.
- Preserve existing user-facing settings compatibility unless a migration plan and tests are included.
- Keep commits separated by scope: local API hardening, secret lifecycle, release supply chain, tests, docs/reporting, and refactors should be separate logical commits.

## Current Baseline To Verify First

Before changing behavior, inspect and verify these files:

- `src/settings.py`
- `src/security_utils.py`
- `src/www/settings.js`
- `src/chrome_downloader.py`
- `src/nodriver_tixcraft.py`
- `src/util.py`
- `tests/`
- `.github/workflows/security-checks.yml`
- `.github/workflows/build-release.yml`
- `requirement.txt`
- `docs/security/security-audit-2026-06-17.md`

Run the current verification suite:

```bash
python3 -m compileall src tests
python3 -m pytest
python3 -m bandit -q -r src -x src/assets,src/www/dist --severity-level high --confidence-level high
python3 -m pip_audit -r requirement.txt
detect-secrets scan src .github tests requirement.txt requirements-dev.txt pyproject.toml --exclude-files '(^|/)(src/assets|src/www/dist)/|.*\.(png|gif|ico|ttf|mp3|wav|onnx)$'
git diff --check
```

If local tools are missing, use a temporary venv under `/tmp` and keep repo-tracked files clean unless you are intentionally updating project tooling.

## Priority 0: Finish Validation Of The Current Security Patch

Objective: prove that the current hardening works in the real app flow, not only in static tests.

Tasks:

1. Install runtime dependencies in an isolated venv and run the settings UI locally.
2. Verify `/load` returns `_security.local_api_token` only to loopback requests.
3. Verify the browser UI stores the token via `installLocalApiToken()` and sends `X-Tickets-Hunter-Token` on mutation requests.
4. Verify `/save`, `/reset`, `/run`, `/pause`, `/resume`, `/shutdown`, `/sendkey`, `/ocr`, `/test_discord_webhook`, and `/test_telegram` reject requests without the local token.
5. Verify the server binds only `127.0.0.1`, not `0.0.0.0`.
6. Verify malformed config is rejected with a clear 400 response and valid config remains compatible.
7. Verify `/ocr` rejects invalid base64 and oversized decoded payloads.
8. Verify no runtime file writes escape `src/` app root during settings operations.

Acceptance:

- A new local integration test file covers token-required mutation behavior without launching real browser automation.
- Manual smoke notes are added to the security report or a new dated test evidence file.
- Any compatibility issue found in the UI token flow is fixed and covered by a test.

## Priority 1: Secret Lifecycle Upgrade

Objective: move from long-lived plaintext secrets in `settings.json` toward a safer local secret lifecycle.

Recommended simple path:

1. Keep non-secret preferences in `settings.json`.
2. Add a `secrets` abstraction that can support:
   - OS keyring when available.
   - Local encrypted or permission-restricted fallback when keyring is unavailable.
   - Explicit "runtime only" fields for session cookies and notification tokens.
3. Start with a compatibility-preserving migration:
   - On load, read existing `settings.json` secret fields.
   - Offer or perform local migration to secret storage.
   - Keep field names stable in the UI.
   - Store only references or empty placeholders in `settings.json` after migration.

Secret fields:

- `accounts.*_password`
- `accounts.*_sid`
- `accounts.ibonqware`
- `accounts.funone_session_cookie`
- `accounts.fansigo_cookie`
- `advanced.discord_webhook_url`
- `advanced.telegram_bot_token`
- Any future payment, account, session, webhook, API key, or token fields.

Tests:

- Existing plaintext `settings.json` loads correctly.
- Migration preserves user-visible values in the UI.
- Saved config does not persist migrated secrets in plaintext.
- Runtime code can still retrieve secrets for automation.
- `detect-secrets` stays clean for repo files.

Acceptance:

- `settings.json` becomes a preference file rather than a long-term secret store.
- Documentation explains local secret stewardship in user-facing language.
- The security report is updated with residual risk and migration status.

## Priority 1: Release Artifact Manifest And SBOM

Objective: make every published executable and bundled asset traceable.

Tasks:

1. Add a release manifest generator script.
2. Include SHA-256 hashes for:
   - release zip
   - `settings.exe`
   - `nodriver_tixcraft.exe`
   - `src/assets/model/*/custom.onnx`
   - `src/assets/model/*/charsets.json`
   - vendored `src/www/dist` files
   - Chrome download manifest, when Chrome is downloaded
3. Add a CycloneDX SBOM or equivalent Python dependency inventory to release artifacts.
4. Update `.github/workflows/build-release.yml` to upload manifest and SBOM with the draft release.
5. Document how users can verify downloaded artifacts.

Tests:

- Manifest generation works on Linux for source assets.
- Release workflow generates manifest on Windows.
- Manifest hashes match actual artifact bytes.
- Missing artifact causes a clear workflow failure.

Acceptance:

- Every release artifact has a reproducible hash record.
- The report links release trust to concrete manifest evidence.

## Priority 1: Runtime Dependency Compatibility Verification

Objective: confirm the upgraded dependency pins are secure and compatible with the app.

Tasks:

1. Create a clean venv from `requirement.txt`.
2. Import all core packages: `ddddocr`, `zendriver`, `tornado`, `requests`, `PIL`, `cv2`, `onnxruntime`.
3. Run a settings UI smoke test.
4. Run a non-ticketing automation dry path where possible without external sites.
5. If any dependency upgrade breaks runtime behavior, pin the nearest secure compatible version and record the decision in the report.

Acceptance:

- `pip-audit` remains clean.
- Runtime imports pass.
- Settings UI smoke passes.
- Compatibility notes are recorded in `docs/security/security-audit-2026-06-17.md` or a dated companion evidence note.

## Priority 2: POST Migration For Control Endpoints

Objective: make state-changing operations explicit and less triggerable by accidental links or browser behavior.

Target endpoints:

- `/run`
- `/pause`
- `/resume`
- `/reset`
- `/shutdown`

Implementation path:

1. Add `POST` handlers for each control endpoint.
2. Update `src/www/settings.js` to use `POST`.
3. Keep `GET` compatibility for one transition version, protected by the local token and returning a deprecation header or warning field.
4. Add tests for `POST` success and missing-token failure.
5. Add tests that `GET` compatibility remains protected.

Acceptance:

- UI uses `POST` for all state-changing operations.
- Existing local-only/token controls remain active.
- Migration is documented.

## Priority 2: Full Static-Analysis Backlog Triage

Objective: turn the current full Bandit findings into an intentional backlog rather than recurring noise.

Known categories:

- Best-effort `except/pass` blocks in platform automation.
- Non-cryptographic `random` used for human-like wait timing.
- Empty string defaults on password/token field names.
- Subprocess imports and controlled executable launch.
- Existing invalid escape sequence warnings in platform JavaScript strings.

Tasks:

1. Run full Bandit without severity filtering and save a local triage summary.
2. Classify findings as:
   - must-fix
   - accepted-by-design with reason
   - false positive
   - refactor backlog
3. Fix high-value low-risk items:
   - replace silent `except/pass` with debug logging where available
   - convert obvious regex/JS string literals to raw strings where safe
   - add `# nosec` only with a short reason for accepted-by-design findings
4. Keep CI high/high gate for now, but add a documented path toward stricter gates.

Acceptance:

- A `docs/security/static-analysis-triage-YYYY-MM-DD.md` file records decisions.
- Full Bandit output is explainable.
- No new high-confidence high-severity finding is allowed.

## Priority 2: Product Scope And Abuse-Resistance UX

Objective: make legal-use and platform-respect boundaries part of the product workflow, not only a disclaimer.

Tasks:

1. Add a concise first-run or settings-page scope-control note:
   - personal lawful use
   - platform terms awareness
   - no resale / no malicious high-rate automation
   - user-owned credentials only
2. Add a refresh-rate / dwell-time guardrail that communicates risk clearly and uses positive-scope wording.
3. Add documentation for safe testing and local-only security checks.
4. Keep wording affirmative and precise: describe approved operating scope, stewardship, and validation path.

Acceptance:

- Users see scope controls before high-risk automation settings.
- Docs align with `LEGAL_NOTICE.md` without relying only on liability disclaimers.
- No UI copy encourages bypassing, evasion, resale, credential sharing, or platform harm.

## Priority 2: Logging And Secret Redaction

Objective: ensure debug logs are useful without exposing secrets.

Tasks:

1. Add a shared redaction helper for passwords, cookies, webhook URLs, Telegram tokens, session IDs, account identifiers where appropriate.
2. Apply redaction to debug paths in:
   - settings API errors
   - notification tests
   - platform login helpers
   - cookie injection logs
   - exception reporting
3. Add tests that known secret patterns are redacted.
4. Document what can appear in logs.

Acceptance:

- Logs can confirm behavior without showing raw secrets.
- Tests cover token, webhook, cookie, and password redaction.

## Priority 3: Platform Adapter Refactor

Objective: make the large platform automation files easier to test and secure.

Recommended architecture:

- Pure decision helpers: URL detection, selector choice, keyword parsing, retry policy, form-fill decision.
- Browser adapter layer: NoDriver/CDP calls.
- Platform state model: explicit step, result, next action, and error state.
- Test fixtures: local HTML snippets and mocked tab/browser objects.

Start with one platform that has active complexity, such as iBon or HKTICKETING, before generalizing.

Acceptance:

- At least one platform has pure helper tests.
- Browser I/O is separated enough that future security tests do not require a real browser or external platform.
- Refactor does not change user-visible behavior.

## Priority 3: Documentation And Governance Maintenance

Objective: keep the security work traceable across future AI-assisted changes.

Tasks:

1. Add `docs/security/README.md` linking:
   - audit report
   - this goal prompt
   - static-analysis triage
   - release artifact manifest instructions
2. Add a PR checklist item requiring:
   - security test pass
   - no new plaintext secrets
   - dependency audit pass
   - local/mock-only boundary for tests
3. Add a short `SECURITY.md` if the project does not already have one:
   - supported versions
   - vulnerability reporting path
   - no real credentials in issues
   - responsible disclosure expectations
4. Keep future security goal prompts versioned under `docs/security/`.

Acceptance:

- A maintainer can find the current security posture in one directory.
- A future Codex session can resume from versioned prompts and reports.

## Suggested Commit Plan

Use separate logical commits:

1. `test: verify local settings API security flow`
2. `security: migrate local secrets lifecycle`
3. `security: add release manifest and sbom`
4. `security: migrate control endpoints to post`
5. `docs: triage static analysis backlog`
6. `docs: add security governance and follow-up prompt`

## Done Definition

The follow-up goal is complete when:

- Current security patch has local integration evidence.
- Runtime dependencies are verified after security pin upgrades.
- Secrets have a concrete migration path, with at least the first compatibility-preserving implementation landed.
- Release artifacts have manifest/SBOM evidence.
- Control endpoints use `POST` in the UI.
- Full static-analysis findings are triaged.
- Security docs are discoverable from `docs/security/README.md`.
- All verification commands pass or have documented, bounded exceptions.
- The final report clearly separates implemented controls, accepted residual risks, and next validation layers.

## Final Response Requirements For Codex

When this goal is executed, the final response should report:

- Files changed.
- Commits created, if requested.
- Verification commands and outcomes.
- Security findings fixed.
- Residual risks intentionally left for later.
- Any blocked item with exact command/error evidence.
