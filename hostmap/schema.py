from __future__ import annotations

from copy import deepcopy


# 1.1 records complete file inventories and separates VPN port hints from
# observed services; offline diffs additionally report changed file contents.
SCHEMA_VERSION = "1.1"

MODE_POLICIES = {
    "safe": {
        "include_configs": True,
        "include_git_metadata": True,
        "include_local_vpn_roots": False,
        "description": "Default reviewer bundle with redacted configs and deploy metadata.",
    },
    "paranoid": {
        "include_configs": False,
        "include_git_metadata": False,
        "include_local_vpn_roots": False,
        "description": "Metadata-heavy mode that skips copied configs and repo evidence.",
    },
    "local": {
        "include_configs": True,
        "include_git_metadata": True,
        "include_local_vpn_roots": True,
        "description": "Safe mode plus extra local VPN config roots with redaction.",
    },
}


def mode_policy_for(mode: str) -> dict:
    try:
        return deepcopy(MODE_POLICIES[mode])
    except KeyError as exc:
        raise ValueError(f"unknown hostmap mode: {mode}") from exc
