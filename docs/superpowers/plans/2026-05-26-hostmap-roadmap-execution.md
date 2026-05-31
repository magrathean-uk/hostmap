# Hostmap Roadmap Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the roadmap core in one pass: schema v1, bundle QA, structured evidence collectors, offline diffing, Mermaid diagrams, and aligned reviewer prompts without breaking hostmap's read-only safety model.

**Architecture:** Keep one CLI and one collector, but move from mostly ad hoc text dumps to a mixed bundle with stable JSON contracts plus reviewer Markdown. Add small pure-Python parsers for command output and copied files so new features stay testable from fixtures. Implement diff as bundle-to-bundle comparison only, never live-host-to-live-host state.

**Tech Stack:** Python 3.10+, argparse, dataclasses, json, pathlib, subprocess, zipfile, pytest

---

### Task 1: Add schema v1 and mode policy contract

**Files:**
- Create: `hostmap/schema.py`
- Modify: `hostmap/collect.py`
- Modify: `hostmap/cli.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from hostmap.collect import HostMapper, HostmapOptions


def test_manifest_includes_schema_and_mode_policy(tmp_path: Path) -> None:
    result = HostMapper(
        HostmapOptions(output_root=tmp_path, mode="paranoid", max_zip_mb=10, create_zip=False, timestamp="test")
    ).run()

    assert result.manifest["schema_version"] == "1.0"
    assert result.manifest["mode_policy"]["include_configs"] is False
    assert result.manifest["mode_policy"]["include_git_metadata"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_schema.py::test_manifest_includes_schema_and_mode_policy -v`
Expected: FAIL with missing `schema_version` and `mode_policy`.

- [ ] **Step 3: Write minimal implementation**

```python
SCHEMA_VERSION = "1.0"

MODE_POLICIES = {
    "safe": {"include_configs": True, "include_git_metadata": True, "include_local_vpn_roots": False},
    "paranoid": {"include_configs": False, "include_git_metadata": False, "include_local_vpn_roots": False},
    "local": {"include_configs": True, "include_git_metadata": True, "include_local_vpn_roots": True},
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_schema.py::test_manifest_includes_schema_and_mode_policy -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hostmap/schema.py hostmap/collect.py hostmap/cli.py tests/test_schema.py
git commit -m "feat: add schema and mode policy contract"
```

### Task 2: Add bundle QA and review-pack outputs

**Files:**
- Create: `hostmap/review_pack.py`
- Modify: `hostmap/collect.py`
- Test: `tests/test_review_pack.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from hostmap.collect import HostMapper, HostmapOptions


def test_bundle_qa_and_review_pack_outputs_exist(tmp_path: Path) -> None:
    result = HostMapper(
        HostmapOptions(output_root=tmp_path, mode="paranoid", max_zip_mb=10, create_zip=True, timestamp="test")
    ).run()

    qa = json.loads((result.output_dir / "bundle_qa.json").read_text())
    review = json.loads((result.output_dir / "review-pack/checklists.json").read_text())

    assert qa["zip_open_ok"] is True
    assert "member_name_findings" in qa
    assert "operator" in review
    assert (result.output_dir / "review-pack/agent-context.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_review_pack.py::test_bundle_qa_and_review_pack_outputs_exist -v`
Expected: FAIL because files do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
qa = {
    "zip_open_ok": True,
    "member_name_findings": [],
    "text_scan_findings": [],
}
checklists = {
    "reviewer": ["Start with summary.md", "Check runtime and apps evidence"],
    "operator": ["Check failed units", "Check backups and ingress"],
    "ai_agent": ["Separate facts from inference", "Use manifest and JSON contracts first"],
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_review_pack.py::test_bundle_qa_and_review_pack_outputs_exist -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hostmap/review_pack.py hostmap/collect.py tests/test_review_pack.py
git commit -m "feat: add bundle qa and review pack outputs"
```

### Task 3: Add structured evidence collectors and Mermaid diagrams

**Files:**
- Create: `hostmap/parsers.py`
- Modify: `hostmap/collect.py`
- Test: `tests/test_collect_structured.py`

- [ ] **Step 1: Write the failing test**

```python
from hostmap.parsers import parse_systemd_units, parse_ss_listeners, render_service_graph


def test_structured_collectors_render_service_graph() -> None:
    units = parse_systemd_units("nginx.service loaded active running A web server\n")
    listeners = parse_ss_listeners("tcp LISTEN 0 128 127.0.0.1:8080 0.0.0.0:* users:((\"python3\",pid=1,fd=7))\n")
    graph = render_service_graph(
        services=[{"name": "nginx", "kind": "systemd"}],
        listeners=listeners,
        routes=[{"source": "cloudflared", "target": "nginx", "label": "https"}],
    )

    assert units[0]["unit"] == "nginx.service"
    assert listeners[0]["port"] == 8080
    assert "graph TD" in graph
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collect_structured.py::test_structured_collectors_render_service_graph -v`
Expected: FAIL because parser module does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def parse_systemd_units(text: str) -> list[dict]:
    ...

def parse_ss_listeners(text: str) -> list[dict]:
    ...

def render_service_graph(services: list[dict], listeners: list[dict], routes: list[dict]) -> str:
    return "graph TD\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_collect_structured.py::test_structured_collectors_render_service_graph -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hostmap/parsers.py hostmap/collect.py tests/test_collect_structured.py
git commit -m "feat: add structured collectors and diagrams"
```

### Task 4: Add offline diff mode

**Files:**
- Create: `hostmap/diffing.py`
- Modify: `hostmap/cli.py`
- Test: `tests/test_diff.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from hostmap.diffing import diff_manifests


def test_diff_manifests_reports_added_removed_and_changed() -> None:
    before = {"files": ["a"], "mode": "safe", "schema_version": "1.0"}
    after = {"files": ["a", "b"], "mode": "paranoid", "schema_version": "1.0"}

    diff = diff_manifests(before, after)

    assert diff["added_files"] == ["b"]
    assert diff["removed_files"] == []
    assert diff["changed_fields"]["mode"] == {"before": "safe", "after": "paranoid"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_diff.py::test_diff_manifests_reports_added_removed_and_changed -v`
Expected: FAIL because diffing module does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def diff_manifests(before: dict, after: dict) -> dict:
    before_files = set(before.get("files", []))
    after_files = set(after.get("files", []))
    return {
        "added_files": sorted(after_files - before_files),
        "removed_files": sorted(before_files - after_files),
        "changed_fields": {
            key: {"before": before[key], "after": after[key]}
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key) and key != "files"
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_diff.py::test_diff_manifests_reports_added_removed_and_changed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hostmap/diffing.py hostmap/cli.py tests/test_diff.py
git commit -m "feat: add offline diff mode"
```

### Task 5: Align docs and verify roadmap requirements

**Files:**
- Modify: `README.md`
- Modify: `docs/prompts.md`
- Modify: `skills/hostmap/SKILL.md`
- Test: `tests/test_docs_contract.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_docs_reference_schema_diff_review_pack_and_diagrams() -> None:
    readme = Path("README.md").read_text()
    prompts = Path("docs/prompts.md").read_text()
    skill = Path("skills/hostmap/SKILL.md").read_text()

    assert "schema_version" in readme
    assert "diff" in readme
    assert "review-pack" in prompts
    assert "Mermaid" in skill
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_contract.py::test_docs_reference_schema_diff_review_pack_and_diagrams -v`
Expected: FAIL on missing docs references.

- [ ] **Step 3: Write minimal implementation**

```markdown
- schema v1 bundle includes structured JSON contracts and review-pack outputs
- `hostmap diff <before> <after>` compares two existing bundles
- Mermaid diagrams summarize service, ingress, and app relationships
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_contract.py::test_docs_reference_schema_diff_review_pack_and_diagrams -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/prompts.md skills/hostmap/SKILL.md tests/test_docs_contract.py
git commit -m "docs: align hostmap contracts and review guidance"
```
