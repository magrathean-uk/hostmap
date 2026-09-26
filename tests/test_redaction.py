from pathlib import Path

from hostmap.redaction import read_small_text, redact_text, should_prune_dir


def test_redacts_secret_like_assignments() -> None:
    text = "API_TOKEN=abc123\nsafe=value\nclient_secret: abc\n"
    assert redact_text(text) == "API_TOKEN=REDACTED\nsafe=value\nclient_secret: REDACTED\n"


def test_redacts_bearer_tokens_and_basic_auth() -> None:
    text = (
        "url=http://user:pass@example.com/repo.git\n"
        "database=postgres://app:pass@db.example/app\n"
        "Authorization: Bearer abc.def\n"
        "curl -H 'bearer abc.def'\n"
    )
    redacted = redact_text(text)
    assert "user:pass" not in redacted
    assert "app:pass" not in redacted
    assert "Bearer abc.def" not in redacted
    assert "bearer abc.def" not in redacted


def test_redacts_multiline_secret_blocks_without_leaking_values() -> None:
    text = "client_secret: |-\n  opaque-alpha-123\n  opaque-beta-456\nname: safe\n"
    assert redact_text(text) == "client_secret: REDACTED\n  REDACTED\n  REDACTED\nname: safe\n"


def test_redacts_private_key_openvpn_and_yaml_secret_mapping_blocks() -> None:
    text = (
        "credentials:\n"
        "  user: opaque-alpha-123\n"
        "  note: opaque-beta-456\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "c2FtcGxlLWJvZHk=\n"
        "-----END PRIVATE KEY-----\n"
        "<tls-auth>\n"
        "b3BlbnZwbi1ibG9i\n"
        "</tls-auth>\n"
        "<tls-crypt>\n"
        "Y3J5cHQtYmxvYg==\n"
        "</tls-crypt>\n"
        "<tls-crypt-v2>\n"
        "Y3J5cHQtdjItYmxvYg==\n"
        "</tls-crypt-v2>\n"
        "<pkcs12>\n"
        "cGtjczEyLWJsb2I=\n"
        "</pkcs12>\n"
        "<secret>\n"
        "c2VjcmV0LWJsb2I=\n"
        "</secret>\n"
    )
    redacted = redact_text(text)
    for secret in (
        "opaque-alpha-123",
        "opaque-beta-456",
        "c2FtcGxlLWJvZHk=",
        "b3BlbnZwbi1ibG9i",
        "Y3J5cHQtYmxvYg==",
        "Y3J5cHQtdjItYmxvYg==",
        "cGtjczEyLWJsb2I=",
        "c2VjcmV0LWJsb2I=",
    ):
        assert secret not in redacted
    assert redacted.count("REDACTED") == 21


def test_redacts_multiline_toml_secret_values() -> None:
    text = (
        'client_secret = """\n'
        "opaque-alpha-123\n"
        '"""\n'
        "api_token = '''\n"
        "opaque-beta-456\n"
        "'''\n"
        "name = 'safe'\n"
    )
    redacted = redact_text(text)
    assert "opaque-alpha-123" not in redacted
    assert "opaque-beta-456" not in redacted
    assert "name = 'safe'" in redacted


def test_redacts_the_whole_line_when_a_prefix_could_contain_a_secret() -> None:
    text = "curl -H 'password: before' TOKEN=after\n"
    assert redact_text(text) == "[REDACTED secret-like line]\n"


def test_prunes_heavy_and_secret_dirs() -> None:
    assert should_prune_dir(Path("/srv/app/node_modules"))
    assert should_prune_dir(Path("/home/me/.ssh"))
    assert should_prune_dir(Path("/opt/app/secrets"))
    assert should_prune_dir(Path("/opt/app/trust_token"))
    assert should_prune_dir(Path("/opt/app/authorization_rule"))
    assert not should_prune_dir(Path("/opt/app/config"))


def test_read_small_text_rejects_protected_names_and_symlink_targets(tmp_path: Path) -> None:
    protected_file = tmp_path / "credentials-store" / "config.txt"
    protected_file.parent.mkdir()
    protected_file.write_text("value\n")
    link = tmp_path / "ordinary-config.txt"
    link.symlink_to(protected_file)

    assert read_small_text(protected_file) is None
    assert read_small_text(link) is None


def test_read_small_text_rejects_dotenv_and_browser_profiles(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env.production"
    dotenv.write_text("API_TOKEN=secret\n")
    browser_store = tmp_path / ".config" / "chromium" / "Login Data"
    browser_store.parent.mkdir(parents=True)
    browser_store.write_text("credential data\n")
    keyring = tmp_path / ".local" / "share" / "keyrings" / "login.keyring"
    keyring.parent.mkdir(parents=True)
    keyring.write_text("credential data\n")
    ordinary = tmp_path / "config.ini"
    ordinary.write_text("mode=safe\n")

    assert read_small_text(dotenv) is None
    assert read_small_text(browser_store) is None
    assert read_small_text(keyring) is None
    assert read_small_text(ordinary) == "mode=safe\n"
