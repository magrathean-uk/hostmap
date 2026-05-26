from __future__ import annotations


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
    mode = manifest.get("mode", "unknown")
    hostname = manifest.get("hostname", "unknown")
    schema_version = manifest.get("schema_version", "unknown")
    return (
        "# Hostmap Agent Context\n\n"
        f"- Hostname: `{hostname}`\n"
        f"- Schema version: `{schema_version}`\n"
        f"- Mode: `{mode}`\n"
        "- Read JSON contracts before raw text dumps.\n"
        "- Distinguish facts, inference, and manual follow-up.\n"
        "- Treat secrets as redacted and absent by design.\n"
    )
