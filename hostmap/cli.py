from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from . import __version__
from .collect import HostMapper, HostmapOptions
from .diffing import write_diff_bundle


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def build_collect_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hostmap",
        description="Create a safe, read-only Linux host architecture map.",
    )
    parser.add_argument("--output", default="hostmap-output", help="Output root directory.")
    parser.add_argument(
        "--mode",
        choices=["safe", "paranoid", "local"],
        default="safe",
        help="Collection depth. safe copies redacted small configs; paranoid skips configs; local includes more local VPN config roots with redaction.",
    )
    parser.add_argument("--max-zip-mb", type=positive_int, default=500, help="Maximum archive size in MiB (positive integer).")
    parser.add_argument("--no-zip", action="store_true", help="Do not create a zip archive.")
    parser.add_argument("--version", action="version", version=f"hostmap {__version__}")
    return parser


def build_diff_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hostmap diff",
        description="Compare two existing hostmap bundles without touching a live host.",
    )
    parser.add_argument("before", help="Earlier hostmap bundle directory.")
    parser.add_argument("after", help="Later hostmap bundle directory.")
    parser.add_argument("--output", required=True, help="Output directory for diff files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "diff":
        parser = build_diff_parser()
        args = parser.parse_args(argv[1:])
        try:
            diff_path = write_diff_bundle(Path(args.before), Path(args.after), Path(args.output))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"diff_path={diff_path}")
        return 0

    parser = build_collect_parser()
    args = parser.parse_args(argv)
    if platform.system() != "Linux":
        parser.error("host collection requires Linux; offline diff is available on any platform")
    options = HostmapOptions(
        output_root=Path(args.output),
        mode=args.mode,
        max_zip_mb=args.max_zip_mb,
        create_zip=not args.no_zip,
    )
    try:
        result = HostMapper(options).run()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"output_dir={result.output_dir}")
    if result.zip_path:
        print(f"zip_path={result.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
