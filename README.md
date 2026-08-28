# hostmap

`hostmap` creates a safe, read-only architecture and evidence map of a Linux host. It is intended for operators, reviewers, incident responders, and AI agents that need to understand how a machine is assembled without changing it or collecting raw secrets.

Built by [Magrathean UK](https://magrathean.uk). Current project status: **alpha**. The bundle contract is schema v1 (`schema_version: "1.0"`).

## Output

A run produces a timestamped directory containing Markdown, JSON, reviewer prompts, Mermaid diagrams, a manifest, and bundle-quality evidence. It can also create a ZIP archive for offline review.

Typical coverage includes:

- OS, kernel, package, and language/runtime versions;
- systemd services, timers, sockets, listeners, processes, cron, and filesystems;
- Docker, Docker Compose, Podman, Kubernetes, and k3s;
- nginx, Apache, Caddy, Traefik, HAProxy, Cloudflare Tunnel, and VPN tooling;
- Git repositories, CI definitions, deployment files, and declared dependencies;
- databases, queues, monitoring, logging, and backup tooling;
- directory-only filesystem maps with heavy and sensitive paths pruned;
- structured application, edge, backup, and package inventories;
- reviewer-friendly service and dependency diagrams.

## Safety model

`hostmap` is read-only. It does not restart services, edit files, install packages, change firewall rules, or call external network APIs. It is an architecture and documentation tool, not a vulnerability scanner.

Default collection excludes private keys, token files, databases, browser profiles, caches, container stores, build outputs, and large files. Small included configuration files are redacted line by line. The manifest records commands, collected files, skips, and mode policy.

Redaction reduces risk; it does not make an infrastructure inventory public-safe. Generated bundles may still reveal hostnames, topology, service names, software versions, paths, and operational relationships. Review every bundle before sharing it outside the system owner's trust boundary.

## Requirements

- Linux host.
- Python 3.10 or later.
- Permission to inspect the target machine and its service/configuration metadata.

Root is not required for the basic run. Additional privileges may expose more inventory; use only the minimum needed and review the resulting bundle accordingly.

## Install and run

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

- `safe` — default; includes redacted small configuration, deployment, and CI files.
- `paranoid` — versions, runtime snapshots, and directory maps only.
- `local` — safe mode plus additional local VPN configuration roots, still redacted.

The generated archive is named like:

```text
hostmap-output/2026-05-20-120000.zip
```

## Bundle contract

Important paths include:

- `manifest.json` — schema version, mode policy, files, commands, and skips;
- `bundle_qa.json` — archive-open and redaction-scan checks;
- `review-pack/` — agent context and reviewer role checklists;
- `apps/services.json` — discovered application and service inventory;
- `edge/connectivity.json` — ingress, proxy, tunnel, and VPN evidence;
- `operations/backups.json` — observed backup tooling and configuration evidence;
- `packages/installed.json` and `packages/declared.json` — package evidence;
- `graphs/services.mmd` — Mermaid service graph.

Presence is evidence, not proof of health. A configured service, backup, firewall, or deployment path may still be stale or broken and must be validated on the target host.

## Offline diff

Compare two existing bundles without touching a live host:

```bash
python3 -m hostmap diff /path/to/before /path/to/after --output hostmap-diff
```

## Reviewer prompts and Codex skill

Reusable review prompts live in [`docs/prompts.md`](docs/prompts.md). The Codex skill lives at [`skills/hostmap/SKILL.md`](skills/hostmap/SKILL.md).

After copying `skills/hostmap` into a Codex skills directory, a user can ask:

```text
Use the hostmap skill to map this Linux machine safely for review.
```

## Development

```bash
python3 -m pip install . pytest
python3 -m pytest -q
python3 -m hostmap --mode paranoid --output /tmp/hostmap-smoke
```

## Security and licence

Report security issues through [`SECURITY.md`](./SECURITY.md). `hostmap` is licensed under the [MIT Licence](./LICENSE). Third-party notices are in [`license.md`](./license.md), and trade mark notices are in [`TRADEMARKS.md`](./TRADEMARKS.md).
