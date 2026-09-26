import json
import os
import zipfile
from pathlib import Path

import pytest

from hostmap.collect import HostMapper, HostmapOptions


def stub_slow_collectors(monkeypatch) -> None:
    monkeypatch.setattr(HostMapper, "collect_versions", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_runtime", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_filesystem_maps", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_tool_matrices", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_configs", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_git_and_ci", lambda self: None)


def test_manifest_includes_schema_and_mode_policy(tmp_path: Path, monkeypatch) -> None:
    stub_slow_collectors(monkeypatch)
    result = HostMapper(
        HostmapOptions(output_root=tmp_path, mode="paranoid", max_zip_mb=10, create_zip=False, timestamp="test")
    ).run()

    assert result.manifest["schema_version"] == "1.1"
    assert result.manifest["mode_policy"]["include_configs"] is False
    assert result.manifest["mode_policy"]["include_git_metadata"] is False


def test_bundle_qa_and_review_pack_outputs_exist(tmp_path: Path, monkeypatch) -> None:
    stub_slow_collectors(monkeypatch)
    result = HostMapper(
        HostmapOptions(output_root=tmp_path, mode="paranoid", max_zip_mb=10, create_zip=True, timestamp="test")
    ).run()

    qa = json.loads((result.output_dir / "bundle_qa.json").read_text())
    review = json.loads((result.output_dir / "review-pack/checklists.json").read_text())

    assert qa["zip_open_ok"] is True
    assert "member_name_findings" in qa
    assert "operator" in review
    assert (result.output_dir / "review-pack/agent-context.md").exists()
    assert (result.output_dir / "recommendations.md").exists()
    with zipfile.ZipFile(result.zip_path) as zf:
        assert zf.namelist().count("ARCHIVE_SIZE.txt") == 1


@pytest.mark.parametrize("create_zip", [False, True])
def test_manifest_covers_exact_bundle_contents(tmp_path, monkeypatch, create_zip) -> None:
    stub_slow_collectors(monkeypatch)
    result = HostMapper(HostmapOptions(output_root=tmp_path, create_zip=create_zip, timestamp="test")).run()
    manifest = json.loads((result.output_dir / "manifest.json").read_text())
    actual_files = {str(path.relative_to(result.output_dir)) for path in result.output_dir.rglob("*") if path.is_file()}
    assert len(manifest["files"]) == len(set(manifest["files"]))
    assert set(manifest["files"]) == actual_files
    assert manifest == result.manifest
    if create_zip:
        with zipfile.ZipFile(result.zip_path) as archive:
            assert set(archive.namelist()) == actual_files
            for name in actual_files:
                assert archive.read(name) == (result.output_dir / name).read_bytes(), name


def test_archive_limit_includes_metadata_and_leaves_no_archive(tmp_path) -> None:
    mapper = HostMapper(HostmapOptions(output_root=tmp_path, max_zip_mb=1, timestamp="test"))
    mapper.output_dir.mkdir()
    (mapper.output_dir / "evidence.bin").write_bytes(os.urandom(1024 * 1024))
    with pytest.raises((SystemExit, ValueError), match="archive exceeds"):
        mapper.build_zip()
    assert not (tmp_path / "test.zip").exists()
    assert not (tmp_path / ".test.zip.tmp").exists()
