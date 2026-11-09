import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "check_rules", Path(__file__).parent.parent / "scripts" / "check_rules.py"
)
check_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_rules)


def test_headings_give_section_numbers():
    text = "# T\n## 1. Docs\n### 1.1 Location\n## 2. Code\n"
    assert set(check_rules.HEADING.findall(text)) == {"1", "1.1", "2"}


def test_bad_section_refs_in_other_files():
    sections = {"1", "1.1", "4.6"}
    bad = "RULES " + "§3.9"  # split, so that the rule check does not flag this file
    text = f"See RULES §1.1 and `docs/RULES.md` §4.6. Bad: {bad}. Own section §7 of this file is ignored."
    assert check_rules.bad_section_refs(text, sections, own=False) == ["3.9"]


def test_bad_section_refs_inside_rules_doc():
    assert check_rules.bad_section_refs("See §1.1 and §9.", {"1", "1.1"}, own=True) == ["9"]


def test_repo_has_no_bad_refs():
    assert check_rules.check_public(check_rules.git_files(staged=False)) == []
