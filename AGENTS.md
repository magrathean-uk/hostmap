# Hostmap Agent Guide

Read `README.md`, `docs/prompts.md`, and `skills/hostmap/SKILL.md` before
changing the related contract.

## Repo map

- `hostmap/cli.py`: command parsing and subcommand routing.
- `hostmap/collect.py`: safe host collection and bundle assembly.
- `hostmap/redaction.py`: secret and sensitive-path filtering.
- `hostmap/schema.py`: bundle contract.
- `hostmap/parsers.py`: structured command-output parsing and graphs.
- `hostmap/diffing.py`: offline bundle comparison.
- `hostmap/review_pack.py`: reviewer artifacts and bundle QA.
- `tests/`: contract, collector, diff, docs, and redaction coverage.

## Rules

- Inspect `git status --short` first and preserve unrelated work.
- Keep collection read-only. Do not install software, edit host state, restart
  services, change firewall rules, or make network API calls.
- Default to safe exclusion and redaction when evidence may contain secrets.
- Keep machine-specific facts in generated bundles, never in the public skill.
- Treat `.venv/`, `.pytest_cache/`, `hostmap-output/`, diff output, and archives
  as generated or local state.
- Update README, prompts, skill guidance, schemas, and tests together when the
  bundle contract changes.
- Keep diagnostics local. Do not add telemetry.

## Verify

```sh
python3 -m pytest -q
# Linux host or CI:
python3 -m hostmap --mode paranoid --output /tmp/hostmap-smoke
python3 -m hostmap diff /path/to/before /path/to/after --output /tmp/hostmap-diff
```

Use Python 3.10 or newer. Run the test suite for normal changes. Run the
paranoid smoke on Linux when collection, CLI routing, bundling, or redaction
changes; it maps the current host and is the CI smoke lane. Report any skipped
check and its blocker.
