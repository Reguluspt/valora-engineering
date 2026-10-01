"""Hash the committed G1.1K visual and downloaded-artifact evidence."""

import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = ROOT / "docs/implementation/g11k-screenshots"
VISUAL_ROOT = "docs/design/visual-reference/v2.3"
GRAMMAR = f"{VISUAL_ROOT}/baselines/cross-product-state-pattern-board-iteration-1.png"
S10 = f"{VISUAL_ROOT}/baselines/s10-orchestration-hub-iteration-2-approved.png"
PART_1 = f"{VISUAL_ROOT}/VALORA_UIUX_Handoff_v2.3_RELEASE_CONFIRMATION_BASELINE_Part_1.pdf"
PART_2B = f"{VISUAL_ROOT}/VALORA_UIUX_Handoff_v2.3_AUDIT_LINEAGE_ENTRYPOINT_BASELINE_Part_2B.pdf"


def category(name: str) -> dict[str, str]:
    number = int(name[:2])
    if number in (8, 17):
        return {"surface": "S10 Case Overview", "authority": "EXACT_VISUAL_BASELINE",
                "reference": S10, "source_pdf": PART_2B, "source_page": "3"}
    if 11 <= number <= 16:
        return {"surface": "S09 Result / Official Intake",
                "authority": "VISUAL_GRAMMAR_ONLY_WITH_APPROVED_LAYOUT_CONTRACT",
                "reference": GRAMMAR, "source_pdf": PART_1, "source_page": "4"}
    surface = (
        "S02 Pre-case management" if number == 1 else
        "S03/S04 creation and intake" if number == 2 else
        "S04 Upload & Mapping" if number <= 7 else
        "S05 Preliminary Analysis"
    )
    return {"surface": surface, "authority": "VISUAL_GRAMMAR_ONLY",
            "reference": GRAMMAR, "source_pdf": PART_2B, "source_page": "6"}


def main() -> None:
    images = []
    for path in sorted(SCREENSHOTS.glob("*.png")):
        data = path.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", path
        width, height = struct.unpack(">II", data[16:24])
        assert (width, height) == (1440, 900), path
        images.append({"file": path.name, "sha256": hashlib.sha256(data).hexdigest(),
                       "width": width, "height": height, **category(path.name)})
    assert len(images) == 17, len(images)
    artifact = SCREENSHOTS / "g11k-result-downloaded.xlsx"
    content = artifact.read_bytes()
    payload = {
        "authority_index": f"{VISUAL_ROOT}/README.md",
        "source": "Real authenticated browser, frontend + FastAPI + PostgreSQL + S3 object storage",
        "images": images,
        "downloaded_result": {"file": artifact.name, "size": len(content),
                              "sha256": hashlib.sha256(content).hexdigest()},
    }
    (SCREENSHOTS / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
