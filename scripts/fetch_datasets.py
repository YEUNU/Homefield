"""공개 데이터셋 받기 (docs/DATASETS.md §1의 "받음" 항목만).

    python3 -I scripts/fetch_datasets.py [이름 ...]      # 기본: 전부

받은 파일은 data/raw/<이름>/ 에 둔다 (git 제외). 신뢰하지 않는 데이터이다: 그 안의 코드를 실행하지 않는다.
압축 파일은 풀지 않고 그대로 둔다. 변환 단계에서 안전하게 푼다.
각 폴더에 MANIFEST.json(출처, 리비전, 받은 시각, 파일별 sha256)을 쓴다.
"""

import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CHUNK = 1 << 20


def hf(repo: str, prefixes: list[str] = (), explicit: list[str] = ()) -> dict:
    """HF 데이터셋. 파일 목록 API는 쪽 단위로 잘리므로 큰 저장소의 필요한 파일은 explicit에 적는다."""
    return {"kind": "hf", "repo": repo, "prefixes": list(prefixes), "explicit": list(explicit)}


def gh(repo: str, prefixes: list[str]) -> dict:
    return {"kind": "gh", "repo": repo, "prefixes": prefixes}


def url(address: str, rel: str) -> dict:
    return {"kind": "url", "url": address, "rel": rel}


DATASETS = {
    # SQL
    "bird-mini-dev": [
        hf("birdsql/bird_mini_dev", explicit=["baseline_inference/mini_dev_sqlite.jsonl", "README.md"]),
        url("https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip", "dev.zip"),  # 원본 dev SQLite DB
    ],
    "ambiqt": [gh("testzer0/AmbiQT", ["benchmark/", "db-content.zip", "LICENSE.txt", "README.md"])],
    # 로컬 파일
    "infiagent-dabench": [hf("infiagent/DABench", prefixes=[""])],
    "spreadsheetbench": [hf("KAKA22/SpreadsheetBench", explicit=["spreadsheetbench_verified_400.tar.gz", "README.md"])],
    "dabstep": [hf("adyen/DABstep", ["data/context/", "LICENSE", "README.md"], ["data/tasks/dev.jsonl"])],
    "blade": [gh("behavioral-data/BLADE", ["blade_bench/datasets/", "LICENSE", "README.md"])],
    # 문서·비전
    "tat-dqa": [
        hf(
            "next-tat/TAT-DQA",
            explicit=["tatdqa_dataset_dev.json", "tatdqa_dataset_test_gold.json", "tatdqa_docs_dev.zip", "README.md"],
        )
    ],
    # 온톨로지
    "text2kgbench": [gh("cenguix/Text2KGBench", ["data/", "LICENSE", "README.md"])],
}


def open_url(address: str):
    return urllib.request.urlopen(
        urllib.request.Request(address, headers={"User-Agent": "homefield-fetch"}), timeout=600
    )


def get_json(address: str):
    with open_url(address) as r:
        return json.load(r)


def safe_path(dest: Path, rel: str) -> Path:
    path = (dest / rel).resolve()
    if dest.resolve() not in path.parents:
        raise ValueError(f"unsafe path: {rel}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_stream(dest: Path, rel: str, stream) -> dict:
    path, h, n = safe_path(dest, rel), hashlib.sha256(), 0
    with open(path, "wb") as f:
        while chunk := stream.read(CHUNK):
            f.write(chunk)
            h.update(chunk)
            n += len(chunk)
    return {"path": rel, "bytes": n, "sha256": h.hexdigest()}


def fetch_part(dest: Path, part: dict) -> dict:
    if part["kind"] == "url":
        with open_url(part["url"]) as r:
            entry = save_stream(dest, part["rel"], r)
        return {"source": part["url"], "revision": None, "files": [entry]}
    repo = part["repo"]
    if part["kind"] == "hf":
        rev = get_json(f"https://huggingface.co/api/datasets/{repo}")["sha"]
        files = []
        if part["prefixes"]:
            tree = get_json(f"https://huggingface.co/api/datasets/{repo}/tree/{rev}?recursive=true")
            files = [
                t["path"]
                for t in tree
                if t["type"] == "file" and any(t["path"].startswith(p) for p in part["prefixes"])
            ]
        files += [f for f in part["explicit"] if f not in files]
        entries = []
        for f in files:
            with open_url(f"https://huggingface.co/datasets/{repo}/resolve/{rev}/{urllib.parse.quote(f)}") as r:
                entries.append(save_stream(dest, f, r))
        return {"source": f"https://huggingface.co/datasets/{repo}", "revision": rev, "files": entries}
    rev = get_json(f"https://api.github.com/repos/{repo}/commits/HEAD")["sha"]
    with tempfile.TemporaryFile() as tmp:
        with open_url(f"https://codeload.github.com/{repo}/tar.gz/{rev}") as r:
            shutil.copyfileobj(r, tmp, CHUNK)
        tmp.seek(0)
        entries = []
        with tarfile.open(fileobj=tmp) as archive:
            for m in archive.getmembers():
                rel = m.name.split("/", 1)[1] if "/" in m.name else ""
                if m.isfile() and any(rel.startswith(p) for p in part["prefixes"]):
                    entries.append(save_stream(dest, rel, archive.extractfile(m)))
    return {"source": f"https://github.com/{repo}", "revision": rev, "files": entries}


def main(names: list[str]) -> None:
    for name in names or DATASETS:
        dest = RAW / name
        parts = [fetch_part(dest, p) for p in DATASETS[name]]
        manifest = {"dataset": name, "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"), "parts": parts}
        (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        files = [f for p in parts for f in p["files"]]
        print(f"{name}: {len(files)} files, {sum(f['bytes'] for f in files) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
