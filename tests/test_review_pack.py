from hostmap.review_pack import build_agent_context, build_review_checklists


def test_agent_context_escapes_manifest_values_for_markdown() -> None:
    context = build_agent_context(
        {
            "hostname": "host`name\n<&>",
            "mode": "safe",
            "schema_version": "1.0",
        }
    )

    assert "Hostname: <code>host`name &lt;&amp;&gt;</code>" in context
    assert "Do not infer that secrets are absent" in context


def test_agent_context_uses_unknown_for_non_string_manifest_values() -> None:
    context = build_agent_context({"hostname": None, "mode": 1, "schema_version": ""})

    assert "Hostname: <code>unknown</code>" in context
    assert "Mode: <code>unknown</code>" in context
    assert "Schema version: <code>unknown</code>" in context


def test_review_checklists_cover_all_review_roles() -> None:
    assert set(build_review_checklists()) == {"reviewer", "operator", "ai_agent"}
