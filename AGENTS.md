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

## Working guidance — GPT-6 Astra

Based on [OpenAI's Astra prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices), reviewed 2026-09-19. These are working instructions, not a change to model or API settings.

- Complete the authorized task through implementation and relevant verification. Make routine choices yourself; ask only when a missing decision materially changes the result or requires new authority. Prepare reviewable work before requesting any necessary final approval.
- Current user instructions take precedence over repository and skill guidance within system and tool constraints. Preserve explicit exclusions and owner holds. Historical plans and session notes do not grant current authorization. If a file or skill blocks progress, identify its exact path and rule.
- Keep changes small and practical. Inspect current source and Git status, preserve unrelated work, and use existing conventions. Do not add speculative abstractions, dependencies, or unrelated cleanup. Commit, push, deploy, install, and live-service changes require authorization for that action.
- Use the reasoning effort the task needs. Follow explicit project delegation rules; otherwise use subagents only when requested, with bounded independent tasks and distinct file ownership. Batch independent reads; serialize dependent operations and conflicting edits.
- Run meaningful checks for the changed behavior and required project gates. Avoid tests that merely repeat low-impact edits. Broaden or repeat verification only after changes, failures, or unresolved concerns. Distinguish local checks from device, browser, and live-service evidence.
- Write concise, plain, outcome-first updates. State what changed, why, verification, and material gaps. Avoid filler and unnecessary formatting.
- Keep durable instructions in AGENTS.md and maintained product documentation. Do not create duplicate assistant instruction files or disposable plans, transcripts, status reports, and screenshots in source directories unless requested. Preserve source, tests, fixtures, assets, licences, and operational evidence regardless of who created them.
