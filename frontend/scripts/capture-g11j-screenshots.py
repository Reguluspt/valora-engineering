"""Exercise G1.1J on the synthetic fixture and capture reproducible 1440x900 evidence.

Start `npm run browser:fixture` and Vite with `VITE_API_BASE_URL=/` first.
Requires Python Playwright and a local Chrome or Edge executable.
"""

import json
import os
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "docs" / "implementation" / "g11j-screenshots"
BASE = "http://127.0.0.1:5173/"
ROUTE = "/workbench/projects/completion-acceptance/preliminary-completion"
FIXTURE = "http://127.0.0.1:8000/__fixture/scenario?completion="
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


def scenario(name: str) -> None:
    with urlopen(FIXTURE + name, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"Fixture rejected completion scenario: {name}")


def capture(page, filename: str, state: str, records: list[dict]) -> None:
    assert page.get_by_role("main").count() == 1, f"{state}: missing main landmark"
    assert page.get_by_role("navigation", name="Điều hướng chính").count() == 1, f"{state}: missing navigation"
    assert page.locator('nav[aria-label="Điều hướng chính"] [aria-current="page"]').count() <= 1
    page.screenshot(path=str(OUTPUT / filename), full_page=False, animations="disabled")
    records.append({
        "candidate": f"docs/implementation/g11j-screenshots/{filename}",
        "viewport": "1440x900",
        "state": state,
        "authority_type": "VISUAL_GRAMMAR_ONLY_WITH_APPROVED_LAYOUT_CONTRACT",
        "references": [
            f"{REFERENCE}/README.md",
            f"{REFERENCE}/VALORA_UIUX_Handoff_v2.3_RELEASE_CONFIRMATION_BASELINE_Part_1.pdf#page=4",
            f"{REFERENCE}/baselines/s10-orchestration-hub-iteration-2-approved.png",
            f"{REFERENCE}/baselines/s12-workbench-approved.png",
            f"{REFERENCE}/baselines/cross-product-state-pattern-board-iteration-1.png",
        ],
    })
    print(filename)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    scenario("ready")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=browser_executable(), headless=True, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1440, "height": 900}, device_scale_factor=1,
            locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh", reduced_motion="reduce",
            accept_downloads=True,
        )
        page.clock.set_fixed_time("2026-10-01T08:00:00+07:00")
        page.goto(f"{BASE}#{ROUTE}", wait_until="domcontentloaded")
        page.wait_for_function("document.querySelector('.sidebar') || document.querySelector('input[name=organization_slug]')")
        if page.locator('input[name="organization_slug"]').count():
            page.locator('input[name="organization_slug"]').fill("chi-nhanh-gia-lai")
            page.locator('input[name="email"]').fill("operator@valora.local")
            page.locator('input[name="password"]').fill("fixture-password")
            page.get_by_role("button", name="Đăng nhập").click()
        page.locator(".precase-completion-page").wait_for(timeout=15000)
        page.evaluate("document.fonts.ready")

        assert page.get_by_role("button", name="Tạo kết quả sơ bộ").count() == 1
        capture(page, "01-result-ready.png", "result-ready", records)
        page.get_by_role("button", name="Tạo kết quả sơ bộ").click()
        page.get_by_role("dialog", name="Xác nhận thao tác Pre-case").get_by_role("button", name="Xác nhận", exact=True).click()
        page.get_by_role("button", name="Tải tệp Excel").wait_for(timeout=15000)
        assert page.get_by_role("button", name="Tạo kết quả sơ bộ").count() == 0
        capture(page, "02-result-generated.png", "result-generated/customer-unbound", records)
        with page.expect_download() as download_info:
            page.get_by_role("button", name="Tải tệp Excel").click()
        assert download_info.value.suggested_filename == "ket-qua-so-bo-v2.xlsx"

        page.get_by_label("Tên, mã số thuế hoặc số điện thoại").fill("An Phú")
        page.get_by_role("button", name="Tìm khách hàng").click()
        page.get_by_role("radio", name="Thiết bị An Phú MST 0101234567").check()
        capture(page, "03-customer-selected.png", "customer-selected/unbound", records)
        page.get_by_role("button", name="Gắn khách hàng đã chọn").click()
        page.get_by_role("dialog", name="Xác nhận thao tác Pre-case").get_by_role("button", name="Xác nhận", exact=True).click()
        page.get_by_role("button", name="Chuyển sang thẩm định chính thức").wait_for(timeout=15000)
        assert page.get_by_role("button", name="Gắn khách hàng đã chọn").count() == 0
        capture(page, "04-customer-bound.png", "customer-bound/intake-ready", records)
        page.get_by_role("button", name="Chuyển sang thẩm định chính thức").click()
        page.get_by_role("dialog", name="Xác nhận thao tác Pre-case").wait_for()
        capture(page, "05-intake-confirmation.png", "intake-confirmation", records)
        page.get_by_role("button", name="Xác nhận chuyển chính thức").click()
        page.get_by_text("Đã tiếp nhận chính thức").wait_for(timeout=15000)
        assert page.get_by_role("heading", name="Kết quả sơ bộ & tiếp nhận").count() == 1
        assert page.get_by_role("button", name="Chuyển sang thẩm định chính thức").count() == 0
        assert page.get_by_role("button", name="Tạo kết quả sơ bộ").count() == 0
        capture(page, "07-intake-frozen.png", "intake-committed/read-only", records)

        scenario("blocking")
        page.reload(wait_until="domcontentloaded")
        page.get_by_text("Có vấn đề đang ngăn bước tiếp theo").wait_for(timeout=15000)
        assert page.get_by_role("button", name="Chuyển sang thẩm định chính thức").count() == 0
        assert page.get_by_role("alert").get_by_text("Đang có vấn đề ngăn tiếp nhận chính thức", exact=False).count() == 1
        capture(page, "06-blocking-issue.png", "open-blocking-issue", records)

        scenario("unavailable")
        page.reload(wait_until="domcontentloaded")
        page.get_by_text("Bước Pre-case hiện chưa khả dụng").wait_for(timeout=15000)
        assert page.get_by_role("button", name="Tạo kết quả sơ bộ").count() == 0
        capture(page, "08-result-unavailable.png", "result-unavailable", records)
        browser.close()

    (OUTPUT / "manifest.json").write_text(json.dumps({
        "synthetic_only": True, "route": ROUTE, "captures": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
