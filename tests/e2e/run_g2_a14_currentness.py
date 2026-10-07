"""Real browser reads after external faults in explicitly isolated synthetic fixtures."""
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["A14_EVIDENCE_DIR"])
    base = os.environ.get("A14_BASE_URL", "http://127.0.0.1:5173")
    records = []
    expect.set_options(timeout=60000)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for fault in ("missing", "corrupt", "inactive", "merged", "ambiguous"):
            fixture = json.loads((evidence / f"fixture-{fault}.json").read_text(encoding="utf-8-sig"))
            project = fixture["project_id"]
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            login = context.request.post(base + "/api/v1/auth/login", data={"organization_slug": fixture["organization_slug"],
                "email": "operator@a5.invalid", "password": os.environ["A14_SYNTHETIC_PASSWORD"]})
            assert login.ok
            page = context.new_page()
            page.set_default_timeout(60000)
            commands = []
            page.on("request", lambda request: commands.append(request.url) if request.method == "POST" and "/supplier-quotes/" in request.url else None)
            api = base + f"/api/v1/projects/{project}"
            before = context.request.get(api + "/supplier-quotes/preparation").json()
            if before["result"] == "COMPLETE":
                subprocess.run(["docker", "exec", "-e", "PYTHONPATH=/app", "valora-a14-backend-v2", "python", "/e2e/g2_a14_fixture_fault.py", project, fault], check=True, capture_output=True, text=True)
            page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
            page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
            region = page.get_by_role("region", name="Báo giá NCC toàn hồ sơ")
            expect(region).to_have_attribute("aria-busy", "false")
            after = context.request.get(api + "/supplier-quotes/preparation").json()
            case_response = context.request.get(api + "/case-state")
            assert case_response.ok, case_response.text()
            case = case_response.json()
            assert case["case_version"] == after["case_version"]
            assert case["stages"][7]["result"] == after["result"]
            assert after["result"] == ("BLOCKED" if fault == "ambiguous" else "STALE"), after
            assert all(c["supplier_count"] == 0 for c in after["coverage"])
            expect(region.get_by_text("Đang bị chặn" if fault == "ambiguous" else "Cần xem lại", exact=True)).to_be_visible()
            expect(region.get_by_role("button", name="Hoàn tất báo giá NCC này", exact=True)).to_have_count(0)
            region.get_by_role("heading", name="Báo giá NCC · Toàn hồ sơ", exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(evidence / f"currentness-{fault}.png"), animations="disabled")
            if fault in ("missing", "corrupt"):
                catalog = context.request.get(api + "/supplier-quotes/sources").json()
                assert catalog["items"] and all(s["available"] is False for s in catalog["items"])
                register = region.get_by_role("button", name="Đăng ký báo giá nháp", exact=True)
                if register.count():
                    register.click()
                    dialog = page.get_by_role("dialog")
                    source = dialog.get_by_label("Nguồn báo giá đã lưu", exact=False)
                    expect(source).to_have_value("")
                    assert source.locator("option[value]:not([value='']):not([disabled])").count() == 0
                    expect(dialog.get_by_role("button", name="Đăng ký báo giá nháp", exact=True)).to_be_disabled()
                    dialog.get_by_role("button", name="Hủy", exact=True).click()
            assert commands == []
            records.append({"fault": fault, "fixture": fixture, "before": before, "after": after, "case_state": case, "commands": commands,
                "capture": f"currentness-{fault}.png", "viewport": {"width": 1440, "height": 900}})
            (evidence / "currentness-evidence.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"currentness-{fault}: PASS", flush=True)
            context.close()
        browser.close()


if __name__ == "__main__":
    main()
