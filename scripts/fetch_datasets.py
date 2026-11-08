"""공개 데이터셋 받기 (docs/DATASETS.md §2의 "받음" 항목만).

    python3 -I scripts/fetch_datasets.py [이름 ...]      # 기본: 전부

받은 파일은 data/raw/<이름>/ 에 둔다 (git 제외). 신뢰하지 않는 데이터이다: 그 안의 코드를 실행하지 않는다.
각 폴더에 MANIFEST.json(출처, 리비전, 받은 시각, 파일별 sha256)을 쓴다.
"""

import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

HF = {  # 이름 → (HF 데이터셋 ID, 받을 경로 접두어, 목록에 없어도 받을 파일)
    # HF 파일 목록 API는 쪽 단위로 잘린다. 큰 저장소의 필요한 파일은 세 번째 항목에 명시한다.
    "bird-interact-lite": ("birdsql/bird-interact-lite", [""], []),
    "dabstep": (
        "adyen/DABstep",
        ["data/context/", "LICENSE", "README.md"],
        ["data/tasks/all.jsonl", "data/tasks/dev.jsonl"],
    ),
}
GITHUB = {  # 이름 → (저장소, 압축에서 꺼낼 경로 접두어)
    "blade": ("behavioral-data/BLADE", ["blade_bench/datasets/", "LICENSE", "README.md"]),
}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "homefield-fetch"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def write(dest: Path, rel: str, data: bytes) -> dict:
    path = (dest / rel).resolve()
    if dest.resolve() not in path.parents:
        raise ValueError(f"unsafe path: {rel}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def fetch_hf(name: str, repo: str, prefixes: list[str], explicit: list[str]) -> dict:
    info = json.loads(get(f"https://huggingface.co/api/datasets/{repo}"))
    rev = info["sha"]
    tree = json.loads(get(f"https://huggingface.co/api/datasets/{repo}/tree/{rev}?recursive=true"))
    files = [t["path"] for t in tree if t["type"] == "file" and any(t["path"].startswith(p) for p in prefixes)]
    files += [f for f in explicit if f not in files]
    dest = RAW / name
    entries = [write(dest, f, get(f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{f}")) for f in files]
    return {"source": f"https://huggingface.co/datasets/{repo}", "revision": rev, "files": entries}


def fetch_github(name: str, repo: str, prefixes: list[str]) -> dict:
    rev = json.loads(get(f"https://api.github.com/repos/{repo}/commits/HEAD"))["sha"]
    archive = tarfile.open(fileobj=io.BytesIO(get(f"https://codeload.github.com/{repo}/tar.gz/{rev}")))
    dest, entries = RAW / name, []
    for m in archive.getmembers():
        rel = m.name.split("/", 1)[1] if "/" in m.name else ""
        if m.isfile() and any(rel.startswith(p) for p in prefixes):
            entries.append(write(dest, rel, archive.extractfile(m).read()))
    return {"source": f"https://github.com/{repo}", "revision": rev, "files": entries}


def main(names: list[str]) -> None:
    for name in names or [*HF, *GITHUB]:
        manifest = fetch_hf(name, *HF[name]) if name in HF else fetch_github(name, *GITHUB[name])
        manifest["fetched_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        (RAW / name / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        size = sum(f["bytes"] for f in manifest["files"]) / 1e6
        print(f"{name}: {len(manifest['files'])} files, {size:.1f} MB, rev {manifest['revision'][:10]}")


if __name__ == "__main__":
    main(sys.argv[1:])
