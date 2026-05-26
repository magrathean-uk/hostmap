import json
from pathlib import Path

from hostmap.cli import main
from hostmap.diffing import diff_manifests


def test_diff_manifests_reports_added_removed_and_changed() -> None:
    before = {"files": ["a"], "mode": "safe", "schema_version": "1.0"}
    after = {"files": ["a", "b"], "mode": "paranoid", "schema_version": "1.0"}

    diff = diff_manifests(before, after)

    assert diff["added_files"] == ["b"]
    assert diff["removed_files"] == []
    assert diff["changed_fields"]["mode"] == {"before": "safe", "after": "paranoid"}


def test_cli_diff_writes_output(tmp_path: Path) -> None:
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    out_dir = tmp_path / "diff"
    before_dir.mkdir()
    after_dir.mkdir()
    (before_dir / "manifest.json").write_text(json.dumps({"files": ["a"], "mode": "safe", "schema_version": "1.0"}))
    (after_dir / "manifest.json").write_text(json.dumps({"files": ["a", "b"], "mode": "safe", "schema_version": "1.0"}))

    exit_code = main(["diff", str(before_dir), str(after_dir), "--output", str(out_dir)])

    assert exit_code == 0
    diff = json.loads((out_dir / "diff.json").read_text())
    assert diff["added_files"] == ["b"]
