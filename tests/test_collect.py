from pathlib import Path

from hostmap.collect import HostMapper, HostmapOptions


def test_paranoid_smoke_generates_zip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(HostMapper, "collect_versions", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_runtime", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_filesystem_maps", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_tool_matrices", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_configs", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_git_and_ci", lambda self: None)
    result = HostMapper(
        HostmapOptions(output_root=tmp_path, mode="paranoid", max_zip_mb=10, create_zip=True, timestamp="test")
    ).run()
    assert result.output_dir.exists()
    assert result.zip_path is not None
    assert result.zip_path.exists()
    assert (result.output_dir / "manifest.json").exists()
    assert (result.output_dir / "bundle_qa.json").exists()
