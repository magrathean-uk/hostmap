from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .collect import HostMapper, HostmapOptions
from .diffing import write_diff_bundle


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
    parser.add_argument("--max-zip-mb", type=int, default=500, help="Maximum archive size.")
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
    argv = argv or []
    if argv and argv[0] == "diff":
        args = build_diff_parser().parse_args(argv[1:])
        diff_path = write_diff_bundle(Path(args.before), Path(args.after), Path(args.output))
        print(f"diff_path={diff_path}")
        return 0

    args = build_collect_parser().parse_args(argv)
    options = HostmapOptions(
        output_root=Path(args.output),
        mode=args.mode,
        max_zip_mb=args.max_zip_mb,
        create_zip=not args.no_zip,
    )
    result = HostMapper(options).run()
    print(f"output_dir={result.output_dir}")
    if result.zip_path:
        print(f"zip_path={result.zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
