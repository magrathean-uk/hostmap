from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .collect import HostMapper, HostmapOptions


def build_parser() -> argparse.ArgumentParser:
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
