"""Developer acceptance for #206 only, against an independent disposable real stack.

No PO E2E/SQ certification, provider calls, shared fixture changes or authority mocks.
The lost-response case drops transport only after the real Apply has committed.
"""
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["ISSUE206_EVIDENCE_DIR"])
    fixtures = json.loads((evidence / "fixtures.json").read_text(encoding="utf-8-sig"))
    password = os.environ["ISSUE206_SYNTHETIC_PASSWORD"]
    base = "http://localhost:51206"
    results = {}
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)

        def open_case(name, viewer=False, viewport=None):
            f = fixtures[name]
            context = browser.new_context(viewport=viewport or {"width": 1440, "height": 900})
            page = context.new_page()
            page.set_default_timeout(20000)
            page.goto(base, wait_until="networkidle")
            page.get_by_label("Mã đơn vị").fill(f["organization_slug"])
            page.get_by_label("Email").fill("viewer@issue206.invalid" if viewer else "operator@issue206.invalid")
            page.get_by_label("Mật khẩu").fill(password)
            page.get_by_role("button", name="Đăng nhập", exact=True).click()
            page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
            page.goto(f'{base}/#/workbench/projects/{f["project_id"]}/overview', wait_until="networkidle")
            region = page.get_by_role("region", name="Danh mục nhập sau tiếp nhận")
            expect(region).to_have_attribute("aria-busy", "false")
            return f, context, page, region

        def read(context, f, path):
            response = context.request.get(f'{base}/api/v1/projects/{f["project_id"]}{path}')
            assert response.ok, (path, response.status)
            return response.json()

        def post(context, f, path, payload):
            csrf = next(cookie["value"] for cookie in context.cookies() if cookie["name"] == "XSRF-TOKEN")
            return context.request.post(f'{base}/api/v1/projects/{f["project_id"]}{path}', data=payload,
                                        headers={"X-CSRF-Token": csrf, "Origin": base})

        def validate(page, region):
            region.get_by_role("button", name="Kiểm tra danh mục nhập", exact=True).click()
            expect(region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True)).to_be_visible()
            expect(region).to_have_attribute("aria-busy", "false")

        f, context, page, region = open_case("normal")
        commands = []
        page.on("request", lambda req: commands.append({"path": req.url.rsplit("/", 1)[-1], "body": req.post_data_json})
                if req.method == "POST" and "/asset-imports/" in req.url else None)
        assert len(read(context, f, "/asset-lines")["items"]) == 0
        expect(region.get_by_role("table")).to_be_visible()
        expect(region.get_by_role("table").get_by_role("row")).to_have_count(4)
        assert not commands
        validate(page, region)
        assert len(read(context, f, "/asset-lines")["items"]) == 0
        page.get_by_role("button", name="Xem và xác nhận áp dụng danh mục", exact=True).click()
        expect(region.locator("h2")).to_be_focused()
        apply_button = region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True)
        apply_button.click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        page.keyboard.press("Escape")
        expect(dialog).not_to_be_visible()
        expect(apply_button).to_be_focused()
        assert len(commands) == 1
        apply_button.click()
        expect(dialog).to_be_visible()
        page.screenshot(path=str(evidence / "apply-dialog-desktop.png"), full_page=True, animations="disabled")
        # Keyboard stays in the Fluent modal.
        for _ in range(6):
            page.keyboard.press("Tab")
            assert dialog.evaluate("el => el.contains(document.activeElement)")
        dialog.get_by_role("button", name="Xác nhận áp dụng", exact=True).evaluate("el => { el.click(); el.click(); }")
        expect(region.get_by_text("Danh mục đã được áp dụng", exact=True)).to_be_visible()
        lines = read(context, f, "/asset-lines")["items"]
        assert len(lines) == 3
        assert all(line["appraised_unit_price"] is None and line["review_status"] == "pending" and line["validation_status"] == "unvalidated" for line in lines)
        assert [c["path"] for c in commands] == ["validate", "apply"]
        assert set(commands[0]["body"]) == {"expected_case_version"}
        assert commands[1]["body"]["expected_case_version"] != commands[0]["body"]["expected_case_version"]
        assert commands[1]["body"]["contract_version"] == "s12-post-intake-guarded-apply-v2"
        assert set(commands[1]["body"]) == {"confirm", "contract_version", "expected_case_version"}
        state = read(context, f, "/case-state")
        assert next(s for s in state["stages"] if s["stage"] == "ASSET_REVIEW")["result"] == "INCOMPLETE"
        page.get_by_role("button", name="Mở Bàn làm việc tài sản", exact=True).click()
        expect(page.get_by_role("region", name="Rà soát tài sản")).to_be_visible()
        expect(page.get_by_role("button", name="Kiểm tra dữ liệu", exact=True)).to_be_visible()
        for _ in range(8):
            page.get_by_role("button", name="Tải lại trạng thái rà soát", exact=True).click()
            page.wait_for_load_state("networkidle")
            state = read(context, f, "/case-state")
            if next(s for s in state["stages"] if s["stage"] == "ASSET_REVIEW")["result"] == "COMPLETE":
                break
            key = state["next_action"]["semantic_route_key"]
            assert key in ("asset_review_line_validate_required", "asset_review_line_review_required")
            label = "Kiểm tra dữ liệu" if key.endswith("validate_required") else "Chấp nhận"
            page.get_by_role("region", name="Rà soát tài sản").get_by_role("button", name=label, exact=True).click()
            page.get_by_role("dialog").get_by_role("button", name="Xác nhận " + label.lower(), exact=True).click()
            page.wait_for_load_state("networkidle")
        else:
            raise AssertionError("Existing Asset Review did not complete")
        page.get_by_role("button", name="Tải lại trạng thái danh mục", exact=True).click()
        page.get_by_role("button", name="Xác nhận toàn bộ danh mục", exact=True).click()
        with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as confirmed:
            page.get_by_role("dialog").get_by_role("button", name="Xác nhận danh mục", exact=True).click()
        assert confirmed.value.ok
        page.wait_for_load_state("networkidle")
        state = read(context, f, "/case-state")
        assert next(s for s in state["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "COMPLETE", state["stages"]
        results["normal"] = {"post_count": len(commands), "official_lines": len(lines), "initial_asset_review": "INCOMPLETE",
                             "existing_asset_review_and_workbench_server_complete": True}
        print("normal + existing Asset Review/Workbench: PASS", flush=True)
        context.close()

        f, context, page, region = open_case("lost", viewport={"width": 1280, "height": 720})
        validate(page, region)
        posts = []
        def lose_after_commit(route):
            upstream = route.fetch()
            assert upstream.ok
            posts.append(upstream.status)
            route.abort("connectionreset")
        page.route("**/asset-imports/*/apply", lose_after_commit)
        region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True).click()
        page.get_by_role("dialog").get_by_role("button", name="Xác nhận áp dụng", exact=True).click()
        expect(region.get_by_text("Kết quả chưa xác định", exact=True)).to_be_visible()
        assert page.evaluate("Object.keys(localStorage).some(k => k.startsWith('valora:post-intake:'))")
        expect(region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True)).to_have_count(0)
        page.screenshot(path=str(evidence / "lost-response-laptop.png"), full_page=True)
        page.reload(wait_until="networkidle")
        expect(region.get_by_text("Danh mục đã được áp dụng", exact=True)).to_be_visible()
        assert len(posts) == 1
        assert len(read(context, f, "/asset-lines")["items"]) == 3
        assert not page.evaluate("Object.keys(localStorage).some(k => k.startsWith('valora:post-intake:'))")
        results["lost-response"] = {"actual_committed_post_count": len(posts), "get_only_reload_proved_promotion": True}
        print("lost committed response + reload reconciliation: PASS", flush=True)
        context.close()

        f, context, page, region = open_case("stale")
        validate(page, region)
        region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True).click()
        state = read(context, f, "/case-state")
        assert post(context, f, f'/asset-imports/{f["batch_id"]}/validate', {"expected_case_version": state["case_version"]}).ok
        old = {"confirm": True, "contract_version": "s12-post-intake-guarded-apply-v2", "expected_case_version": state["case_version"]}
        assert post(context, f, f'/asset-imports/{f["batch_id"]}/apply', old).status == 409
        page.get_by_role("dialog").get_by_role("button", name="Xác nhận áp dụng", exact=True).click()
        expect(page.get_by_role("dialog")).not_to_be_visible()
        expect(region).to_have_attribute("aria-busy", "false")
        assert len(read(context, f, "/asset-lines")["items"]) == 0
        state = read(context, f, "/case-state")
        for malformed in ({"confirm": False}, {"confirm": "true"}, {"confirm": True, "contract_version": "s12-pr-004-v1"},
                          {**old, "command_id": "unexpected"}):
            assert post(context, f, f'/asset-imports/{f["batch_id"]}/apply', malformed).status in (400, 422)
        results["stale-and-strict-schema"] = {"stale_cas_status": 409, "official_lines": 0, "malformed_denials": 4}
        print("stale dialog/CAS + strict schemas: PASS", flush=True)
        context.close()

        f, context, page, region = open_case("invalid")
        def inject_validation_output(route):
            upstream = route.fetch()
            assert upstream.ok
            subprocess.run(["docker", "compose", "-f", "tests/e2e/issue206/compose.yml", "exec", "-T", "-e", "PYTHONPATH=/app",
                            "backend", "python", "/acceptance/validation_output_fault.py", f["project_id"]], check=True, capture_output=True)
            route.fulfill(response=upstream)
        page.route("**/asset-imports/*/validate", inject_validation_output)
        region.get_by_role("button", name="Kiểm tra danh mục nhập", exact=True).click()
        expect(region).to_have_attribute("aria-busy", "false")
        expect(region.get_by_role("button", name="Áp dụng danh mục chính thức", exact=True)).to_have_count(0)
        expect(region.get_by_text("Không hợp lệ", exact=True)).to_be_visible()
        assert len(read(context, f, "/asset-lines")["items"]) == 0
        page.screenshot(path=str(evidence / "invalid-staging.png"), full_page=True)
        results["invalid-validation-output-fault"] = {"official_lines": 0, "apply_offered": False, "actual_rows_retained": True}
        print("invalid validation-output fault: PASS", flush=True)
        context.close()

        f, context, page, region = open_case("scope", viewer=True)
        expect(region.get_by_role("button", name="Kiểm tra danh mục nhập", exact=True)).to_have_count(0)
        assert post(context, f, f'/asset-imports/{f["batch_id"]}/validate', {"expected_case_version": "a" * 64}).status == 403
        assert post(context, f, f'/asset-imports/{f["batch_id"]}/apply', old).status == 403
        response = context.request.get(f'{base}/api/v1/projects/{fixtures["normal"]["project_id"]}/case-state')
        assert response.status == 404
        results["permissions-and-tenant"] = {"viewer_post_status": 403, "other_tenant_get_status": 404}
        context.close()
        browser.close()
    (evidence / "browser-results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
