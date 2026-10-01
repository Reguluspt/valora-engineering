"""Read-only integrated browser checks for basic access and request sanity."""

import json
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
BASE = "http://localhost"
API = "/api/v1"
PROJECT_CODE = os.getenv("G11K_PROJECT_CODE", "G11K-E2E-20261001-007")


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=os.getenv("G11K_BROWSER_CHANNEL"))
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(BASE, wait_until="networkidle")
        page.get_by_label("Mã đơn vị").fill("g11k-synthetic-main")
        page.get_by_label("Email").fill("owner@g11k.invalid")
        page.get_by_label("Mật khẩu").fill(os.environ["G11K_SYNTHETIC_PASSWORD"])
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").click()
        page.get_by_role("heading", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.get_by_role("columnheader").first.wait_for()
        assert page.get_by_role("columnheader").count() > 0
        assert page.get_by_role("button", name="Tạo yêu cầu sơ bộ").count() > 0
        page.keyboard.press("Tab")
        focused = page.evaluate("""() => ({
            tag: document.activeElement?.tagName,
            visible: document.activeElement?.matches(':focus-visible') ?? false,
        })""")
        assert focused["tag"] in {"A", "BUTTON", "INPUT", "SELECT", "TEXTAREA"}, focused
        assert focused["visible"], focused

        resolved = context.request.get(f"{BASE}{API}/projects/resolve?ref={PROJECT_CODE}")
        assert resolved.status == 200
        project_id = resolved.json()["project_id"]
        requests = []
        page.on("request", lambda request: requests.append(request.url)
                if "/api/v1/" in request.url else None)
        start = time.perf_counter()
        page.goto(f"{BASE}/#/workbench/projects/{project_id}/overview", wait_until="networkidle")
        page.get_by_role("heading", name="Tổng quan hồ sơ").wait_for()
        overview_ms = round((time.perf_counter() - start) * 1000)
        page.wait_for_timeout(2000)
        case_state_requests = [url for url in requests if "/case-state" in url]
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert page.get_by_text("Tiếp nhận chính thức", exact=True).count() > 0
        report = {
            "project_code": PROJECT_CODE,
            "project_id": project_id,
            "viewport": {"width": 1440, "height": 900},
            "management_table_has_column_headers": True,
            "management_primary_action_is_button": True,
            "keyboard_focus": focused,
            "overview_heading_present": True,
            "overview_navigation_ms": overview_ms,
            "overview_api_request_count_after_2s": len(requests),
            "overview_case_state_request_count_after_2s": len(case_state_requests),
            "overview_no_horizontal_overflow": True,
            "overview_completed_state_present": True,
        }
        (ROOT / "docs/implementation/g11k-browser-sanity-evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
