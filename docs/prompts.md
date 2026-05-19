# Hostmap Prompts

## Generate A Local System Map

```text
Use the Linux system architecture mapping skill on this machine.

Goal: create a safe, shareable architecture map of this Linux host for review.

Rules:
- Do not change services, configs, packages, firewall rules, users, permissions, or running containers.
- Read-only inspection only.
- Do not collect secrets, private keys, tokens, passwords, database files, browser profiles, SSH material, or credential stores.
- Redact secret-looking values from any small config files that are included.
- Exclude heavy/generated trees such as `.git`, `node_modules`, `.venv`, `target`, Docker/containerd storage, journals, caches, databases, backups, and build artifacts unless only listing their directory names is safe.
- Clearly separate confirmed facts from inference and from items that need manual verification.

Please map this system broadly, even if some services are not installed. Check for common Linux architecture components including:
- systemd services, timers, sockets, paths
- cron/anacron
- running processes and listeners
- nginx, Apache, Caddy, Traefik, HAProxy
- Cloudflare Tunnel, Tailscale, WireGuard, OpenVPN, ZeroTier
- Docker, Docker Compose, Podman, containerd, Kubernetes, k3s, microk8s
- Git repositories and CI files such as GitHub Actions, GitLab CI, Forgejo/Gitea workflows
- deployment scripts and service unit files
- databases such as Postgres, MySQL/MariaDB, Redis, MongoDB, SQLite locations
- queues such as RabbitMQ, Kafka, NATS, Redis queues
- monitoring/logging such as Prometheus, Grafana, Loki, Monit, Netdata, Uptime Kuma, Telegraf
- backup tooling such as Borg, Restic, rclone, rsnapshot, database dump jobs
- package/language/runtime versions: OS, kernel, systemd, Docker, Python, Node, npm, Go, Rust, Java, PHP, Ruby, .NET where present

Create a local output folder named:

`hostmap-output/YYYY-MM-DD-HHMM/`

Inside it, generate markdown and JSON files such as:
- `README.md`
- `summary.md`
- `manifest.json`
- `redaction-report.md`
- `filesystem/`
- `runtime/`
- `ingress/`
- `containers/`
- `apps/`
- `data/`
- `operations/`
- `versions/`
- `recommendations.md`

Also create a compressed reviewer archive:

`hostmap-output/YYYY-MM-DD-HHMM.zip`

Keep the archive below 500MB.

After generating it:
1. Verify the archive opens successfully.
2. Scan archive member names for obvious secret/heavy paths.
3. Scan included text for unredacted secret-looking assignments.
4. Report the final archive path, size, included sections, exclusions, and anything that could not be read due to permissions.

Do not delete the generated output unless I explicitly ask.
```

## Improve The Public Skill From A Local Bundle

```text
Update the Linux system architecture mapping skill to support this machine better.

I have generated a hostmap output bundle from my Linux machine. Review the output and identify any services, runtimes, deployment systems, CI systems, proxies, databases, monitoring tools, or backup tools that were present but not properly recognized.

Do not add my machine-specific hostnames, domains, paths, secrets, or private architecture facts into the public skill.

Instead, improve the generic skill/collector so it can detect this class of system on any Linux host.

For each improvement:
- explain the generic pattern being added
- list the commands/files checked
- keep collection read-only
- add redaction rules if needed
- add tests or sample fixtures where practical
- update the generated markdown sections/templates if the new detector needs its own output

Keep the public skill generic and safe. Machine-specific facts belong only in generated hostmap output, not in the skill.
```
