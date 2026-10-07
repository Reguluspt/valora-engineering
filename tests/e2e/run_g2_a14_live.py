"""A14 real-stack browser journey with deterministic transport fault injection."""
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["A14_EVIDENCE_DIR"])
    evidence.mkdir(parents=True, exist_ok=True)
    fixture = json.loads((evidence / "fixture.json").read_text(encoding="utf-8-sig"))
    project = fixture["project_id"]
    base = os.environ.get("A14_BASE_URL", "http://127.0.0.1:5173")
    commands, matrix, captures, errors = [], {}, [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900}, timezone_id="Asia/Ho_Chi_Minh")
        page = context.new_page()
        page.set_default_timeout(60000)
        expect.set_options(timeout=60000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        api = f"{base}/api/v1/projects/{project}"

        def read(path):
            response = context.request.get(api + path)
            assert response.ok, (path, response.status, response.text())
            return response.json()

        def prep():
            return read("/supplier-quotes/preparation")

        def stage():
            return next(s for s in read("/case-state")["stages"] if s["stage"] == "SUPPLIER_QUOTES")["result"]

        def settled():
            page.wait_for_load_state("networkidle")
            expect(page.get_by_role("region", name="Báo giá NCC toàn hồ sơ")).to_have_attribute("aria-busy", "false")

        def capture(name):
            settled()
            page.get_by_role("heading", name="Báo giá NCC · Toàn hồ sơ", exact=True).scroll_into_view_if_needed()
            if name in ("02-draft-mapped-warnings", "03-conflict-recovery", "04-confirmed-complete-downstream-hold"):
                warning = page.get_by_role("region", name="Báo giá NCC toàn hồ sơ").get_by_text("Cảnh báo: Chênh lệch tuyệt đối trên 15%", exact=True).last
                warning.scroll_into_view_if_needed()
                expect(warning).to_be_visible()
            page.screenshot(path=str(evidence / f"{name}.png"), animations="disabled")
            captures.append({"path": f"{name}.png", "viewport": {"width": 1440, "height": 900},
                "case_state": read("/case-state"), "preparation": prep()})
            (evidence / "browser-progress.json").write_text(json.dumps({"matrix": matrix, "captures": captures, "commands": commands}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(name, flush=True)

        def observe(response):
            if response.request.method == "POST" and "/supplier-quotes/" in response.url:
                payload = response.request.post_data_json
                commands.append({"operation": response.url.rsplit("/", 1)[-1], "status": response.status,
                    "command_id": payload["command_id"], "contract": payload["contract_version"], "quote_id": payload["quote_id"],
                    "revision_id": payload["expected_revision_id"], "member_count": len(payload["expected_line_versions"]),
                    "confirm": payload["confirm"]})
        page.on("response", observe)
        login = context.request.post(base + "/api/v1/auth/login", data={"organization_slug": fixture["organization_slug"],
            "email": "operator@a5.invalid", "password": os.environ["A14_SYNTHETIC_PASSWORD"]})
        assert login.ok, login.text()
        csrf = next(c["value"] for c in context.cookies() if c["name"] == "XSRF-TOKEN")
        headers = {"X-CSRF-Token": csrf, "Origin": base}
        initial_prices = [(l["id"], l["appraised_unit_price"]) for l in read("/asset-lines")["items"]]
        def forbidden_counts():
            counts = json.loads(subprocess.check_output(["docker", "exec", "-e", "PYTHONPATH=/app", "valora-a14-backend-v2",
                "python", "/e2e/g2_a14_fixture_fault.py", project, "counts"], text=True))
            return {key: counts[key] for key in ("appraised_price_decisions", "ncc_selection_revisions")}
        initial_counts = forbidden_counts()
        state = read("/case-state")
        assert state["current_stage"] == "SUPPLIER_QUOTES"
        assert next(s for s in state["stages"] if s["stage"] == "PRICE_EVIDENCE")["result"] == "COMPLETE"
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        settled()
        heading = page.get_by_role("heading", name="Báo giá NCC · Toàn hồ sơ", exact=True)
        expect(heading).to_be_focused()
        page.get_by_role("button", name="Tổng quan hồ sơ", exact=True).click()
        expect(page.get_by_text("Tạo và hoàn thiện báo giá NCC", exact=True)).to_be_visible()
        before = len(commands)
        page.get_by_role("button", name="Tiếp tục xử lý", exact=True).click()
        settled()
        expect(heading).to_be_focused()
        assert len(commands) == before
        assert stage() == "INCOMPLETE" and all(c["supplier_count"] == 0 for c in prep()["coverage"])
        matrix["next-action-first-use"] = "PASS: PRICE_EVIDENCE COMPLETE; existing Workbench opens/focuses; zero coverage; navigation has no quotation command"
        capture("01-first-use-incomplete")
        region = page.get_by_role("region", name="Báo giá NCC toàn hồ sơ")
        # Canonical Asset Context remains independent of the project workspace.
        page.locator("tr[aria-label]").first.click()
        tabs = page.get_by_role("tablist", name="Nội dung của tài sản đang chọn").get_by_role("tab")
        assert tabs.count() == 4
        for label in ["Tổng quan", "Thông số kỹ thuật", "Nguồn giá & Chứng cứ", "Lịch sử"]:
            expect(tabs.get_by_text(label, exact=True).first).to_be_attached()
        matrix["canonical-tabs"] = "PASS: exactly four; quotation workspace separate from PRICE_EVIDENCE"
        page.get_by_role("button", name="Đóng ngữ cảnh tài sản", exact=True).click()

        def post_ui(operation, button, key=False):
            with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/supplier-quotes/" + operation)) as mutation:
                if key:
                    button.focus()
                    page.keyboard.press("Enter")
                else:
                    button.click()
            assert mutation.value.ok, (mutation.value.status, mutation.value.text())
            settled()

        def fill_terms(dialog, number="BG-A14-01"):
            now = datetime.now()
            values = {"Số báo giá": number, "Ngày báo giá": now.strftime("%Y-%m-%d"),
                "Ngày hiệu lực (giờ địa phương)": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                "Hạn rà soát (giờ địa phương)": (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M"),
                "Tiền tệ (3 chữ hoa)": "VND", "Thuế": "Đã gồm", "Giao hàng": "Đã gồm", "Tình trạng/điều kiện": "Mới",
                "Bảo hành": "12 tháng", "Thanh toán": "Chuyển khoản", "Giới hạn": "Tổng hợp kiểm thử", "Vị trí nguồn": "Page 1"}
            for label, value in values.items():
                dialog.get_by_label(re.compile("^" + re.escape(label) + r"\s*\*?$" )).fill(value)
            dialog.get_by_label("Cơ sở so sánh", exact=False).select_option("same_working_unit_basis")

        def register(document_id, number):
            region.get_by_role("button", name="Đăng ký báo giá nháp", exact=True).click()
            dialog = page.get_by_role("dialog")
            issuer = dialog.get_by_label("Nhà cung cấp phát hành báo giá", exact=False)
            expect(issuer).to_be_visible()
            options = issuer.locator("option").all_text_contents()
            assert any("Thiết bị A14" in o for o in options) and fixture["supplier_id"] not in " ".join(options), options
            issuer.select_option(fixture["supplier_id"])
            retained = dialog.get_by_label("Nguồn báo giá đã lưu", exact=False)
            expect(retained).to_be_visible()
            options = retained.locator("option").all_text_contents()
            assert any("Synthetic source" in o for o in options) and " ".join(options).find("/objects/") == -1
            index = fixture["source_document_ids"].index(document_id)
            retained.select_option(fixture["source_revision_ids"][index])
            fill_terms(dialog, number)
            expect(dialog.get_by_role("checkbox")).to_have_count(0)
            post_ui("register", dialog.get_by_role("button", name="Đăng ký báo giá nháp", exact=True))

        document = fixture["source_document_ids"][0]
        register(document, "BG-A14-01")
        assert stage() == "INCOMPLETE" and all(c["supplier_count"] == 0 for c in prep()["coverage"])
        matrix["human-selectors-registration"] = "PASS: readable issuer and retained source; no UUID typing, upload/OCR or checklist; registration contributes zero"
        row = lambda doc=document: region.get_by_role("table", name="Báo giá và phiên bản", exact=True).get_by_role("row").filter(has_text="BG-A14-01")

        def latest_row():
            return row().filter(has_text="Mới nhất")

        def open_action(target, name, exact=True):
            target.get_by_role("button", name="Xem báo giá", exact=False).click()
            page.get_by_role("dialog").get_by_role("button", name=name, exact=exact).click()

        for index, line_id in enumerate(fixture["lines"]):
            open_action(latest_row(), "Thêm dòng báo giá")
            dialog = page.get_by_role("dialog")
            dialog.get_by_label("Tài sản trong danh mục đã chốt", exact=False).select_option(line_id)
            price = "800000.12345678" if index < 2 else "123456789012345678.12345678"
            dialog.get_by_label("Đơn giá NCC", exact=False).fill(price)
            dialog.get_by_label("Vị trí dòng trong nguồn", exact=False).fill(f"Row {index + 1}")
            post_ui("register-line", dialog.get_by_role("button", name="Ghi nhận dòng báo giá", exact=True))
        history = read("/supplier-quotes")["items"]
        assert len(history[0]["items"]) == 3 and stage() == "INCOMPLETE"
        assert all(c["supplier_count"] == 0 for c in prep()["coverage"])
        warned = [i for i in history[0]["items"] if i["line_id"] != fixture["lines"][2]]
        assert all(set(i["warning_codes"]) == {"below_working_price", "difference_exceeds_15_percent"} for i in warned)
        assert next(i for i in history[0]["items"] if i["line_id"] == fixture["lines"][2])["warning_codes"] == []
        expect(latest_row().get_by_text("Cảnh báo: Giá NCC thấp hơn đơn giá làm việc", exact=True).first).to_be_visible()
        expect(latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True)).to_be_enabled()
        matrix["line-decimal-warnings-null"] = "PASS: three explicit mappings; exact Decimal string; draft zero coverage; below price and strict >15% warnings do not block; NULL working price has no fabricated warning"
        capture("02-draft-mapped-warnings")

        # A concurrent real line command makes the original browser confirmation CAS obsolete.
        def compete(route):
            payload = route.request.post_data_json
            current_item = read("/supplier-quotes")["items"][0]["items"][0]
            replacement = dict(payload, command_id=str(uuid.uuid4()), contract_version="supplier-quote-line-registration-v1",
                item={k: current_item[k] for k in ("line_id", "quantity", "unit", "unit_price", "source_locator")})
            response = context.request.post(api + "/supplier-quotes/register-line", data=replacement, headers=headers)
            assert response.ok, response.text()
            route.continue_()
        page.route("**/supplier-quotes/confirm", compete, times=1)
        before = len(commands)
        with page.expect_response(lambda r: r.url.endswith("/supplier-quotes/confirm") and r.request.method == "POST") as conflict:
            latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True).click()
        assert conflict.value.status == 409
        settled()
        assert len(commands) == before + 1 and stage() == "INCOMPLETE"
        expect(region.get_by_text("Xung đột phiên bản.", exact=False).first).to_be_visible()
        matrix["real-409-no-blind-retry"] = "PASS: competing PostgreSQL line command; old confirmation rejected 409; fresh preparation/history/Case State; no automatic confirmation replay"
        capture("03-conflict-recovery")
        before = len(commands)
        post_ui("confirm", latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True), key=True)
        assert len(commands) == before + 1 and page.get_by_role("dialog").count() == 0
        assert stage() == "COMPLETE" and all(c["supplier_count"] == 1 for c in prep()["coverage"])
        assert read("/case-state")["next_action"]["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
        matrix["d6-one-click-one-supplier-complete"] = "PASS: one keyboard activation, one confirmation command, no second professional step; one issuer explicitly covers all sealed lines; COMPLETE from server"
        capture("04-confirmed-complete-downstream-hold")

        register(fixture["source_document_ids"][1], "BG-A14-OPTIONAL")
        assert stage() == "COMPLETE"
        optional = region.get_by_role("row").filter(has_text="BG-A14-OPTIONAL")
        open_action(optional, "Loại báo giá nháp")
        dialog = page.get_by_role("dialog")
        expect(dialog.get_by_role("button", name="Loại báo giá nháp", exact=True)).to_be_disabled()
        dialog.get_by_label("Lý do", exact=False).fill("Báo giá bổ sung chưa sử dụng")
        post_ui("reject", dialog.get_by_role("button", name="Loại báo giá nháp", exact=True))
        assert stage() == "COMPLETE"
        matrix["optional-draft-rejection"] = "PASS: optional draft preserves COMPLETE; explicit reason required; no rejection of confirmed authority"

        for mode, label in [("correction", "Sửa bằng phiên bản mới"), ("replacement", "Thay thế bằng phiên bản mới"), ("negotiation", "Phiên bản thương lượng")]:
            open_action(latest_row(), label)
            dialog = page.get_by_role("dialog")
            dialog.get_by_label("Lý do tạo phiên bản mới", exact=False).fill("Phiên bản tổng hợp " + mode)
            post_ui("revise", dialog.get_by_role("button", name=label, exact=True))
            assert stage() == ("COMPLETE" if mode == "negotiation" else "INCOMPLETE")
            if mode == "negotiation":
                # Fault occurs only after the real confirmation has committed successfully.
                (evidence / "drop-next-quote-response.flag").write_text("synthetic fault", encoding="utf-8")
                latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True).click()
                expect(region.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True)).to_be_visible()
                settled()
                attempt = page.evaluate("Object.keys(sessionStorage).filter(k => k.startsWith('valora:supplier-quotes:')).map(k => JSON.parse(sessionStorage.getItem(k)))[0]")
                assert attempt and attempt["commandId"]
                historical = read("/supplier-quotes/command-receipts/" + attempt["commandId"])
                assert historical["historical"] and historical["result"]["command_id"] == attempt["commandId"]
                attempts = [json.loads(line) for line in (evidence / "transport.jsonl").read_text(encoding="utf-8").splitlines()
                    if json.loads(line).get("command_id") == attempt["commandId"] and json.loads(line)["method"] == "POST"]
                assert len(attempts) == 1 and attempts[0]["response_dropped"]
                capture("05-unknown-committed-outcome")
                region.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True).click()
                settled()
                expect(region.get_by_role("button", name="Kiểm tra kết quả thao tác", exact=True)).to_have_count(0)
                assert stage() == "COMPLETE"
                matrix["unknown-original-uuid-reconcile"] = "PASS: actual committed response lost; original UUID retained; historical receipt queried before fresh authority; no automatic new command"
            else:
                post_ui("confirm", latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True))
                assert stage() == "COMPLETE"
            matrix[mode] = "PASS: append-only successor; coverage consequence observed from backend, never assumed locally"

        open_action(latest_row(), "Thu hồi báo giá", exact=False)
        dialog = page.get_by_role("dialog")
        reason = dialog.get_by_label("Lý do", exact=False)
        reason.fill("x" * 2001)
        expect(reason).to_have_attribute("aria-invalid", "true")
        assert reason.get_attribute("aria-describedby")
        reason.fill("Thu hồi báo giá tổng hợp hiện tại")
        first = dialog.get_by_role("button", name="Đóng", exact=True)
        first.focus()
        page.keyboard.press("Shift+Tab")
        assert dialog.evaluate("d => d.contains(document.activeElement)")
        post_ui("withdraw", dialog.get_by_role("button", name="Thu hồi báo giá", exact=True), key=True)
        assert stage() == "INCOMPLETE" and all(c["supplier_count"] == 0 for c in prep()["coverage"])
        matrix["withdraw-reason-accessibility"] = "PASS: explicit target/reason; field error association; dialog focus trap; keyboard command; no older revision fallback"
        capture("06-withdrawn-no-coverage")

        # Confirm one further successor to test COMPLETE outside DRAFT.
        open_action(latest_row(), "Sửa bằng phiên bản mới")
        dialog = page.get_by_role("dialog")
        dialog.get_by_label("Lý do tạo phiên bản mới", exact=False).fill("Hoàn thiện sau thu hồi")
        post_ui("revise", dialog.get_by_role("button", name="Sửa bằng phiên bản mới", exact=True))
        post_ui("confirm", latest_row().get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True))
        assert stage() == "COMPLETE"
        archive = context.request.post(api + "/archive", headers=headers)
        assert archive.ok, archive.text()
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
        settled()
        assert stage() == "COMPLETE" and prep()["writable"] is False
        expect(region.get_by_role("button", name="Đăng ký báo giá nháp", exact=True)).to_have_count(0)
        expect(region.get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True)).to_have_count(0)
        capture("07-nondraft-complete-read-only")
        viewer = browser.new_context(viewport={"width": 1440, "height": 900})
        response = viewer.request.post(base + "/api/v1/auth/login", data={"organization_slug": fixture["organization_slug"],
            "email": "viewer@a5.invalid", "password": os.environ["A14_SYNTHETIC_PASSWORD"]})
        assert response.ok
        denied = viewer.request.get(api + "/supplier-quotes/preparation")
        assert denied.ok and denied.json()["writable"] is False
        viewer_page = viewer.new_page()
        viewer_page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        viewer_page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
        viewer_region = viewer_page.get_by_role("region", name="Báo giá NCC toàn hồ sơ")
        expect(viewer_region).to_have_attribute("aria-busy", "false")
        expect(viewer_region.get_by_role("button", name="Đăng ký báo giá nháp", exact=True)).to_have_count(0)
        expect(viewer_region.get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True)).to_have_count(0)
        viewer_page.screenshot(path=str(evidence / "08-viewer-read-only.png"))
        safe = viewer.request.get(base + "/api/v1/projects/00000000-0000-4000-8000-000000000000/supplier-quotes")
        assert safe.status == 404
        viewer.close()
        matrix["viewer-cross-scope-nondraft"] = "PASS: real viewer read-only; safe out-of-scope 404; intact COMPLETE readable after archive; official UI writes unavailable"
        current_prices = [(l["id"], l["appraised_unit_price"]) for l in read("/asset-lines")["items"]]
        assert current_prices == initial_prices
        assert forbidden_counts() == initial_counts
        assert not page.get_by_role("button", name="Chọn NCC đã xác nhận giá", exact=True).count()
        assert not page.get_by_role("link", name="Chọn NCC đã xác nhận giá", exact=False).count()
        assert all(s["result"] == "NOT_AVAILABLE" for s in read("/case-state")["stages"][8:])
        matrix["downstream-price-boundaries"] = "PASS: no SUPPLIER_SELECTION CTA; downstream NOT_AVAILABLE; initial working prices unchanged by every quotation action"
        selection_calls = []
        page.on("request", lambda request: selection_calls.append(request.url) if "/ncc-selection" in request.url else None)
        page.goto(f"{base}/#/workbench/projects/{project}/ncc-selection", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Chưa có hành động tiếp theo được phép", exact=True)).to_be_visible()
        assert selection_calls == []
        matrix["direct-selection-route-hold"] = "PASS: direct legacy route remains unavailable; no selection service called"
        assert errors == [], errors
        (evidence / "browser-evidence.json").write_text(json.dumps({"fixture": fixture, "commands": commands, "matrix": matrix,
            "captures": captures, "page_errors": errors, "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "initial_forbidden_counts": initial_counts, "final_forbidden_counts": forbidden_counts(),
            "limitations": ["The main journey proves NULL working price and viewer/non-DRAFT reads. The separate live negatives harness proves zero working price with unassessed basis, actual closed-session, cross-tenant 404 and unauthenticated 401. Comparable-zero/other incomparable bases and explicit 403 remain supported by focused provider/controller/API tests. Separate live currentness evidence covers missing/corrupt source and inactive/merged/ambiguous issuers. These are synthetic single-browser proofs, not a load or assistive-technology certification."]}, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()


if __name__ == "__main__":
    main()
