import json
from pathlib import Path

from hostmap.collect import HostMapper, HostmapOptions
from hostmap.parsers import parse_ss_listeners, parse_systemd_units, render_service_graph


def test_structured_collectors_render_service_graph() -> None:
    units = parse_systemd_units(
        "UNIT LOAD ACTIVE SUB DESCRIPTION\n"
        "nginx.service loaded active running A web server\n"
        "cloudflared.service loaded active running Cloudflare Tunnel\n"
    )
    listeners = parse_ss_listeners(
        'tcp LISTEN 0 128 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=1,fd=7))\n'
    )
    graph = render_service_graph(
        services=[{"name": "nginx.service", "kind": "systemd"}],
        listeners=listeners,
        routes=[{"source": "cloudflared", "target": "nginx.service", "label": "https"}],
    )

    assert units[0]["unit"] == "nginx.service"
    assert listeners[0]["port"] == 8080
    assert "graph TD" in graph
    assert "cloudflared" in graph


def test_run_writes_structured_outputs(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: test\n")
    (repo / "docker-compose.yml").write_text("services:\n  web:\n    image: nginx\n")
    (repo / "package.json").write_text('{"dependencies":{"next":"15.0.0"}}\n')
    (repo / "pyproject.toml").write_text("[project]\ndependencies = [\"httpx>=0.27\"]\n")
    (repo / "go.mod").write_text("module example.com/app\nrequire github.com/gin-gonic/gin v1.10.0\n")

    def fake_run_command(self, name: str, cmd: str, timeout: int = 60) -> str:
        outputs = {
            "hostnamectl": "",
            "uname": "",
            "os-release": "",
            "systemd": "",
            "docker": "",
            "docker-compose": "",
            "podman": "",
            "kubectl": "",
            "k3s": "",
            "nginx": "",
            "apache": "",
            "caddy": "",
            "traefik": "",
            "haproxy": "",
            "cloudflared": "",
            "tailscale": "",
            "git": "",
            "python": "",
            "node": "",
            "npm": "",
            "go": "",
            "rust": "",
            "java": "",
            "php": "",
            "ruby": "",
            "dotnet": "",
            "packages": "bash\t5.2\nnginx\t1.27.0\n",
            "runtime/systemd-failed.txt": "0 loaded units listed.\n",
            "runtime/systemd-units.txt": (
                "UNIT LOAD ACTIVE SUB DESCRIPTION\n"
                "nginx.service loaded active running A web server\n"
                "cloudflared.service loaded active running Cloudflare Tunnel\n"
                "backup-system.timer loaded active waiting System Backup Timer\n"
            ),
            "runtime/systemd-timers.txt": (
                "NEXT LEFT LAST PASSED UNIT ACTIVATES\n"
                "Fri 2026-05-23 01:00:00 UTC 1h Thu 2026-05-22 01:00:00 UTC 2h ago backup-system.timer backup-system.service\n"
            ),
            "runtime/systemd-sockets.txt": "LISTEN UNIT ACTIVATES\n",
            "runtime/listeners.txt": (
                'tcp LISTEN 0 128 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=1,fd=7))\n'
                'udp UNCONN 0 0 0.0.0.0:51820 0.0.0.0:* users:(("wg",pid=2,fd=8))\n'
            ),
            "runtime/processes.txt": "1 0 root Ss nginx nginx: master process\n",
            "runtime/cron.txt": "/etc/cron.d/backup-system\n",
            "runtime/filesystems.txt": "Filesystem Type Size Used Avail Use% Mounted on\n/dev/sda1 ext4 50G 20G 30G 40% /\n",
            "containers/docker.txt": '[{"Name":"stack","Status":"running","ConfigFiles":"/srv/app/docker-compose.yml"}]\n',
            "containers/podman.txt": "",
            "containers/kubernetes.txt": "",
            "git-status": "## main...origin/main\n",
            "git-log": "abcdef 2026-05-22 00:00:00 +0000 init\n",
            "git-remote": "origin\thttps://example.com/repo.git (fetch)\n",
        }
        return outputs.get(name, "")

    monkeypatch.setattr(HostMapper, "run_command", fake_run_command)
    monkeypatch.setattr(HostMapper, "collect_filesystem_maps", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_tool_matrices", lambda self: None)
    monkeypatch.setattr(HostMapper, "collect_configs", lambda self: None)
    monkeypatch.setattr(HostMapper, "find_git_repos", lambda self: [repo])

    result = HostMapper(
        HostmapOptions(output_root=tmp_path / "out", mode="safe", max_zip_mb=10, create_zip=False, timestamp="test")
    ).run()

    services = json.loads((result.output_dir / "apps/services.json").read_text())
    edge = json.loads((result.output_dir / "edge/connectivity.json").read_text())
    backups = json.loads((result.output_dir / "operations/backups.json").read_text())
    installed = json.loads((result.output_dir / "packages/installed.json").read_text())
    declared = json.loads((result.output_dir / "packages/declared.json").read_text())
    graph = (result.output_dir / "graphs/services.mmd").read_text()

    assert any(service["name"] == "nginx.service" for service in services["systemd_units"])
    assert "cloudflare_tunnel" in edge
    assert backups["timers"][0]["unit"] == "backup-system.timer"
    assert installed[0]["name"] == "bash"
    assert any(item["source"] == "package.json" for item in declared)
    assert "graph TD" in graph
