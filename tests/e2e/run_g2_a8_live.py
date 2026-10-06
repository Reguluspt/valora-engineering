"""A8 browser acceptance against real APIs; no mocked responses or SQL lifecycle writes."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["A8_EVIDENCE_DIR"])
    evidence.mkdir(parents=True, exist_ok=True)
    project = os.environ["A8_PROJECT_ID"]
    base = os.environ.get("A8_BASE_URL", "http://localhost:5173")
    checkpoints = {}
    commands = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=os.environ.get("A8_BROWSER_CHANNEL", "chrome"), headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.set_default_timeout(20000)
        api = f"{base}/api/v1/projects/{project}"
        def read(path):
            response = context.request.get(api + path)
            assert response.ok, (path, response.status)
            return response.json()
        def checkpoint(name):
            state = read("/case-state")
            region = page.get_by_role("region", name="Chuẩn bị danh mục tài sản")
            expect(region).to_have_attribute("aria-busy", "false")
            expect(page.get_by_role("dialog")).to_have_count(0)
            result = next(s for s in state["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"]
            expect(region.locator(".asset-review-heading")).to_contain_text({"COMPLETE": "Hoàn tất", "STALE": "Cần xem lại",
                "INCOMPLETE": "Chưa hoàn tất", "BLOCKED": "Bị chặn", "NOT_AVAILABLE": "Chưa khả dụng"}[result])
            checkpoints[name] = {"case_version": state["case_version"], "current_stage": state["current_stage"],
                                 "stages": state["stages"], "next_action": state["next_action"]}
            page.screenshot(path=str(evidence / f"{name}.png"), full_page=True)
            print(name, flush=True)
        def observe(response):
            if response.request.method == "POST" and "/asset-workbench/" in response.url:
                payload = response.request.post_data_json
                commands.append({"path": response.url.rsplit("/", 1)[-1], "status": response.status,
                                 "member_count": len(payload["expected_line_versions"]), "explicit_confirm": payload["confirm"]})
        page.on("response", observe)
        page.goto(base, wait_until="networkidle")
        page.get_by_label("Mã đơn vị").fill(os.environ.get("A8_ORGANIZATION_SLUG", "a5-synthetic"))
        page.get_by_label("Email").fill("operator@a5.invalid")
        page.get_by_label("Mật khẩu").fill(os.environ["A8_SYNTHETIC_PASSWORD"])
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        page.get_by_role("button", name="Tải lại trạng thái rà soát", exact=True).wait_for()
        csrf = next(cookie["value"] for cookie in context.cookies() if cookie["name"] == "XSRF-TOKEN")
        headers = {"X-CSRF-Token": csrf, "Origin": base}
        # Set up the missing-description scenario using only the existing confirmed value path.
        for line in read("/asset-lines")["items"]:
            saved = context.request.patch(api + f'/asset-lines/{line["id"]}/draft', data={
                "field_key": "description", "draft_value": "", "base_value": line["description"], "version_token": line["version_token"]}, headers=headers)
            assert saved.ok
            committed = context.request.post(api + f'/asset-lines/{line["id"]}/draft/commit', data={
                "field_keys": ["description"], "confirm": True, "version_token": line["version_token"]}, headers=headers)
            assert committed.ok
        page.reload(wait_until="networkidle")
        def review_all():
            for _ in range(16):
                with page.expect_response(lambda response: response.request.method == "GET" and response.url.endswith("/case-state")):
                    page.get_by_role("button", name="Tải lại trạng thái rà soát", exact=True).click()
                page.wait_for_load_state("networkidle")
                state = read("/case-state")
                if next(s for s in state["stages"] if s["stage"] == "ASSET_REVIEW")["result"] == "COMPLETE":
                    return
                action = state["next_action"]
                key = action["semantic_route_key"]
                assert key in ("asset_review_line_validate_required", "asset_review_line_review_required"), action
                label = "Kiểm tra dữ liệu" if key.endswith("validate_required") else "Chấp nhận"
                page.get_by_role("region", name="Rà soát tài sản").get_by_role("button", name=label, exact=True).click()
                dialog = page.get_by_role("dialog")
                if dialog.get_by_role("textbox").count():
                    dialog.get_by_role("textbox").fill("Xác nhận bằng chứng hiện tại sau thay đổi")
                with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/validate" if label == "Kiểm tra dữ liệu" else "/review-decision")) as mutation:
                    dialog.get_by_role("button", name="Xác nhận " + label.lower(), exact=True).click()
                assert mutation.value.ok, mutation.value.status
                page.wait_for_load_state("networkidle")
            raise AssertionError("Review did not complete within bounded iterations")
        checkpoint("01-asset-review-prerequisite")
        checkpoint("02-description-required")
        assert not read("/asset-workbench/preparation")["can_confirm"]
        assert all(not line["description"] for line in read("/asset-lines")["items"])
        lines = read("/asset-lines")["items"]
        def description(line, value, name):
            page.locator("tr[aria-label]").filter(has_text=line["asset_name"]).first.click()
            expect(page.get_by_role("region", name="Mô tả tài sản")).to_contain_text(line["asset_name"])
            field = page.get_by_role("textbox", name="Mô tả nháp", exact=True)
            expect(field).to_be_enabled()
            old = next(item for item in read("/asset-lines")["items"] if item["id"] == line["id"])["description"]
            field.fill(value)
            page.get_by_role("button", name="Lưu nháp", exact=True).click()
            expect(page.get_by_role("button", name="Áp dụng nháp mô tả", exact=True)).to_be_enabled()
            assert next(item for item in read("/asset-lines")["items"] if item["id"] == line["id"])["description"] == old
            checkpoint(name + "-draft")
            page.get_by_role("button", name="Áp dụng nháp mô tả", exact=True).click()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/draft/commit")) as mutation:
                page.get_by_role("dialog").get_by_role("button", name="Xác nhận áp dụng mô tả", exact=True).click()
            assert mutation.value.ok
            page.wait_for_load_state("networkidle")
            assert next(item for item in read("/asset-lines")["items"] if item["id"] == line["id"])["description"] == value
        for index, line in enumerate(lines):
            description(line, f"Thiết bị tổng hợp {index + 1}; cấu hình và tình trạng đã mô tả cho việc so sánh sau này.", f"03-description-{index + 1}")
        review_all()
        checkpoint("03-review-complete-preparation-action")
        assert read("/case-state")["next_action"]["semantic_route_key"] == "asset_workbench_prepare_required"
        page.get_by_role("button", name="Tổng quan hồ sơ", exact=True).click()
        page.get_by_role("button", name="Tiếp tục xử lý", exact=True).click()
        expect(page.get_by_role("region", name="Chuẩn bị danh mục tài sản")).to_be_visible()
        assert not commands
        page.get_by_role("textbox", name="Tìm theo tên tài sản", exact=True).fill(lines[0]["asset_name"])
        expect(page.locator("tr[aria-label]")).to_have_count(1)
        assert all(item["appraised_unit_price"] is None for item in read("/asset-lines")["items"])
        confirm = page.get_by_role("button", name="Xác nhận toàn bộ danh mục", exact=True)
        expect(confirm).to_be_visible()
        confirm.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_contain_text(f"toàn bộ {len(lines)} tài sản")
        page.get_by_role("button", name="Hủy", exact=True).click()
        expect(confirm).to_be_focused()
        assert not commands
        confirm.click()
        page.keyboard.press("Escape")
        expect(confirm).to_be_focused()
        confirm.click()
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as mutation:
            dialog.get_by_role("button", name="Xác nhận danh mục", exact=True).click()
        assert mutation.value.ok
        page.wait_for_load_state("networkidle")
        checkpoint("04-complete-without-price")
        state = read("/case-state")
        assert state["current_stage"] == "ASSET_WORKBENCH" and state["next_action"]["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
        assert next(s for s in state["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "COMPLETE"
        description(lines[0], "Mô tả chính thức đã chỉnh sửa theo dữ liệu hiện tại.", "05-official-change")
        checkpoint("06-stale-after-change")
        assert next(s for s in read("/case-state")["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "STALE"
        review_all()
        page.get_by_role("button", name="Xác nhận lại toàn bộ danh mục", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("button", name="Xác nhận danh mục", exact=True)).to_be_disabled()
        dialog.get_by_role("textbox").fill("Mô tả thay đổi đã được kiểm tra và rà soát lại")
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as mutation:
            dialog.get_by_role("button", name="Xác nhận danh mục", exact=True).click()
        assert mutation.value.ok
        page.wait_for_load_state("networkidle")
        checkpoint("07-reconfirmed")
        page.get_by_role("button", name="Rút xác nhận danh mục", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("button", name="Xác nhận rút", exact=True)).to_be_disabled()
        dialog.get_by_role("textbox").fill("Cần xem lại tuyên bố sẵn sàng của danh mục")
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/withdraw")) as mutation:
            dialog.get_by_role("button", name="Xác nhận rút", exact=True).click()
        assert mutation.value.ok
        page.wait_for_load_state("networkidle")
        checkpoint("08-withdrawn")
        assert next(s for s in read("/case-state")["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "INCOMPLETE"
        page.get_by_role("button", name="Xác nhận lại toàn bộ danh mục", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("textbox").fill("Thử xác nhận sau khi xem lại")
        line = read("/asset-lines")["items"][0]
        csrf = next(cookie["value"] for cookie in context.cookies() if cookie["name"] == "XSRF-TOKEN")
        changed = context.request.patch(api + f'/asset-lines/{line["id"]}',
                                        data={"quantity": float(line["quantity"]) + 1, "row_version": int(line["version_token"])},
                                        headers={"X-CSRF-Token": csrf, "Origin": base})
        assert changed.ok, changed.status
        before = len(commands)
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as mutation:
            dialog.get_by_role("button", name="Xác nhận danh mục", exact=True).click()
        assert mutation.value.status == 409
        page.wait_for_load_state("networkidle")
        assert len(commands) == before + 1 and commands[-1]["status"] == 409
        expect(page.get_by_text("Dữ liệu hoặc điều kiện đã thay đổi.", exact=False)).to_be_visible()
        checkpoint("09-conflict-refresh-no-replay")
        review_all()
        page.get_by_role("button", name="Xác nhận lại toàn bộ danh mục", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("textbox").fill("Đã tải lại dữ liệu và xác nhận điều kiện hiện tại")
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as mutation:
            dialog.get_by_role("button", name="Xác nhận danh mục", exact=True).click()
        assert mutation.value.ok
        page.wait_for_load_state("networkidle")
        checkpoint("10-final-downstream-hold")
        assert read("/case-state")["next_action"]["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
        assert not page.get_by_role("button", name="Nguồn giá và chứng cứ", exact=True).count()
        (evidence / "browser-evidence.json").write_text(json.dumps({"project_id": project, "checkpoints": checkpoints,
                                                                   "commands": commands}, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
