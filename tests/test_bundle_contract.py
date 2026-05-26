import json
import zipfile
from pathlib import Path

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

    assert result.manifest["schema_version"] == "1.0"
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
