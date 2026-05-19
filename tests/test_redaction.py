from pathlib import Path

from hostmap.redaction import redact_text, should_prune_dir


def test_redacts_secret_like_assignments() -> None:
    text = "API_TOKEN=abc123\nsafe=value\nclient_secret: abc\n"
    assert redact_text(text) == "API_TOKEN=REDACTED\nsafe=value\nclient_secret: REDACTED\n"


def test_redacts_bearer_tokens_and_basic_auth() -> None:
    text = "url=https://user:pass@example.com/repo.git\nAuthorization: Bearer abc.def\n"
    redacted = redact_text(text)
    assert "user:pass" not in redacted
    assert "Bearer abc.def" not in redacted


def test_prunes_heavy_and_secret_dirs() -> None:
    assert should_prune_dir(Path("/srv/app/node_modules"))
    assert should_prune_dir(Path("/home/me/.ssh"))
    assert should_prune_dir(Path("/opt/app/secrets"))
    assert should_prune_dir(Path("/opt/app/trust_token"))
    assert should_prune_dir(Path("/opt/app/authorization_rule"))
    assert not should_prune_dir(Path("/opt/app/config"))
