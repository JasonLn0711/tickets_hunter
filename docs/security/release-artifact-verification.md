# Release Artifact Verification

Tickets Hunter release builds publish two security artifacts next to packaged ZIP / executable outputs:

- `release-manifest.json` records SHA256 hashes for release ZIP files, Windows executables, bundled model and charset assets, frontend `dist` assets, and the Chrome download manifest when present.
- `sbom.cdx.json` records pinned Python dependencies in CycloneDX 1.5 format.

## Maintainer Generation

For a source-only verification pass:

```bash
python scripts/release_manifest.py \
  --output /tmp/tickets-hunter-release-manifest.json \
  --sbom-output /tmp/tickets-hunter-sbom.cdx.json
```

For a packaged release build, run the same script with the built `dist/tickets_hunter` directory and `--require-dist` so missing executables fail the release job:

```bash
python scripts/release_manifest.py \
  --dist-dir dist/tickets_hunter \
  --release-dir . \
  --output release-manifest.json \
  --sbom-output sbom.cdx.json \
  --require-dist
```

## User Verification

After downloading a release package and its `release-manifest.json`, compute SHA256 locally and compare it with the matching manifest entry:

```bash
sha256sum tickets_hunter.zip
```

On Windows PowerShell:

```powershell
Get-FileHash .\tickets_hunter.zip -Algorithm SHA256
```

The artifact is aligned with the published release when the computed hash exactly matches the manifest `sha256` value for the same path or file name.

## SBOM Review

The SBOM is intended for dependency inventory and vulnerability review. Maintainers should compare SBOM changes with `requirement.txt`, then run:

```bash
python -m pip_audit -r requirement.txt
```

This gives the release a traceable dependency baseline without requiring users to inspect source code before every install.
