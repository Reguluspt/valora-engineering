"""Real-stack Pre-case browser proof; no fake API or lifecycle fixture state."""

import json
import os
import sys
import hashlib
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "implementation" / "g11k-screenshots"
WORKBOOK = Path(__file__).parent / "fixtures" / "g11k_synthetic_assets.xlsx"
PROJECT_CODE = os.getenv("G11K_PROJECT_CODE", "G11K-E2E-20261001-001")
BASE = "http://localhost"
API = "http://localhost:8000/api/v1"


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel=os.getenv("G11K_BROWSER_CHANNEL"))
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = context.new_page()
        errors: list[dict[str, object]] = []
        authenticated = [False]
        authenticated_errors: list[dict[str, object]] = []
        commands: dict[str, object] = {}
        checkpoints: dict[str, object] = {}
        def record_response(response):
            if response.status >= 400:
                item = {"status": response.status, "url": response.url}
                errors.append(item)
                if authenticated[0]:
                    authenticated_errors.append(item)
        page.on("response", record_response)
        page.goto(BASE, wait_until="networkidle")
        page.get_by_label("Mã đơn vị").fill("g11k-synthetic-main")
        page.get_by_label("Email").fill("owner@g11k.invalid")
        page.get_by_label("Mật khẩu").fill(os.environ["G11K_SYNTHETIC_PASSWORD"])
        page.get_by_role("button", name="Đăng nhập", exact=True).click()
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").wait_for()
        authenticated[0] = True
        page.get_by_role("link", name="Quản lý yêu cầu sơ bộ").click()
        page.get_by_role("heading", name="Quản lý yêu cầu sơ bộ").wait_for()
        page.screenshot(path=str(EVIDENCE / "01-precase-management.png"))
        print("MANAGEMENT", page.url, page.locator("main").inner_text()[:700])
        print("COOKIES", [(cookie["name"], cookie["secure"]) for cookie in context.cookies()])
        print("DOCUMENT_COOKIE_NAMES", page.evaluate("document.cookie.split(';').map(v => v.trim().split('=')[0])"))

        if PROJECT_CODE not in page.locator("main").inner_text():
            page.get_by_role("button", name="Tạo yêu cầu sơ bộ").first.click()
            page.get_by_label("Mã hồ sơ").fill(PROJECT_CODE)
            page.get_by_label("Tên yêu cầu sơ bộ").fill("Danh mục thiết bị tổng hợp G1.1K")
            page.get_by_label("Mô tả").fill("Dữ liệu tổng hợp dành riêng cho kiểm chứng E2E G1.1K.")
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/api/v1/projects")) as create_response:
                page.get_by_role("button", name="Tạo yêu cầu sơ bộ", exact=True).click()
            print("CREATE_RESPONSE", create_response.value.status, create_response.value.text())
            commands["create_project"] = {"status": create_response.value.status,
                                           "payload": create_response.value.request.post_data_json,
                                           "response": create_response.value.json()}
        else:
            page.locator("tr").filter(has_text=PROJECT_CODE).get_by_role("button", name="Mở nhập liệu").click()
        page.get_by_role("heading", name="Danh mục thiết bị tổng hợp G1.1K").wait_for()
        page.screenshot(path=str(EVIDENCE / "02-created-intake-start.png"))
        print("INTAKE", page.url, page.locator("main").inner_text()[:1100])
        project_id = page.url.split("/projects/")[1].split("/")[0]
        project = context.request.get(f"{API}/projects/{project_id}")
        case_state = context.request.get(f"{API}/projects/{project_id}/case-state")
        print("PROJECT", project.status, project.json())
        print("CASE_STATE", case_state.status, case_state.json()["next_action"])
        checkpoints["created_request"] = case_state.json()["next_action"]

        if project.json()["current_preliminary_import_batch_id"] is None:
            page.get_by_label("Tệp Excel (.xlsx hoặc .xls)").set_input_files(str(WORKBOOK))
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/asset-imports")) as batch_response:
                page.get_by_role("button", name="Tải tệp Excel", exact=True).click()
            print("BATCH_RESPONSE", batch_response.value.status, batch_response.value.text())
            commands["create_batch"] = {"status": batch_response.value.status,
                                         "payload": batch_response.value.request.post_data_json,
                                         "response": batch_response.value.json()}
            if batch_response.value.status != 201:
                page.screenshot(path=str(EVIDENCE / "03-batch-rbac-blocker.png"))
                print("BATCH_BLOCKED_UI", page.locator("main").inner_text()[:1300])
                print("HTTP_ERRORS", json.dumps(errors))
                return
            page.get_by_text("g11k_synthetic_assets.xlsx").first.wait_for(timeout=20000)
            page.screenshot(path=str(EVIDENCE / "03-upload-actionable.png"))
            print("AFTER_UPLOAD", page.locator("main").inner_text()[:1400])
            page.reload(wait_until="networkidle")
            page.get_by_text("g11k_synthetic_assets.xlsx").first.wait_for()
            print("AFTER_UPLOAD_RELOAD", page.locator("main").inner_text()[:1000])
            print("CASE_STATE_AFTER_UPLOAD", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
            checkpoints["source_uploaded"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]

        analyze_button = page.get_by_role("button", name="Phân tích cấu trúc", exact=True)
        if analyze_button.count() > 0:
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/structure-snapshots")) as structure_response:
                analyze_button.click()
            structure = structure_response.value.json()
            assert structure_response.value.status == 201, structure
            print("STRUCTURE", structure["id"], structure["candidate_count"], structure["disposition"])
            commands["analyze_structure"] = {"status": structure_response.value.status, "response": structure}
            page.get_by_text("Vùng bảng được phát hiện").wait_for()
            page.screenshot(path=str(EVIDENCE / "04-structure-review.png"))
            print("STRUCTURE_UI", page.locator("main").inner_text()[:2200])
        if page.get_by_role("button", name="Tạo đề xuất ánh xạ").count() > 0:
            page.get_by_label("Bản phân tích cấu trúc").select_option(index=1)
            page.locator('input[name="workbook-candidate"]').first.check()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/column-mapping/proposals")) as proposal_response:
                page.get_by_role("button", name="Tạo đề xuất ánh xạ").click()
            proposal = proposal_response.value.json()
            assert proposal_response.value.status == 201, proposal
            print("PROPOSAL", proposal["decision_id"], proposal["review_required"], proposal["mapping_snapshot"]["fields"])
            commands["mapping_proposal"] = {"status": proposal_response.value.status,
                                              "payload": proposal_response.value.request.post_data_json,
                                              "response": proposal}
            page.locator('[data-mapping-stage="proposal"]').wait_for()
            page.screenshot(path=str(EVIDENCE / "05-mapping-proposal.png"), full_page=True)
            print("PROPOSAL_UI", page.locator("main").inner_text()[:2800])
            assert [page.get_by_label(f"Vai trò cho cột {letter}").input_value() for letter in "ABCDEFG"] == [
                "row_number", "raw_asset_name", "raw_description", "unit", "quantity",
                "customer_unit_price", "customer_amount",
            ]
            page.get_by_label("Tôi đã rà soát vùng bảng và từng vai trò cột.").check()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/column-mapping/confirmations")) as confirmation_response:
                page.get_by_role("button", name="Xác nhận ánh xạ").click()
            confirmation = confirmation_response.value.json()
            assert confirmation_response.value.status == 201, confirmation
            print("CONFIRMATION", confirmation)
            commands["mapping_confirmation"] = {"status": confirmation_response.value.status,
                                                   "payload": confirmation_response.value.request.post_data_json,
                                                   "response": confirmation}
            page.get_by_role("button", name="Tạo dữ liệu tạm").wait_for()
            page.screenshot(path=str(EVIDENCE / "06-mapping-confirmed.png"))
            print("CONFIRMED_UI", page.locator("main").inner_text()[:2500])
            page.reload(wait_until="networkidle")
            page.get_by_role("button", name="Tạo dữ liệu tạm").wait_for()
            print("CONFIRMED_RELOAD", page.locator("main").inner_text()[:1300])
            current_batch = context.request.get(f"{API}/projects/{project_id}").json()["current_preliminary_import_batch_id"]
            recovery_response = context.request.get(
                f"{API}/projects/{project_id}/asset-imports/{current_batch}/column-mapping/state"
            )
            assert recovery_response.status == 200
            commands["mapping_confirmation"]["recovery_after_reload"] = recovery_response.json()
        if page.get_by_role("button", name="Tạo dữ liệu tạm").count() > 0:
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/column-mapping/materializations")) as materialization_response:
                page.get_by_role("button", name="Tạo dữ liệu tạm").click()
            materialization = materialization_response.value.json()
            assert materialization_response.value.status == 201, materialization
            print("MATERIALIZATION", materialization)
            commands["mapping_materialization"] = {"status": materialization_response.value.status,
                                                      "payload": materialization_response.value.request.post_data_json,
                                                      "response": materialization}
            page.get_by_text("Đã đưa 12 dòng tài sản").wait_for()
            page.screenshot(path=str(EVIDENCE / "07-staging-materialized.png"))
            print("MATERIALIZED_UI", page.locator("main").inner_text()[:2500])
            page.reload(wait_until="networkidle")
            page.get_by_text("Đã đưa 12 dòng tài sản").wait_for()
            print("MATERIALIZED_RELOAD", page.locator("main").inner_text()[:1800])
            print("CASE_STATE_AFTER_MATERIALIZE", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
            checkpoints["mapping_materialized"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]
        page.get_by_role("link", name="Tổng quan hồ sơ").click()
        page.get_by_role("heading", name="Tổng quan hồ sơ").wait_for()
        analysis_is_next = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]["semantic_route_key"] == "preliminary_analysis_pending"
        if analysis_is_next:
            page.screenshot(path=str(EVIDENCE / "08-case-overview-preanalysis.png"))
        print("OVERVIEW_PREANALYSIS", page.url, page.locator("main").inner_text()[:3500])
        if analysis_is_next:
            page.get_by_role("button", name="Tiếp tục xử lý").click()
        else:
            page.goto(f"{BASE}/#/workbench/projects/{project_id}/preliminary-analysis", wait_until="networkidle")
        page.get_by_role("heading", name="Phân tích danh mục").wait_for()
        print("ANALYSIS_START", page.url, page.locator("main").inner_text()[:1600])
        if page.get_by_role("button", name="Chốt phân tích sơ bộ").count() > 0:
            rows = page.locator("tr[data-row-source]")
            assert rows.count() == 12, rows.count()
            for index in range(rows.count()):
                row = rows.nth(index)
                source_row = int(row.get_attribute("data-row-source"))
                row.get_by_label(f"Cơ sở giá dòng {source_row}").fill("Giá tham chiếu tổng hợp đã rà soát")
                row.get_by_label(f"Giá tham chiếu dòng {source_row}").fill(str(100000 + index * 1000))
                row.get_by_label(f"Vận chuyển dòng {source_row}").fill("2")
                row.get_by_label(f"Đơn giá đề xuất dòng {source_row}").fill(str(90000 + index * 1000))
                row.get_by_label(f"Xác nhận rà soát dòng {source_row}").check()
            assert page.get_by_role("button", name="Chốt phân tích sơ bộ").is_enabled(), page.locator("main").inner_text()[:2500]
            page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
            # Let the enabled button's Fluent background transition finish before capture.
            page.wait_for_timeout(250)
            assert page.get_by_role("button", name="Chốt phân tích sơ bộ").is_enabled()
            page.screenshot(path=str(EVIDENCE / "09-analysis-review.png"), full_page=True)
            print("ANALYSIS_REVIEW", page.locator("main").inner_text()[:2100])
            page.get_by_role("button", name="Chốt phân tích sơ bộ").click()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/preliminary-analyses")) as finalize_response:
                page.get_by_role("button", name="Xác nhận chốt").click()
            print("ANALYSIS_FINALIZE_RESPONSE", finalize_response.value.status, finalize_response.value.text()[:1800])
            commands["analysis_finalize"] = {"status": finalize_response.value.status,
                                                "payload": finalize_response.value.request.post_data_json,
                                                "response": finalize_response.value.json()}
            assert finalize_response.value.status in (200, 201)
        page.get_by_text("Đã chốt phân tích sơ bộ · phiên bản").first.wait_for()
        page.screenshot(path=str(EVIDENCE / "10-analysis-finalized.png"), full_page=True)
        print("ANALYSIS_FINALIZED", page.locator("main").inner_text()[:2300])
        page.reload(wait_until="networkidle")
        page.get_by_text("Đã chốt phân tích sơ bộ · phiên bản").first.wait_for()
        print("ANALYSIS_RELOAD", page.locator("main").inner_text()[:600])
        print("CASE_STATE_AFTER_ANALYSIS", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
        checkpoints["analysis_finalized"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]
        page.get_by_role("button", name="Về Tổng quan hồ sơ").click()
        page.get_by_role("heading", name="Tổng quan hồ sơ").wait_for()
        page.get_by_role("button", name="Tiếp tục xử lý").click()
        page.get_by_role("heading", name="Kết quả sơ bộ & tiếp nhận").wait_for()
        print("COMPLETION_START", page.url, page.locator("main").inner_text()[:1700])
        if page.get_by_role("button", name="Tạo kết quả sơ bộ").count() > 0:
            page.screenshot(path=str(EVIDENCE / "11-result-ready.png"))
            page.get_by_role("button", name="Tạo kết quả sơ bộ").click()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/preliminary-results")) as result_response:
                page.get_by_role("button", name="Xác nhận", exact=True).click()
            print("RESULT_RESPONSE", result_response.value.status, result_response.value.text())
            commands["result_generate"] = {"status": result_response.value.status,
                                             "payload": result_response.value.request.post_data_json,
                                             "response": result_response.value.json()}
            assert result_response.value.status == 201
        page.get_by_role("button", name="Tải tệp Excel").wait_for()
        page.screenshot(path=str(EVIDENCE / "12-result-created.png"))
        print("RESULT_CREATED_UI", page.locator("main").inner_text()[:2200])
        state = context.request.get(f"{API}/projects/{project_id}/case-state").json()
        result_id = state["preliminary"]["current_preliminary_result_artifact_id"]
        result_metadata_response = context.request.get(f"{API}/projects/{project_id}/preliminary-results/{result_id}")
        assert result_metadata_response.status == 200
        result_metadata = result_metadata_response.json()
        with page.expect_download() as download_event:
            page.get_by_role("button", name="Tải tệp Excel").click()
        download = download_event.value
        result_path = EVIDENCE / "g11k-result-downloaded.xlsx"
        download.save_as(result_path)
        downloaded = result_path.read_bytes()
        assert len(downloaded) == result_metadata["file_size_bytes"]
        assert hashlib.sha256(downloaded).hexdigest() == result_metadata["content_checksum_sha256"]
        print("RESULT_READ_DOWNLOAD", result_metadata, "download_name", download.suggested_filename,
              "download_size", len(downloaded), "download_sha256", hashlib.sha256(downloaded).hexdigest())
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="Tải tệp Excel").wait_for()
        print("RESULT_RELOAD", page.locator("main").inner_text()[:900])
        print("CASE_STATE_AFTER_RESULT", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
        checkpoints["result_generated"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]
        page.get_by_role("button", name="Về Tổng quan hồ sơ").click()
        page.get_by_role("heading", name="Tổng quan hồ sơ").wait_for()
        assert context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]["semantic_route_key"] == "official_intake_pending"
        page.get_by_role("button", name="Tiếp tục xử lý").click()
        page.get_by_role("heading", name="Kết quả sơ bộ & tiếp nhận").wait_for()
        project_now = context.request.get(f"{API}/projects/{project_id}").json()
        if project_now["customer_id"] is None:
            page.get_by_label("Tên, mã số thuế hoặc số điện thoại").fill("G11K-SYNTHETIC-001")
            page.get_by_role("button", name="Tìm khách hàng").click()
            page.get_by_role("radiogroup", name="Chọn Customer đang hoạt động").wait_for()
            page.get_by_role("radiogroup", name="Chọn Customer đang hoạt động").get_by_role("radio").first.check()
            page.screenshot(path=str(EVIDENCE / "13-customer-selected.png"), full_page=True)
            print("CUSTOMER_SELECTED_UI", page.locator("main").inner_text()[:1800])
            page.get_by_role("button", name="Gắn khách hàng đã chọn").click()
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/preliminary-customer")) as customer_response:
                page.get_by_role("button", name="Xác nhận", exact=True).click()
            print("CUSTOMER_BIND_RESPONSE", customer_response.value.status, customer_response.value.text())
            commands["customer_bind"] = {"status": customer_response.value.status,
                                          "payload": customer_response.value.request.post_data_json,
                                          "response": customer_response.value.json()}
            assert customer_response.value.status in (200, 201)
        page.get_by_role("button", name="Chuyển sang thẩm định chính thức").wait_for()
        page.screenshot(path=str(EVIDENCE / "14-customer-bound.png"))
        print("CUSTOMER_BOUND_UI", page.locator("main").inner_text()[:2400])
        page.reload(wait_until="networkidle")
        page.get_by_text("Khách hàng tổng hợp G1.1K").first.wait_for()
        print("CUSTOMER_RELOAD", page.locator("main").inner_text()[:1000])
        print("CASE_STATE_AFTER_CUSTOMER", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
        checkpoints["customer_bound"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]
        if page.get_by_role("button", name="Chuyển sang thẩm định chính thức").count() > 0:
            page.get_by_role("button", name="Chuyển sang thẩm định chính thức").click()
            assert page.evaluate("document.querySelector('dialog[open]').contains(document.activeElement)")
            page.keyboard.press("Tab")
            assert page.evaluate("document.querySelector('dialog[open]').contains(document.activeElement)")
            page.screenshot(path=str(EVIDENCE / "15-official-intake-confirmation.png"))
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/official-intake")) as intake_response:
                page.get_by_role("button", name="Xác nhận chuyển chính thức").click()
            print("OFFICIAL_INTAKE_RESPONSE", intake_response.value.status, intake_response.value.text())
            commands["official_intake"] = {"status": intake_response.value.status,
                                            "payload": intake_response.value.request.post_data_json,
                                            "response": intake_response.value.json()}
            assert intake_response.value.status == 201
        page.get_by_text("Đã tiếp nhận chính thức").first.wait_for()
        page.screenshot(path=str(EVIDENCE / "16-official-intake-committed.png"))
        print("OFFICIAL_INTAKE_UI", page.locator("main").inner_text()[:2500])
        page.reload(wait_until="networkidle")
        page.get_by_text("Đã tiếp nhận chính thức").first.wait_for()
        print("OFFICIAL_INTAKE_RELOAD", page.locator("main").inner_text()[:1200])
        print("CASE_STATE_AFTER_INTAKE", context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"])
        checkpoints["official_intake_committed"] = context.request.get(f"{API}/projects/{project_id}/case-state").json()["next_action"]
        page.get_by_role("button", name="Về Tổng quan hồ sơ").click()
        page.get_by_role("heading", name="Tổng quan hồ sơ").wait_for()
        page.screenshot(path=str(EVIDENCE / "17-case-overview-post-intake.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        print("OVERVIEW_POST_INTAKE", page.locator("main").inner_text()[:3900])
        print("HTTP_ERRORS", json.dumps(errors))
        assert not authenticated_errors, authenticated_errors
        (EVIDENCE.parent / "g11k-runtime-evidence.json").write_text(json.dumps({
            "project_code": PROJECT_CODE,
            "project_id": project_id,
            "commands": commands,
            "case_state_checkpoints": checkpoints,
            "result_metadata": result_metadata,
            "result_download": {"size": len(downloaded), "sha256": hashlib.sha256(downloaded).hexdigest()},
            "post_intake_case_state": context.request.get(f"{API}/projects/{project_id}/case-state").json(),
            "authenticated_http_errors": authenticated_errors,
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        context.close()
        browser.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
