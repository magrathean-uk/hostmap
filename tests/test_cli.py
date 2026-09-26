import json
import subprocess
import sys
from pathlib import Path

import pytest

from hostmap import __version__
from hostmap.cli import main
from hostmap.collect import HostmapResult


def test_main_uses_process_arguments(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr("hostmap.cli.platform.system", lambda: "Linux")
    monkeypatch.setattr(sys, "argv", ["hostmap", "--mode", "paranoid", "--output", str(tmp_path), "--no-zip"])
    seen = []

    def fake_run(mapper):
        seen.append(mapper.options)
        return HostmapResult(tmp_path / "test", None, {})

    monkeypatch.setattr("hostmap.cli.HostMapper.run", fake_run)
    assert main() == 0
    assert seen[0].mode == "paranoid"
    assert seen[0].output_root == tmp_path
    assert seen[0].create_zip is False
    assert "output_dir=" in capsys.readouterr().out


def test_explicit_empty_arguments_do_not_use_process_arguments(monkeypatch) -> None:
    monkeypatch.setattr("hostmap.cli.platform.system", lambda: "Linux")
    monkeypatch.setattr(sys, "argv", ["hostmap", "--unexpected-option"])
    seen = []

    def fake_run(mapper):
        seen.append(mapper.options)
        return HostmapResult(Path("unused"), None, {})

    monkeypatch.setattr("hostmap.cli.HostMapper.run", fake_run)
    assert main([]) == 0
    assert seen[0].mode == "safe"


@pytest.mark.parametrize("arguments, expected", [(["--version"], f"hostmap {__version__}"), (["--help"], "--mode"), (["diff", "--help"], "Earlier hostmap bundle")])
def test_module_entrypoint(arguments, expected) -> None:
    result = subprocess.run([sys.executable, "-m", "hostmap", *arguments], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


@pytest.mark.parametrize("value", ["0", "-1", "nope"])
def test_invalid_archive_limit_fails_before_collection(value, monkeypatch, capsys) -> None:
    def unexpected_collection(_):
        pytest.fail("invalid options must not collect the host")

    monkeypatch.setattr("hostmap.cli.HostMapper.run", unexpected_collection)
    with pytest.raises(SystemExit) as exc:
        main(["--max-zip-mb", value])
    assert exc.value.code == 2
    assert "positive integer" in capsys.readouterr().err


def test_collection_rejects_unsupported_platform(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr("hostmap.cli.platform.system", lambda: "Darwin")
    with pytest.raises(SystemExit) as exc:
        main(["--output", str(tmp_path / "out")])
    assert exc.value.code == 2
    assert "requires Linux" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_missing_diff_input_is_readable_cli_error(tmp_path, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["diff", str(tmp_path / "missing"), str(tmp_path / "also-missing"), "--output", str(tmp_path / "out")])
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert str(tmp_path / "missing") in error
    assert "Traceback" not in error


def test_module_diff_compares_evidence_without_collecting(tmp_path) -> None:
    for name, content in (("before", "old"), ("after", "new")):
        bundle = tmp_path / name
        bundle.mkdir()
        (bundle / "manifest.json").write_text(json.dumps({"files": ["evidence.txt"]}))
        (bundle / "evidence.txt").write_text(content)
    result = subprocess.run(
        [sys.executable, "-m", "hostmap", "diff", str(tmp_path / "before"), str(tmp_path / "after"), "--output", str(tmp_path / "diff")],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "diff" / "diff.json").read_text())["changed_files"] == ["evidence.txt"]
