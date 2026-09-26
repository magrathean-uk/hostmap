from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from pathlib import PurePosixPath


def _manifest_files(manifest: dict) -> set[str]:
    files = manifest.get("files", [])
    if not isinstance(files, list) or not all(isinstance(path, str) for path in files):
        raise ValueError("manifest 'files' must be a list of relative paths")

    safe_paths: set[str] = set()
    for path in files:
        pure_path = PurePosixPath(path)
        if (
            not path
            or pure_path.is_absolute()
            or "." in pure_path.parts
            or ".." in pure_path.parts
            or pure_path.as_posix() != path
        ):
            raise ValueError(f"manifest contains an unsafe file path: {path!r}")
        safe_paths.add(path)
    return safe_paths


def _bundle_root(bundle_dir: Path) -> Path:
    if not bundle_dir.is_dir():
        raise ValueError(f"bundle directory does not exist: {bundle_dir}")
    return bundle_dir.resolve()


def _bundle_file(bundle_root: Path, relative_path: str) -> Path:
    path = (bundle_root / relative_path).resolve()
    try:
        path.relative_to(bundle_root)
    except ValueError as exc:
        raise ValueError(f"manifest file resolves outside bundle: {relative_path!r}") from exc
    if not path.is_file():
        raise ValueError(f"manifest file is missing or not a regular file: {relative_path!r}")
    return path


def _file_digest(path: Path) -> bytes:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def _validated_bundle_files(bundle_dir: Path, manifest: dict) -> tuple[Path, dict[str, Path]]:
    bundle_root = _bundle_root(bundle_dir)
    return bundle_root, {relative_path: _bundle_file(bundle_root, relative_path) for relative_path in _manifest_files(manifest)}


def diff_manifests(before: dict, after: dict) -> dict:
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("manifest JSON must contain an object")
    before_files = _manifest_files(before)
    after_files = _manifest_files(after)
    changed_fields = {}
    for key in sorted(set(before) | set(after)):
        if key == "files":
            continue
        before_present = key in before
        after_present = key in after
        if not before_present or not after_present or before[key] != after[key]:
            change = {"before": before.get(key), "after": after.get(key)}
            if not before_present or not after_present:
                change["before_present"] = before_present
                change["after_present"] = after_present
            changed_fields[key] = change
    return {
        "schema_version": after.get("schema_version") or before.get("schema_version"),
        "added_files": sorted(after_files - before_files),
        "removed_files": sorted(before_files - after_files),
        "changed_fields": changed_fields,
    }


def load_manifest(bundle_dir: Path) -> dict:
    bundle_root = _bundle_root(bundle_dir)
    manifest_path = _bundle_file(bundle_root, "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest JSON must contain an object")
    return manifest


def changed_bundle_files(before_dir: Path, after_dir: Path, before: dict, after: dict) -> list[str]:
    _before_root, before_files = _validated_bundle_files(before_dir, before)
    _after_root, after_files = _validated_bundle_files(after_dir, after)
    return _changed_bundle_files(before_files, after_files)


def _changed_bundle_files(before_files: dict[str, Path], after_files: dict[str, Path]) -> list[str]:
    changed: list[str] = []
    for relative_path in sorted(set(before_files) & set(after_files)):
        before_path = before_files[relative_path]
        after_path = after_files[relative_path]
        if before_path.stat().st_size != after_path.stat().st_size or _file_digest(before_path) != _file_digest(after_path):
            changed.append(relative_path)
    return changed


def _ensure_output_is_separate(before_dir: Path, after_dir: Path, output_dir: Path) -> None:
    output_path = output_dir.resolve()
    for name, bundle_dir in (("before", before_dir), ("after", after_dir)):
        bundle_root = _bundle_root(bundle_dir)
        if output_path == bundle_root or output_path.is_relative_to(bundle_root):
            raise ValueError(f"output directory must not be {name} bundle or inside it: {output_dir}")


def _report_path(output_dir: Path, name: str) -> Path:
    path = output_dir / name
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing diff report: {path}")
    return path


def _write_new_text(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def write_diff_bundle(before_dir: Path, after_dir: Path, output_dir: Path) -> Path:
    _ensure_output_is_separate(before_dir, after_dir, output_dir)
    before = load_manifest(before_dir)
    after = load_manifest(after_dir)
    _before_root, before_files = _validated_bundle_files(before_dir, before)
    _after_root, after_files = _validated_bundle_files(after_dir, after)
    diff = diff_manifests(before, after)
    diff["changed_files"] = _changed_bundle_files(before_files, after_files)
    diff_path = _report_path(output_dir, "diff.json")
    summary_path = _report_path(output_dir, "summary.md")

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_new_text(diff_path, json.dumps(diff, indent=2, sort_keys=True) + "\n")
    _write_new_text(
        summary_path,
        "# Hostmap Diff\n\n"
        f"- Added files: `{len(diff['added_files'])}`\n"
        f"- Removed files: `{len(diff['removed_files'])}`\n"
        f"- Changed files: `{len(diff['changed_files'])}`\n"
        f"- Changed fields: `{len(diff['changed_fields'])}`\n",
    )
    return diff_path
