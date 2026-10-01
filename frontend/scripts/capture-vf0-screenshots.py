"""Capture synthetic VF0 browser evidence against the local fixture API and Vite app.

Run the fixture API (`npm run browser:fixture`) and Vite (`npm run dev`) first.
Requires the local Python Playwright package and Chrome or Edge executable.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "docs" / "implementation" / "vf0-screenshots"
BASE = "http://localhost:5173/"
FIXTURE = "http://127.0.0.1:8000/__fixture/scenario"
REFERENCE = "docs/design/visual-reference/v2.3"
CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)


def browser_executable() -> str:
    configured = os.environ.get("VALORA_CHROMIUM_PATH")
    if configured and Path(configured).is_file():
        return configured
    for path in CHROME_PATHS:
        if path.is_file():
            return str(path)
    raise RuntimeError("Set VALORA_CHROMIUM_PATH to an installed Chrome or Edge executable")


def scenario(**values: str) -> None:
    with urlopen(f"{FIXTURE}?{urlencode(values)}", timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"Fixture rejected scenario: {values}")


def open_surface(page, route: str, selector: str) -> None:
    page.goto(f"{BASE}#{route}", wait_until="domcontentloaded")
    page.reload(wait_until="domcontentloaded")
    page.locator(selector).first.wait_for(timeout=15000)
    page.evaluate("document.fonts.ready")


def capture(page, name: str, route: str, selector: str, authority: str, references: list[str], records: list[dict]) -> None:
    open_surface(page, route, selector)
    capture_current(page, name, route, authority, references, records)


def capture_current(page, name: str, route: str, authority: str, references: list[str], records: list[dict]) -> None:
    assert page.get_by_role("main").count() == 1, f"{name}: expected one main landmark"
    assert page.get_by_role("navigation", name="Điều hướng chính").count() == 1, f"{name}: missing primary navigation"
    assert page.locator('nav[aria-label="Điều hướng chính"] [aria-current="page"]').count() <= 1, f"{name}: multiple current pages"
    path = OUTPUT / name
    page.screenshot(path=str(path), full_page=False, animations="disabled")
    records.append({
        "candidate": f"docs/implementation/vf0-screenshots/{name}",
        "viewport": f"{page.viewport_size['width']}x{page.viewport_size['height']}",
        "fixture": route,
        "authority_type": authority,
        "references": references,
    })
    print(name)


def create_mapping_proposal(page) -> None:
    open_surface(page, "/workbench/projects/precase-acceptance/preliminary-intake", "select")
    page.get_by_label("Bản phân tích cấu trúc").select_option("structure-precase")
    page.locator('input[name="workbook-candidate"]').check()
    page.get_by_role("button", name="Tạo đề xuất ánh xạ").click()
    page.locator('[data-mapping-stage="proposal"]').wait_for(timeout=15000)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=browser_executable(), headless=True, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            reduced_motion="reduce",
        )
        page.clock.set_fixed_time("2026-09-30T00:00:00+07:00")
        page.goto(f"{BASE}#/workbench/projects/project-acceptance/overview", wait_until="domcontentloaded")
        page.wait_for_function("document.querySelector('.sidebar') || document.querySelector('input[name=organization_slug]')")
        if page.locator('input[name="organization_slug"]').count():
            page.locator('input[name="organization_slug"]').fill("chi-nhanh-gia-lai")
            page.locator('input[name="email"]').fill("operator@valora.local")
            page.locator('input[name="password"]').fill("fixture-password")
            page.get_by_role("button", name="Đăng nhập").click()
        page.locator(".sidebar").wait_for(timeout=15000)

        scenario(case="normal", projects="populated", precase="upload", ncc="normal", workbench="normal")
        capture(page, "s10-overview-1440x900.png", "/workbench/projects/project-acceptance/overview", "[data-case-stage]",
                "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/s10-orchestration-hub-iteration-2-approved.png"], records)
        capture(page, "s02-management-1440x900.png", "/workbench/preliminary-requests", ".precase-management-table",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s12-workbench-approved.png"], records)
        capture(page, "s03-create-1440x900.png", "/workbench/preliminary-requests/new", ".precase-create-form",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s11-asset-confirmation-approved.png"], records)
        capture(page, "s04-upload-1440x900.png", "/workbench/projects/precase-acceptance/preliminary-intake", ".precase-intake-step",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s12-workbench-approved.png"], records)
        scenario(precase="review")
        create_mapping_proposal(page)
        capture_current(page, "s04-mapping-review-1440x900.png", "/workbench/projects/precase-acceptance/preliminary-intake + synthetic proposal",
                        "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s12-workbench-approved.png"], records)
        scenario(precase="analysis")
        capture(page, "s05-analysis-editable-1440x900.png", "/workbench/projects/precase-acceptance/preliminary-analysis", ".precase-analysis-table tbody tr",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s12-workbench-approved.png"], records)
        for row in range(3, 15):
            page.get_by_label(f"Cơ sở giá dòng {row}").fill("Thuyết minh đơn giá")
            page.get_by_label(f"Giá tham chiếu dòng {row}").fill("1000000")
            page.get_by_label(f"Vận chuyển dòng {row}").fill("5")
            page.get_by_label(f"Đơn giá đề xuất dòng {row}").fill("1050000")
            page.get_by_label(f"Xác nhận rà soát dòng {row}").check()
        page.get_by_role("button", name="Chốt phân tích sơ bộ", exact=True).click()
        page.get_by_role("button", name="Xác nhận chốt", exact=True).click()
        page.locator('[data-analysis-state="completed"]').wait_for(timeout=15000)
        page.screenshot(path=str(OUTPUT / "s05-analysis-completed-1440x900.png"), full_page=False, animations="disabled")
        records.append({"candidate": "docs/implementation/vf0-screenshots/s05-analysis-completed-1440x900.png", "viewport": "1440x900",
                        "fixture": "/workbench/projects/precase-acceptance/preliminary-analysis + confirmed synthetic rows",
                        "authority_type": "VISUAL_GRAMMAR_ONLY", "references": [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/s12-workbench-approved.png"]})
        print("s05-analysis-completed-1440x900.png")

        scenario(precase="review")
        create_mapping_proposal(page)
        page.get_by_label("Tôi đã rà soát vùng bảng và từng vai trò cột.").check()
        scenario(precase="conflict")
        page.get_by_role("button", name="Xác nhận ánh xạ").click()
        page.locator(".valora-message--warning").wait_for(timeout=15000)
        capture_current(page, "s04-conflict-1440x900.png", "/workbench/projects/precase-acceptance/preliminary-intake + synthetic 409",
                        "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/cross-product-state-pattern-board-iteration-1.png"], records)
        scenario(precase="upload", workbench="normal")
        capture(page, "s12-workbench-1440x900.png", "/workbench/projects/workbench-acceptance", ".workbench-container",
                "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/s12-workbench-approved.png"], records)
        page.locator(".grid-row").first.click()
        page.locator("#asset-context-drawer").wait_for(timeout=15000)
        page.locator("#asset-context-drawer button:focus").wait_for(timeout=15000)
        capture_current(page, "s13-asset-context-drawer-1440x900.png", "/workbench/projects/workbench-acceptance + drawer",
                        "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/s13-asset-context-drawer-approved.png"], records)
        page.get_by_role("button", name="Nguồn giá & chứng cứ").click()
        page.get_by_role("region", name="Nguồn giá & chứng cứ").wait_for(timeout=15000)
        capture_current(page, "price-evidence-1440x900.png", "/workbench/projects/workbench-acceptance + price/evidence drawer",
                        "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/price-evidence-approved.png"], records)
        scenario(ncc="normal")
        open_surface(page, "/workbench/projects/project-acceptance/ncc-selection", ".ncc-page")
        page.locator(".ncc-table-row").first.click()
        page.locator(".ncc-drawer").wait_for(timeout=15000)
        assert page.get_by_role("dialog", name="Chi tiết dòng tài sản").count() == 1, "NCC drawer has no dialog landmark"
        page.locator(".ncc-drawer-close:focus").wait_for(timeout=15000)
        capture_current(page, "ncc-selection-1440x900.png", "/workbench/projects/project-acceptance/ncc-selection + drawer",
                        "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/ncc-selection-iteration-1-approved.png"], records)
        page.locator('.ncc-candidate input[type="radio"]:not([disabled])').first.check()
        page.locator('[data-primary-action="true"]').scroll_into_view_if_needed()
        capture_current(page, "ncc-selection-candidate-selected-1440x900.png",
                        "/workbench/projects/project-acceptance/ncc-selection + eligible quote selected",
                        "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/ncc-selection-iteration-1-approved.png"], records)
        scenario(m365="normal")
        capture(page, "m365-workspace-1440x900.png", "/workbench/projects/project-acceptance/documents", ".m365-page",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md", f"{REFERENCE}/baselines/m365-return-revalidation-iteration-1.png"], records)
        capture(page, "m365-oauth-return-1440x900.png", "/workbench/m365/return", ".m365-return-page",
                "VISUAL_GRAMMAR_ONLY", [f"{REFERENCE}/README.md"], records)
        scenario(case="normal")
        page.set_viewport_size({"width": 1920, "height": 1080})
        capture(page, "s10-overview-1920x1080.png", "/workbench/projects/project-acceptance/overview", "[data-case-stage]",
                "EXACT_VISUAL_BASELINE", [f"{REFERENCE}/baselines/s10-orchestration-hub-iteration-2-approved.png"], records)
        browser.close()

    (OUTPUT / "manifest.json").write_text(json.dumps({"synthetic_only": True, "captures": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
