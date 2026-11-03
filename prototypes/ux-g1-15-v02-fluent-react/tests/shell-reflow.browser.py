"""Compare shell reflow in installed Edge without changing application fixtures on disk."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


VIEWPORTS = [(320, 640), (390, 844), (768, 1024), (1024, 768), (1280, 800), (1440, 900)]
GEOMETRY = """() => {
  const box=e=>{if(!e)return null;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom,clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,overflowX:s.overflowX,display:s.display,radius:s.borderRadius,background:s.backgroundColor}};
  const selectors=['html','body','.app-layout','.sidebar','.sidebar-card','.app-main','.topbar','.topbar .fui-Breadcrumb','.topbar ol','.topbar-right','.page','.page-header','.stats-strip','.workarea','.grid-area','.table-scroll','.asset-drawer','.detail-tabs','.drawer-scroll','.drawer-footer','.summary-screen','.summary-cards','.summary-columns','.summary-panel','.summary-confirmation','.summary-attention-scroll'];
  const selector=e=>{if(e.id)return '#'+CSS.escape(e.id);const a=[];while(e&&e!==document.body){const c=[...e.classList].filter(x=>!/^f[0-9a-z]+$/.test(x)).slice(0,2);let n=e.tagName.toLowerCase()+c.map(x=>'.'+CSS.escape(x)).join('');if(e.parentElement)n+=':nth-child('+([...e.parentElement.children].indexOf(e)+1)+')';a.unshift(n);e=e.parentElement;}return 'body > '+a.join(' > ')};
  const beyond=[...document.querySelectorAll('.page *')].filter(e=>e.clientWidth>0&&!e.closest('.table-scroll')&&getComputedStyle(e).display!=='none'&&(e.scrollWidth>e.clientWidth+1||e.getBoundingClientRect().right>innerWidth+1));
  return {width:innerWidth,height:innerHeight,dpr:devicePixelRatio,documentWidth:document.documentElement.scrollWidth,scrollX,scrollY,boxes:Object.fromEntries(selectors.map(s=>[s,box(document.querySelector(s))])),tiles:[...document.querySelectorAll('.sidebar.collapsed .side-btn')].map(e=>({name:e.getAttribute('aria-label')||e.textContent,box:box(e),icon:box(e.querySelector('.fui-Button__icon'))})),breadcrumbs:[...document.querySelectorAll('.topbar button')].map(e=>({name:e.textContent,box:box(e)})),overflow:beyond.map(e=>({selector:selector(e),text:e.textContent.slice(0,100),box:box(e),parent:box(e.parentElement),scrollAncestor:(()=>{let p=e.parentElement;while(p&&getComputedStyle(p).overflowX==='visible')p=p.parentElement;return p?{selector:selector(p),box:box(p)}:null})()}))};
}"""


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def hashes(root):
    return {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in [*root.joinpath("src").glob("*"), root / "package.json", root / "package-lock.json", *root.joinpath("tests").glob("*")] if p.is_file()}


def geometry(page):
    return page.evaluate(GEOMETRY)


def shell_only(page):
    return page.evaluate("""() => {
      const children=[...document.querySelector('.page').children].filter(e=>!e.matches('.page-header,.page-footer'));
      const originals=children.map(e=>e.getAttribute('style'));
      children.forEach(e=>e.style.display='none');
      const main=document.querySelector('.app-main'),top=document.querySelector('.topbar');
      const result={documentWidth:document.documentElement.scrollWidth,mainClient:main.clientWidth,mainScroll:main.scrollWidth,topClient:top.clientWidth,topScroll:top.scrollWidth};
      children.forEach((e,i)=>originals[i]===null?e.removeAttribute('style'):e.setAttribute('style',originals[i]));
      return result;
    }""")


def failures(g, isolated, collapsed):
    b, width = g["boxes"], g["width"]
    errors = []
    for selector in [".sidebar", ".sidebar-card", ".app-main", ".topbar", ".topbar .fui-Breadcrumb", ".topbar-right", ".page", ".page-header"]:
        r = b[selector]
        if r["x"] < -.5 or r["right"] > width + .5:
            errors.append(selector + " exceeds viewport")
    if isolated["documentWidth"] > width or isolated["mainScroll"] > isolated["mainClient"] + 1 or isolated["topScroll"] > isolated["topClient"] + 1:
        errors.append("shell generates overflow with feature surfaces excluded")
    for crumb in g["breadcrumbs"]:
        if crumb["box"]["right"] > width + .5 or crumb["box"]["scrollWidth"] > crumb["box"]["clientWidth"] + 1:
            errors.append("breadcrumb clipped: " + crumb["name"])
    if width < 768:
        if abs(b[".app-main"]["width"] - width) > .5:
            errors.append("sidebar squeezes main")
        if b[".sidebar"]["bottom"] > b[".topbar"]["y"] + .5:
            errors.append("sidebar/topbar overlap")
    if b[".topbar"]["bottom"] > b[".page-header"]["y"] + .5:
        errors.append("topbar/content overlap")
    if collapsed:
        for tile in g["tiles"]:
            r, icon = tile["box"], tile["icon"]
            if abs(r["width"] - 44) > .1 or abs(r["height"] - 44) > .1 or abs(icon["x"] + icon["width"] / 2 - r["x"] - 22) > .5 or abs(icon["y"] + icon["height"] / 2 - r["y"] - 22) > .5:
                errors.append("icon tile is not symmetric 44x44")
    return errors


def new_page(browser, url, width, height, count, logs, fixtures):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
    page.on("console", lambda m: logs.append({"type": m.type, "text": m.text, "location": m.location}))
    page.on("pageerror", lambda e: logs.append({"type": "pageerror", "text": str(e)}))
    if count == 150:
        def replace(route):
            response = route.fetch()
            body = response.text()
            anchor = "const similar = ["
            assert body.count(anchor) == 1
            injection = 'initial.push(...Array.from({length:144},(_,i)=>({...initial[i%6],id:`TS-${String(i+7).padStart(3,"0")}`,name:`Hệ thống gia công cơ khí chính xác và điều khiển tự động tích hợp cho nhà máy thiết bị công nghiệp ${i+7}`})));\n'
            modified = body.replace(anchor, injection + anchor)
            fixtures.append({"originalSha256": hashlib.sha256(body.encode()).hexdigest(), "fixtureSha256": hashlib.sha256(modified.encode()).hexdigest(), "injection": injection})
            route.fulfill(response=response, body=modified)
        page.route("**/src/App.tsx", replace)
    page.goto(url, timeout=60000)
    page.locator("tbody tr").nth(count - 1).wait_for(state="attached")
    return page


def focus_evidence(page, out, name):
    page.keyboard.press("Tab")
    focused = page.evaluate("""() => {const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,text:e.textContent,name:e.getAttribute('aria-label'),rect:r.toJSON(),outline:s.outline,visible:e.matches(':focus-visible'),hit:e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}}""")
    page.screenshot(path=str(out / (name + ".png")))
    return focused


def keyboard(page, out, width):
    observations = []
    toggle = page.get_by_role("button", name="Thu gọn thanh điều hướng", exact=True)
    toggle.focus()
    observations.append(focus_evidence(page, out, f"{width}-toggle-next-focus"))
    toggle.focus()
    page.keyboard.press("Space")
    assert page.locator(".sidebar.collapsed").count() == 1
    assert page.get_by_role("button", name="Mở rộng thanh điều hướng", exact=True).evaluate("e=>e===document.activeElement")
    page.keyboard.press("Enter")
    assert page.locator(".sidebar.collapsed").count() == 0
    page.keyboard.press("Escape")
    assert toggle.evaluate("e=>e===document.activeElement")
    page.locator(".topbar button").first.focus()
    for i in range(3):
        if i:
            observations.append(focus_evidence(page, out, f"{width}-breadcrumb-{i}-focus"))
        assert page.locator(".topbar").evaluate("e=>e.contains(document.activeElement)")
        g = geometry(page)
        r = page.evaluate("document.activeElement.getBoundingClientRect().toJSON()")
        assert r["x"] >= 0 and r["right"] <= g["width"] and r["y"] >= 0 and r["bottom"] <= g["height"]
    page.locator(".topbar button").first.focus()
    page.keyboard.press("Enter")
    assert page.locator("h1").inner_text() == "Phân tích danh mục"
    page.wait_for_function("document.activeElement===document.querySelector('h1')")
    page.locator(".sidebar").get_by_role("button", name="Tổng kết & phiên bản", exact=True).focus()
    page.keyboard.press("Enter")
    page.locator(".summary-screen").wait_for()
    page.wait_for_function("document.activeElement===document.querySelector('h1')")
    page.locator(".sidebar").get_by_role("button", name="Phân tích danh mục", exact=True).focus()
    page.keyboard.press("Space")
    page.locator(".table-scroll").wait_for()
    page.wait_for_function("document.activeElement===document.querySelector('h1')")
    page.locator(".grid-toolbar input").fill("TS-001")
    page.locator(".grid-toolbar select").select_option("unviewed")
    price = page.get_by_role("spinbutton", name="Đơn giá đề xuất — nhân viên quyết định", exact=True)
    price.fill("123456789")
    page.keyboard.down("Control")
    page.keyboard.press("A")
    page.keyboard.up("Control")
    page.keyboard.type("123456789")
    before = page.evaluate("""() => ({route:document.querySelector('h1').textContent,selected:document.querySelector('.drawer-eyebrow').textContent,search:document.querySelector('.grid-toolbar input').value,filter:document.querySelector('.grid-toolbar select').value,fields:[...document.querySelectorAll('.asset-drawer input')].map(e=>e.value),stats:document.querySelector('.stats-strip').textContent})""")
    toggle.click()
    page.get_by_role("button", name="Mở rộng thanh điều hướng", exact=True).click()
    after = page.evaluate("""() => ({route:document.querySelector('h1').textContent,selected:document.querySelector('.drawer-eyebrow').textContent,search:document.querySelector('.grid-toolbar input').value,filter:document.querySelector('.grid-toolbar select').value,fields:[...document.querySelectorAll('.asset-drawer input')].map(e=>e.value),stats:document.querySelector('.stats-strip').textContent})""")
    assert before == after, {"before": before, "after": after}
    page.set_viewport_size({"width": 1280, "height": 800})
    assert page.locator(".sidebar.collapsed").count() == 0
    page.get_by_role("button", name="Thu gọn thanh điều hướng", exact=True).click()
    page.set_viewport_size({"width": width, "height": 640})
    assert page.locator(".sidebar.collapsed").count() == 1
    page.set_viewport_size({"width": 1280, "height": 800})
    assert page.locator(".sidebar.collapsed").count() == 1
    return {"keyboardObservations": observations, "togglePreservesState": before, "resizePreservesExpandedAndCollapsed": True, "escape": "No overlay/disclosure created; Escape leaves toggle focus intact"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--phase", choices=["baseline", "final"], required=True)
    args = parser.parse_args()
    out = args.output.resolve() / args.phase
    out.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = os.environ["TEMP"] = str(args.scratch.resolve())
    root = Path(__file__).resolve().parents[1]
    frozen = hashes(root)
    results, logs, fixtures = [], [], []
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    log = (out / "vite.log").open("w", encoding="utf-8")
    server = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(port), "--strictPort"], cwd=root, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                urllib.request.urlopen(url, timeout=1).close()
                break
            except OSError:
                if time.monotonic() > deadline or server.poll() is not None:
                    raise RuntimeError("Task Vite unavailable")
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="msedge", headless=True)
            save(out / "environment.json", {"browser": browser.version, "mode": "installed Edge headless; explicit CSS viewports; DPR 1; no real zoom claim", "url": url})
            for width, height in VIEWPORTS:
                for count in [6, 150]:
                    for collapsed in [False, True]:
                        page = new_page(browser, url, width, height, count, logs, fixtures)
                        if collapsed:
                            page.get_by_role("button", name="Thu gọn thanh điều hướng", exact=True).click()
                        for screen, panel in [("workbench", "open"), ("workbench", "closed"), ("summary", "NA")]:
                            name = f"{width}x{height}-{count}-{'collapsed' if collapsed else 'expanded'}-{screen}-{panel}"
                            try:
                                if panel == "closed":
                                    page.get_by_role("button", name="Đóng panel", exact=True).click()
                                if screen == "summary":
                                    page.locator(".sidebar").get_by_role("button", name="Tổng kết & phiên bản", exact=True).click()
                                page.evaluate("window.scrollTo(0,0)")
                                page.evaluate("() => Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))")
                                g = geometry(page)
                                isolated = shell_only(page)
                                errors = failures(g, isolated, collapsed)
                                page.screenshot(path=str(out / (name + ".png")), full_page=True)
                                save(out / (name + ".json"), {"geometry": g, "featureExcludedDiagnostic": isolated, "shellFailures": errors})
                                result = {"case": name, "width": width, "height": height, "assets": count, "sidebar": "collapsed" if collapsed else "expanded", "screen": screen, "panel": panel, "status": "FAIL" if errors else "PASS", "shellFailures": errors, "documentWidth": g["documentWidth"], "mainClientWidth": g["boxes"][".app-main"]["clientWidth"], "mainScrollWidth": g["boxes"][".app-main"]["scrollWidth"], "isolated": isolated, "nonTableOverflowCount": len(g["overflow"])}
                            except Exception:
                                result = {"case": name, "status": "NOT VERIFIED", "error": traceback.format_exc()}
                            results.append(result)
                            save(out / "results.json", results)
                            print(json.dumps(result, ensure_ascii=True), flush=True)
                        page.close()
            if args.phase == "final":
                keyboard_results = []
                for width in [320, 390, 768, 1440]:
                    page = new_page(browser, url, width, 900, 6, logs, fixtures)
                    try:
                        keyboard_results.append({"width": width, "status": "PASS", "evidence": keyboard(page, out, width)})
                    except Exception:
                        keyboard_results.append({"width": width, "status": "FAIL", "error": traceback.format_exc()})
                    page.close()
                save(out / "keyboard.json", keyboard_results)
            browser.close()
        after = hashes(root)
        save(out / "source-integrity.json", {"before": frozen, "after": after, "unchanged": frozen == after})
        save(out / "console.json", logs)
        save(out / "fixtures.json", fixtures)
        fatal = [x for x in logs if x["type"] in ["error", "pageerror"] and "favicon" not in x.get("location", {}).get("url", "")]
        save(out / "fatal-console.json", fatal)
        print("RESULT", len(results), "CASES", sum(x["status"] == "PASS" for x in results), "PASS", sum(x["status"] == "FAIL" for x in results), "FAIL", sum(x["status"] == "NOT VERIFIED" for x in results), "NOT VERIFIED", "SOURCE UNCHANGED", frozen == after, flush=True)
        if args.phase == "baseline":
            return int(frozen != after or bool(fatal) or any(x["status"] == "NOT VERIFIED" for x in results))
        return int(frozen != after or bool(fatal) or any(x["status"] != "PASS" for x in results) or any(x["status"] != "PASS" for x in keyboard_results))
    finally:
        server.terminate()
        server.wait(timeout=15)
        log.close()
        save(out / "cleanup.json", {"vitePid": server.pid, "returncode": server.returncode})


if __name__ == "__main__":
    raise SystemExit(main())
