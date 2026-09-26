---
name: hostmap
description: Safely map a Linux host architecture for review. Use when a user wants read-only discovery of systemd, containers, ingress, CI/deploy files, runtimes, monitoring, backups, filesystem layout, or a shareable redacted reviewer bundle.
---

# Hostmap

Use this skill to create or review a safe architecture map of a Linux host.

## Rules

- Read-only inspection only.
- Do not restart services, edit configs, install packages, change users, alter firewall rules, or modify containers.
- Do not collect secrets, private keys, token files, passwords, database files, browser profiles, SSH material, or credential stores.
- Redact secret-looking values from any included small config files.
- Separate confirmed facts from inference and from items that need manual verification.
- Use existing local container sockets only; do not query remote container contexts or Kubernetes cluster APIs.
- Preserve existing output directories and archives; select a new output location if a run would collide.

## Preferred Tool

If the `hostmap` CLI is available, run:

```bash
hostmap --output hostmap-output --mode safe
```

If it is not installed but this repository is present, run:

```bash
python3 -m hostmap --output hostmap-output --mode safe
```

For highly sensitive environments, use:

```bash
hostmap --output hostmap-output --mode paranoid
```

## What To Inspect

Check broad Linux architecture surfaces, even if some are absent:

- systemd units, timers, sockets, paths
- cron/anacron
- running processes and network listeners
- nginx, Apache, Caddy, Traefik, HAProxy
- Cloudflare Tunnel, Tailscale, WireGuard, OpenVPN, ZeroTier
- Docker, Docker Compose, Podman, containerd, Kubernetes, k3s, microk8s
- Git repositories and CI files
- deployment scripts and service unit files
- Postgres, MySQL/MariaDB, Redis, MongoDB, SQLite locations
- RabbitMQ, Kafka, NATS, Redis queues
- Prometheus, Grafana, Loki, Monit, Netdata, Uptime Kuma, Telegraf
- Borg, Restic, rclone, rsnapshot, database dump jobs
- OS, package, and language runtime versions

## Output Review

After generating a bundle:

1. Verify the archive opens successfully.
2. Scan member names for obvious secret/heavy paths.
3. Scan included text for unredacted secret-looking assignments.
4. Report final archive path, size, included sections, exclusions, and unreadable paths.

Review from structured outputs first:

- `manifest.json` and `bundle_qa.json`
- `review-pack/checklists.json`
- `apps/services.json`, `edge/connectivity.json`, `operations/backups.json`
- Mermaid diagrams under `graphs/`

Schema v1.1 records each generated file once. Check final archive QA and treat default VPN ports as hints, not confirmed services. Co-present ingress services do not establish a route. Filesystem walks are bounded, and unavailable sockets or skipped cluster queries leave unknowns.

Use Mermaid service graphs as reviewer aids only; they summarize collected facts and do not replace raw evidence.

Do not delete generated output unless the user asks.

For offline comparison, run `hostmap diff BEFORE AFTER --output NEW_OUTPUT` with complete bundle directories and output outside both inputs. Review `added_files`, `removed_files`, `changed_files` (byte changes), and manifest `changed_fields`. Existing diff reports are preserved. Diff works on non-Linux systems too.

## Updating This Skill

Do not add a user's hostnames, domains, private paths, or architecture facts to
the public skill. Improve generic detectors and redaction rules only. Machine
facts belong in generated hostmap output.
