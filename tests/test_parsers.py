from pathlib import Path

from hostmap.parsers import (
    parse_go_mod_dependencies,
    parse_package_json,
    parse_pyproject_dependencies,
    parse_systemd_units,
    parse_systemd_timers,
    parse_tabular_packages,
    render_service_graph,
)


def test_systemd_parser_handles_failed_unit_marker() -> None:
    units = parse_systemd_units("● nginx.service loaded failed failed Web server\n")
    assert units == [
        {
            "name": "nginx.service",
            "unit": "nginx.service",
            "load": "loaded",
            "active": "failed",
            "sub": "failed",
            "description": "Web server",
        }
    ]


def test_systemd_parsers_ignore_command_errors_and_legends() -> None:
    assert parse_systemd_units("Failed to connect to bus: No medium found\n") == []
    assert parse_systemd_timers("Failed to connect to bus: No medium found\n") == []
    assert parse_systemd_timers("NEXT LEFT LAST PASSED UNIT ACTIVATES\n") == []


def test_package_parser_accepts_pacman_whitespace_format() -> None:
    assert parse_tabular_packages("bash 5.2.37-1\npython\t3.13.0\ncommand not-found\n") == [
        {"name": "bash", "version": "5.2.37-1"},
        {"name": "python", "version": "3.13.0"},
    ]


def test_package_parsers_handle_common_declarations_and_redact_urls(tmp_path: Path) -> None:
    package_json = tmp_path / "package.json"
    package_json.write_text('{"dependencies":{"private":"git+https://user:pass@example.com/repo.git"}}')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        "dependencies = [\n"
        '  "httpx[http2]>=0.27", # ] in a comment\n'
        "  # 'commented>=1.0',\n"
        "  'private @ https://user:pass@example.com/pkg.whl', # ] in a comment\n"
        "]\n"
        "[project.optional-dependencies]\n"
        'test = ["pytest>=8"]\n'
    )
    go_mod = tmp_path / "go.mod"
    go_mod.write_text(
        "module example.com/app\n"
        "require (\n"
        "  github.com/example/direct v1.2.3\n"
        "  github.com/example/indirect v1.2.4 // indirect\n"
        ")\n"
    )

    package_rows = parse_package_json(package_json)
    pyproject_rows = parse_pyproject_dependencies(pyproject)
    go_rows = parse_go_mod_dependencies(go_mod)

    assert "user:pass" not in package_rows[0]["version"]
    assert [row["package"] for row in pyproject_rows] == ["httpx[http2]", "private"]
    assert pyproject_rows[0]["version"] == ">=0.27"
    assert "user:pass" not in pyproject_rows[1]["version"]
    assert all(row["package"] != "commented" for row in pyproject_rows)
    assert [row["version"] for row in go_rows] == ["v1.2.3", "v1.2.4"]


def test_service_graph_escapes_labels_uses_valid_label_edges_and_keeps_nodes_distinct() -> None:
    graph = render_service_graph(
        services=[{"name": "a-b"}, {"name": "a_b"}],
        listeners=[{"local_address": "127.0.0.1", "port": 8080, "process": 'users:(("app",pid=1))'}],
        routes=[{"source": "a-b", "target": "a_b", "label": 'route "one"'}],
    )

    assert graph.count('["a-b"]') == 1
    assert graph.count('["a_b"]') == 1
    assert '&quot;app&quot;' in graph
    assert '-->|"route &quot;one&quot;"|' in graph
