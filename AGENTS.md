# Hostmap project context

Hostmap is a Python CLI for Linux host inventories and offline bundle comparison. Its supported Python version is 3.10 or newer. [CONTRIBUTING.md](.github/CONTRIBUTING.md) describes setup and checks; [README.md](README.md) describes the user contract.

## Collection model

Host collection reads local evidence and writes bundle output. Docker and Podman collection uses existing local sockets; Kubernetes evidence comes from local files. Exclusions, text redaction and bundle QA are implemented by `hostmap/redaction.py` and `hostmap/collect.py`.

Bundles, archives and diff reports are generated artefacts. Fixtures and live Linux host checks cover different execution environments. A clean redaction or QA result describes the checks performed on a bundle rather than its publication status.

## Change map

| Area | Source | Validation |
| --- | --- | --- |
| CLI and modes | `hostmap/cli.py`, `hostmap/schema.py` | `tests/test_cli.py`, `tests/test_bundle_contract.py` |
| Collection and output | `hostmap/collect.py` | `tests/test_collect.py`, `tests/test_collect_structured.py`, `tests/test_bundle_contract.py` |
| Exclusions and secrets | `hostmap/redaction.py`, QA in `hostmap/collect.py` | `tests/test_redaction.py`, `tests/test_bundle_contract.py` |
| Structured evidence and review | `hostmap/parsers.py`, `hostmap/review_pack.py` | `tests/test_parsers.py`, `tests/test_review_pack.py` |
| Offline comparison | `hostmap/diffing.py` | `tests/test_diff.py`, `tests/test_cli.py` |

## Command and documentation references

```bash
python3 -m pytest -q
```

[CONTRIBUTING.md](.github/CONTRIBUTING.md) includes the Linux paranoid smoke and archive checks. `tests/test_docs_contract.py` covers documentation references. Bundle-contract documentation spans `hostmap/schema.py`, the tests, [README.md](README.md), [review prompts](docs/prompts.md) and the [Hostmap skill](skills/hostmap/SKILL.md).

The evidence model distinguishes observations, hints and unknowns. Default VPN ports alone are insufficient evidence for a service; co-present proxies are insufficient evidence for a route. [CLAUDE.md](CLAUDE.md) imports this project context.
