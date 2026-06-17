import json
from pathlib import Path

import pytest

from scripts import release_manifest


def test_release_manifest_hashes_source_assets(tmp_path):
    repo = tmp_path
    model_dir = repo / "src" / "assets" / "model" / "universal"
    web_dist = repo / "src" / "www" / "dist"
    model_dir.mkdir(parents=True)
    web_dist.mkdir(parents=True)
    (model_dir / "custom.onnx").write_bytes(b"model")
    (model_dir / "charsets.json").write_text('{"A": 1}', encoding="utf-8")
    (web_dist / "jquery.min.js").write_text("console.log('ok')", encoding="utf-8")

    manifest = release_manifest.build_manifest(
        repo,
        repo / "dist" / "tickets_hunter",
        repo / "dist" / "release",
        require_dist=False,
    )

    paths = {entry["path"]: entry for entry in manifest["artifacts"]}
    assert "src/assets/model/universal/custom.onnx" in paths
    assert paths["src/assets/model/universal/custom.onnx"]["sha256"] == release_manifest.sha256_file(model_dir / "custom.onnx")
    assert "src/www/dist/jquery.min.js" in paths


def test_release_manifest_requires_release_executables_when_requested(tmp_path):
    dist_dir = tmp_path / "dist" / "tickets_hunter"
    dist_dir.mkdir(parents=True)

    with pytest.raises(SystemExit) as exc:
        release_manifest.build_manifest(tmp_path, dist_dir, tmp_path / "dist" / "release", require_dist=True)

    assert "missing release executables" in str(exc.value)


def test_sbom_uses_pinned_requirement_versions(tmp_path):
    requirement_file = tmp_path / "requirement.txt"
    requirement_file.write_text("requests==2.33.0\n# comment\n-r other.txt\n", encoding="utf-8")

    sbom = release_manifest.build_sbom(requirement_file)

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["components"] == [
        {
            "type": "library",
            "name": "requests",
            "version": "2.33.0",
            "purl": "pkg:pypi/requests@2.33.0",
        }
    ]
