from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

from .redaction import read_small_text, redact_text


LISTENER_RE = re.compile(r"(?P<host>.+):(?P<port>\d+)$")
SYSTEMD_UNIT_RE = re.compile(r"\.(service|socket|timer|path|target|mount|automount|swap|slice|scope|device)$")
GO_REQUIRE_RE = re.compile(r"^(?P<package>[A-Za-z0-9./_-]+)\s+(?P<version>v[0-9][^\s]*)(?:\s+//.*)?$")
PYPROJECT_REQUIREMENT_RE = re.compile(
    r"^(?P<package>[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[^\]]+\])?)(?P<version>.*)$"
)


def parse_systemd_units(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("UNIT ") or line.endswith("loaded units listed."):
            continue
        if line.startswith("● "):
            line = line[2:]
        parts = line.split(None, 4)
        if len(parts) < 4 or not SYSTEMD_UNIT_RE.search(parts[0]):
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
        if len(parts) < 2 or not parts[-2].endswith(".timer"):
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
        else:
            parts = line.split()
            if len(parts) == 2 and any(char.isdigit() for char in parts[1]):
                rows.append({"name": parts[0], "version": parts[1]})
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
        text = read_small_text(path)
        if text is None:
            return []
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    rows: list[dict] = []
    for section in ("dependencies", "devDependencies"):
        dependencies = data.get(section) or {}
        if not isinstance(dependencies, dict):
            continue
        for name, version in sorted(dependencies.items()):
            rows.append(
                {
                    "source": path.name,
                    "package": name,
                    "version": redact_text(str(version)).rstrip("\r\n"),
                    "group": section,
                }
            )
    return rows


def parse_pyproject_dependencies(path: Path) -> list[dict]:
    text = read_small_text(path)
    if text is None:
        return []
    rows: list[dict] = []
    in_project = False
    in_deps = False
    for line in text.splitlines():
        stripped = strip_toml_comment(line).strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            in_deps = False
            continue
        if not in_project:
            continue
        if re.match(r"^dependencies\s*=\s*\[", stripped):
            in_deps = True
        if in_deps:
            for match in re.finditer(r'"((?:\\.|[^"\\])*)"|\'([^\']*)\'', stripped):
                dep = match.group(1) if match.group(1) is not None else match.group(2)
                requirement = PYPROJECT_REQUIREMENT_RE.match(dep)
                if not requirement:
                    continue
                package = requirement.group("package")
                version = requirement.group("version").strip()
                rows.append(
                    {
                        "source": path.name,
                        "package": package,
                        "version": redact_text(version.strip()).rstrip("\r\n"),
                        "group": "dependencies",
                    }
                )
            if has_unquoted_closing_bracket(stripped):
                in_deps = False
    return rows


def parse_go_mod_dependencies(path: Path) -> list[dict]:
    text = read_small_text(path)
    if text is None:
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
                rows.append(
                    {
                        "source": path.name,
                        "package": match.group("package"),
                        "version": match.group("version"),
                        "group": "dependencies",
                    }
                )
    return rows


def render_service_graph(services: list[dict], listeners: list[dict], routes: list[dict]) -> str:
    lines = ["graph TD"]
    seen_nodes: set[str] = set()

    def add_node(node_id: str, label: str) -> None:
        if node_id in seen_nodes:
            return
        seen_nodes.add(node_id)
        lines.append(f'  {node_id}["{escape_mermaid_label(label)}"]')

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
        edge = f"  {source_id}"
        if label:
            edge += f' -->|"{escape_mermaid_label(str(label))}"| {target_id}'
        else:
            edge += f" --> {target_id}"
        lines.append(edge)

    return "\n".join(lines) + "\n"


def safe_node_id(text: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", str(text)).strip("_") or "node"
    return f"{normalized}_{sha256(str(text).encode('utf-8')).hexdigest()[:12]}"


def escape_mermaid_label(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def has_unquoted_closing_bracket(text: str) -> bool:
    quote: str | None = None
    escaped = False
    for char in text:
        if quote == '"' and escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if quote is None and char == "]":
            return True
    return False


def strip_toml_comment(text: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote == '"' and escaped:
            escaped = False
            continue
        if quote == '"' and char == "\\":
            escaped = True
            continue
        if char in {'"', "'"}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            continue
        if quote is None and char == "#":
            return text[:index]
    return text
