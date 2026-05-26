from __future__ import annotations

import json
from pathlib import Path


def diff_manifests(before: dict, after: dict) -> dict:
    before_files = set(before.get("files", []))
    after_files = set(after.get("files", []))
    changed_fields = {}
    for key in sorted(set(before) | set(after)):
        if key == "files":
            continue
        if before.get(key) != after.get(key):
            changed_fields[key] = {"before": before.get(key), "after": after.get(key)}
    return {
        "schema_version": after.get("schema_version") or before.get("schema_version"),
        "added_files": sorted(after_files - before_files),
        "removed_files": sorted(before_files - after_files),
        "changed_fields": changed_fields,
    }


def load_manifest(bundle_dir: Path) -> dict:
    return json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))


def write_diff_bundle(before_dir: Path, after_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    before = load_manifest(before_dir)
    after = load_manifest(after_dir)
    diff = diff_manifests(before, after)
    (output_dir / "diff.json").write_text(json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(
        "# Hostmap Diff\n\n"
        f"- Added files: `{len(diff['added_files'])}`\n"
        f"- Removed files: `{len(diff['removed_files'])}`\n"
        f"- Changed fields: `{len(diff['changed_fields'])}`\n",
        encoding="utf-8",
    )
    return output_dir / "diff.json"
