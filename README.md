# hostmap

`hostmap` creates a safe, read-only architecture map of a Linux host. It is for
reviewers, operators, and AI agents that need evidence about how a machine is
put together without collecting secrets or changing the system.

It generates Markdown plus JSON, then optionally zips the result.

Current bundle contract is schema v1 (`schema_version: "1.0"`).

## What It Maps

- OS, kernel, package, and language/runtime versions
- systemd services, timers, sockets, listeners, processes, cron, filesystems
- Docker, Docker Compose, Podman, Kubernetes, k3s
- nginx, Apache, Caddy, Traefik, HAProxy, Cloudflare Tunnel, VPN tools
- Git repositories, GitHub/GitLab/Gitea/Forgejo CI files, deploy files
- databases, queues, monitoring, logging, and backup tool presence
- directory-only filesystem maps with heavy and secret paths pruned
- structured app, edge, backup, and package inventories
- Mermaid diagrams for reviewer-friendly service maps

## Safety Model

`hostmap` is read-only. It does not restart services, edit files, install
packages, change firewall rules, or make network API calls.

It is an architecture/documentation tool, not a vulnerability scanner.

By default it excludes secret paths, private keys, token files, databases,
browser profiles, caches, Docker/containerd stores, build outputs, and large
files. Small included config files are redacted line by line.

## Install And Run

From a checkout:

```bash
python3 -m hostmap --output hostmap-output --mode safe
```

Or install locally:

```bash
python3 -m pip install .
hostmap --output hostmap-output --mode safe
```

Modes:

- `safe`: default; includes redacted small config/deploy/CI files
- `paranoid`: versions, runtime snapshots, and directory maps only
- `local`: safe mode plus extra local VPN config roots with redaction

Bundle highlights:

- `manifest.json` with `schema_version`, mode policy, files, commands, skips
- `bundle_qa.json` with zip-open and redaction scan checks
- `review-pack/` with agent context and role checklists
- `apps/services.json`, `edge/connectivity.json`, `operations/backups.json`
- `packages/installed.json` and `packages/declared.json`
- `graphs/services.mmd` Mermaid graph

The generated archive is named like:

```text
hostmap-output/2026-05-20-120000.zip
```

## AI Reviewer Prompt

See [docs/prompts.md](docs/prompts.md) for prompts users can give to GPT-5.5
Pro, Codex, or another reviewer agent.

## Offline Diff

Compare two existing bundles without touching a live host:

```bash
python3 -m hostmap diff /path/to/before /path/to/after --output hostmap-diff
```

## Codex Skill

The reusable skill lives at [skills/hostmap/SKILL.md](skills/hostmap/SKILL.md).
Users can copy `skills/hostmap` into their Codex skills directory and ask:

```text
Use the hostmap skill to map this Linux machine safely for review.
```

## Development

```bash
python3 -m pytest -q
python3 -m hostmap --mode paranoid --output /tmp/hostmap-smoke
```
