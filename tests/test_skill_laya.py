from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_generic_and_elastic_skills_keep_laya_as_an_optional_adapter():
    generic = (ROOT / "skills" / "jev-decision" / "SKILL.md").read_text()
    elastic = (ROOT / "skills" / "examples" / "elastic-investigation" / "SKILL.md").read_text()
    assert "main LLM" in generic
    assert "same choices" in generic
    assert "Jev never creates" in elastic
    assert "main LLM" in elastic
    assert "from laya" not in generic.lower()
    assert "from laya" not in elastic.lower()
