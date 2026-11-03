"""Exercise the preliminary summary through an isolated local browser and synthetic fixtures."""

import argparse
import hashlib
import json
import re
import socket
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


LABELS = ["Đã xem", "Chưa xem", "Thiếu đơn giá", "Thiếu chứng cứ", "Cần kiểm tra lại"]
LONG_NAME = "Hệ thống máy gia công cơ khí chính xác điều khiển tự động tích hợp bộ cấp phôi và tủ điều khiển trung tâm dùng trong nhà xưởng công nghiệp " * 3
LONG_ID = "SYNTHETIC-ASSET-" + "150" * 20


def source_hashes(root):
    paths = sorted((root / "src").glob("*")) + [root / "package.json", root / "package-lock.json", Path(__file__).resolve()]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def summary(page):
    page.get_by_role("button", name="Tổng kết & xuất", exact=True).click()
    page.get_by_role("region", name="Tổng kết kết quả sơ bộ", exact=True).wait_for()
    page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")


def counts(page):
    return page.locator(".summary-cards dd").all_text_contents()


def total(page):
    return page.locator(".total-price strong").inner_text()


def geometry(page):
    return page.locator(".summary-screen").evaluate("""e=>{
      const box=x=>({text:x.innerText,rect:x.getBoundingClientRect().toJSON(),client:[x.clientWidth,x.clientHeight],scroll:[x.scrollWidth,x.scrollHeight],font:getComputedStyle(x).fontSize,color:getComputedStyle(x).color,background:getComputedStyle(x.closest('.total-price,.summary-cards>div')||x).backgroundColor,outline:getComputedStyle(x).outline});
      return {viewport:[innerWidth,innerHeight],bodyOverflow:document.documentElement.scrollWidth>innerWidth,
        screen:box(e),cards:[...e.querySelectorAll('.summary-cards>div')].map(box),
        panels:[...e.querySelectorAll('.summary-panel')].map(box),total:box(e.querySelector('.total-price')),
        cta:box(e.querySelector('.summary-confirmation>button')),list:box(e.querySelector('.summary-attention-scroll')),
        figures:[...e.querySelectorAll('dd,.total-price strong')].map(box),
        clipped:[...e.querySelectorAll('dt,dd,strong,small,button,.summary-reasons,.summary-asset-id,.fui-Checkbox__label')].filter(x=>x.clientWidth>0&&x.scrollWidth>x.clientWidth+1).map(box)};
    }""")


def contrast(foreground, background):
    def luminance(color):
        values = [float(v) / 255 for v in re.findall(r"[\d.]+", color)[:3]]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(v * w for v, w in zip(linear, [.2126, .7152, .0722]))
    high, low = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (high + .05) / (low + .05)


def verify_layout(page, count, out, name):
    expected = ["1/6", "5", "3", "2", "1"] if count == 6 else ["1/150", "149", "75", "50", "25"]
    assert page.locator(".summary-cards dt").all_text_contents() == LABELS
    assert counts(page) == expected, counts(page)
    assert total(page) == ("514.480.000 đ" if count == 6 else "12.862.000.000 đ"), total(page)
    assert page.locator(".summary-list>li").count() == count - 1
    assert page.locator(".summary-list>li").filter(has_text="TS-006").count() == 1
    assert page.locator(".summary-list>li").filter(has_text="TS-006").locator(".summary-reasons span").all_text_contents() == ["Thiếu đơn giá", "Cần kiểm tra nguồn", "Chưa xem"]
    g = geometry(page)
    assert not g["bodyOverflow"] and not g["clipped"], g
    assert all(float(f["font"].replace("px", "")) >= 24 for f in g["figures"]), g["figures"]
    g["figureContrastRatios"] = [contrast(f["color"], f["background"]) for f in g["figures"]]
    assert all(ratio >= 4.5 for ratio in g["figureContrastRatios"]), g["figureContrastRatios"]
    if page.viewport_size["width"] >= 1280:
        assert g["cta"]["rect"]["bottom"] <= page.viewport_size["height"], g["cta"]
    assert len(g["cards"]) == 5
    assert page.locator(".summary-confirmation>button").count() == 1
    assert page.locator(".summary-confirmation>button").is_disabled()
    assert page.locator(".summary-screen [role='grid']").count() == 0
    assert page.get_by_role("region", name="Các tài sản cần chú ý", exact=True).count() == 1
    assert page.get_by_role("region", name="Xem trước kết quả", exact=True).count() == 1
    assert page.get_by_role("heading", name="Các tài sản cần chú ý", level=2, exact=True).count() == 1
    assert page.get_by_role("heading", name="Xem trước kết quả", level=2, exact=True).count() == 1
    assert page.get_by_role("heading", name="Lịch sử phiên bản (bộ nhớ trang)", level=3, exact=True).count() == 1
    assert page.locator(".summary-screen").get_by_text("Đơn giá chưa xác định được để trống", exact=False).is_visible()
    page.screenshot(path=str(out / (name + "-viewport.png")))
    page.screenshot(path=str(out / (name + "-full.png")), full_page=True)
    if count == 150:
        last = page.locator(".summary-list>li").last
        last.get_by_role("button").scroll_into_view_if_needed()
        assert last.get_by_role("button").is_visible()
        assert last.locator("strong").inner_text() == LONG_NAME.strip()
        assert last.locator(".summary-asset-id").inner_text() == LONG_ID
        assert not geometry(page)["clipped"]
        page.screenshot(path=str(out / (name + "-last-row.png")))
        g["listAfterScroll"] = geometry(page)["list"]
    return {"counts": expected, "total": total(page), "geometry": g}


def verify_empty(page):
    assert counts(page) == ["6/6", "0", "0", "2", "0"], counts(page)
    assert page.locator(".summary-list>li").count() == 0
    assert page.locator(".summary-empty").is_visible()
    assert "Bạn vẫn cần xem các chỉ số cảnh báo" in page.locator(".summary-empty").inner_text()
    assert page.locator(".summary-confirmation>button").is_disabled()
    return {"counts": counts(page), "text": page.locator(".summary-empty").inner_text(), "missingEvidenceDoesNotInventAttentionRows": True}


def verify_price_state(page, unknown):
    assert total(page) == "0 đ", total(page)
    assert counts(page) == (["1/6", "5", "6", "2", "1"] if unknown else ["1/6", "5", "0", "2", "1"])
    assert page.locator(".summary-list>li").count() == (6 if unknown else 5)
    assert "không coi là giá 0" in page.locator(".total-price").inner_text()
    return {"unknown": unknown, "counts": counts(page), "total": total(page)}


def verify_navigation(page, asset_id="TS-004"):
    before_total = total(page)
    before_counts = counts(page)
    row = page.locator(".summary-list>li").filter(has=page.get_by_role("button", name="Xử lý " + asset_id, exact=True))
    before_name = row.locator("strong").inner_text()
    row.get_by_role("button").click()
    assert page.locator(".summary-screen").count() == 0
    assert page.locator(".drawer-name").inner_text() == before_name
    assert asset_id in page.locator(".drawer-eyebrow").inner_text()
    assert page.locator(".selected-row .asset-link small").inner_text() == asset_id
    assert page.get_by_label("Lọc tài sản", exact=True).input_value() == "all"
    assert page.get_by_placeholder("Tìm tài sản, model, công suất...").input_value() == ""
    assert not page.locator(".selected-row .viewed").count()
    selected_row = page.locator(".selected-row").inner_text()
    summary(page)
    assert total(page) == before_total
    after_counts = counts(page)
    assert int(after_counts[1]) == int(before_counts[1]) - 1, (before_counts, after_counts)
    return {"selected": asset_id, "name": before_name, "row": selected_row, "beforeCounts": before_counts, "afterCounts": after_counts, "totalUnchanged": True, "targetViewedOnlyWhenLeaving": True}


def tab_to(page, selector):
    seen = []
    for _ in range(180):
        if page.locator(selector).evaluate("e=>e===document.activeElement"):
            return seen
        page.keyboard.press("Tab")
        seen.append(page.evaluate("({tag:document.activeElement.tagName,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.innerText})"))
    raise AssertionError({"unreachable": selector, "focusOrder": seen})


def verify_keyboard_versions(page):
    assert page.locator("h1").evaluate("e=>e===document.activeElement")
    order = tab_to(page, ".summary-attention-scroll")
    ring = page.locator(".summary-attention-scroll").evaluate("e=>getComputedStyle(e).outlineStyle")
    assert ring == "solid", ring
    page.keyboard.press("Tab")
    assert page.get_by_role("button", name="Xử lý TS-002", exact=True).evaluate("e=>e===document.activeElement")
    page.keyboard.press("Enter")
    assert page.locator(".selected-row .asset-link small").inner_text() == "TS-002"
    order += tab_to(page, ".header-actions button:last-child")
    page.keyboard.press("Enter")
    page.locator(".summary-screen").wait_for()
    page.wait_for_function("document.activeElement===document.querySelector('h1')")
    order += tab_to(page, ".summary-confirmation input[type=checkbox]")
    assert page.locator(".summary-confirmation>button").is_disabled()
    page.keyboard.press("Space")
    assert page.get_by_role("checkbox").is_checked()
    page.keyboard.press("Tab")
    assert page.locator(".summary-confirmation>button").evaluate("e=>e===document.activeElement")
    page.keyboard.press("Enter")
    assert page.locator(".summary-meta strong").inner_text() == "v01"
    assert not page.get_by_role("checkbox").is_checked()
    assert page.locator(".summary-confirmation>button").is_disabled()
    assert page.locator(".summary-history-list li").count() == 1
    page.get_by_role("checkbox").check()
    page.locator(".summary-confirmation>button").click()
    assert page.locator(".summary-meta strong").inner_text() == "v02"
    assert page.locator(".summary-history-list li").all_text_contents() == ["Phiên bản v02Bản chụp minh họa", "Phiên bản v01Bản chụp minh họa"]
    assert "CHƯA tạo file Excel hoặc lưu máy chủ" in page.locator(".notice").inner_text()
    assert "không phải “Chấp nhận làm cơ sở thẩm định”" in page.locator(".summary-confirmation").inner_text()
    assert counts(page)[1] == "4", counts(page)
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Quay lại danh mục", exact=True).click()
    summary(page)
    assert not page.get_by_role("checkbox").is_checked()
    return {"focusOrder": order, "focusRing": ring, "keyboardNavigation": True, "versions": ["v02", "v01"], "ackResetAfterConfirmAndRoute": True, "unviewedNotAutoReviewed": True}


def verify_manual_and_dirty(page):
    page.get_by_role("checkbox").check()
    page.locator(".summary-confirmation>button").click()
    page.get_by_role("button", name="Quay lại danh mục", exact=True).click()
    field = page.get_by_label("Đơn giá đề xuất — nhân viên quyết định", exact=True)
    field.fill("123456789")
    field.press("Tab")
    survey = page.get_by_label("Đơn giá khảo sát", exact=True)
    survey.fill("90000000")
    survey.press("Tab")
    assert field.input_value() == "123456789"
    evidence = page.get_by_label("Diễn giải và dán chứng cứ", exact=True)
    evidence.fill("Nguồn minh họa https://example.org/summary-fixture")
    evidence.press("Tab")
    assert page.get_by_role("link", name="https://example.org/summary-fixture", exact=True).count() == 1
    summary(page)
    assert total(page) == "551.393.578 đ", total(page)
    assert "Có thay đổi chưa xuất thành phiên bản mới" in page.locator(".summary-preview").inner_text()
    assert page.locator(".summary-meta strong").inner_text() == "v01"
    page.get_by_role("checkbox").check()
    page.locator(".summary-confirmation>button").click()
    assert page.locator(".summary-meta strong").inner_text() == "v02"
    assert "Có thay đổi chưa xuất thành phiên bản mới" not in page.locator(".summary-preview").inner_text()
    return {"manualPriceRetainedAfterSurveyEdit": "123456789", "linkEvidenceRetained": True, "total": total(page), "staleWarningShownThenCleared": True}


def verify_pan(page):
    page.get_by_role("button", name="Quay lại danh mục", exact=True).click()
    page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")
    viewport = page.locator(".table-scroll")
    viewport.scroll_into_view_if_needed()
    viewport.focus()
    before = page.locator(".stats-strip").inner_text()
    selected = page.locator(".selected-row").inner_text()
    r = viewport.bounding_box()
    x, y = r["x"] + r["width"] - 30, min(r["y"] + 100, page.viewport_size["height"] - 60)
    page.mouse.move(x, y)
    page.keyboard.down("Space")
    page.mouse.down(button="right")
    assert viewport.evaluate("e=>e.classList.contains('panning')")
    page.mouse.move(x - 80, y - 60, steps=6)
    moved = viewport.evaluate("e=>[e.scrollLeft,e.scrollTop]")
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    assert moved[0] > 0 and moved[1] > 0, moved
    assert not viewport.evaluate("e=>e.classList.contains('panning')")
    assert page.locator(".stats-strip").inner_text() == before
    assert page.locator(".selected-row").inner_text() == selected
    summary(page)
    assert total(page) == "12.862.000.000 đ"
    return {"trustedSpaceRightDrag": True, "scroll": moved, "stateUnchanged": True, "summaryReturnTotal": total(page)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    frozen = source_hashes(root)
    results, console, fixtures = [], [], []
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    log = (out / "vite.log").open("w", encoding="utf-8")
    server = subprocess.Popen(["node", str(root / "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", str(port), "--strictPort"], cwd=root, stdout=log, stderr=subprocess.STDOUT)

    def run(name, action):
        try:
            result = {"name": name, "status": "PASS", "evidence": action()}
        except Exception as error:
            result = {"name": name, "status": "FAIL", "error": str(error), "trace": traceback.format_exc()}
        results.append(result)
        print(json.dumps({k: v for k, v in result.items() if k != "evidence"}, ensure_ascii=True), flush=True)

    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                urllib.request.urlopen(url, timeout=1).close()
                break
            except OSError:
                if time.monotonic() > deadline or server.poll() is not None:
                    raise RuntimeError("Local Vite server unavailable")
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            version = browser.version

            def new_page(width=1440, height=900, count=6, fixture="normal", collapsed=False):
                page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.on("console", lambda m: console.append({"type": m.type, "text": m.text, "location": m.location}))
                page.on("pageerror", lambda e: console.append({"type": "pageerror", "text": str(e)}))
                page.on("response", lambda r: console.append({"type": "http-error", "status": r.status, "url": r.url}) if r.status >= 400 else None)
                injection = ""
                if count == 150:
                    injection += "for(let i=6;i<150;i++){const a=structuredClone(initial[i%6]);a.id='SYNTH-'+String(i+1).padStart(3,'0');initial.push(a);}\n"
                    injection += f"initial[149].name={json.dumps(LONG_NAME)};initial[149].id={json.dumps(LONG_ID)};\n"
                if fixture == "empty":
                    injection += "initial.forEach(a=>{a.viewed=true;a.needsRecheck=false;a.proposed??=10;});\n"
                if fixture in ("unknown", "zero"):
                    injection += "initial.forEach(a=>a.proposed=" + ("null" if fixture == "unknown" else "0") + ");\n"
                if fixture == "large-total":
                    injection += "initial[0].proposed=99999999999999;\n"
                if injection:
                    def replace(route):
                        response = route.fetch()
                        body = response.text()
                        anchor = "const similar = ["
                        assert body.count(anchor) == 1, "Fixture anchor changed"
                        modified = body.replace(anchor, injection + anchor)
                        fixtures.append({"count": count, "fixture": fixture, "injection": injection, "servedOriginalSha256": hashlib.sha256(body.encode()).hexdigest(), "servedFixtureSha256": hashlib.sha256(modified.encode()).hexdigest()})
                        route.fulfill(response=response, body=modified)
                    page.route("**/src/App.tsx", replace)
                page.goto(url)
                page.locator("tbody tr").nth(count - 1).wait_for(state="attached")
                if collapsed:
                    page.get_by_role("button", name="Thu gọn thanh điều hướng", exact=True).click()
                summary(page)
                return page

            for width, height in [(1440, 900), (1280, 800)]:
                for count in [6, 150]:
                    for collapsed in [False, True]:
                        name = f"{width}x{height}-{count}-{'collapsed' if collapsed else 'expanded'}"
                        page = new_page(width, height, count, collapsed=collapsed)
                        run(name, lambda: verify_layout(page, count, out, name))
                        page.close()
            for width, height, label in [(1152, 720, "125"), (720, 450, "200")]:
                page = new_page(width, height, 150)
                name = "css-viewport-equivalent-" + label + "percent"
                run(name, lambda: verify_layout(page, 150, out, name))
                page.close()
            for fixture in ["empty", "unknown", "zero"]:
                page = new_page(fixture=fixture)
                run(fixture, lambda: verify_empty(page) if fixture == "empty" else verify_price_state(page, fixture == "unknown"))
                page.screenshot(path=str(out / (fixture + ".png")), full_page=True)
                page.close()
            page = new_page(fixture="large-total", width=720, height=450)
            run("large-total-readable", lambda: {"total": total(page), "geometry": geometry(page)} if total(page) == "200.000.304.479.998 đ" and not geometry(page)["clipped"] else (_ for _ in ()).throw(AssertionError(geometry(page))))
            page.screenshot(path=str(out / "large-total.png"), full_page=True)
            page.close()
            for name, action, count in [("asset-navigation", verify_navigation, 6), ("keyboard-ack-versions", verify_keyboard_versions, 6), ("manual-price-evidence-dirty-version", verify_manual_and_dirty, 6), ("space-right-drag-regression", verify_pan, 150)]:
                page = new_page(count=count)
                run(name, lambda: action(page))
                page.screenshot(path=str(out / (name + ".png")), full_page=True)
                page.close()
            page = new_page(count=150)
            run("long-name-id-navigation", lambda: verify_navigation(page, LONG_ID))
            page.close()
            after = source_hashes(root)
            run("source-and-runner-frozen", lambda: {"unchanged": True} if frozen == after else (_ for _ in ()).throw(AssertionError({"before": frozen, "after": after})))
            browser.close()
        fatal = [e for e in console if e["type"] in ("error", "pageerror", "http-error") and not (e.get("url", "").endswith("/favicon.ico") and e.get("status") == 404) and not (e.get("location", {}).get("url", "").endswith("/favicon.ico") and "404" in e.get("text", ""))]
        report = {"browser": "Microsoft Edge headless", "version": version, "zoom": "125/200% CSS viewport equivalents only; real browser zoom was not measured", "sourceHashes": frozen, "hashesAfterRun": after, "results": results, "fatalBrowserLogs": fatal, "faviconPolicy": "Inherited favicon.ico HTTP 404 retained as an out-of-scope advisory; no response mocked"}
        for name, data in [("results.json", report), ("console.json", console), ("fixtures.json", fixtures)]:
            (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("RESULT", sum(r["status"] == "PASS" for r in results), "PASS", sum(r["status"] == "FAIL" for r in results), "FAIL 0 SKIP", len(fatal), "FATAL BROWSER LOGS", flush=True)
        return 1 if any(r["status"] == "FAIL" for r in results) or fatal else 0
    finally:
        server.terminate()
        server.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
