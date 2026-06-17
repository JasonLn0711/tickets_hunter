#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SOURCE_ASSET_PATTERNS = (
    "src/assets/model/*/custom.onnx",
    "src/assets/model/*/charsets.json",
    "src/www/dist/**/*",
)
EXECUTABLE_NAMES = ("settings.exe", "nodriver_tixcraft.exe")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as infile:
        for chunk in iter(lambda: infile.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_entry(repo_root: Path, path: Path, category: str) -> dict:
    return {
        "path": path.relative_to(repo_root).as_posix() if path.is_relative_to(repo_root) else path.as_posix(),
        "category": category,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def collect_source_assets(repo_root: Path) -> list:
    entries = []
    seen = set()
    for pattern in SOURCE_ASSET_PATTERNS:
        for path in repo_root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                entries.append(file_entry(repo_root, path, "source-asset"))
    return sorted(entries, key=lambda item: item["path"])


def collect_release_artifacts(repo_root: Path, dist_dir: Path, release_dir: Path, require_dist: bool) -> list:
    entries = []

    if release_dir.exists():
        for path in sorted(release_dir.glob("*.zip")):
            if path.is_file():
                entries.append(file_entry(repo_root, path, "release-zip"))

    if dist_dir.exists():
        found = set()
        for executable_name in EXECUTABLE_NAMES:
            for path in dist_dir.rglob(executable_name):
                if path.is_file():
                    found.add(executable_name)
                    entries.append(file_entry(repo_root, path, "windows-executable"))
        chrome_manifest = dist_dir / "webdriver" / "chrome-download-manifest.json"
        if chrome_manifest.exists():
            entries.append(file_entry(repo_root, chrome_manifest, "chrome-download-manifest"))
        if require_dist:
            missing = sorted(set(EXECUTABLE_NAMES) - found)
            if missing:
                raise SystemExit("missing release executables: " + ", ".join(missing))
    elif require_dist:
        raise SystemExit(f"dist directory not found: {dist_dir}")

    return sorted(entries, key=lambda item: item["path"])


def parse_requirement_line(line: str) -> tuple:
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("-r "):
        return "", ""
    if "==" in line:
        name, version = line.split("==", 1)
        return name.strip(), version.strip()
    return line, ""


def build_sbom(requirement_file: Path) -> dict:
    components = []
    for line in requirement_file.read_text(encoding="utf-8").splitlines():
        name, version = parse_requirement_line(line)
        if not name:
            continue
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name.lower()}@{version}" if version else f"pkg:pypi/{name.lower()}",
        }
        components.append(component)
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {
                "type": "application",
                "name": "tickets_hunter",
            },
        },
        "components": components,
    }


def build_manifest(repo_root: Path, dist_dir: Path, release_dir: Path, require_dist: bool) -> dict:
    artifacts = []
    artifacts.extend(collect_source_assets(repo_root))
    artifacts.extend(collect_release_artifacts(repo_root, dist_dir, release_dir, require_dist))
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "tickets_hunter",
        "hash_algorithm": "sha256",
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Tickets Hunter release manifest and dependency SBOM.")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--dist-dir", default="dist/tickets_hunter", help="Built release directory.")
    parser.add_argument("--release-dir", default="dist/release", help="Directory containing release zip files.")
    parser.add_argument("--require-dist", action="store_true", help="Fail if release executables are missing.")
    parser.add_argument("--requirement-file", default="requirement.txt", help="Pinned Python requirement file.")
    parser.add_argument("--output", default="dist/release/release-manifest.json", help="Manifest output path.")
    parser.add_argument("--sbom-output", default="dist/release/sbom.cdx.json", help="SBOM output path.")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    dist_dir = (repo_root / args.dist_dir).resolve()
    release_dir = (repo_root / args.release_dir).resolve()
    requirement_file = (repo_root / args.requirement_file).resolve()

    manifest = build_manifest(repo_root, dist_dir, release_dir, args.require_dist)
    sbom = build_sbom(requirement_file)

    output = (repo_root / args.output).resolve()
    sbom_output = (repo_root / args.sbom_output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sbom_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sbom_output.write_text(json.dumps(sbom, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {sbom_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
