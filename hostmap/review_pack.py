from __future__ import annotations

from html import escape


def _inline_code_value(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "unknown"
    return escape(value.replace("\r", " ").replace("\n", " "), quote=False)


def build_review_checklists() -> dict[str, list[str]]:
    return {
        "reviewer": [
            "Start with summary.md, manifest.json, and bundle_qa.json.",
            "Use runtime, apps, ingress, and operations evidence before inferring architecture.",
            "Treat missing collectors as unknowns, not absence.",
        ],
        "operator": [
            "Check failed units, timers, sockets, listeners, and repositories first.",
            "Review edge maps and backup evidence before making change plans.",
            "Separate present tooling from active routing and running services.",
        ],
        "ai_agent": [
            "Use schema_version and JSON contracts first; Markdown is reviewer-friendly context.",
            "Separate confirmed facts from inference and unresolved gaps.",
            "Do not treat hostmap as a vulnerability scanner.",
        ],
    }


def build_agent_context(manifest: dict) -> str:
    mode = _inline_code_value(manifest.get("mode"))
    hostname = _inline_code_value(manifest.get("hostname"))
    schema_version = _inline_code_value(manifest.get("schema_version"))
    return (
        "# Hostmap Agent Context\n\n"
        f"- Hostname: <code>{hostname}</code>\n"
        f"- Schema version: <code>{schema_version}</code>\n"
        f"- Mode: <code>{mode}</code>\n"
        "- Read JSON contracts before raw text dumps.\n"
        "- Distinguish facts, inference, and manual follow-up.\n"
        "- Do not infer that secrets are absent from redaction or collector exclusions.\n"
    )
