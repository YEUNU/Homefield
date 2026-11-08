"""docs/RULES.md §4의 기계 검사.

python3 scripts/check_rules.py               # 추적 중인 파일 전체 (CI)
python3 scripts/check_rules.py --staged      # staged 파일만 (pre-commit)
python3 scripts/check_rules.py --internal internal   # 내부 문서 머리말·이름 검사
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

PRIVATE_IP = re.compile(
    r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b"
)
DOC_STATUS = {"초안", "확정", "폐기"}
ADR_STATUS = {"결정", "가정", "폐기", "대체됨"}
UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9_]*\.md$")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
DATE = re.compile(r"\b20\d{2}-\d{2}(-\d{2})?\b")
ADR_NAME = re.compile(r"^\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.md$")


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
        errs.append(f"{path}: 파일 이름 규칙 위반 (RULES §1.2)")
    fm = front_matter(path.read_text(encoding="utf-8"))
    if fm is None:
        return errs + [f"{path}: 머리말(front matter) 없음 (RULES §1.3)"]
    if fm.get("status") not in statuses:
        errs.append(f"{path}: status는 {sorted(statuses)} 중 하나 (현재: {fm.get('status')!r})")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm.get("updated", "")):
        errs.append(f"{path}: updated는 YYYY-MM-DD")
    if fm.get("audience") != audience:
        errs.append(f"{path}: audience는 {audience!r}")
    return errs


def check_public(files: list[str]) -> list[str]:
    errs = []
    for f in files:
        p = Path(f)
        if f.startswith("internal/"):
            errs.append(f"{f}: internal/ 은 Homefield에서 추적하지 않는다 (RULES §1.1)")
            continue
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # 바이너리
        for n, line in enumerate(text.splitlines(), 1):
            if PRIVATE_IP.search(line):
                errs.append(f"{f}:{n}: 사설 IP 금지. 환경변수로 쓴다 (RULES §1.7)")
        if p.parent == Path("docs") and p.suffix == ".md" and p.name != "README.md":
            errs += check_doc(p, "배포", DOC_STATUS, UPPER_SNAKE)
        if (p.parent == Path("docs") or f == "README.md") and p.suffix == ".md":
            body = text.split("\n---", 1)[1] if text.startswith("---\n") else text
            if DATE.search(body):
                errs.append(f"{f}: 배포 문서 본문에 날짜를 쓰지 않는다. 최종 상태만 쓴다 (RULES §1.3)")
    return errs


def check_internal(root: Path) -> list[str]:
    errs = []
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root)
        if ".git" in rel.parts or p.name == "README.md":
            continue
        if rel.parts[0] == "decisions":
            errs += check_doc(p, "내부", ADR_STATUS, ADR_NAME)
        elif rel.parts[0] == "design":
            errs += check_doc(p, "내부", DOC_STATUS, KEBAB)
        else:
            errs += check_doc(p, "내부", DOC_STATUS, UPPER_SNAKE)
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
