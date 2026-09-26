from __future__ import annotations

import re
import sys
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
    r"/(\.mozilla|\.config/(google-chrome|chromium|brave-browser|microsoft-edge)|"
    r"\.local/share/(keyrings|kwalletd)|\.pki/nssdb)(/|$)|"
    r"tunnel-token|"
    r"(?:^|/)\.env(?:\.[^/]*)?$|"
    r"\.(pem|key|p8|jks|p12|kdbx|sqlite|db|sql|bak|dump)$|"
    r"authorized_keys|id_rsa|id_ed25519|known_hosts|"
    r"wallet|keyring|keystore|keychain|warp\.sqlite)"
)

SECRET_DIR_WORD_RE = re.compile(
    r"(?i)(password|passwd|secret|token|credential|authorization|private|oauth)"
)

SENSITIVE_LINE_RE = re.compile(
    r"(?i)(password|passwd|\bpass\b|secret|token|credential|authorization|api[_-]?key|private[_-]?key|"
    r"client[_-]?secret|access[_-]?key|tunnel[_-]?token|github_token|gitlab_token|"
    r"cloudflare.*token|cf_api|aws_.*key|b2_.*key|mysql_pwd|pgpassword|privatekey)"
)

SIMPLE_KEY_VALUE_RE = re.compile(
    r"^(?P<prefix>\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_.-]*\s*)(?P<separator>[=:])"
)
BLOCK_SCALAR_RE = re.compile(r"[=:]\s*[>|][+-]?\s*(?:#.*)?$")
YAML_SECRET_MAPPING_RE = re.compile(r":\s*(?:#.*)?$")
URL_USERINFO_RE = re.compile(r"\b(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*://)[^/\s@]*@")
AUTH_CREDENTIAL_RE = re.compile(r"(?i:\b(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]+")
PEM_PRIVATE_KEY_BEGIN_RE = re.compile(r"(?i)-----BEGIN [^-]*PRIVATE KEY-----")
PEM_PRIVATE_KEY_END_RE = re.compile(r"(?i)-----END [^-]*PRIVATE KEY-----")
OPENVPN_SECRET_BLOCK_START_RE = re.compile(
    r"^\s*<(key|tls-auth|tls-crypt(?:-v2)?|pkcs12|secret)>\s*$", re.IGNORECASE
)
TOML_TRIPLE_QUOTE_RE = re.compile(r"[=:]\s*(?P<quote>\"\"\"|''')")


def is_secret_path(path: Path | str) -> bool:
    return SECRET_PATH_RE.search(str(path)) is not None


def has_sensitive_path_component(path: Path) -> bool:
    for index, part in enumerate(path.parts):
        # macOS exposes ordinary temporary and system paths below /private.  The
        # root-level namespace is not a user-owned private credential directory.
        if sys.platform == "darwin" and path.is_absolute() and index == 1 and part == "private":
            continue
        if SECRET_DIR_WORD_RE.search(part):
            return True
    return False


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
    if has_sensitive_path_component(path):
        return True
    return is_secret_path(path)


def redact_text(text: str) -> str:
    out: list[str] = []
    redacted_block_indent: int | None = None
    redacted_until: re.Pattern[str] | None = None
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        ending = raw_line[len(line) :]
        indentation = len(line) - len(line.lstrip())

        if redacted_until is not None:
            out.append(f"{' ' * indentation}REDACTED{ending}")
            if redacted_until.search(line):
                redacted_until = None
            continue

        if PEM_PRIVATE_KEY_BEGIN_RE.search(line):
            out.append(f"{' ' * indentation}REDACTED{ending}")
            redacted_until = PEM_PRIVATE_KEY_END_RE
            continue

        openvpn_secret_block = OPENVPN_SECRET_BLOCK_START_RE.match(line)
        if openvpn_secret_block:
            out.append(f"{' ' * indentation}REDACTED{ending}")
            redacted_until = re.compile(rf"^\s*</{re.escape(openvpn_secret_block.group(1))}>\s*$", re.IGNORECASE)
            continue

        if redacted_block_indent is not None:
            if line.strip() and indentation > redacted_block_indent:
                out.append(f"{' ' * indentation}REDACTED{ending}")
                continue
            if line.strip():
                redacted_block_indent = None

        if SENSITIVE_LINE_RE.search(line):
            key_value = SIMPLE_KEY_VALUE_RE.match(line)
            if key_value:
                separator = key_value.group("separator")
                spacing = " " if separator == ":" else ""
                line = f"{key_value.group('prefix').rstrip()}{separator}{spacing}REDACTED"
                original_line = raw_line.rstrip("\r\n")
                triple_quote = TOML_TRIPLE_QUOTE_RE.search(original_line)
                if triple_quote and triple_quote.group("quote") not in original_line[triple_quote.end() :]:
                    redacted_until = re.compile(re.escape(triple_quote.group("quote")))
                elif BLOCK_SCALAR_RE.search(original_line) or (
                    separator == ":" and YAML_SECRET_MAPPING_RE.search(original_line)
                ):
                    redacted_block_indent = indentation
            else:
                line = "[REDACTED secret-like line]"
        line = URL_USERINFO_RE.sub(r"\g<scheme>REDACTED@", line)
        line = AUTH_CREDENTIAL_RE.sub(lambda match: f"{match.group(0).split()[0]} REDACTED", line)
        out.append(f"{line}{ending}")
    return "".join(out)


def read_small_text(path: Path, max_bytes: int = MAX_TEXT_FILE_BYTES) -> str | None:
    try:
        resolved_path = path.resolve(strict=True)
        if (
            is_secret_path(path)
            or has_sensitive_path_component(path)
            or is_secret_path(resolved_path)
            or has_sensitive_path_component(resolved_path)
            or not path.is_file()
            or path.stat().st_size > max_bytes
        ):
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")
