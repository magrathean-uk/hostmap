# Working on Hostmap

Hostmap is a Python CLI for Linux host inventories and offline bundle comparison. Use Python 3.10 or newer. See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for setup and checks, and [README.md](README.md) for the user contract.

Carry authorized work through its relevant checks and make routine local development decisions without repeated confirmation. Use bounded delegation for independent tasks when it helps, with clear file ownership.

## Boundaries

- Inspect Git status before editing and preserve unrelated work.
- Keep host collection read-only apart from its output files. Do not add package installation, service changes, firewall changes, telemetry, remote container contexts, or network API queries to the collector.
- During collection, use existing local Docker and Podman sockets. Kubernetes evidence stays local; do not query cluster APIs.
- Exclude sensitive paths and redact included text. Never treat redaction or a clean QA report as permission to publish a bundle.
- Keep real hostnames, domains, private paths, credentials, and infrastructure details out of public docs, skills, tests, and fixtures. Use synthetic examples.
- Preserve existing bundles, archives, and diff reports. Keep generated output and caches out of source changes.
- Legal files (`LICENSE`, `NOTICE`, `docs/legal/`, contributor terms, copyright and attribution strings) are owner-controlled: change them only on the owner's explicit instruction.

## Change map

| Area | Source | Validation |
| --- | --- | --- |
| CLI and modes | `hostmap/cli.py`, `hostmap/schema.py` | `tests/test_cli.py`, `tests/test_bundle_contract.py` |
| Collection and output | `hostmap/collect.py` | `tests/test_collect.py`, `tests/test_collect_structured.py`, `tests/test_bundle_contract.py` |
| Exclusions and secrets | `hostmap/redaction.py`, QA in `hostmap/collect.py` | `tests/test_redaction.py`, `tests/test_bundle_contract.py` |
| Structured evidence and review | `hostmap/parsers.py`, `hostmap/review_pack.py` | `tests/test_parsers.py`, `tests/test_review_pack.py` |
| Offline comparison | `hostmap/diffing.py` | `tests/test_diff.py`, `tests/test_cli.py` |

Run `python3 -m pytest -q` for code changes. For collection, CLI routing, bundling, or redaction changes, also run the Linux paranoid smoke and archive checks in [CONTRIBUTING.md](.github/CONTRIBUTING.md). Use an authorized Linux host and report skipped checks plainly. Do not equate fixture tests with live host coverage.

When the bundle contract changes, reconcile `hostmap/schema.py`, tests, [README.md](README.md), [review prompts](docs/prompts.md), and the [Hostmap skill](skills/hostmap/SKILL.md). Preserve the distinction between observations, hints, and unknowns. Default VPN ports do not establish a service, and co-present proxies do not establish a route.

For documentation changes, check relative links, command flags, schema references, and `tests/test_docs_contract.py`. Keep guidance here; [CLAUDE.md](CLAUDE.md) imports it. Complete the relevant checks and state what was actually verified.
