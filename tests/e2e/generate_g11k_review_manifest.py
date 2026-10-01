"""Bind the staged G1.1K candidate to deterministic review file hashes.

The commit SHA cannot appear inside a file in that same commit. Record the
resolved frozen HEAD beside this manifest in the review transcript and PR.
"""

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = Path("docs/implementation")
CHANGED = DOCS / "G11K_CHANGED_FILES.txt"
REVIEW = DOCS / "G11K_REVIEW_MANIFEST.json"
SUMS = DOCS / "G11K_SHA256SUMS.txt"
GENERATED = {path.as_posix() for path in (CHANGED, REVIEW, SUMS)}
BASE = "5fcb110c379b25079dd1b374de8a2e5b9c494dfd"


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True,
    ).stdout


def stage(path: Path) -> None:
    subprocess.run(["git", "add", "--", path.as_posix()], cwd=ROOT, check=True)


def staged_bytes(path: str) -> bytes:
    return git("show", f":{path}")


def main() -> None:
    assert git("rev-parse", "origin/main").decode().strip() == BASE
    staged = {
        path.decode("utf-8") for path in git(
            "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z", "origin/main",
        ).split(b"\0") if path
    }
    assert "tests/e2e/generate_g11k_review_manifest.py" in staged
    paths = sorted(staged | GENERATED)
    assert all((ROOT / path).is_file() or path in GENERATED for path in paths)

    (ROOT / CHANGED).write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")
    stage(CHANGED)

    review_files = [
        {"path": path, "sha256": hashlib.sha256(staged_bytes(path)).hexdigest()}
        for path in paths if path not in {REVIEW.as_posix(), SUMS.as_posix()}
    ]
    payload = {
        "schema": "valora-g11k-review-manifest-v1",
        "task_id": "VALORA-TASK-OS-G1-1K-PRECASE-PRODUCT-CLOSURE-E2E",
        "baseline_main_sha": BASE,
        "baseline_ci": [
            {"number": 523, "run_id": 36823627276,
             "head_sha": "21eb2e264a0f819cd3caa053fa0769128c5d06a0", "conclusion": "success"},
            {"number": 525, "run_id": 36845969447,
             "head_sha": BASE, "conclusion": "success"},
        ],
        "frozen_head_binding": "Resolve git rev-parse HEAD; exact SHA is recorded in review transcripts and Draft PR",
        "changed_file_count": len(paths),
        "source_pdf_and_screen_authority": "docs/design/visual-reference/v2.3/README.md",
        "project_code": "G11K-E2E-20261001-007",
        "evidence": {
            "report": "docs/implementation/G11K_PRECASE_PRODUCT_CLOSURE_E2E_EVIDENCE.md",
            "runtime": "docs/implementation/g11k-runtime-evidence.json",
            "replay": "docs/implementation/g11k-replay-evidence.json",
            "negative": "docs/implementation/g11k-negative-evidence.json",
            "storage": "docs/implementation/g11k-storage-evidence.json",
            "browser_sanity": "docs/implementation/g11k-browser-sanity-evidence.json",
            "visual": "docs/implementation/g11k-screenshots/manifest.json",
            "workbook": "tests/e2e/fixtures/g11k_synthetic_assets.xlsx",
        },
        "files": review_files,
    }
    (ROOT / REVIEW).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    stage(REVIEW)

    (ROOT / SUMS).write_text(
        "".join(
            f"{hashlib.sha256(staged_bytes(path)).hexdigest()}  {path}\n"
            for path in paths if path != SUMS.as_posix()
        ),
        encoding="utf-8",
    )
    stage(SUMS)

    actual = {
        path.decode("utf-8") for path in git(
            "diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z", "origin/main",
        ).split(b"\0") if path
    }
    assert actual == set(paths)
    print(f"{len(paths)} changed files; SHA256SUMS sha256="
          f"{hashlib.sha256(staged_bytes(SUMS.as_posix())).hexdigest()}")


if __name__ == "__main__":
    main()
