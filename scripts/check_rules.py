"""Machine checks for docs/RULES.md §6.

python3 scripts/check_rules.py               # all tracked files (CI)
python3 scripts/check_rules.py --staged      # staged files only (pre-commit)
python3 scripts/check_rules.py --internal internal   # check front matter and names of internal docs
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

PRIVATE_IP = re.compile(
    r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b"
)
DOC_STATUS = {"draft", "stable", "deprecated"}
ADR_STATUS = {"accepted", "assumed", "deprecated", "superseded"}
UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9_]*\.md$")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
DATE = re.compile(r"\b20\d{2}-\d{2}(-\d{2})?\b")
ADR_NAME = re.compile(r"^\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.md$")
RULES_DOC = Path("docs/RULES.md")
HEADING = re.compile(r"^#{2,3} (\d+(?:\.\d+)?)\.? ", re.M)
SECTION = r"§(\d+(?:\.\d+)?)"
# In other files: "RULES §1.2" or "`docs/RULES.md` §1.2". Inside RULES.md every "§" is a self-reference.
RULES_REF = re.compile(r"RULES(?:\.md)?`? " + SECTION)


def git_files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    return [f for f in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines() if f]


def front_matter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.split("#")[0].strip()
    return fm


def check_doc(path: Path, audience: str, statuses: set[str], name_re: re.Pattern) -> list[str]:
    errs = []
    if not name_re.match(path.name):
        errs.append(f"{path}: file name rule violation (RULES §1.2)")
    fm = front_matter(path.read_text(encoding="utf-8"))
    if fm is None:
        return errs + [f"{path}: no front matter (RULES §1.3)"]
    if fm.get("status") not in statuses:
        errs.append(f"{path}: status must be one of {sorted(statuses)} (now: {fm.get('status')!r})")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm.get("updated", "")):
        errs.append(f"{path}: updated must be YYYY-MM-DD")
    if fm.get("audience") != audience:
        errs.append(f"{path}: audience must be {audience!r}")
    return errs


def bad_section_refs(text: str, sections: set[str], own: bool) -> list[str]:
    """Section numbers that the text cites from RULES.md and that RULES.md does not have."""
    refs = re.findall(SECTION, text) if own else RULES_REF.findall(text)
    return sorted({r for r in refs if r not in sections})


def check_public(files: list[str]) -> list[str]:
    errs = []
    sections = set(HEADING.findall(RULES_DOC.read_text(encoding="utf-8"))) if RULES_DOC.is_file() else None
    for f in files:
        p = Path(f)
        if f.startswith("internal/"):
            errs.append(f"{f}: internal/ must not be tracked in Homefield (RULES §1.1)")
            continue
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # binary
        for n, line in enumerate(text.splitlines(), 1):
            if PRIVATE_IP.search(line):
                errs.append(f"{f}:{n}: private IP not allowed. Use an environment variable (RULES §1.7)")
        if sections is not None:
            for ref in bad_section_refs(text, sections, own=p == RULES_DOC):
                errs.append(f"{f}: RULES §{ref} does not exist (RULES §1.8)")
        if p.parent == Path("docs") and p.suffix == ".md" and p.name != "README.md":
            errs += check_doc(p, "public", DOC_STATUS, UPPER_SNAKE)
        if (p.parent == Path("docs") or f == "README.md") and p.suffix == ".md":
            body = text.split("\n---", 1)[1] if text.startswith("---\n") else text
            if DATE.search(body):
                errs.append(
                    f"{f}: do not write dates in the body of a deployment doc. Write only the final state (RULES §1.3)"
                )
    return errs


def check_internal(root: Path) -> list[str]:
    errs = []
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root)
        if ".git" in rel.parts or p.name == "README.md":
            continue
        if rel.parts[0] == "decisions":
            errs += check_doc(p, "internal", ADR_STATUS, ADR_NAME)
        elif rel.parts[0] == "design":
            errs += check_doc(p, "internal", DOC_STATUS, KEBAB)
        else:
            errs += check_doc(p, "internal", DOC_STATUS, UPPER_SNAKE)
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--internal", type=Path)
    args = ap.parse_args()
    errs = check_internal(args.internal) if args.internal else check_public(git_files(args.staged))
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
