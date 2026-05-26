from __future__ import annotations

import json
import re
from pathlib import Path


LISTENER_RE = re.compile(r"(?P<host>.+):(?P<port>\d+)$")
PYPROJECT_DEP_RE = re.compile(r'^\s*"([^"]+)"\s*$')
GO_REQUIRE_RE = re.compile(r"^([A-Za-z0-9./_-]+)\s+v[0-9][^\s]*$")


def parse_systemd_units(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("UNIT ") or line.endswith("loaded units listed."):
            continue
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        row = {
            "name": parts[0],
            "unit": parts[0],
            "load": parts[1],
            "active": parts[2],
            "sub": parts[3],
            "description": parts[4] if len(parts) > 4 else "",
        }
        rows.append(row)
    return rows


def parse_systemd_timers(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("NEXT ") or line.endswith("timers listed."):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        rows.append(
            {
                "unit": parts[-2],
                "activates": parts[-1],
                "raw": line,
            }
        )
    return rows


def parse_ss_listeners(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Netid ") or line.startswith("State "):
            continue
        parts = line.split(None, 6)
        if len(parts) < 5:
            continue
        match = LISTENER_RE.search(parts[4])
        if not match:
            continue
        process = parts[6] if len(parts) > 6 else ""
        rows.append(
            {
                "network": parts[0],
                "state": parts[1],
                "local_address": match.group("host"),
                "port": int(match.group("port")),
                "process": process,
            }
        )
    return rows


def parse_tabular_packages(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("$ "):
            continue
        if "\t" in line:
            name, version = line.split("\t", 1)
            rows.append({"name": name, "version": version})
    return rows


def parse_compose_projects(text: str) -> list[dict]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []
    rows: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "name": item.get("Name") or item.get("name"),
                "status": item.get("Status") or item.get("status"),
                "config_files": item.get("ConfigFiles") or item.get("configFiles"),
            }
        )
    return rows


def parse_package_json(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return []
    rows: list[dict] = []
    for section in ("dependencies", "devDependencies"):
        for name, version in sorted((data.get(section) or {}).items()):
            rows.append({"source": path.name, "package": name, "version": version, "group": section})
    return rows


def parse_pyproject_dependencies(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows: list[dict] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies") and "[" in stripped:
            in_deps = True
            continue
        if in_deps and "]" in stripped:
            break
        if in_deps:
            match = PYPROJECT_DEP_RE.match(stripped.rstrip(","))
            if match:
                dep = match.group(1)
                package, _, version = dep.partition(" ")
                rows.append({"source": path.name, "package": package, "version": version.strip(), "group": "dependencies"})
    return rows


def parse_go_mod_dependencies(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows: list[dict] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "require (":
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if stripped.startswith("require "):
            stripped = stripped[len("require ") :]
        if in_block or stripped.startswith(tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")):
            match = GO_REQUIRE_RE.match(stripped)
            if match:
                package, version = stripped.split(None, 1)
                rows.append({"source": path.name, "package": package, "version": version, "group": "dependencies"})
    return rows


def render_service_graph(services: list[dict], listeners: list[dict], routes: list[dict]) -> str:
    lines = ["graph TD"]
    seen_nodes: set[str] = set()

    def add_node(node_id: str, label: str) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        lines.append(f'  {node_id}["{label}"]')

    for service in services:
        unit = service.get("name") or service.get("unit") or "unknown"
        node_id = safe_node_id(unit)
        add_node(node_id, unit)

    for listener in listeners:
        port_label = f'{listener.get("local_address", "*")}:{listener.get("port", "?")}'
        port_id = safe_node_id(f"port-{port_label}")
        add_node(port_id, port_label)
        process = listener.get("process") or "listener"
        process_id = safe_node_id(str(process))
        add_node(process_id, str(process))
        lines.append(f"  {process_id} --> {port_id}")

    for route in routes:
        source = route.get("source", "source")
        target = route.get("target", "target")
        label = route.get("label", "")
        source_id = safe_node_id(source)
        target_id = safe_node_id(target)
        add_node(source_id, source)
        add_node(target_id, target)
        edge = f"  {source_id} --> {target_id}"
        if label:
            edge += f'|"{label}"|'
        lines.append(edge)

    return "\n".join(lines) + "\n"


def safe_node_id(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", text).strip("_") or "node"
