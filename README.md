# hostmap

`hostmap` creates a read-only architecture and evidence map of a Linux host. It collects service, runtime, package, network, filesystem, deployment, and repository metadata into a reviewer bundle while excluding or redacting sensitive content. The project is alpha software. The generated bundle contract has `schema_version: "1.1"`.

Built by [Magrathean UK](https://magrathean.uk).

## What it collects

A safe run can include:

- operating system, kernel, systemd, package-manager, and language-runtime versions;
- systemd units, failed units, timers, sockets, listeners, processes, cron paths, and filesystem usage;
- Docker Compose through a detected local Docker socket and Podman through a detected local Podman socket;
- installed component probes for ingress, VPN, datastores, monitoring, and backup tools;
- bounded directory maps for selected host roots, with files omitted;
- redacted small configuration files from selected service directories;
- Git repository state, recent commit and remote metadata, CI files, deployment files, and selected declared dependencies;
- structured JSON inventories, Mermaid service graphs, review checklists, and archive quality evidence.

Presence is evidence about what was observed. It does not prove that a service, route, backup, firewall, or deployment is healthy or active. A missing collector, unavailable command, permission error, or excluded source is recorded as a gap or unknown where possible.

## Safety and data handling

Host collection is read-only and writes only the requested output bundle. It does not restart services, edit host configuration, install packages, change users or permissions, alter firewall rules, modify containers, or call external network APIs. It is an architecture and documentation tool, not a vulnerability scanner.

The collector excludes secret-looking paths, private keys, token files, credential stores, database files, browser profiles, caches, container stores, build outputs, binary files, and copied input text files larger than 512 KiB. Included small text is redacted for secret-like assignments, URLs with credentials, authorization values, and supported multiline secret blocks. Command output is collected separately and is not subject to the copied-input size limit. Directory maps list directory names only and are bounded by depth and entry limits.

Redaction lowers exposure but does not make a bundle public-safe. Bundles may still contain hostnames, paths, topology, service names, software versions, repository paths, and operational relationships. Review `bundle_qa.json`, `manifest.json`, and the generated files before sharing them outside the system owner's trust boundary.

The collector uses only local container sockets. It does not query remote Docker or Podman contexts, Kubernetes cluster APIs, or k3s cluster APIs. Kubernetes-related output includes `kubectl` client and `k3s` version commands plus local service-unit evidence. Unavailable commands, sockets, or paths remain unknown.

## Requirements

- Linux for host collection.
- Python 3.10 or newer.
- Permission to inspect the target machine's service and configuration metadata.

Root is not required for a basic run. Additional privileges can expose more inventory, so use the minimum needed and review the resulting bundle.

## Install and run

From a checkout, run the module directly:

```bash
python3 -m hostmap --output hostmap-output --mode safe
```

The package also exposes the `hostmap` console command after installation:

```bash
python3 -m pip install .
hostmap --output hostmap-output --mode safe
```

Collection creates a timestamped directory below the output root and, by default, a sibling ZIP archive. A conflicting timestamped bundle or archive is preserved and causes the run to stop. Use `--no-zip` for a directory-only bundle or `--max-zip-mb N` for a positive archive size limit in MiB.

The available modes are:

- `safe` (default): redacted small configs, repository metadata, CI, deployment, and dependency evidence;
- `paranoid`: versions, runtime snapshots, and directory maps without copied configs or Git metadata;
- `local`: safe mode plus additional local WireGuard and OpenVPN configuration roots, still redacted.

`--version` prints the package version. Help, version output, and offline diff work on non-Linux systems; host collection requires Linux.

## Bundle contents

Start review with:

- `manifest.json`, which records schema, mode policy, commands, files, skips, and redaction policy;
- `bundle_qa.json`, which records archive-open status and member-name and text-scan findings;
- `summary.md` and `review-pack/`, which provide orientation and reviewer checklists;
- `runtime/`, `containers/`, `apps/`, `ingress/`, `edge/`, and `operations/` for structured evidence;
- `graphs/services.mmd` for a reviewer aid derived from collected service and listener data.

Important structured files include `apps/services.json`, `edge/connectivity.json`, `ingress/routes.json`, `operations/backups.json`, `packages/installed.json`, and, in safe or local mode, `packages/declared.json`. `ingress/routes.json` is currently emitted as an empty route list. VPN default ports are recorded as hints only. Installed ingress tools are not treated as proof of routing. Mermaid graphs summarize evidence and do not replace the raw command outputs.

## Offline bundle diff

Compare two complete bundle directories without inspecting a live host:

```bash
python3 -m hostmap diff /path/to/before /path/to/after --output hostmap-diff
```

The output contains `diff.json` and `summary.md`. The diff reports added and removed manifest files, byte-level changes in files declared by each manifest, and changed manifest fields. Missing versus explicitly `null` fields are distinguished. The output directory must be outside both input bundles. Existing diff reports are never overwritten, and unsafe manifest paths, missing files, symlinks that resolve outside a bundle, and incomplete bundles are rejected. A diff identifies changes; it does not judge operational significance.

## Review prompts and skill

Reusable prompts are in [`docs/prompts.md`](docs/prompts.md). The Codex skill is in [`skills/hostmap/SKILL.md`](skills/hostmap/SKILL.md). After copying that skill into a supported skills directory, a user can ask:

```text
Use the hostmap skill to map this Linux machine safely for review.
```

## Development

The project uses the standard Python package layout and pytest. From a checkout:

```bash
python3 -m pip install . pytest
python3 -m pytest -q
python3 -m hostmap --mode paranoid --output /tmp/hostmap-smoke
```

The paranoid smoke command is intended for a Linux host because collection is Linux-only. It writes a new timestamped bundle below the output root. Existing bundles and archives remain intact.

## Project documents

- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Support](SUPPORT.md)
- [Licence and third-party notices](license.md)
- [MIT licence text](LICENSE)
- [Trademark notices](TRADEMARKS.md)

`hostmap` is copyright © 2026 Magrathean UK Ltd. and is licensed under the MIT Licence. See [`license.md`](license.md) for the project and dependency notice.
