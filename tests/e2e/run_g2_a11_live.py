"""A11 product evidence on the migrated live stack using synthetic retained material."""
import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["A11_EVIDENCE_DIR"])
    evidence.mkdir(parents=True, exist_ok=True)
    project = os.environ["A11_PROJECT_ID"]
    base = os.environ.get("A11_BASE_URL", "http://127.0.0.1:5173")
    checkpoints, commands, matrix, remote_requests = {}, [], {}, []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, timezone_id="Asia/Ho_Chi_Minh")
        page = context.new_page()
        page.on("pageerror", lambda error: print("browser-error:", error, flush=True))
        page.set_default_timeout(20000)
        api = f"{base}/api/v1/projects/{project}"

        def read(path):
            response = context.request.get(api + path)
            assert response.ok, (path, response.status, response.text())
            return response.json()

        def command_payload(operation, extra):
            prep = read("/price-evidence/preparation")
            return {"command_id": str(uuid.uuid4()), "contract_version": {
                "register": "price-evidence-registration-v1", "confirm": "price-evidence-confirmation-v1",
                "withdraw": "price-evidence-withdrawal-v1"}[operation], "confirm": True,
                "expected_project_row_version": prep["project_row_version"], "expected_case_version": prep["case_version"],
                "expected_seal_id": prep["seal_id"], "expected_authoritative_set_sha256": prep["authoritative_set_sha256"],
                "expected_membership_version": prep["membership_version"], "expected_workbench_confirmation_id": prep["workbench_confirmation_id"],
                "expected_line_versions": [{"line_id": line["line_id"], "row_version": line["row_version"]} for line in prep["lines"]], **extra}

        def stage():
            return next(s for s in read("/case-state")["stages"] if s["stage"] == "PRICE_EVIDENCE")["result"]

        def settled():
            page.wait_for_load_state("networkidle")
            expect(page.locator('.workbench-stage-regions [aria-busy="true"]')).to_have_count(0)
            expect(page.get_by_role("region", name="Nguồn giá và chứng cứ toàn hồ sơ")).to_have_attribute("aria-busy", "false")

        def checkpoint(name):
            settled()
            checkpoints[name] = {"case_state": read("/case-state"), "workspace": read("/price-evidence/workspace"),
                                 "viewport": {"width": 1440, "height": 900}, "capture": f"{name}.png"}
            page.screenshot(path=str(evidence / f"{name}.png"), animations="disabled")
            (evidence / "browser-progress.json").write_text(json.dumps({"project_id": project, "checkpoints": checkpoints,
                "commands": commands, "matrix": matrix, "completed": False}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(name, flush=True)

        def observe(response):
            if response.request.method == "POST" and "/price-evidence/" in response.url:
                payload = response.request.post_data_json
                commands.append({"operation": response.url.rsplit("/", 1)[-1], "status": response.status,
                                 "command_id": payload["command_id"], "contract": payload["contract_version"],
                                 "line_id": payload.get("line_id"), "member_count": len(payload["expected_line_versions"]),
                                 "confirm": payload["confirm"]})

        page.on("response", observe)
        page.on("request", lambda request: remote_requests.append(request.url) if request.url.startswith("https://example.com") else None)
        page.goto(base, wait_until="networkidle")
        page.get_by_label("Mã đơn vị").fill(os.environ.get("A11_ORGANIZATION_SLUG", "a11-synthetic"))
        page.get_by_label("Email").fill("operator@a5.invalid")
        page.get_by_label("Mật khẩu").fill(os.environ["A11_SYNTHETIC_PASSWORD"])
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        page.get_by_role("button", name="Tải lại trạng thái rà soát", exact=True).wait_for()
        page.wait_for_load_state("networkidle")
        csrf = next(cookie["value"] for cookie in context.cookies() if cookie["name"] == "XSRF-TOKEN")
        headers = {"X-CSRF-Token": csrf, "Origin": base}
        # Upstream prerequisites use their certified APIs and human confirmation UI.
        for line in read("/asset-lines")["items"]:
            if not line["description"]:
                response = context.request.patch(api + f'/asset-lines/{line["id"]}/draft', data={
                    "field_key": "description", "draft_value": "Thiết bị tổng hợp; cấu hình và tình trạng phục vụ so sánh nguồn giá.",
                    "base_value": line["description"], "version_token": line["version_token"]}, headers=headers)
                assert response.ok, response.text()
                response = context.request.post(api + f'/asset-lines/{line["id"]}/draft/commit', data={
                    "field_keys": ["description"], "confirm": True, "version_token": line["version_token"]}, headers=headers)
                assert response.ok, response.text()
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Tải lại trạng thái rà soát", exact=True).wait_for()
        page.wait_for_load_state("networkidle")
        for _ in range(16):
            state = read("/case-state")
            if next(s for s in state["stages"] if s["stage"] == "ASSET_REVIEW")["result"] == "COMPLETE":
                break
            key = state["next_action"]["semantic_route_key"]
            assert key in ("asset_review_line_validate_required", "asset_review_line_review_required"), state
            label = "Kiểm tra dữ liệu" if key.endswith("validate_required") else "Chấp nhận"
            page.get_by_role("region", name="Rà soát tài sản").get_by_role("button", name=label, exact=True).click()
            dialog = page.get_by_role("dialog")
            if dialog.get_by_role("textbox").count():
                dialog.get_by_role("textbox").fill("Đã xem xét dữ liệu tổng hợp hiện tại")
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/validate" if label == "Kiểm tra dữ liệu" else "/review-decision")) as mutation:
                dialog.get_by_role("button", name="Xác nhận " + label.lower(), exact=True).click()
            assert mutation.value.ok, mutation.value.text()
            page.wait_for_load_state("networkidle")
        if read("/asset-workbench/preparation")["can_confirm"]:
            page.get_by_role("button", name="Xác nhận toàn bộ danh mục", exact=True).click()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-workbench/confirm")) as mutation:
                page.get_by_role("dialog").get_by_role("button", name="Xác nhận danh mục", exact=True).click()
            assert mutation.value.ok, mutation.value.text()
            settled()

        state = read("/case-state")
        assert next(s for s in state["stages"] if s["stage"] == "ASSET_WORKBENCH")["result"] == "COMPLETE"
        assert state["current_stage"] == "PRICE_EVIDENCE" and state["next_action"]["kind"] == "PENDING"
        target = state["next_action"]["context"]["line_id"]
        before = len(commands)
        page.get_by_role("button", name="Tổng quan hồ sơ", exact=True).click()
        page.get_by_role("button", name="Tiếp tục xử lý", exact=True).click()
        settled()
        expect(page.get_by_role("tab", name="Nguồn giá & Chứng cứ", exact=True)).to_have_attribute("aria-selected", "true")
        expect(page.get_by_role("tab", name="Nguồn giá & Chứng cứ", exact=True)).to_be_focused()
        assert len(commands) == before
        assert read("/price-evidence/workspace?line_id=" + target)["line_covered"] is False
        matrix["01-next-action-navigation"] = "PASS: existing Workbench, no evidence mutation"
        matrix["02-exact-deficient-line-focus"] = f"PASS: {target}"
        tabs = page.get_by_role("tablist", name="Nội dung của tài sản đang chọn").get_by_role("tab")
        assert tabs.count() == 4
        for label in ["Tổng quan", "Thông số kỹ thuật", "Nguồn giá & Chứng cứ", "Lịch sử"]:
            expect(tabs.get_by_text(label, exact=True).first).to_be_attached()
        assert not page.get_by_text("Giá thẩm định", exact=True).count()
        matrix["03-first-use-boundary"] = "PASS: four canonical tabs; no legacy final-price authority"
        checkpoint("01-first-use-incomplete")
        lines = read("/asset-lines")["items"]

        def select(line):
            page.locator("tr[aria-label]").filter(has_text=line["asset_name"]).first.click()
            page.get_by_role("tab", name="Nguồn giá & Chứng cứ", exact=True).click()
            settled()
            expect(page.get_by_role("region", name="Chứng cứ của tài sản").get_by_role("heading", name=line["asset_name"], exact=True)).to_be_visible()

        def post_ui(operation, button):
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/price-evidence/" + operation)) as mutation:
                button.click()
            assert mutation.value.ok, (mutation.value.status, mutation.value.text())
            settled()

        def source_form(origin="Nguồn tổng hợp A11", correction=False, category="internet_survey"):
            dialog = page.get_by_role("dialog")
            dialog.get_by_label("Loại nguồn").select_option(category)
            for label, value in {
                "Nhà xuất bản / tác giả / nguồn gốc": origin,
                "Tham chiếu HTTPS công khai": "https://example.com/synthetic-evidence",
                "Vị trí nguồn (trang, mục, dòng)": "Bảng tổng hợp, dòng 1",
                "Ngày nguồn / ngày hiệu lực": datetime.now().strftime("%Y-%m-%d"),
                "Thời điểm quan sát / ghi nhận (giờ địa phương)": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                "Nội dung văn bản lưu giữ": "Nguồn tổng hợp có giá trị 1000000 VND cho một thiết bị mới; không phải dữ liệu thật.",
                "Hạn chế của nguồn": "Tổng hợp phục vụ kiểm thử; chưa có khảo sát thị trường thật.",
                "Giá trị ghi nhận": "1000000", "Mã tiền tệ (3 chữ hoa)": "VND", "Đơn vị tính": "chiếc",
                "Cơ sở số lượng": "1", "Thuế": "Đã gồm", "Giao hàng": "Chưa gồm", "Tình trạng tài sản nguồn": "Mới",
                "Vị trí giá trị trong nguồn": "Bảng giá dòng 1",
            }.items():
                dialog.get_by_label(label).fill(value)
            if correction:
                dialog.get_by_label("Lý do tạo phiên bản thay thế").fill("Cập nhật mô tả nguồn sau khi kiểm tra lại")
            dialog.get_by_role("checkbox", name="Tôi xác nhận tạo phiên bản nguồn thay thế; lịch sử được giữ nguyên" if correction else "Tôi xác nhận đăng ký nội dung nguồn đã kiểm tra", exact=True).check()
            post_ui("register", dialog.get_by_role("button", name="Xác nhận đăng ký nguồn", exact=True))

        page.get_by_role("button", name="Đăng ký nguồn giá", exact=True).click()
        expect(page.get_by_role("dialog").get_by_role("button", name="Xác nhận đăng ký nguồn", exact=True)).to_be_disabled()
        source_form()
        assert read("/price-evidence/workspace")["covered_count"] == 0
        assert not remote_requests
        matrix["04-internet-registration"] = "PASS: retained text and HTTPS reference, no remote request, zero coverage"

        def decide(line, disposition="qualifying_basis"):
            select(line)
            page.get_by_role("button", name="Đánh giá cho tài sản này", exact=True).first.click()
            dialog = page.get_by_role("dialog")
            dialog.get_by_label("Quyết định phù hợp").select_option(disposition)
            for label in ["Phần nguồn liên quan", "Lý do liên quan đến tài sản đang chọn", "Lý do phù hợp làm cơ sở",
                          "Hạn chế khi áp dụng", "Tính phù hợp theo thời gian", "Lý do lựa chọn thứ tự ưu tiên nguồn"]:
                dialog.get_by_label(label).fill("Đã xem xét thiết bị tổng hợp, đơn vị, thời điểm và điều kiện tương ứng.")
            dialog.get_by_label("Ngày áp dụng").fill(datetime.now().strftime("%Y-%m-%d"))
            dialog.get_by_label("Hạn rà soát lại (giờ địa phương)").fill((datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"))
            reason = dialog.get_by_label("Lý do quyết định / thay thế quyết định trước")
            if reason.count():
                reason.fill("Đã xem xét lại nguồn hiện tại và giải quyết điều kiện trước")
            dialog.get_by_role("checkbox", name="Tôi xác nhận quyết định cho đúng nguồn và dòng tài sản này", exact=True).check()
            post_ui("decide", dialog.get_by_role("button", name="Xác nhận quyết định", exact=True))

        decide(lines[0])
        assert read("/price-evidence/workspace")["covered_count"] == 1
        assert not read("/price-evidence/workspace?line_id=" + lines[1]["id"])["line_covered"]
        matrix["05-exact-line-acceptance"] = "PASS: one line qualifying"
        select(lines[0])
        checkpoint("02-registered-accepted-one-line")
        for line in lines[1:]:
            decide(line)
        assert read("/price-evidence/workspace")["covered_count"] == len(lines)
        assert len({c["line_id"] for c in commands if c["operation"] == "decide"}) == len(lines)
        matrix["06-shared-source-separate-decisions"] = "PASS: distinct exact line commands, no fanout"
        matrix["07-full-sealed-coverage"] = "PASS: server projection covers three sealed lines"

        def confirm(reason=None, capture=None):
            trigger = page.get_by_role("button", name="Xác nhận lại bộ chứng cứ toàn hồ sơ" if reason else "Xác nhận bộ chứng cứ toàn hồ sơ", exact=True)
            trigger.click()
            dialog = page.get_by_role("dialog")
            expect(dialog).to_contain_text(f"toàn bộ {len(lines)} tài sản")
            # Focus remains inside Fluent's modal after forward/backward tab navigation.
            for key in ["Tab", "Shift+Tab", "Tab"]:
                page.keyboard.press(key)
                assert dialog.evaluate("el => el.contains(document.activeElement)")
            page.keyboard.press("Escape")
            expect(trigger).to_be_focused()
            trigger.click()
            expect(dialog).to_be_visible()
            if reason:
                expect(dialog.get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True)).to_be_disabled()
                dialog.get_by_role("textbox").fill(reason)
            if capture:
                expect(dialog.get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True)).to_be_visible()
                page.screenshot(path=str(evidence / f"{capture}.png"), animations="disabled")
                checkpoints[capture] = {"viewport": {"width": 1440, "height": 900}, "capture": f"{capture}.png", "case_state": read("/case-state")}
            post_ui("confirm", dialog.get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True))

        confirm(capture="03-whole-set-confirmation-dialog")
        assert stage() == "COMPLETE"
        assert read("/case-state")["next_action"]["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
        assert all(line["appraised_unit_price"] is None for line in read("/asset-lines")["items"])
        matrix["08-whole-set-confirm"] = "PASS"
        matrix["09-fresh-complete"] = "PASS: Case State v5"
        matrix["10-downstream-hold"] = "PASS: NO_AUTHORIZED_DOWNSTREAM_ACTION"
        matrix["11-optional-working-price"] = "PASS: all absent; PRICE_EVIDENCE COMPLETE"
        matrix["18-keyboard-focus"] = "PASS: selected tab, labelled fields, dialog trap, Escape returns trigger, explicit confirmation"
        checkpoint("04-complete-downstream-hold")

        select(lines[0])
        page.get_by_role("button", name="Tạo phiên bản thay thế", exact=True).first.click()
        page.get_by_role("dialog").get_by_label("Nhà xuất bản / tác giả / nguồn gốc").wait_for()
        source_form("Nguồn tổng hợp A11 đã cập nhật", correction=True)
        assert stage() in ("STALE", "INCOMPLETE")
        assert read("/price-evidence/workspace")["covered_count"] == 0
        checkpoint("05-stale-successor-recovery")
        for line in lines:
            decide(line)
        confirm(reason="Đã đánh giá lại nguồn thay thế cho từng dòng hiện tại")
        assert stage() == "COMPLETE"
        matrix["12-correction-stale"] = "PASS: successor revision invalidates previous coverage; no silent reconciliation"
        matrix["13-reconfirmation"] = "PASS: reason and three new exact-line decisions restore COMPLETE"
        page.get_by_role("button", name="Rút xác nhận bộ chứng cứ toàn hồ sơ", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("button", name="Xác nhận rút bộ chứng cứ", exact=True)).to_be_disabled()
        dialog.get_by_role("textbox").fill("Cần xem lại tuyên bố bộ chứng cứ toàn hồ sơ")
        post_ui("withdraw-confirmation", dialog.get_by_role("button", name="Xác nhận rút bộ chứng cứ", exact=True))
        assert stage() == "INCOMPLETE" and read("/price-evidence/workspace")["covered_count"] == len(lines)
        matrix["14-confirmation-withdrawal"] = "PASS: non-COMPLETE; sources and qualifying coverage retained"
        checkpoint("06-withdrawn-confirmation")
        # Real concurrent mutation invalidates the open confirmation's CAS; it is never replayed.
        page.get_by_role("button", name="Xác nhận lại bộ chứng cứ toàn hồ sơ", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("textbox").fill("Xem xét bộ chứng cứ sau khi rút")
        current = read("/price-evidence/workspace")["sources"][0]
        material = read("/price-evidence/sources/" + current["evidence_revision_id"])["material"]
        material["origin"] = "Nguồn bổ sung đồng thời tổng hợp"
        concurrent = context.request.post(api + "/price-evidence/register", headers=headers, data=command_payload("register", {
            "source_id": str(uuid.uuid4()), "predecessor_revision_id": None, "material": material, "reason_note": None}))
        assert concurrent.ok, concurrent.text()
        before = len(commands)
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/price-evidence/confirm")) as conflict:
            dialog.get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True).click()
        assert conflict.value.status == 409
        settled()
        assert len(commands) == before + 1
        expect(page.get_by_text("Dữ liệu hoặc điều kiện đã thay đổi.", exact=False)).to_be_visible()
        matrix["15-cas-conflict"] = "PASS: real concurrent registration, one 409, fresh reads, no replay"
        checkpoint("07-conflict-refresh-no-replay")

        # Fault injection drops only the response AFTER the actual command commits on the real API.
        lost = {}
        def lose_response(route):
            payload = route.request.post_data_json
            response = route.fetch()
            assert response.ok, response.text()
            lost.update({"command_id": payload["command_id"], "status": response.status, "receipt": response.json()})
            route.abort("connectionfailed")
        page.route("**/price-evidence/confirm", lose_response, times=1)
        page.get_by_role("button", name="Xác nhận lại bộ chứng cứ toàn hồ sơ", exact=True).click()
        page.get_by_role("dialog").get_by_role("textbox").fill("Đã tải lại và kiểm tra bộ chứng cứ hiện tại")
        page.get_by_role("dialog").get_by_role("button", name="Xác nhận toàn bộ chứng cứ", exact=True).click()
        expect(page.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True)).to_be_enabled()
        assert lost["receipt"]["historical"] and stage() == "COMPLETE"
        page.reload(wait_until="networkidle")
        recover = page.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True)
        settled()
        expect(recover).to_be_enabled()
        with page.expect_response(lambda r: r.url.endswith("/price-evidence/command-receipts/" + lost["command_id"])) as reconciled:
            recover.click()
        assert reconciled.value.ok and reconciled.value.json()["result"]["command_id"] == lost["command_id"]
        settled()
        expect(page.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True)).to_have_count(0)
        matrix["16-unknown-original-receipt"] = {"result": "PASS", "fault": "real commit, response aborted, reload persists UUID",
            "command_id": lost["command_id"], "receipt_command_id": reconciled.value.json()["result"]["command_id"]}
        checkpoint("08-reconciled-current-complete")

        # Both other certified source categories are submitted through real labelled forms/selectors.
        select(lines[0])
        page.get_by_role("button", name="Đăng ký nguồn giá", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_label("Loại nguồn").select_option("unit_price_explanation")
        for label, value in {
            "Nhà xuất bản / tác giả / nguồn gốc": "Giải trình tổng hợp A11", "Vị trí nguồn (trang, mục, dòng)": "Giải trình mục 1",
            "Ngày nguồn / ngày hiệu lực": datetime.now().strftime("%Y-%m-%d"),
            "Thời điểm quan sát / ghi nhận (giờ địa phương)": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "Nội dung văn bản lưu giữ": "Giải trình tổng hợp từ nguồn khảo sát đã lưu giữ; hệ số một, cùng đơn vị và tiền tệ.",
            "Hạn chế của nguồn": "Chỉ phục vụ kiểm thử", "Giá trị ghi nhận": "1000000", "Mã tiền tệ (3 chữ hoa)": "VND",
            "Đơn vị tính": "chiếc", "Cơ sở số lượng": "1", "Thuế": "Đã gồm", "Giao hàng": "Chưa gồm",
            "Tình trạng tài sản nguồn": "Mới", "Vị trí giá trị trong nguồn": "Phép tính 1", "Hệ số nguồn 1": "1",
            "Giả định": "Nguồn cùng tiền tệ và đơn vị", "Phép tính và diễn giải": "1000000 × 1 = 1000000 VND/chiếc",
        }.items():
            dialog.get_by_label(label).fill(value)
        dialog.get_by_label("Nguồn đầu vào 1").select_option(current["evidence_revision_id"])
        dialog.get_by_role("checkbox", name="Tôi xác nhận đăng ký nội dung nguồn đã kiểm tra", exact=True).check()
        post_ui("register", dialog.get_by_role("button", name="Xác nhận đăng ký nguồn", exact=True))
        matrix["category-unit-price-explanation"] = "PASS: registered-source selector, decimal strings, exact structured method"

        # A10 accepts retained historical result transcription, without asserting final-result authority for this fixture.
        prior = context.request.post(base + "/api/v1/projects", headers=headers,
            data={"code": "A11-PRIOR-SYNTH", "name": "Hồ sơ nguồn lịch sử tổng hợp"})
        assert prior.ok, prior.text()
        prior_id = prior.json()["id"]
        prior_line = context.request.post(base + f"/api/v1/projects/{prior_id}/asset-lines", headers=headers,
            data={"asset_name": "Thiết bị nguồn lịch sử tổng hợp", "description": "Dòng nguồn để kiểm tra selector cùng đơn vị"})
        assert prior_line.ok, prior_line.text()
        select(lines[0])
        page.get_by_role("button", name="Đăng ký nguồn giá", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_label("Loại nguồn").select_option("prior_appraisal_result")
        expect(dialog.get_by_label("Hồ sơ thẩm định trước")).to_be_enabled()
        dialog.get_by_label("Hồ sơ thẩm định trước").select_option(label="A11-PRIOR-SYNTH · Hồ sơ nguồn lịch sử tổng hợp")
        expect(dialog.get_by_label("Tài sản trong hồ sơ trước")).to_be_enabled()
        dialog.get_by_label("Tài sản trong hồ sơ trước").select_option(label="Thiết bị nguồn lịch sử tổng hợp")
        for label, value in {
            "Nhà xuất bản / tác giả / nguồn gốc": "Kết quả lịch sử tổng hợp A11", "Vị trí nguồn (trang, mục, dòng)": "Kết quả mục 2",
            "Ngày thẩm định trước": datetime.now().strftime("%Y-%m-%d"),
            "Thời điểm quan sát / ghi nhận (giờ địa phương)": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "Nội dung văn bản lưu giữ": "Trích đoạn kết quả thẩm định lịch sử tổng hợp; không phải báo giá nhà cung cấp.",
            "Hạn chế của nguồn": "Nguồn tổng hợp kiểm thử", "Giá trị ghi nhận": "1000000", "Mã tiền tệ (3 chữ hoa)": "VND",
            "Đơn vị tính": "chiếc", "Cơ sở số lượng": "1", "Thuế": "Đã gồm", "Giao hàng": "Chưa gồm",
            "Tình trạng tài sản nguồn": "Mới", "Vị trí giá trị trong nguồn": "Kết quả mục 2",
            "Trích đoạn kết quả thẩm định trước": "Kết quả lịch sử tổng hợp: một thiết bị có giá trị 1000000 VND/chiếc.",
            "Vị trí kết quả thẩm định trước": "Kết quả trang 1, dòng 2",
        }.items():
            dialog.get_by_label(label).fill(value)
        dialog.get_by_role("checkbox", name="Tôi xác nhận đăng ký nội dung nguồn đã kiểm tra", exact=True).check()
        post_ui("register", dialog.get_by_role("button", name="Xác nhận đăng ký nguồn", exact=True))
        matrix["category-prior-appraisal-result"] = {"result": "PASS: readable same-tenant project and exact line selectors",
            "fixture_limitation": "manual retained result transcription under A10; fixture is not a certified appraisal-result record", "project_id": prior_id}

        # Append-only exact relationship withdrawal retains history, then an explicit successor decision restores it.
        select(lines[0])
        primary = page.get_by_role("region", name="Nguồn tổng hợp A11 đã cập nhật · Phiên bản 2", exact=True)
        primary.get_by_role("button", name="Rút quan hệ", exact=True).click()
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("button", name="Xác nhận rút chứng cứ", exact=True)).to_be_disabled()
        dialog.get_by_label("Lý do rút chứng cứ").fill("Xem xét lại quan hệ đúng dòng tài sản tổng hợp")
        post_ui("withdraw", dialog.get_by_role("button", name="Xác nhận rút chứng cứ", exact=True))
        assert read("/price-evidence/workspace")["covered_count"] == len(lines) - 1
        select(lines[0])
        primary.get_by_role("button", name="Đánh giá cho tài sản này", exact=True).click()
        dialog = page.get_by_role("dialog")
        for label in ["Phần nguồn liên quan", "Lý do liên quan đến tài sản đang chọn", "Lý do phù hợp làm cơ sở",
                      "Hạn chế khi áp dụng", "Tính phù hợp theo thời gian", "Lý do lựa chọn thứ tự ưu tiên nguồn"]:
            dialog.get_by_label(label).fill("Đã xem xét lại đúng nguồn và đúng tài sản hiện tại.")
        dialog.get_by_label("Ngày áp dụng").fill(datetime.now().strftime("%Y-%m-%d"))
        dialog.get_by_label("Hạn rà soát lại (giờ địa phương)").fill((datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"))
        dialog.get_by_label("Lý do quyết định / thay thế quyết định trước").fill("Khôi phục quan hệ bằng quyết định kế tiếp đã xem xét")
        dialog.get_by_role("checkbox", name="Tôi xác nhận quyết định cho đúng nguồn và dòng tài sản này", exact=True).check()
        post_ui("decide", dialog.get_by_role("button", name="Xác nhận quyết định", exact=True))
        matrix["exact-relationship-withdrawal"] = "PASS: reasoned append-only withdrawal loses one line; explicit successor decision restores that line"
        confirm(reason="Đã kiểm tra các nguồn bổ sung và quan hệ mới; xác nhận bộ chứng cứ hiện tại")

        session = context.request.post(base + "/api/v1/workbench/sessions", headers=headers, data={"project_id": project})
        assert session.ok
        no_session_payload = command_payload("register", {"source_id": str(uuid.uuid4()), "predecessor_revision_id": None,
            "material": material, "reason_note": None})
        closed = context.request.post(base + "/api/v1/workbench/sessions/" + session.json()["id"] + "/close", headers=headers)
        assert closed.ok
        invalid_session = context.request.post(api + "/price-evidence/register", headers=headers, data=no_session_payload)
        assert invalid_session.status == 404, invalid_session.text()
        page.get_by_role("button", name="Tải lại trạng thái nguồn giá", exact=True).click()
        settled()
        assert not read("/price-evidence/preparation")["can_register"]
        expect(page.get_by_role("button", name="Đăng ký nguồn giá", exact=True)).to_have_count(0)
        restored = context.request.post(base + "/api/v1/workbench/sessions", headers=headers, data={"project_id": project})
        assert restored.ok
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Tải lại trạng thái nguồn giá", exact=True).wait_for()
        settled()

        # Live non-DRAFT is reached through the existing archive API; no status/proof SQL.
        assert stage() == "COMPLETE", read("/case-state")
        stale_payload = command_payload("register", {"source_id": str(uuid.uuid4()), "predecessor_revision_id": None,
            "material": material, "reason_note": None})
        archived = context.request.post(api + "/archive", headers=headers)
        assert archived.ok, archived.text()
        rejected = context.request.post(api + "/price-evidence/register", headers=headers, data=stale_payload)
        assert rejected.status == 400, rejected.text()
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Tải lại trạng thái nguồn giá", exact=True).wait_for()
        settled()
        assert stage() == "COMPLETE"
        assert not read("/price-evidence/preparation")["can_register"]
        expect(page.get_by_role("button", name="Đăng ký nguồn giá", exact=True)).to_have_count(0)
        viewer = browser.new_context(viewport={"width": 1440, "height": 900})
        login = viewer.request.post(base + "/api/v1/auth/login", data={"organization_slug": os.environ.get("A11_ORGANIZATION_SLUG", "a11-synthetic"),
            "email": "viewer@a5.invalid", "password": os.environ["A11_SYNTHETIC_PASSWORD"]})
        assert login.ok, login.text()
        vcsrf = next(cookie["value"] for cookie in viewer.cookies() if cookie["name"] == "XSRF-TOKEN")
        denied = viewer.request.post(api + "/price-evidence/register", data=stale_payload,
            headers={"X-CSRF-Token": vcsrf, "Origin": base})
        assert denied.status == 403
        other = viewer.request.get(base + "/api/v1/projects/00000000-0000-4000-8000-000000000000/price-evidence/workspace")
        assert other.status == 404
        viewer.close()
        matrix["17-denied-nondraft"] = "PASS: live closed session 404 and UI writes unavailable; non-DRAFT 400, COMPLETE read preserved; viewer 403; out-of-scope 404."
        checkpoint("09-nondraft-read-only-complete")
        (evidence / "browser-evidence.json").write_text(json.dumps({"project_id": project, "fixture": "A11 migrated synthetic live stack",
            "checkpoints": checkpoints, "commands": commands, "matrix": matrix, "remote_reference_requests": remote_requests}, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
