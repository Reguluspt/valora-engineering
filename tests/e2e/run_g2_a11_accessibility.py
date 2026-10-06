"""A11 real Fluent field errors, drawer keys and modal focus, without evidence writes."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    base = os.environ.get("A11_BASE_URL", "http://127.0.0.1:5173")
    project = os.environ["A11_PROJECT_ID"]
    evidence = Path(os.environ["A11_EVIDENCE_DIR"])
    evidence.mkdir(parents=True, exist_ok=True)
    mutations = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("request", lambda request: mutations.append(request.url) if request.method == "POST" and "/price-evidence/" in request.url else None)
        page.goto(base, wait_until="networkidle")
        page.get_by_label("Mã đơn vị").fill(os.environ["A11_ORGANIZATION_SLUG"])
        page.get_by_label("Email").fill("operator@a5.invalid")
        page.get_by_label("Mật khẩu").fill(os.environ["A11_SYNTHETIC_PASSWORD"])
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.goto(f"{base}/#/workbench/projects/{project}")
        page.get_by_role("button", name="Tải lại trạng thái nguồn giá", exact=True).wait_for()
        page.wait_for_load_state("networkidle")
        page.locator("tr[aria-label]").first.click()
        price = page.get_by_role("tab", name="Nguồn giá & Chứng cứ", exact=True)
        price.focus()
        page.keyboard.press("ArrowRight")
        expect(page.get_by_role("tab", name="Lịch sử", exact=True)).to_be_focused()
        page.keyboard.press("ArrowLeft")
        expect(price).to_be_focused()
        page.keyboard.press("Enter")
        expect(price).to_have_attribute("aria-selected", "true")
        trigger = page.get_by_role("button", name="Đăng ký nguồn giá", exact=True)
        expect(trigger).to_be_enabled()
        trigger.focus()
        page.keyboard.press("Enter")
        dialog = page.get_by_role("dialog")
        origin = dialog.get_by_label("Nhà xuất bản / tác giả / nguồn gốc")
        origin.fill("a" * 2001)
        expect(origin).to_have_attribute("aria-invalid", "true")
        described = origin.get_attribute("aria-describedby")
        assert described
        assert any("Tối đa 2000 ký tự" in page.locator("[id='" + identity + "']").inner_text() for identity in described.split())
        expect(dialog.get_by_role("button", name="Xác nhận đăng ký nguồn", exact=True)).to_be_disabled()
        for key in ["Tab"] * 25 + ["Shift+Tab"] * 25:
            page.keyboard.press(key)
            assert dialog.evaluate("el => el.contains(document.activeElement)")
        page.keyboard.press("Escape")
        expect(trigger).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.get_by_role("button", name="Xem ngữ cảnh tài sản", exact=True)).to_be_focused()
        confirmation = page.get_by_role("button", name="Xác nhận lại bộ chứng cứ toàn hồ sơ", exact=True)
        capture = None
        if confirmation.count():
            confirmation.click()
            expect(dialog).to_be_visible()
            expect(dialog).to_contain_text("toàn bộ 3 tài sản")
            dialog.get_by_role("textbox").fill("Đã xem xét các nguồn hiện tại; lý do tổng hợp để kiểm tra hộp thoại")
            expect(dialog.get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True)).to_be_enabled()
            capture = "10-whole-set-reconfirmation-dialog.png"
            page.screenshot(path=str(evidence / capture), animations="disabled")
            page.keyboard.press("Escape")
            expect(confirmation).to_be_focused()
        assert not mutations
        (evidence / "accessibility-evidence.json").write_text(json.dumps({"project_id": project,
            "capture": capture,
            "viewport": {"width": 1440, "height": 900}, "result": "PASS", "checks": ["tab arrows and Enter",
                "labelled field error aria-invalid/describedby", "50 forward/backward focus-trap checks",
                "Escape returns modal trigger", "drawer Escape returns context trigger", "zero evidence mutations"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
