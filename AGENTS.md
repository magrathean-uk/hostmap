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

<!-- clean-development-policy:v2 (canonical text: ~/dev/source/dev-bootstrap/snippets/clean-development-policy.md) -->
## Clean development (mandatory)

This project follows [Clean Development](https://github.com/magrathean-uk/clean-development) and the machine rule that nothing creates tool state under `~` (only the allow-listed agent homes).

- Load `~/dev/machine/env.zsh`; `~/.zshenv` does this for every zsh. Machine storage preferences live in `~/dev/machine/storage.conf`; workspace navigation is in `~/dev/START-HERE.md`.
- New sessions select `/Volumes/4TB/machine/cache` when the configured volume is actually mounted and writable, otherwise `~/dev/machine/cache` for ordinary smaller work. Use routed `DEVCACHE`, `CLEAN_DEVELOPMENT_{ROOT,CACHE_ROOT,BUILD_ROOT,SCRATCH_ROOT}`, `BOLYKI_DEV_LIBS` and `TMPDIR`; builds and scratch are beneath the selected cache. Keep active-session destinations fixed; stop if required storage disappears. Other users configure their own volume and fallback.
- SpecieX, large video/model jobs and VMs require external storage; never use internal fallback. Persistent labs, credentials, installed toolchains, source and final deliverables are not disposable caches.
- All active Git entry points belong under `~/dev/source/`, third-party repositories in `source/third-party/`, websites in `source/magrathean/`, and Teslatlas products/docs in `source/teslatlas-service/`. Do not read, scan, move or edit `~/dev/porn`.
- Preserve routed tool homes/caches, caller overrides and SDK/toolchain choices. Never unset or bypass routing. Scrubbed environments must restore the reviewed routing before cache-writing tools run; preserve intentional hermetic Git/Cargo isolation.
- Run builds, tests, installs and anything else that writes caches or build output through Clean Development: `clean-development run --session session-only -- <command>`. Follow its docs and keep its receipts.
- Do not add installers or scripts that default into `~` (`~/.cargo`, `~/.rustup`, `~/.cache`, `~/.npm`, `~/.swiftpm`, `~/.gradle`, ...) and do not hardcode `$HOME` paths for caches; use the routed variables.
- Before finishing, run `dev-env-check`, `dev-projects-check` and `dev-audit`; require passing environment/project checks and no new home-audit entries compared with the task baseline. Fix violations your work caused.

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
