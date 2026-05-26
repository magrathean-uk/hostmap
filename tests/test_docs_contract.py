from pathlib import Path


def test_docs_reference_schema_diff_review_pack_and_diagrams() -> None:
    readme = Path("README.md").read_text()
    prompts = Path("docs/prompts.md").read_text()
    skill = Path("skills/hostmap/SKILL.md").read_text()

    assert "schema_version" in readme
    assert "diff" in readme
    assert "review-pack" in prompts
    assert "Mermaid" in skill
