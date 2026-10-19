"""Real API/auth/UI evidence using an existing locally installed Chromium."""
import json
import os
import subprocess
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]
DOCKER = Path(os.environ["LOCALAPPDATA"]) / "Programs/DockerDesktop/resources/bin/docker.exe"
EVIDENCE = Path(os.environ["ISSUE208_EVIDENCE_DIR"])
BASE = "http://localhost:51208"
PASSWORD = os.environ["ISSUE208_SYNTHETIC_PASSWORD"]


def main():
    expect.set_options(timeout=30000)
    seeded = subprocess.run([str(DOCKER), "compose", "-f", "tests/e2e/issue208/compose.yml", "exec", "-T", "backend", "python", "/acceptance/browser_fixtures.py"], cwd=ROOT, capture_output=True, text=True, check=True)
    fixtures = json.loads(seeded.stdout.strip().splitlines()[-1])
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = {}
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, executable_path=os.environ.get("ISSUE208_BROWSER", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))

        def open_case(name, width=1440, height=900):
            f = fixtures[name]
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto(BASE, wait_until="domcontentloaded")
            page.get_by_label("Mã đơn vị").fill(f["slug"])
            page.get_by_label("Email").fill("operator@issue208.invalid")
            page.get_by_label("Mật khẩu").fill(PASSWORD)
            page.get_by_role("button", name="Đăng nhập", exact=True).click()
            page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
            page.goto(f'{BASE}/#/workbench/projects/{f["project_id"]}', wait_until="domcontentloaded")
            page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
            region = page.get_by_role("region", name="Nhập nguyên bản báo giá TXT", exact=True)
            expect(region).to_have_attribute("aria-busy", "false")
            return f, context, page, region

        f, context, page, region = open_case("normal")
        imports = []
        page.on("request", lambda req: imports.append(req.method) if "/quotation-documents/import" in req.url and req.method == "POST" else None)
        trigger = region.get_by_role("button", name="Nhập tài liệu báo giá TXT", exact=True)
        trigger.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("Synthetic original import acceptance")
        text = '<script>window.ISSUE208_EXECUTED=true</script>\r\n' + "Báo giá tổng hợp 😀\n" * 350
        content = b"\xef\xbb\xbf" + text.encode()
        dialog.locator('input[type="file"]').set_input_files({"name": "synthetic-vietnamese.txt", "mimeType": "text/plain", "buffer": content})
        preview = dialog.get_by_role("textbox", name="Xem trước văn bản thuần (tối đa 4.096 ký tự Unicode)")
        expect(preview).to_have_value(__import__("re").compile("<script>"))
        assert len(preview.input_value()) <= 4096
        assert page.evaluate("window.ISSUE208_EXECUTED") is None
        assert imports == []
        expect(dialog.get_by_text("Bản xem trước đã được rút gọn. Tệp gốc được lưu đủ nguyên byte.")).to_be_visible()
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        expect(trigger).to_be_focused()
        assert imports == []
        trigger.click()
        dialog.locator('input[type="file"]').set_input_files({"name": "synthetic-vietnamese.txt", "mimeType": "text/plain", "buffer": content})
        confirm = dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True)
        expect(confirm).to_be_enabled()
        for _ in range(7):
            page.keyboard.press("Tab")
            assert dialog.evaluate("element => element.contains(document.activeElement)")
        page.screenshot(path=str(EVIDENCE / "txt-confirm-desktop.png"), full_page=True, animations="disabled")
        dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True).evaluate("element => {element.click(); element.click();}")
        expect(region.get_by_text("Đã lưu nguyên bản tài liệu", exact=True)).to_be_visible()
        expect(dialog).not_to_be_visible()
        assert imports == ["POST"]
        assert page.evaluate("Object.keys(sessionStorage).filter(k=>k.startsWith('valora:quotation-txt:')).length") == 0
        results["normal"] = dict(real_auth_without_workbench_edit=True, escaped_bounded_preview=True, cancel_no_dispatch=True, double_click_one_post=True, focus_containment=True)
        context.close()

        f, context, page, region = open_case("lost", 1280, 720)
        commands = []
        def lost_response(route):
            upstream = route.fetch()
            assert upstream.status == 201
            commands.append(upstream.json()["command_id"])
            route.abort("connectionreset")
        page.route("**/quotation-documents/import", lost_response)
        region.get_by_role("button", name="Nhập tài liệu báo giá TXT", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.locator('input[type="file"]').set_input_files({"name": "synthetic-lost.txt", "mimeType": "text/plain", "buffer": b"synthetic lost response\r\n"})
        expect(dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True)).to_be_enabled()
        dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True).click()
        expect(dialog.get_by_text("Chưa xác định được kết quả. Kiểm tra biên nhận của thao tác gốc.")).to_be_visible()
        assert len(commands) == 1
        stored = page.evaluate("Object.entries(sessionStorage).filter(([k])=>k.startsWith('valora:quotation-txt:')).map(([,v])=>v)")
        assert len(stored) == 1 and "synthetic-lost" not in stored[0] and "synthetic lost response" not in stored[0]
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
        expect(region.get_by_text("Kết quả chưa xác định", exact=True)).to_be_visible()
        with page.expect_response(lambda response: "/quotation-documents/import-receipts/" in response.url and response.request.method == "GET", timeout=60000) as checked:
            region.get_by_role("button", name="Kiểm tra kết quả", exact=True).click()
        checked_status = checked.value.json()
        assert checked.value.status == 200 and checked_status["outcome"] == "finalized", checked.value.status
        expect(region.get_by_text("Đã lưu nguyên bản tài liệu", exact=True)).to_be_visible()
        assert len(commands) == 1
        page.screenshot(path=str(EVIDENCE / "txt-lost-response-laptop.png"), full_page=True, animations="disabled")
        results["lost_response"] = dict(committed=True, persisted_identity_only=True, remount_get_only_reconciliation=True, original_command_id=commands[0])
        context.close()

        _, context, page, region = open_case("viewer")
        region.get_by_role("button", name="Nhập tài liệu báo giá TXT", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.locator('input[type="file"]')).to_be_disabled()
        expect(dialog.get_by_text("Chưa được nhập tài liệu", exact=True)).to_be_visible()
        results["viewer"] = dict(server_capability_denied=True)
        context.close()

        f, context, page, region = open_case("stale", 1280, 720)
        stale_posts = []
        def change_before_dispatch(route):
            subprocess.run([str(DOCKER), "compose", "-f", "tests/e2e/issue208/compose.yml", "exec", "-T", "backend", "python",
                "/acceptance/browser_fixtures.py", "--bump-project", f["project_id"]], cwd=ROOT, capture_output=True, check=True)
            stale_posts.append(True)
            route.continue_()
        page.route("**/quotation-documents/import", change_before_dispatch)
        region.get_by_role("button", name="Nhập tài liệu báo giá TXT", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.locator('input[type="file"]').set_input_files({"name": "synthetic-stale.txt", "mimeType": "text/plain", "buffer": b"synthetic original"})
        dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True).click()
        expect(dialog.get_by_text("Xung đột phiên bản hoặc tệp gốc. Kiểm tra kết quả của lần nhập này.")).to_be_visible()
        assert stale_posts == [True]
        expect(dialog.get_by_role("button", name="Khôi phục lần nhập này", exact=True)).to_be_disabled()
        dialog.get_by_role("button", name="Kiểm tra kết quả", exact=True).click()
        expect(dialog.get_by_text("Máy chủ chưa ghi nhận lần nhập này. Chọn lại tệp, xem lại hồ sơ và xác nhận một lần nhập mới.")).to_be_visible()
        expect(dialog.get_by_role("button", name="Xác nhận nhập tài liệu", exact=True)).to_be_disabled()
        assert stale_posts == [True]
        results["stale"] = dict(real_project_cas_conflict=True, no_automatic_retry=True)
        context.close()
        browser.close()
    (EVIDENCE / "browser-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
