from __future__ import annotations

import re
from pathlib import Path

MAX_TEXT_FILE_BYTES = 512 * 1024

PRUNE_DIR_NAMES = {
    ".cache",
    ".codex",
    ".git",
    ".hg",
    ".mypy_cache",
    ".next",
    ".npm",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "dist",
    "node_modules",
    "out",
    "releases",
    "target",
    "tmp",
    "vendor",
}

PSEUDO_OR_DYNAMIC_ROOTS = {
    "/dev",
    "/proc",
    "/run",
    "/sys",
    "/tmp",
    "/mnt",
    "/media",
}

SECRET_PATH_RE = re.compile(
    r"(?i)(/(creds|credentials|\.ssh|\.gnupg|\.password-store)(/|$)|"
    r"tunnel-token|"
    r"\.(pem|key|p8|jks|p12|kdbx|sqlite|db|sql|bak|dump)$|"
    r"authorized_keys|id_rsa|id_ed25519|known_hosts|"
    r"wallet|keystore|keychain|warp\.sqlite)"
)

SECRET_DIR_WORD_RE = re.compile(
    r"(?i)(password|passwd|secret|token|credential|authorization|private|oauth)"
)

SENSITIVE_LINE_RE = re.compile(
    r"(?i)(password|passwd|secret|token|authorization|api[_-]?key|private[_-]?key|"
    r"client[_-]?secret|access[_-]?key|tunnel[_-]?token|github_token|gitlab_token|"
    r"cloudflare.*token|cf_api|aws_.*key|b2_.*key|mysql_pwd|pgpassword|privatekey)"
)


def is_secret_path(path: Path | str) -> bool:
    return SECRET_PATH_RE.search(str(path)) is not None


def should_prune_dir(path: Path) -> bool:
    text = str(path)
    if text in PSEUDO_OR_DYNAMIC_ROOTS:
        return True
    if text.startswith("/var/lib/docker") or text.startswith("/var/lib/containerd"):
        return True
    if text.startswith("/var/log/journal"):
        return True
    if any(part in PRUNE_DIR_NAMES for part in path.parts):
        return True
    if any(SECRET_DIR_WORD_RE.search(part) for part in path.parts):
        return True
    return is_secret_path(path)


def redact_text(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines():
        if SENSITIVE_LINE_RE.search(line):
            if "=" in line:
                key = line.split("=", 1)[0].rstrip()
                line = f"{key}=REDACTED"
            elif ":" in line:
                key = line.split(":", 1)[0].rstrip()
                line = f"{key}: REDACTED"
            else:
                line = "[REDACTED secret-like line]"
        line = re.sub(r"https://[^/@\s]+@", "https://REDACTED@", line)
        line = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer REDACTED", line)
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def read_small_text(path: Path, max_bytes: int = MAX_TEXT_FILE_BYTES) -> str | None:
    if is_secret_path(path):
        return None
    try:
        if not path.is_file() or path.stat().st_size > max_bytes:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")
