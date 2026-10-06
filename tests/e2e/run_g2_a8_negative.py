"""Real authentication, tenant, session and read-only browser negatives on synthetic A8 data."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    base = os.environ.get("A8_BASE_URL", "http://localhost:5173")
    project = os.environ["A8_PROJECT_ID"]
    evidence = Path(os.environ["A8_EVIDENCE_DIR"])
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.environ.get("A8_BROWSER_CHANNEL", "chrome"), headless=True)
        api = f"{base}/api/v1/projects/{project}"
        anonymous = browser.new_context()
        results["unauthenticated"] = anonymous.request.get(api + "/asset-workbench/preparation").status
        assert results["unauthenticated"] == 401

        def login(email):
            context = browser.new_context(viewport={"width": 1024, "height": 768})
            page = context.new_page()
            page.goto(base, wait_until="networkidle")
            page.get_by_label("Mã đơn vị").fill(os.environ.get("A8_ORGANIZATION_SLUG", "a5-synthetic"))
            page.get_by_label("Email").fill(email)
            page.get_by_label("Mật khẩu").fill(os.environ["A8_SYNTHETIC_PASSWORD"])
            page.get_by_role("button", name="Đăng nhập", exact=True).click()
            page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
            return context, page

        operator, page = login("operator@a5.invalid")
        csrf = next(cookie["value"] for cookie in operator.cookies() if cookie["name"] == "XSRF-TOKEN")
        headers = {"X-CSRF-Token": csrf, "Origin": base}
        results["malformed_contract"] = operator.request.post(api + "/asset-workbench/confirm", data={"confirm": False}, headers=headers).status
        assert results["malformed_contract"] == 400
        foreign = os.environ["A8_FOREIGN_PROJECT_ID"]
        denied = operator.request.get(f"{base}/api/v1/projects/{foreign}/asset-workbench/preparation")
        results["foreign_tenant"] = denied.status
        assert denied.status == 404 and foreign not in denied.text()
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        expect(page.get_by_role("button", name="Rút xác nhận danh mục", exact=True)).to_be_visible()
        expect(page.locator(".grid-scroll-viewport")).to_be_visible()
        page.screenshot(path=str(evidence / "small-laptop-layout-check.png"), full_page=True)
        assert page.locator(".grid-scroll-viewport").bounding_box()["height"] >= 80
        page.get_by_role("button", name="Rút xác nhận danh mục", exact=True).click()
        expect(page.get_by_role("dialog").get_by_role("button", name="Xác nhận rút", exact=True)).to_be_disabled()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(page.get_by_role("button", name="Rút xác nhận danh mục", exact=True)).to_be_focused()
        page.screenshot(path=str(evidence / "11-small-laptop-keyboard.png"), full_page=True)
        session = operator.request.post(base + "/api/v1/workbench/sessions", data={"project_id": project}, headers=headers)
        assert session.ok
        assert operator.request.post(base + f'/api/v1/workbench/sessions/{session.json()["id"]}/close', headers=headers).ok
        results["closed_session"] = operator.request.get(api + "/asset-workbench/preparation").status
        assert results["closed_session"] == 404
        assert next(s for s in operator.request.get(api + "/case-state").json()["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "COMPLETE"

        viewer, page = login("viewer@a5.invalid")
        results["viewer_preparation_denied"] = viewer.request.get(api + "/asset-workbench/preparation").status
        assert results["viewer_preparation_denied"] == 403
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        region = page.get_by_role("region", name="Chuẩn bị danh mục tài sản")
        expect(region).to_contain_text("Hoàn tất")
        assert not region.get_by_role("button", name="Rút xác nhận danh mục", exact=True).count()
        assert not region.get_by_role("button", name="Xác nhận lại toàn bộ danh mục", exact=True).count()
        page.screenshot(path=str(evidence / "12-viewer-read-only-completion.png"), full_page=True)
        results["readonly_completion_preserved"] = True
        results["keyboard_escape_focus"] = True
        results["small_laptop_grid_visible"] = True
        (evidence / "browser-negatives.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
