import json
from pathlib import Path

from hostmap.cli import main
import pytest

from hostmap.diffing import diff_manifests, write_diff_bundle


def test_diff_manifests_reports_added_removed_and_changed() -> None:
    before = {"files": ["a"], "mode": "safe", "schema_version": "1.0"}
    after = {"files": ["a", "b"], "mode": "paranoid", "schema_version": "1.0"}

    diff = diff_manifests(before, after)

    assert diff["added_files"] == ["b"]
    assert diff["removed_files"] == []
    assert diff["changed_fields"]["mode"] == {"before": "safe", "after": "paranoid"}


def test_diff_normalizes_duplicate_manifest_file_entries() -> None:
    diff = diff_manifests({"files": ["a", "a"]}, {"files": ["a", "b", "b"]})

    assert diff["added_files"] == ["b"]


def test_diff_reports_missing_and_null_manifest_fields_as_different() -> None:
    diff = diff_manifests({"files": []}, {"files": [], "hostname": None})

    assert diff["changed_fields"]["hostname"] == {
        "before": None,
        "after": None,
        "before_present": False,
        "after_present": True,
    }


def test_cli_diff_writes_output(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    out_dir = tmp_path / "diff"
    before_dir.mkdir()
    after_dir.mkdir()
    (before_dir / "a").write_text("before")
    (after_dir / "a").write_text("after")
    (after_dir / "b").write_text("added")
    (before_dir / "unlisted").write_text("before")
    (after_dir / "unlisted").write_text("after")
    (before_dir / "manifest.json").write_text(json.dumps({"files": ["a"], "mode": "safe", "schema_version": "1.0"}))
    (after_dir / "manifest.json").write_text(json.dumps({"files": ["a", "b"], "mode": "safe", "schema_version": "1.0"}))

    exit_code = main(["diff", str(before_dir), str(after_dir), "--output", str(out_dir)])

    assert exit_code == 0
    diff = json.loads((out_dir / "diff.json").read_text())
    assert diff["added_files"] == ["b"]
    assert diff["changed_files"] == ["a"]
    assert "Changed files: `1`" in (out_dir / "summary.md").read_text()


def test_diff_rejects_output_inside_an_input_bundle(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()
    for directory in (before_dir, after_dir):
        (directory / "manifest.json").write_text(json.dumps({"files": []}))

    with pytest.raises(ValueError, match="must not be before bundle"):
        write_diff_bundle(before_dir, after_dir, before_dir / "diff")


def test_diff_rejects_manifest_file_symlinked_outside_bundle(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    output_dir = tmp_path / "diff"
    before_dir.mkdir()
    after_dir.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("not part of the bundle")
    (before_dir / "evidence.txt").symlink_to(outside)
    (after_dir / "evidence.txt").write_text("safe evidence")
    for directory in (before_dir, after_dir):
        (directory / "manifest.json").write_text(json.dumps({"files": ["evidence.txt"]}))

    with pytest.raises(ValueError, match="resolves outside bundle"):
        write_diff_bundle(before_dir, after_dir, output_dir)


def test_diff_validates_declared_files_before_creating_output(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    output_dir = tmp_path / "diff"
    before_dir.mkdir()
    after_dir.mkdir()
    (before_dir / "manifest.json").write_text(json.dumps({"files": ["missing.txt"]}))
    (after_dir / "manifest.json").write_text(json.dumps({"files": []}))

    with pytest.raises(ValueError, match="missing or not a regular file"):
        write_diff_bundle(before_dir, after_dir, output_dir)

    assert not output_dir.exists()


def test_diff_preserves_existing_report_files(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    output_dir = tmp_path / "diff"
    before_dir.mkdir()
    after_dir.mkdir()
    output_dir.mkdir()
    for directory in (before_dir, after_dir):
        (directory / "manifest.json").write_text(json.dumps({"files": []}))
    report = output_dir / "diff.json"
    report.write_text("existing report")

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_diff_bundle(before_dir, after_dir, output_dir)

    assert report.read_text() == "existing report"


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", "a/../b"])
def test_diff_rejects_unsafe_manifest_file_paths(path: str) -> None:
    with pytest.raises(ValueError, match="unsafe file path"):
        diff_manifests({"files": [path]}, {"files": []})
