# Contributing to Hostmap

Keep changes focused on Linux inventory collection, redaction, bundle review, or offline comparison. Use synthetic fixtures when adding a detector or parser. A real host bundle may contain private infrastructure details even after redaction.

## Development setup

From a checkout, with Python 3.10 or newer:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install . pytest
python3 -m pytest -q
```

The `hostmap` package has no declared runtime dependencies. Setuptools and wheel are build requirements; pytest is needed for tests. Source-checkout commands use `python3 -m hostmap`.

Consider [Clean Development](https://github.com/magrathean-uk/clean-development) to keep supported development caches and build output organized.

## Verify a change

Run the test suite for code changes. [AGENTS.md](../AGENTS.md) maps modules to focused tests. For a docs-only change, review links and examples and run:

```sh
python3 -m pytest -q tests/test_docs_contract.py
```

Collection, CLI routing, bundling, and redaction changes also need a smoke run on an authorized Linux host:

```sh
python3 -m hostmap --mode paranoid --output /tmp/hostmap-smoke
```

This inspects that host and writes a timestamped bundle and ZIP. Use the exact new paths printed by the command. Check `manifest.json` and `bundle_qa.json`, open the ZIP, and confirm that its member list matches the manifest. Review the archive member names and text findings before sharing anything. Existing output paths must remain intact.

Exercise offline comparison with complete bundle directories and a fresh report location:

```sh
python3 -m hostmap diff /path/to/before /path/to/after --output /tmp/hostmap-diff
```

For a same-bundle smoke test, pass the same bundle as both inputs and expect no added, removed, or changed files and no changed manifest fields. Diff output must be outside both inputs.

The existing [CI workflow](workflows/ci.yml) runs tests on Python 3.10 and 3.14 and checks a Linux paranoid bundle and same-bundle diff. The [dependency audit workflow](workflows/dependency-audit.yml) runs pip-audit on its installed environment. These describe configured checks, not a guarantee that a particular revision passed.

## Scope and review

- Keep collection read-only apart from output. Do not add remote API calls, telemetry, automatic package installation, or service changes.
- Keep secrets and machine-specific evidence out of commits, issues, and pull requests. See [SECURITY.md](SECURITY.md) for security reports.
- Test exclusions and redaction when adding collection roots or formats. Keep missing tools, permissions, and collection limits visible as gaps.
- Update the schema, tests, README, prompts, and skill together when changing the bundle contract.
- Describe the problem, the resulting behavior, and checks run in a pull request. State any skipped checks and why they were skipped.

Preserve existing copyright and third-party notices. See [licensing and attribution](../docs/legal/third-party-notices.md) and the complete [MIT licence](../LICENSE).
