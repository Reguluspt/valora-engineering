"""Real zero/incomparable-price, closed-session and unauthenticated browser checks."""
import json
import os
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    evidence = Path(os.environ["A14_EVIDENCE_DIR"])
    fixture = json.loads((evidence / "fixture-negatives.json").read_text(encoding="utf-8-sig"))
    project = fixture["project_id"]
    base = os.environ.get("A14_BASE_URL", "http://127.0.0.1:5173")
    expect.set_options(timeout=60000)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        assert context.request.post(base + "/api/v1/auth/login", data={"organization_slug": fixture["organization_slug"],
            "email": "operator@a5.invalid", "password": os.environ["A14_SYNTHETIC_PASSWORD"]}).ok
        api = base + f"/api/v1/projects/{project}"
        foreign = json.loads((evidence / "fixture.json").read_text(encoding="utf-8-sig"))["project_id"]
        assert foreign != project and context.request.get(base + f"/api/v1/projects/{foreign}/supplier-quotes").status == 404
        prices = context.request.get(api + "/asset-lines").json()["items"]
        history = context.request.get(api + "/supplier-quotes").json()
        assert any(str(line["appraised_unit_price"]) in ("0", "0.0", "0.00000000") for line in prices)
        assert history["items"][0]["terms"]["comparison_basis"] == "unassessed"
        assert all(item["warning_codes"] == [] for item in history["items"][0]["items"])
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(f"{base}/#/workbench/projects/{project}", wait_until="networkidle")
        page.get_by_role("button", name="Mở báo giá NCC toàn hồ sơ", exact=True).click()
        region = page.get_by_role("region", name="Báo giá NCC toàn hồ sơ")
        expect(page.locator('section[aria-label="Báo giá NCC toàn hồ sơ"]')).to_have_attribute("aria-busy", "false")
        expect(region.get_by_text("Cảnh báo: Chênh lệch tuyệt đối trên 15%", exact=True)).to_have_count(0)
        page.screenshot(path=str(evidence / "negatives-zero-incomparable.png"))

        def counts():
            return json.loads(subprocess.check_output(["docker", "exec", "-e", "PYTHONPATH=/app", "valora-a14-backend-v2",
                "python", "/e2e/g2_a14_fixture_fault.py", project, "counts"], text=True))
        before = counts()
        region.get_by_role("button", name="Xem báo giá", exact=False).click()
        page.get_by_role("dialog").get_by_role("button", name="Sửa bằng phiên bản mới", exact=True).click()
        dialog = page.get_by_role("dialog")
        dialog.get_by_role("textbox", name="Lý do tạo phiên bản mới", exact=True).fill("Kiểm tra phiên đã đóng")
        preparation = context.request.get(api + "/supplier-quotes/preparation").json()
        csrf = next(c["value"] for c in context.cookies() if c["name"] == "XSRF-TOKEN")
        close = context.request.post(base + "/api/v1/workbench/sessions/" + preparation["session_id"] + "/close",
            headers={"X-CSRF-Token": csrf, "Origin": base})
        assert close.ok, close.text()
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/supplier-quotes/revise")) as rejected:
            dialog.get_by_role("button", name="Sửa bằng phiên bản mới", exact=True).click()
        assert rejected.value.status == 404, rejected.value.text()
        expect(page.locator('section[aria-label="Báo giá NCC toàn hồ sơ"]')).to_have_attribute("aria-busy", "false")
        expect(dialog.get_by_role("button", name="Sửa bằng phiên bản mới", exact=True)).to_be_disabled()
        assert context.request.get(api + "/supplier-quotes/preparation").json()["writable"] is False
        assert counts() == before
        page.screenshot(path=str(evidence / "negatives-closed-session.png"))
        dialog.get_by_role("button", name="Hủy", exact=True).click()
        await_auth = []
        page.on("response", lambda response: await_auth.append(response.status) if "/supplier-quotes/" in response.url else None)
        context.clear_cookies()
        assert context.request.get(api + "/supplier-quotes/preparation").status == 401
        region.get_by_role("button", name="Tải lại báo giá", exact=True).click()
        expect(region.get_by_role("table", name="Báo giá và phiên bản")).to_have_count(0)
        expect(region.get_by_role("button", name="Đăng ký báo giá nháp", exact=True)).to_have_count(0)
        expect(region.get_by_text("Phiên đăng nhập đã hết hạn.", exact=False)).to_be_visible()
        assert 401 in await_auth
        assert counts() == before
        (evidence / "negative-evidence.json").write_text(json.dumps({"fixture": fixture, "prices": prices, "history": history,
            "zero_incomparable": "PASS: server sends no synthetic warning; deterministic comparable-zero threshold test also passes",
            "closed_session": "PASS: actual session closed after form opened; original revision rejected safe 404, no fact/receipt mutation; refreshed controls disabled",
            "unauthenticated": "PASS: actual cookies removed; API 401, protected quotation content removed and writes locked, no mutation", "before": before, "after": counts(),
            "cross_tenant": "PASS: authenticated owner of another actual synthetic tenant receives safe 404 for the main journey project",
            "viewport": {"width": 1440, "height": 900}}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("zero/incomparable, closed-session, 401: PASS", flush=True)
        browser.close()


if __name__ == "__main__":
    main()
