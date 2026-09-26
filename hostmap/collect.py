from __future__ import annotations

import datetime as dt
import json
import os
import platform
import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .parsers import (
    parse_compose_projects,
    parse_go_mod_dependencies,
    parse_package_json,
    parse_pyproject_dependencies,
    parse_ss_listeners,
    parse_systemd_timers,
    parse_systemd_units,
    parse_tabular_packages,
    render_service_graph,
)
from .redaction import read_small_text, redact_text, should_prune_dir
from .review_pack import build_agent_context, build_review_checklists
from .schema import SCHEMA_VERSION, mode_policy_for


CONFIG_NAME_RE = re.compile(
    r"(?i)(^Dockerfile$|^Containerfile$|^Makefile$|^Procfile$|^Caddyfile$|"
    r"\.(ya?ml|toml|json|ini|conf|cfg|service|timer|socket|path|target|sources)$|"
    r"docker-compose.*|compose.*|package\.json|Cargo\.toml|go\.mod|pyproject\.toml|"
    r"requirements.*|Gemfile|composer\.json|pom\.xml|build\.gradle|nginx.*|haproxy.*)"
)

DEPLOY_FILE_RE = re.compile(
    r"(?i)(deploy|release|service|timer|compose|docker|container|procfile|makefile|"
    r"requirements|pyproject|package|cargo|go\.mod|pom\.xml|build\.gradle)"
)

SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (?:^|[,{\s])(?:export\s+)?
    ["']?(?:
        password|passwd|pass|secret|token|credential|authorization|api[_-]?key|
        private[_-]?key|client[_-]?secret|access[_-]?key|tunnel[_-]?token|
        github_token|gitlab_token|cf_api|aws_.*key|b2_.*key|mysql_pwd|pgpassword|
        privatekey|[a-z0-9_.-]*(?:token|secret|password|credential|api[_-]?key)[a-z0-9_.-]*
    )["']?\s*[=:]\s*
    (?P<value>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^,\s#}\]]+)
    """
)
URL_CREDENTIAL_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://(?!REDACTED@)[^/\s@]+@")
AUTH_CREDENTIAL_RE = re.compile(r"(?i)\b(?:bearer|basic)\s+(?!REDACTED\b)[A-Za-z0-9._~+/=-]+")
PEM_PRIVATE_KEY_RE = re.compile(r"(?i)-----BEGIN [^-]*PRIVATE KEY-----")

MAX_DIRECTORY_MAP_DEPTH = 5
MAX_DIRECTORY_MAP_ENTRIES = 10_000
MAX_CONFIG_DEPTH = 5
MAX_CI_DEPTH = 4


@dataclass
class HostmapOptions:
    output_root: Path
    mode: str = "safe"
    max_zip_mb: int = 500
    create_zip: bool = True
    timestamp: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d-%H%M%S"))


@dataclass
class HostmapResult:
    output_dir: Path
    zip_path: Path | None
    manifest: dict


class HostMapper:
    def __init__(self, options: HostmapOptions) -> None:
        self.options = options
        self.output_dir = options.output_root / options.timestamp
        self.mode_policy = mode_policy_for(options.mode)
        self.manifest: dict = {
            "schema_version": SCHEMA_VERSION,
            "hostmap_version": __version__,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "mode": options.mode,
            "mode_policy": self.mode_policy,
            "hostname": platform.node(),
            "files": [],
            "commands": [],
            "skipped": [],
            "redaction": {
                "secret_paths_excluded": True,
                "secret_like_lines_redacted": True,
                "binary_files_excluded": True,
                "max_text_file_bytes": 512 * 1024,
            },
        }

    def run(self) -> HostmapResult:
        if self.output_dir.exists() or self.output_dir.is_symlink():
            raise FileExistsError(f"refusing to replace existing output directory: {self.output_dir}")
        zip_path = self.options.output_root / f"{self.options.timestamp}.zip"
        if self.options.create_zip and (zip_path.exists() or zip_path.is_symlink()):
            raise FileExistsError(f"refusing to replace existing archive: {zip_path}")
        self.output_dir.mkdir(parents=True)
        self.write_text("README.md", self.readme())
        self.write_text("redaction-report.md", self.redaction_report())
        self.collect_versions()
        self.collect_runtime()
        self.collect_filesystem_maps()
        self.collect_tool_matrices()
        if self.mode_policy["include_configs"]:
            self.collect_configs()
        if self.mode_policy["include_git_metadata"]:
            self.collect_git_and_ci()
        self.write_review_pack()
        self.write_text("recommendations.md", self.recommendations())
        self.reserve_output_files()
        self.write_text("summary.md", self.summary())
        self.write_json("manifest.json", self.manifest)
        zip_path: Path | None = None
        self.write_bundle_qa(None)
        if self.options.create_zip:
            try:
                zip_path = self.build_zip()
                self.write_bundle_qa(zip_path)
                zip_path = self.build_zip(replace_existing=True)
            except BaseException:
                archive_path = self.options.output_root / f"{self.options.timestamp}.zip"
                if zip_path is not None and archive_path.is_file() and not archive_path.is_symlink():
                    archive_path.unlink()
                raise
        self.write_bundle_qa(zip_path)
        return HostmapResult(self.output_dir, zip_path, self.manifest)

    def reserve_output_files(self) -> None:
        files = ["bundle_qa.json", "manifest.json", "summary.md"]
        if self.options.create_zip:
            files.append("ARCHIVE_SIZE.txt")
        for rel in files:
            if rel not in self.manifest["files"]:
                self.manifest["files"].append(rel)

    def write_text(self, rel: str, text: str) -> None:
        dest = self.output_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8", errors="replace")
        if rel not in self.manifest["files"]:
            self.manifest["files"].append(rel)

    def write_json(self, rel: str, data: object) -> None:
        self.write_text(rel, json.dumps(data, indent=2, sort_keys=True) + "\n")

    def run_command(self, name: str, cmd: str, timeout: int = 60) -> str:
        self.manifest["commands"].append({"name": name, "command": cmd})
        try:
            output = subprocess.check_output(
                ["bash", "--noprofile", "--norc", "-c", cmd],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                env=self.command_environment(),
            )
        except subprocess.CalledProcessError as exc:
            output = exc.output
        except subprocess.TimeoutExpired:
            output = f"[command timed out after {timeout} seconds]\n"
        except Exception as exc:
            output = f"[command failed: {exc}]\n"
        return redact_text(output)

    def command_succeeds(self, name: str, cmd: str, timeout: int = 30) -> bool:
        self.manifest["commands"].append({"name": name, "command": cmd})
        try:
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                env=self.command_environment(),
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.manifest["skipped"].append({"command": name, "reason": f"timed out after {timeout} seconds"})
            return False
        except OSError as exc:
            self.manifest["skipped"].append({"command": name, "reason": str(exc)})
            return False
        return result.returncode == 0

    @staticmethod
    def command_environment() -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                "DOTNET_NOLOGO": "1",
                "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
                "GOTOOLCHAIN": "local",
                "LC_ALL": "C",
                "RUSTUP_AUTO_INSTALL": "0",
            }
        )
        for name in ("BASH_ENV", "CONTAINER_CONNECTION", "CONTAINER_HOST", "DOCKER_CONTEXT", "DOCKER_HOST", "ENV", "KUBECONFIG"):
            env.pop(name, None)
        for name in tuple(env):
            if name.startswith("BASH_FUNC_"):
                env.pop(name)
        return env

    def collect_versions(self) -> None:
        commands = [
            ("hostnamectl", "hostnamectl 2>&1 || true"),
            ("uname", "uname -a"),
            ("os-release", "cat /etc/os-release 2>/dev/null || true"),
            ("systemd", "systemctl --version 2>&1 | sed -n '1,5p' || true"),
            ("docker", "docker --version 2>&1 || true"),
            ("docker-compose", "docker compose version 2>&1 || docker-compose --version 2>&1 || true"),
            ("podman", "podman --version 2>&1 || true"),
            ("kubectl", "kubectl version --client 2>&1 || true"),
            ("k3s", "k3s --version 2>&1 || true"),
            ("nginx", "nginx -v 2>&1 || true"),
            ("apache", "apache2 -v 2>&1 || httpd -v 2>&1 || true"),
            ("caddy", "caddy version 2>&1 || true"),
            ("traefik", "traefik version 2>&1 || true"),
            ("haproxy", "haproxy -v 2>&1 | head -5 || true"),
            ("cloudflared", "cloudflared --version 2>&1 || true"),
            ("tailscale", "tailscale version 2>&1 || true"),
            ("git", "git --version 2>&1 || true"),
            ("python", "python3 --version 2>&1 || true"),
            ("node", "node --version 2>&1 || true"),
            ("npm", "npm --version 2>&1 || true"),
            ("go", "go version 2>&1 || true"),
            ("rust", "rustc --version 2>&1 || true"),
            ("java", "java -version 2>&1 | head -5 || true"),
            ("php", "php -v 2>&1 | head -5 || true"),
            ("ruby", "ruby --version 2>&1 || true"),
            ("dotnet", "dotnet --info 2>&1 | sed -n '1,25p' || true"),
        ]
        body = []
        for name, cmd in commands:
            body.append(f"$ {cmd}\n{self.run_command(name, cmd, timeout=30)}\n")
        self.write_text("versions/core-tools.txt", "".join(body))
        package_cmds = [
            "dpkg-query -W -f='${Package}\\t${Version}\\n' 2>/dev/null | sort || true",
            "rpm -qa --qf '%{NAME}\\t%{VERSION}-%{RELEASE}\\n' 2>/dev/null | sort || true",
            "pacman -Q 2>/dev/null | sort || true",
        ]
        package_outputs = [self.run_command("packages", cmd, timeout=120) for cmd in package_cmds]
        self.write_text("versions/packages.txt", "\n".join(f"$ {cmd}\n{output}" for cmd, output in zip(package_cmds, package_outputs)))
        installed_packages = parse_tabular_packages("\n".join(package_outputs))
        self.write_json("packages/installed.json", installed_packages)

    def collect_runtime(self) -> None:
        commands = {
            "runtime/systemd-failed.txt": "systemctl --no-pager --failed 2>&1 || true",
            "runtime/systemd-units.txt": "systemctl --no-pager list-units --all 2>&1 || true",
            "runtime/systemd-timers.txt": "systemctl --no-pager list-timers --all 2>&1 || true",
            "runtime/systemd-sockets.txt": "systemctl --no-pager list-sockets --all 2>&1 || true",
            "runtime/listeners.txt": "ss -tulpen 2>&1 || ss -tuln 2>&1 || true",
            "runtime/processes.txt": "ps -eo pid,ppid,user,stat,comm --sort=comm 2>&1 || true",
            "runtime/cron.txt": "find /etc/cron.d /etc/cron.daily /etc/cron.hourly /etc/cron.monthly /etc/cron.weekly -maxdepth 2 -type f -print 2>/dev/null | sort || true",
            "runtime/filesystems.txt": "df -hT 2>&1 && printf '\\n' && findmnt -D -o SOURCE,FSTYPE,SIZE,USED,AVAIL,USE%,TARGET 2>&1 || true",
            "containers/docker.txt": self.docker_compose_command(),
            "containers/podman.txt": self.podman_command(),
            "containers/kubernetes.txt": "systemctl --no-pager list-unit-files 2>&1 | grep -Ei '(^|[-@.])(k3s|kubelet|microk8s)([-@.]|$)' || true",
        }
        outputs: dict[str, str] = {}
        for rel, cmd in commands.items():
            output = self.run_command(rel, cmd, timeout=120)
            outputs[rel] = output
            self.write_text(rel, f"$ {cmd}\n{output}")
        self.write_runtime_structures(outputs)

    @staticmethod
    def docker_compose_command() -> str:
        sockets = [
            Path("/var/run/docker.sock"),
            Path(f"/run/user/{os.getuid()}/docker.sock"),
        ]
        for socket in sockets:
            if socket.is_socket():
                return f"docker --host unix://{socket} compose ls --format json 2>&1 || true"
        return "printf '%s\\n' '[skipped: no local Docker socket found]'"

    @staticmethod
    def podman_command() -> str:
        sockets = [
            Path("/run/podman/podman.sock"),
            Path(f"/run/user/{os.getuid()}/podman/podman.sock"),
        ]
        for socket in sockets:
            if socket.is_socket():
                return f"podman --remote --url unix://{socket} ps --format 'table {{{{.Names}}}}\\t{{{{.Image}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}' 2>&1 || true"
        return "printf '%s\\n' '[skipped: no local Podman socket found]'"

    def collect_filesystem_maps(self) -> None:
        self.write_text(
            "filesystem/README.md",
            "# Filesystem Maps\n\nThese maps list directories only. Files are intentionally omitted.\n",
        )
        for root in ["/", "/etc", "/opt", "/srv", "/home", "/var", "/usr/local", "/root"]:
            path = Path(root)
            name = "root" if root == "/" else root.strip("/").replace("/", "-")
            self.write_text(f"filesystem/{name}-directories.txt", self.directory_map(path))

    def directory_map(self, root: Path) -> str:
        lines = [f"# Directory map for {root}\n", "# Files are intentionally omitted.\n"]
        if not root.exists():
            lines.append("[missing]\n")
            return "".join(lines)
        entries = 0
        truncated = False
        depth_limited = False
        try:
            def onerror(exc: OSError) -> None:
                lines.append(f"[unreadable: {exc}]\n")

            walker = os.walk(root, topdown=True, followlinks=False, onerror=onerror)
            for current, dirs, _files in walker:
                current_path = Path(current)
                dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
                depth = 0 if current_path == root else len(current_path.relative_to(root).parts)
                lines.append(f"{'  ' * depth}{current_path.name or str(current_path)}/\n")
                entries += 1
                if depth >= MAX_DIRECTORY_MAP_DEPTH:
                    depth_limited = depth_limited or bool(dirs)
                    dirs[:] = []
                if entries >= MAX_DIRECTORY_MAP_ENTRIES:
                    truncated = True
                    break
        except OSError as exc:
            lines.append(f"[unreadable: {exc}]\n")
        if truncated:
            lines.append(f"[truncated after {MAX_DIRECTORY_MAP_ENTRIES} directories]\n")
        if depth_limited:
            lines.append(f"[depth limited to {MAX_DIRECTORY_MAP_DEPTH} levels]\n")
        return "".join(lines)

    def collect_tool_matrices(self) -> None:
        checks = {
            "ingress/summary.md": [
                ("nginx", "command -v nginx || test -d /etc/nginx"),
                ("apache", "command -v apache2 || command -v httpd || test -d /etc/apache2 || test -d /etc/httpd"),
                ("caddy", "command -v caddy || test -d /etc/caddy"),
                ("traefik", "command -v traefik || test -d /etc/traefik"),
                ("haproxy", "command -v haproxy || test -d /etc/haproxy"),
                ("cloudflared", "command -v cloudflared || test -d /etc/cloudflared"),
                ("tailscale", "command -v tailscale || test -d /var/lib/tailscale"),
                ("wireguard", "command -v wg || test -d /etc/wireguard"),
                ("openvpn", "command -v openvpn || test -d /etc/openvpn"),
                ("zerotier", "command -v zerotier-cli || test -d /var/lib/zerotier-one"),
            ],
            "data/datastores.md": [
                ("postgres", "command -v psql || systemctl list-unit-files 2>/dev/null | grep -qi postgres"),
                ("mysql-mariadb", "command -v mysql || command -v mariadb || systemctl list-unit-files 2>/dev/null | grep -Eqi 'mysql|mariadb'"),
                ("redis", "command -v redis-cli || systemctl list-unit-files 2>/dev/null | grep -qi redis"),
                ("mongodb", "command -v mongosh || command -v mongo || systemctl list-unit-files 2>/dev/null | grep -qi mongo"),
                ("rabbitmq", "command -v rabbitmqctl || systemctl list-unit-files 2>/dev/null | grep -qi rabbitmq"),
                ("kafka", "command -v kafka-topics || systemctl list-unit-files 2>/dev/null | grep -qi kafka"),
                ("nats", "command -v nats || systemctl list-unit-files 2>/dev/null | grep -qi nats"),
            ],
            "operations/monitoring-backups.md": [
                ("prometheus", "command -v prometheus || test -d /etc/prometheus"),
                ("grafana", "command -v grafana-server || test -d /etc/grafana"),
                ("loki", "command -v loki || test -d /etc/loki"),
                ("monit", "command -v monit || test -d /etc/monit"),
                ("netdata", "command -v netdata || test -d /etc/netdata"),
                ("uptime-kuma", "systemctl list-unit-files 2>/dev/null | grep -qi uptime-kuma"),
                ("telegraf", "command -v telegraf || test -d /etc/telegraf"),
                ("borg", "command -v borg"),
                ("restic", "command -v restic"),
                ("rclone", "command -v rclone"),
                ("rsnapshot", "command -v rsnapshot || test -d /etc/rsnapshot"),
            ],
        }
        for rel, checks_for_file in checks.items():
            rows = ["| Component | Detected |\n", "|---|---:|\n"]
            for label, cmd in checks_for_file:
                found = self.command_succeeds(f"probe:{label}", cmd)
                rows.append(f"| `{label}` | {'yes' if found else 'no'} |\n")
            self.write_text(rel, "".join(rows))

    def collect_configs(self) -> None:
        config_roots = [
            "/etc/nginx",
            "/etc/apache2",
            "/etc/httpd",
            "/etc/caddy",
            "/etc/traefik",
            "/etc/haproxy",
            "/etc/cloudflared",
            "/etc/monit",
            "/etc/prometheus",
            "/etc/grafana",
            "/etc/telegraf",
            "/etc/logrotate.d",
            "/etc/apt/sources.list.d",
            "/etc/yum.repos.d",
        ]
        if self.options.mode == "local":
            config_roots.extend(["/etc/wireguard", "/etc/openvpn"])
        for root in config_roots:
            root_path = Path(root)
            if not root_path.exists():
                continue
            try:
                def onerror(exc: OSError) -> None:
                    self.manifest["skipped"].append({"path": str(exc.filename or root_path), "reason": str(exc)})

                for current, dirs, files in os.walk(root_path, topdown=True, followlinks=False, onerror=onerror):
                    current_path = Path(current)
                    dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
                    if len(current_path.relative_to(root_path).parts) >= MAX_CONFIG_DEPTH:
                        dirs[:] = []
                    for name in sorted(files):
                        path = current_path / name
                        if is_small_file(path) and CONFIG_NAME_RE.search(path.name):
                            self.copy_redacted(path, "config-files")
            except OSError as exc:
                self.manifest["skipped"].append({"path": str(root_path), "reason": str(exc)})

    def collect_git_and_ci(self) -> None:
        repos = self.find_git_repos()
        rows = ["| Repository | State | Last commit | Remote |\n", "|---|---|---|---|\n"]
        repo_entries: list[dict] = []
        declared_packages: list[dict] = []
        for repo in repos:
            qrepo = sh_quote(repo)
            state = self.run_command(
                "git-status",
                f"GIT_OPTIONAL_LOCKS=0 git --no-optional-locks -C {qrepo} -c core.fsmonitor=false -c core.untrackedCache=false status --short --branch 2>&1 | head -30",
                timeout=20,
            ).strip().replace("\n", "<br>")
            last = self.run_command("git-log", f"git -C {qrepo} log -1 --format='%H %ci %s' 2>&1", timeout=20).strip()
            remote = self.run_command("git-remote", f"git -C {qrepo} remote -v 2>&1", timeout=20).strip().replace("\n", "<br>")
            rows.append(f"| `{repo}` | {state} | {last} | {remote} |\n")
            ci_files = self.copy_ci_files(repo)
            deploy_files = self.copy_deploy_files(repo)
            package_manifests, packages = self.collect_declared_packages(repo)
            declared_packages.extend(packages)
            repo_entries.append(
                {
                    "path": str(repo),
                    "state": state,
                    "last_commit": last,
                    "remote": remote,
                    "ci_files": [str(path.relative_to(repo)) for path in ci_files],
                    "deploy_files": [str(path.relative_to(repo)) for path in deploy_files],
                    "package_manifests": [str(path.relative_to(repo)) for path in package_manifests],
                }
            )
        self.write_text("apps/repositories.md", "".join(rows))
        self.write_json("apps/repositories.json", repo_entries)
        self.write_json("packages/declared.json", declared_packages)

    def find_git_repos(self) -> list[Path]:
        roots = self.git_search_roots()
        repos: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            try:
                def onerror(exc: OSError) -> None:
                    self.manifest["skipped"].append({"path": str(exc.filename or root), "reason": str(exc)})

                for current, dirs, _files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
                    current_path = Path(current)
                    depth = len(current_path.relative_to(root).parts)
                    if depth > 5:
                        dirs[:] = []
                        continue
                    if ".git" in dirs:
                        repos.append(current_path)
                        dirs.remove(".git")
                    dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
            except OSError as exc:
                self.manifest["skipped"].append({"path": str(root), "reason": str(exc)})
        return sorted(set(repos))

    @staticmethod
    def git_search_roots() -> list[Path]:
        return [Path("/home"), Path("/opt"), Path("/srv"), Path("/var/www")]

    def copy_ci_files(self, repo: Path) -> list[Path]:
        copied: list[Path] = []
        candidates = [
            repo / ".github",
            repo / ".gitea",
            repo / ".forgejo",
            repo / ".gitlab-ci.yml",
            repo / ".woodpecker.yml",
            repo / "Jenkinsfile",
        ]
        for candidate in candidates:
            if candidate.is_file():
                self.copy_redacted(candidate, f"apps/ci-files/{safe_rel(repo)}")
                copied.append(candidate)
            elif candidate.is_dir():
                try:
                    def onerror(exc: OSError) -> None:
                        self.manifest["skipped"].append({"path": str(exc.filename or candidate), "reason": str(exc)})

                    for current, dirs, files in os.walk(candidate, topdown=True, followlinks=False, onerror=onerror):
                        current_path = Path(current)
                        dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
                        if len(current_path.relative_to(candidate).parts) >= MAX_CI_DEPTH:
                            dirs[:] = []
                        for name in sorted(files):
                            path = current_path / name
                            if is_small_file(path):
                                self.copy_redacted(path, f"apps/ci-files/{safe_rel(repo)}")
                                copied.append(path)
                except OSError as exc:
                    self.manifest["skipped"].append({"path": str(candidate), "reason": str(exc)})
        return copied

    def copy_deploy_files(self, repo: Path) -> list[Path]:
        copied: list[Path] = []
        try:
            for current, dirs, files in os.walk(repo, topdown=True, followlinks=False):
                current_path = Path(current)
                dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
                rel_dir = current_path.relative_to(repo)
                if len(rel_dir.parts) > 2:
                    dirs[:] = []
                    continue
                for name in sorted(files):
                    path = current_path / name
                    rel = path.relative_to(repo)
                    if not is_small_file(path):
                        continue
                    if CONFIG_NAME_RE.search(path.name) and DEPLOY_FILE_RE.search(str(rel)):
                        self.copy_redacted(path, f"apps/deploy-files/{safe_rel(repo)}")
                        copied.append(path)
        except OSError as exc:
            self.manifest["skipped"].append({"path": str(repo), "reason": str(exc)})
        return copied

    def collect_declared_packages(self, repo: Path) -> tuple[list[Path], list[dict]]:
        manifests: list[Path] = []
        packages: list[dict] = []
        candidates = {
            "package.json": parse_package_json,
            "pyproject.toml": parse_pyproject_dependencies,
            "go.mod": parse_go_mod_dependencies,
        }
        try:
            for current, dirs, files in os.walk(repo, topdown=True, followlinks=False):
                current_path = Path(current)
                dirs[:] = sorted(d for d in dirs if not should_prune_dir(current_path / d))
                rel_dir = current_path.relative_to(repo)
                if len(rel_dir.parts) > 2:
                    dirs[:] = []
                    continue
                for name in sorted(files):
                    parser = candidates.get(name)
                    if parser is None:
                        continue
                    path = current_path / name
                    if not is_small_file(path):
                        continue
                    manifests.append(path)
                    for item in parser(path):
                        packages.append({"repo": str(repo), **item})
        except OSError as exc:
            self.manifest["skipped"].append({"path": str(repo), "reason": str(exc)})
        return manifests, packages

    def copy_redacted(self, path: Path, prefix: str) -> None:
        if path.is_symlink():
            self.manifest["skipped"].append({"path": str(path), "reason": "symbolic links are excluded"})
            return
        text = read_small_text(path)
        if text is None:
            self.manifest["skipped"].append({"path": str(path), "reason": "not small text or secret-like path"})
            return
        rel = f"{prefix}/{safe_rel(path)}"
        self.write_text(rel, redact_text(text))

    def build_zip(self, replace_existing: bool = False) -> Path:
        zip_path = self.options.output_root / f"{self.options.timestamp}.zip"
        temporary_path = self.options.output_root / f".{self.options.timestamp}.zip.tmp"
        if (
            zip_path.is_symlink()
            or temporary_path.is_symlink()
            or (zip_path.exists() and not replace_existing)
            or temporary_path.exists()
        ):
            raise FileExistsError(f"refusing to replace existing archive path: {zip_path}")
        reported_size = 0
        for _attempt in range(2):
            size_text = f"{reported_size:020d}"
            self.write_text("ARCHIVE_SIZE.txt", f"{zip_path}\n{size_text} bytes\n")
            mode = "x" if _attempt == 0 else "w"
            with zipfile.ZipFile(temporary_path, mode, compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for path in sorted(self.output_dir.rglob("*")):
                    if path.is_file():
                        archive_name = path.relative_to(self.output_dir)
                        if path.name == "ARCHIVE_SIZE.txt":
                            marker = zipfile.ZipInfo.from_file(path, archive_name)
                            marker.compress_type = zipfile.ZIP_STORED
                            zf.writestr(marker, path.read_bytes())
                        else:
                            zf.write(path, archive_name)
            size = temporary_path.stat().st_size
            if size > self.options.max_zip_mb * 1024 * 1024:
                temporary_path.unlink()
                raise SystemExit(f"archive exceeds {self.options.max_zip_mb}MB")
            if reported_size == size:
                temporary_path.replace(zip_path)
                return zip_path
            reported_size = size
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError("archive size did not stabilize")

    def write_review_pack(self) -> None:
        self.write_json("review-pack/checklists.json", build_review_checklists())
        self.write_text("review-pack/agent-context.md", build_agent_context(self.manifest))

    def write_runtime_structures(self, outputs: dict[str, str]) -> None:
        systemd_units = parse_systemd_units(outputs.get("runtime/systemd-units.txt", ""))
        timers = parse_systemd_timers(outputs.get("runtime/systemd-timers.txt", ""))
        listeners = parse_ss_listeners(outputs.get("runtime/listeners.txt", ""))
        compose_projects = parse_compose_projects(outputs.get("containers/docker.txt", ""))

        unit_names = {item["unit"] for item in systemd_units}
        routes: list[dict] = []

        services = {
            "systemd_units": systemd_units,
            "listeners": listeners,
            "compose_projects": compose_projects,
        }
        self.write_json("apps/services.json", services)
        self.write_json("ingress/routes.json", routes)
        self.write_json(
            "edge/connectivity.json",
            {
                "cloudflare_tunnel": "cloudflared.service" in unit_names,
                "vpn_tools": {
                    "wireguard_default_port_listener": any(item["port"] == 51820 for item in listeners),
                    "openvpn_default_port_listener": any(item["port"] == 1194 for item in listeners),
                    "tailscale": any("tailscale" in item["unit"] for item in systemd_units),
                },
                "listeners": listeners,
            },
        )
        self.write_json(
            "operations/backups.json",
            {
                "timers": [item for item in timers if "backup" in item["unit"]],
                "units": [item for item in systemd_units if "backup" in item["unit"]],
                "cron_paths": [line.strip() for line in outputs.get("runtime/cron.txt", "").splitlines() if "backup" in line.lower()],
            },
        )
        graph_services = [{"name": item["unit"], "kind": "systemd"} for item in systemd_units]
        self.write_text("graphs/services.mmd", render_service_graph(graph_services, listeners, routes))

    def write_bundle_qa(self, zip_path: Path | None) -> None:
        member_name_findings: list[str] = []
        text_scan_findings: list[str] = []
        zip_open_ok = False
        zip_member_count = 0

        if zip_path and zip_path.exists():
            with zipfile.ZipFile(zip_path) as zf:
                members = zf.namelist()
                zip_member_count = len(members)
                zip_open_ok = zf.testzip() is None
            secret_name_re = re.compile(
                r"(?i)(\.pem$|\.key$|\.p12$|\.kdbx$|authorized_keys|id_rsa|id_ed25519|token|secret|password)"
            )
            for member in members:
                if secret_name_re.search(member):
                    member_name_findings.append(member)

        for path in sorted(self.output_dir.rglob("*")):
            if not path.is_file() or path.suffix == ".zip" or path.name == "bundle_qa.json":
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if has_unredacted_secret(text):
                text_scan_findings.append(str(path.relative_to(self.output_dir)))

        self.write_json(
            "bundle_qa.json",
            {
                "zip_requested": self.options.create_zip,
                "zip_present": bool(zip_path and zip_path.exists()),
                "zip_open_ok": zip_open_ok,
                "zip_member_count": zip_member_count,
                "member_name_findings": member_name_findings,
                "text_scan_findings": text_scan_findings,
            },
        )

    def readme(self) -> str:
        return (
            "# Hostmap Output\n\n"
            "This folder is a read-only architecture map of a Linux host. It is intended for review, not restore.\n\n"
            "Secrets, private keys, token files, database files, caches, build outputs, and heavy runtime stores are excluded.\n"
        )

    def redaction_report(self) -> str:
        return (
            "# Redaction Report\n\n"
            "- Secret-looking paths are excluded.\n"
            "- Secret-looking config lines are replaced with `REDACTED`.\n"
            "- Binary files and files larger than 512 KiB are excluded.\n"
            "- Directory maps list directories only and prune common cache/build/runtime trees.\n"
        )

    def summary(self) -> str:
        file_count = len(self.manifest["files"])
        return (
            "# Hostmap Summary\n\n"
            f"- Generated at: `{self.manifest['generated_at']}`\n"
            f"- Hostname: `{self.manifest['hostname']}`\n"
            f"- Mode: `{self.options.mode}`\n"
            f"- Schema version: `{self.manifest['schema_version']}`\n"
            f"- Files written: `{file_count}`\n"
            f"- Commands attempted: `{len(self.manifest['commands'])}`\n\n"
            "Start with `bundle_qa.json`, `manifest.json`, `review-pack/`, `runtime/`, `ingress/`, `containers/`, `apps/`, and `operations/`.\n"
        )

    def recommendations(self) -> str:
        return (
            "# Review Recommendations\n\n"
            "- Start with `bundle_qa.json` to confirm archive integrity and redaction scan status.\n"
            "- Read `manifest.json` and `review-pack/checklists.json` before raw text files.\n"
            "- Use `graphs/services.mmd` and `edge/connectivity.json` to form architecture hypotheses, then confirm them against `runtime/` and `apps/` evidence.\n"
            "- Treat missing collectors and redacted values as unknowns, not absence.\n"
            "- For drift review, compare this bundle against a previous run with `hostmap diff`.\n"
        )


def safe_rel(path: Path) -> str:
    return str(path).lstrip("/")


def sh_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"


def has_unredacted_secret(text: str) -> bool:
    for line in text.splitlines():
        if PEM_PRIVATE_KEY_RE.search(line) or URL_CREDENTIAL_RE.search(line) or AUTH_CREDENTIAL_RE.search(line):
            return True
        for match in SENSITIVE_ASSIGNMENT_RE.finditer(line):
            value = match.group("value").strip().strip("\"'")
            if value and value.casefold() not in {"redacted", "true", "false", "null", "none"}:
                return True
    return False


def is_small_file(path: Path, limit: int = 512 * 1024) -> bool:
    try:
        return not path.is_symlink() and path.is_file() and path.stat().st_size <= limit
    except OSError:
        return False
