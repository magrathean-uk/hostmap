import json
import os
import zipfile
from pathlib import Path

import pytest

from hostmap.collect import HostMapper, HostmapOptions
from hostmap.redaction import should_prune_dir


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
    with zipfile.ZipFile(result.zip_path) as archive:
        assert json.loads((result.output_dir / "bundle_qa.json").read_text())["zip_member_count"] == len(archive.namelist())
        assert archive.read("bundle_qa.json") == (result.output_dir / "bundle_qa.json").read_bytes()
    assert f"{result.zip_path.stat().st_size} bytes" in (result.output_dir / "ARCHIVE_SIZE.txt").read_text()


def test_run_refuses_to_replace_existing_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "test"
    output_dir.mkdir()
    marker = output_dir / "keep.txt"
    marker.write_text("do not replace")

    with pytest.raises(FileExistsError, match="refusing to replace"):
        HostMapper(HostmapOptions(output_root=tmp_path, create_zip=False, timestamp="test")).run()

    assert marker.read_text() == "do not replace"


def test_run_refuses_symlinked_archive_path(tmp_path: Path) -> None:
    target = tmp_path / "archive-target"
    target.write_text("do not replace")
    os.symlink(target, tmp_path / "test.zip")

    with pytest.raises(FileExistsError, match="refusing to replace"):
        HostMapper(HostmapOptions(output_root=tmp_path, timestamp="test")).run()

    assert target.read_text() == "do not replace"


def test_directory_map_is_bounded_and_does_not_follow_symlinks(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    current = root
    for index in range(8):
        current = current / f"level-{index}"
        current.mkdir(parents=True)
    os.symlink(tmp_path, root / "outside")

    def prune_fixture_path(path: Path) -> bool:
        return should_prune_dir(Path("/") / path.relative_to(tmp_path))

    mapper = HostMapper(HostmapOptions(output_root=tmp_path / "output", create_zip=False, timestamp="test"))
    monkeypatch.setattr("hostmap.collect.should_prune_dir", prune_fixture_path)
    directory_map = mapper.directory_map(root)

    assert "level-4/" in directory_map
    assert "level-6/" not in directory_map
    assert "[depth limited to 5 levels]" in directory_map


def test_find_git_repos_detects_git_directory(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "home" / "project"
    (repo / ".git").mkdir(parents=True)
    mapper = HostMapper(HostmapOptions(output_root=tmp_path / "output", create_zip=False, timestamp="test"))
    monkeypatch.setattr(HostMapper, "git_search_roots", staticmethod(lambda: [repo.parent]))
    monkeypatch.setattr(
        "hostmap.collect.should_prune_dir",
        lambda path: should_prune_dir(Path("/") / path.relative_to(tmp_path)),
    )
    assert mapper.find_git_repos() == [repo]


def test_symlinked_files_are_not_copied(tmp_path: Path) -> None:
    source = tmp_path / "secret-source"
    source.write_text("API_TOKEN=not-for-bundle\n")
    linked = tmp_path / "service.yml"
    os.symlink(source, linked)

    mapper = HostMapper(HostmapOptions(output_root=tmp_path / "output", create_zip=False, timestamp="test"))
    mapper.output_dir.mkdir(parents=True)
    mapper.copy_redacted(linked, "config-files")

    assert not list(mapper.output_dir.rglob("*"))
    assert mapper.manifest["skipped"] == [{"path": str(linked), "reason": "symbolic links are excluded"}]


def test_bundle_qa_detects_unredacted_json_and_ignores_redacted_values(tmp_path: Path) -> None:
    mapper = HostMapper(HostmapOptions(output_root=tmp_path / "output", create_zip=False, timestamp="test"))
    mapper.output_dir.mkdir(parents=True)
    mapper.write_text("safe.txt", "password: REDACTED\nhttps://REDACTED@example.test\n")
    mapper.write_text("metadata.json", '{"secret_paths_excluded": true, "token": null}\n')
    mapper.write_text("unsafe.json", '{"token": "unredacted"}\n')
    mapper.write_text("unsafe-uri.txt", "https://opaque-token@example.test\n")
    mapper.write_text("bundle_qa.json", '{"password": "unredacted"}\n')

    mapper.write_bundle_qa(None)

    qa = json.loads((mapper.output_dir / "bundle_qa.json").read_text())
    assert qa["text_scan_findings"] == ["unsafe-uri.txt", "unsafe.json"]


def test_bundle_qa_clean_stubbed_bundle_has_no_text_findings(tmp_path: Path, monkeypatch) -> None:
    for name in (
        "collect_versions",
        "collect_runtime",
        "collect_filesystem_maps",
        "collect_tool_matrices",
        "collect_configs",
        "collect_git_and_ci",
    ):
        monkeypatch.setattr(HostMapper, name, lambda self: None)

    result = HostMapper(HostmapOptions(output_root=tmp_path, mode="paranoid", create_zip=False, timestamp="test")).run()
    qa = json.loads((result.output_dir / "bundle_qa.json").read_text())

    assert qa["text_scan_findings"] == []
