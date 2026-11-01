"""Run the table's local browser acceptance matrix with trusted mouse/keyboard input."""

import argparse
import hashlib
import json
import socket
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


MIN_WIDTHS = [52, 210, 280, 72, 100, 154, 166, 154, 174, 180, 130, 130, 130]
LONG_NAME = "Hệ thống máy gia công cơ khí chính xác điều khiển tự động tích hợp bộ cấp phôi và tủ điều khiển trung tâm dùng trong nhà xưởng công nghiệp"
LONG_SPECS = "Model VALORA SYNTHETIC 150 · Công suất 125 kW · Bộ điều khiển tích hợp · Kích thước 2500 x 1800 x 1600 mm · Xuất xứ minh họa · Động cơ ba pha · Tình trạng đã sử dụng và cần kiểm tra hồ sơ kỹ thuật trước khi quyết định giá"


def geometry(page):
    return page.locator(".table-scroll").evaluate("""v => {
      const t=v.querySelector('table'), h=[...t.querySelectorAll('th')], row=t.querySelector('tbody tr');
      const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
      return {viewport:rect(v),client:[v.clientWidth,v.clientHeight],scroll:[v.scrollLeft,v.scrollTop],extent:[v.scrollWidth,v.scrollHeight],
        bodyOverflow:document.documentElement.scrollWidth>innerWidth,layout:getComputedStyle(t).tableLayout,table:rect(t),
        widths:h.map(e=>rect(e).width),headers:h.map(rect),cells:[...row.cells].map(e=>({...rect(e),text:e.textContent,scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,align:getComputedStyle(e).textAlign})),
        name:rect(row.querySelector('.asset-link > span')),code:rect(row.querySelector('.asset-link small')),
        scrollbar:getComputedStyle(v).scrollbarWidth,overflow:getComputedStyle(v).overflow,
        ready:v.classList.contains('pan-ready'),panning:v.classList.contains('panning'),cursor:getComputedStyle(v).cursor,
        rows:t.tBodies[0].rows.length};
    }""")


def state(page):
    return page.evaluate("""() => ({selected:document.querySelector('.selected-row')?.textContent,
      stats:document.querySelector('.stats-strip')?.textContent,
      search:document.querySelector('.grid-toolbar input')?.value,
      filter:document.querySelector('.grid-toolbar select')?.value,
      fields:[...document.querySelectorAll('.asset-drawer input,.asset-drawer textarea')].map(e=>e.value)})""")


def point(page):
    page.locator(".table-scroll").scroll_into_view_if_needed()
    r = page.locator(".table-scroll").bounding_box()
    height = page.viewport_size["height"]
    top, bottom = max(r["y"], 0), min(r["y"] + r["height"], height)
    assert bottom - top > 100, r
    return r["x"] + r["width"] - 30, top + min((bottom - top) / 2, 150)


def input_state(page, x, y):
    return page.evaluate("""([x,y])=>{const v=document.querySelector('.table-scroll'),t=document.elementFromPoint(x,y),f=document.activeElement;return {x,y,focusTag:f?.tagName,focusClass:f?.className,viewportFocused:f===v,hitTag:t?.tagName,hitClass:t?.className,inside:!!t&&v.contains(t),interactive:!!t?.closest('input,textarea,select,button,a,[contenteditable]:not([contenteditable="false"])')}}""", [x, y])


def pan(page, dx, dy, release="pointerup"):
    x, y = point(page)
    page.mouse.click(x, y)
    x, y = point(page)
    page.mouse.move(x, y)
    admission = input_state(page, x, y)
    assert admission["viewportFocused"] and admission["inside"] and not admission["interactive"], admission
    page.keyboard.down("Space")
    page.mouse.down(button="right")
    during = geometry(page)
    page.mouse.move(x + dx, y + dy, steps=8)
    moved = geometry(page)
    if release == "space":
        page.keyboard.up("Space")
    elif release == "escape":
        page.keyboard.press("Escape")
    elif release == "pointercancel":
        page.locator(".table-scroll").dispatch_event("pointercancel", {"pointerId": 1})
    elif release == "capture":
        page.locator(".table-scroll").evaluate("v=>v.releasePointerCapture(1)")
    elif release == "blur":
        page.evaluate("window.dispatchEvent(new Event('blur'))")
    elif release == "visibility":
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden")
    elif release == "buttons":
        page.locator(".table-scroll").dispatch_event("pointermove", {"pointerId": 1, "buttons": 0})
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    page.wait_for_function("!document.querySelector('.table-scroll').classList.contains('panning')")
    return {"admission": admission, "beforeMove": during, "duringMove": moved, "after": geometry(page), "release": release}


def settle_scroll(page):
    page.evaluate("""() => new Promise(resolve=>{let prev='',stable=0;function step(){const v=document.querySelector('.table-scroll');const now=[v.scrollLeft,v.scrollTop].join();stable=now===prev?stable+1:0;prev=now;if(stable>=5)resolve();else requestAnimationFrame(step)}requestAnimationFrame(step)})""")


def run_case(results, name, action):
    try:
        evidence = action()
        results.append({"name": name, "status": "PASS", "evidence": evidence})
    except Exception as error:
        results.append({"name": name, "status": "FAIL", "error": str(error), "trace": traceback.format_exc()})
    print(json.dumps({"name": name, "status": results[-1]["status"], "error": results[-1].get("error")}), flush=True)


def verify_geometry(page, count):
    g = geometry(page)
    assert g["rows"] == count, g
    assert g["layout"] == "fixed", g
    assert not g["bodyOverflow"], g
    assert g["overflow"] == "auto" and g["scrollbar"] == "none", g
    assert page.locator(".top-scroll").count() == 0
    assert all(actual + .5 >= minimum for actual, minimum in zip(g["widths"], MIN_WIDTHS)), g
    assert abs(sum(g["widths"]) - g["table"]["width"]) < 1, g
    assert g["code"]["y"] >= g["name"]["y"] + g["name"]["height"] - 1, g
    assert abs(g["cells"][1]["x"] - g["cells"][0]["x"] - g["widths"][0]) < 1, g
    assert all(c["scrollWidth"] <= c["clientWidth"] for c in g["cells"][4:12]), g
    assert all(c["align"] == "right" for c in g["cells"][4:12]), g
    assert page.locator("tbody tr").nth(1).locator("td").nth(6).inner_text() == "—"
    return g


def verify_pan(page, count):
    before_state = state(page)
    start = geometry(page)
    right = pan(page, -100, 0)
    assert right["duringMove"]["scroll"][0] > start["scroll"][0], right
    down = pan(page, 0, -90)
    if count == 150:
        assert down["duringMove"]["scroll"][1] > right["after"]["scroll"][1], down
    up = pan(page, 0, 60)
    if count == 150:
        assert up["after"]["scroll"][1] < down["after"]["scroll"][1], up
    left = pan(page, 60, 0)
    assert left["after"]["scroll"][0] < right["after"]["scroll"][0], left
    diagonal = pan(page, -75, -65)
    assert diagonal["after"]["scroll"][0] > left["after"]["scroll"][0], diagonal
    if count == 150:
        assert diagonal["after"]["scroll"][1] > left["after"]["scroll"][1], diagonal
    assert state(page) == before_state, {"before": before_state, "after": state(page)}
    g = geometry(page)
    assert abs(g["headers"][0]["x"] - g["viewport"]["x"]) < 1, g
    assert abs(g["headers"][1]["x"] - g["viewport"]["x"] - g["widths"][0]) < 1, g
    assert abs(g["headers"][0]["y"] - g["viewport"]["y"]) < 1, g
    assert all(abs(h["x"] - c["x"]) < 1 for h, c in zip(g["headers"], g["cells"])), g
    assert not g["panning"] and not g["ready"], g
    assert page.evaluate("getSelection().toString()") == ""
    return {"right": right, "down": down, "up": up, "left": left, "diagonal": diagonal, "stateUnchanged": True,
            "verticalAtNaturalBound": count == 6 and start["extent"][1] <= start["client"][1]}


def verify_context_and_keyboard(page):
    x, y = point(page)
    page.mouse.move(x, y)
    before = geometry(page)["scroll"]
    page.mouse.click(x, y, button="right")
    page.keyboard.press("Escape")
    plain = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert plain and plain["trusted"] and not plain["prevented"], plain
    assert geometry(page)["scroll"] == before
    pan(page, -50, -50)
    eligible = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert eligible and eligible["trusted"] and eligible["prevented"], eligible
    page.mouse.click(x, y, button="right")
    page.keyboard.press("Escape")
    restored = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert restored and not restored["prevented"], restored
    page.mouse.move(x, y)
    before = geometry(page)["scroll"]
    page.keyboard.down("Space")
    page.mouse.down(button="left")
    page.mouse.move(x - 35, y - 35, steps=3)
    page.mouse.up(button="left")
    page.keyboard.up("Space")
    assert geometry(page)["scroll"] == before
    page.keyboard.press("Tab")
    page.locator(".table-scroll").focus()
    before = geometry(page)["scroll"]
    page.keyboard.press("ArrowRight")
    settle_scroll(page)
    assert geometry(page)["scroll"][0] > before[0]
    before_y = geometry(page)["scroll"][1]
    page.keyboard.press("PageDown")
    settle_scroll(page)
    assert geometry(page)["scroll"][1] > before_y
    page.keyboard.press("End")
    settle_scroll(page)
    end = geometry(page)
    assert end["scroll"][1] >= end["extent"][1] - end["client"][1] - 1, end
    page.keyboard.press("Home")
    settle_scroll(page)
    assert geometry(page)["scroll"][1] == 0
    before = geometry(page)["scroll"]
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowDown")
    settle_scroll(page)
    assert geometry(page)["scroll"][0] < before[0] and geometry(page)["scroll"][1] > before[1]
    page.keyboard.press("ArrowUp")
    page.keyboard.press("PageUp")
    settle_scroll(page)
    assert geometry(page)["scroll"][1] == 0
    before = geometry(page)["scroll"]
    page.mouse.move(*point(page))
    page.mouse.wheel(70, 100)
    page.wait_for_function("v=>{const e=document.querySelector('.table-scroll');return e.scrollLeft>v[0]&&e.scrollTop>v[1]}", arg=before)
    settle_scroll(page)
    return {"ordinaryContext": plain, "panContext": eligible, "ordinaryAfterPan": restored, "wheel": geometry(page),
            "touchpadEquivalent": "trusted two-axis mouse.wheel, not physical touchpad hardware"}


def verify_release(page):
    evidence = []
    for release in ["space", "escape", "pointercancel", "capture", "blur", "visibility", "buttons"]:
        result = pan(page, -30, -30, release)
        assert result["beforeMove"]["panning"], result
        assert not result["after"]["panning"] and not result["after"]["ready"], result
        evidence.append(result)
    return {"results": evidence, "supplementalEvents": ["pointercancel", "visibilitychange", "button-state mismatch", "window blur"], "capture": "DOM releasePointerCapture after trusted drag start", "blurLimitation": "Headless tab focus did not produce native blur"}


def verify_excluded_targets(page):
    results = []
    for markup in ['<input aria-label="Fixture editor">', '<textarea aria-label="Fixture editor"></textarea>', '<select aria-label="Fixture editor"><option>Option</option></select>', '<button>Fixture action</button>', '<a href="#fixture">Fixture link</a>', '<span contenteditable="true" tabindex="0">Fixture editor</span>']:
        page.locator("tbody tr").first.locator("td").nth(2).evaluate("(e,html)=>{e.dataset.original=e.innerHTML;e.innerHTML=html}", markup)
        target = page.locator("tbody tr").first.locator("td").nth(2).locator(":scope > *")
        target.focus()
        target.scroll_into_view_if_needed()
        r = target.bounding_box()
        x, y = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2
        page.mouse.move(x, y)
        hit = input_state(page, x, y)
        assert hit["inside"] and hit["interactive"], hit
        assert target.evaluate("(e,p)=>e.contains(document.elementFromPoint(p[0],p[1]))", [x, y]), hit
        before_key = geometry(page)["scroll"]
        page.keyboard.down("Space")
        assert not geometry(page)["ready"], markup
        key = page.evaluate("window.tableEvents.filter(e=>e.type==='keydown'&&e.code==='Space').at(-1)")
        assert key and not key["prevented"], key
        settle_scroll(page)
        after_key = geometry(page)["scroll"]
        target.scroll_into_view_if_needed()
        r = target.bounding_box()
        x, y = r["x"] + r["width"] / 2, r["y"] + r["height"] / 2
        page.mouse.move(x, y)
        assert target.evaluate("(e,p)=>e.contains(document.elementFromPoint(p[0],p[1]))", [x, y])
        before = geometry(page)["scroll"]
        page.mouse.down(button="right")
        page.mouse.move(x - 20, y - 20, steps=2)
        page.mouse.up(button="right")
        page.keyboard.up("Space")
        page.keyboard.press("Escape")
        assert geometry(page)["scroll"] == before and not geometry(page)["panning"], markup
        event = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
        assert event and not event["prevented"], event
        results.append({"target": markup, "hit": hit, "key": key, "beforeNativeSpace": before_key, "afterNativeSpace": after_key, "beforePointerDrag": before, "afterPointerDrag": geometry(page)["scroll"], "context": event, "scrollUnchangedDuringPointerDrag": True})
        page.locator("tbody tr").first.locator("td").nth(2).evaluate("e=>{e.innerHTML=e.dataset.original;delete e.dataset.original}")
    return results


def verify_full_name_and_hint(page):
    name = page.locator(".asset-link").first
    name.focus()
    tooltip = page.get_by_role("tooltip")
    tooltip.wait_for(state="visible")
    assert tooltip.inner_text() == LONG_NAME
    assert LONG_NAME in name.get_attribute("aria-label")
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Ẩn hướng dẫn kéo bảng", exact=True).click()
    region = page.get_by_role("region", name="Cuộn bảng tài sản", exact=True)
    instruction_id = region.get_attribute("aria-describedby")
    assert "Giữ Space + chuột phải để kéo bảng" in page.locator("[id='" + instruction_id + "']").text_content()
    assert page.get_by_role("button", name="Ẩn hướng dẫn kéo bảng", exact=True).count() == 0
    return {"fullNameOnKeyboardFocus": True, "dismissedHintStillDescribesViewport": True}


def verify_summary(page):
    page.get_by_role("button", name="Tổng kết & xuất", exact=True).click()
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Xác nhận phiên bản minh họa", exact=True).click()
    before = page.locator(".summary-screen").inner_text()
    assert "514.480.000" in before and "v01" in before
    page.get_by_role("button", name="Quay lại danh mục", exact=True).click()
    page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")
    pan(page, -100, -80)
    page.get_by_role("button", name="Tổng kết & xuất", exact=True).click()
    after = page.locator(".summary-screen").inner_text()
    assert after == before, {"before": before, "after": after}
    return {"summaryBefore": before, "summaryAfter": after, "equal": True}


def verify_wheel_boundary(page):
    page.locator(".table-scroll").focus()
    page.keyboard.press("End")
    settle_scroll(page)
    page.mouse.move(*point(page))
    before = page.evaluate("scrollY")
    page.mouse.wheel(0, 400)
    page.wait_for_function("y=>scrollY>y", arg=before)
    return {"pageScrollBefore": before, "pageScrollAfter": page.evaluate("scrollY"), "table": geometry(page)}


def verify_conflicts(page):
    search = page.get_by_placeholder("Tìm tài sản, model, công suất...")
    search.fill("Máy")
    page.get_by_label("Lọc tài sản", exact=True).select_option("unviewed")
    field = page.get_by_label("Đơn giá đề xuất — người dùng quyết định", exact=True)
    field.fill("123456789")
    baseline = state(page)
    original_price = page.locator(".selected-row td").nth(8).inner_text()
    x, y = point(page)
    page.mouse.move(x, y)
    before = geometry(page)["scroll"]
    page.keyboard.down("Space")
    page.mouse.down(button="right")
    page.mouse.move(x - 40, y - 40, steps=3)
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    page.keyboard.press("Escape")
    assert geometry(page)["scroll"] == before
    assert field.input_value() == "123456789"
    assert field.evaluate("e=>e===document.activeElement"), "Rejected pan must retain the unsaved editor focus"
    assert page.locator(".selected-row td").nth(8).inner_text() == original_price
    assert not geometry(page)["panning"]
    context = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert context and not context["prevented"], context
    assert state(page)["search"] == baseline["search"] and state(page)["filter"] == baseline["filter"]
    assert state(page) == baseline, {"before": baseline, "after": state(page)}
    field.focus()
    page.mouse.move(*point(page))
    page.keyboard.down("Space")
    assert not geometry(page)["ready"]
    page.keyboard.up("Space")
    search.fill("")
    page.get_by_label("Lọc tài sản", exact=True).select_option("all")
    page.get_by_role("tab", name="Đặc điểm & SL", exact=True).click()
    specs = page.get_by_label("Đặc điểm hiện tại", exact=True)
    specs.fill("Bản nháp thông số chưa lưu")
    page.keyboard.press("Space")
    assert specs.input_value().startswith("Bản nháp thông số chưa lưu")
    assert not geometry(page)["ready"]
    page.mouse.move(*point(page))
    page.mouse.wheel(80, 100)
    assert specs.input_value().startswith("Bản nháp thông số chưa lưu")
    button = page.locator(".asset-link").first
    button.focus()
    page.keyboard.down("Space")
    assert not geometry(page)["ready"]
    page.keyboard.up("Space")
    return {"inputAndDraftPreserved": True, "editorFocusPreserved": True, "uncommittedTablePrice": original_price, "filterSearchPreserved": True, "specDraftPreserved": True, "inputContext": context}


def verify_edges(page):
    page.locator(".table-scroll").focus()
    page.keyboard.press("End")
    settle_scroll(page)
    g = geometry(page)
    pan(page, -5000, -5000)
    edge = geometry(page)
    assert edge["scroll"][0] >= edge["extent"][0] - edge["client"][0] - 1, edge
    assert edge["scroll"][1] >= edge["extent"][1] - edge["client"][1] - 1, edge
    pan(page, 80, 80)
    returned = geometry(page)
    assert returned["scroll"][0] < edge["scroll"][0] and returned["scroll"][1] < edge["scroll"][1], returned
    return {"before": g, "edge": edge, "return": returned}


def verify_context_order(page, admitted, order, ending):
    field = page.get_by_label("Đơn giá đề xuất — người dùng quyết định", exact=True)
    if not admitted:
        field.fill("123456789")
    x, y = point(page)
    if admitted:
        page.mouse.click(x, y)
        x, y = point(page)
    page.mouse.move(x, y)
    before = state(page)
    before_scroll = geometry(page)["scroll"]
    page.evaluate("window.deferTableContext=true")
    page.keyboard.down("Space")
    page.mouse.down(button="right")
    assert geometry(page)["panning"] == admitted
    if ending == "escape":
        page.keyboard.press("Escape")
    elif ending == "blur":
        page.evaluate("window.dispatchEvent(new Event('blur'))")
    elif ending == "pointercancel":
        page.locator(".table-scroll").dispatch_event("pointercancel", {"pointerId": 1})
    elif ending == "capture" and admitted:
        page.locator(".table-scroll").evaluate("v=>v.releasePointerCapture(1)")
    elif ending == "space":
        page.keyboard.up("Space")
    if order == "after-pointerup":
        page.mouse.up(button="right")
    page.locator(".table-scroll").evaluate("e=>e.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,button:0}))")
    keyboard_menu = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert keyboard_menu and keyboard_menu["button"] == 0 and not keyboard_menu["prevented"], keyboard_menu
    page.locator(".table-scroll").evaluate("(e,buttons)=>e.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,button:2,buttons}))", 2 if order == "before-pointerup" else 0)
    menu = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert menu and menu["button"] == 2 and menu["prevented"] == admitted, menu
    if order == "before-pointerup":
        page.mouse.up(button="right")
    page.keyboard.up("Space")
    page.evaluate("window.deferTableContext=false")
    assert not geometry(page)["panning"] and not geometry(page)["ready"]
    assert geometry(page)["scroll"] == before_scroll
    assert state(page) == before, {"before": before, "after": state(page)}
    if not admitted:
        assert field.input_value() == "123456789" and field.evaluate("e=>e===document.activeElement")
    page.mouse.click(x, y, button="right")
    page.keyboard.press("Escape")
    ordinary = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert ordinary and ordinary["trusted"] and not ordinary["prevented"], ordinary
    return {"admittedAtTrustedPointerdown": admitted, "menuOrder": order, "ending": ending, "menu": menu, "keyboardMenu": keyboard_menu, "nextOrdinaryMenu": ordinary,
            "orderingMethod": "Trusted right-pointerdown; native contextmenu deferred by harness; synthetic contextmenu delivered at selected lifecycle boundary", "draftAndStateUnchanged": True}


def verify_button_space(page):
    button = page.get_by_role("button", name="Đóng panel", exact=True)
    button.focus()
    page.mouse.move(*point(page))
    page.keyboard.down("Space")
    key = page.evaluate("window.tableEvents.filter(e=>e.type==='keydown'&&e.code==='Space').at(-1)")
    assert key and not key["prevented"], key
    assert not geometry(page)["ready"] and not geometry(page)["panning"]
    page.keyboard.up("Space")
    page.get_by_role("button", name="Mở panel", exact=True).wait_for()
    assert page.locator(".asset-drawer").count() == 0
    return {"nativeSpaceActivatedFocusedPanelButton": True, "key": key}


def verify_popover_and_unmount(page):
    x, y = point(page)
    page.mouse.click(x, y)
    page.evaluate("const p=document.createElement('div');p.id='test-popover';p.setAttribute('popover','manual');p.textContent='Fixture popover';document.body.append(p);p.showPopover()")
    page.mouse.move(x, y)
    page.keyboard.down("Space")
    assert not geometry(page)["ready"]
    page.mouse.down(button="right")
    assert not geometry(page)["panning"]
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    menu = page.evaluate("window.tableEvents.filter(e=>e.type==='contextmenu').at(-1)")
    assert menu and not menu["prevented"], menu
    page.keyboard.press("Escape")
    page.evaluate("document.getElementById('test-popover').remove()")
    x, y = point(page)
    page.mouse.click(x, y)
    page.keyboard.down("Space")
    page.mouse.down(button="right")
    assert geometry(page)["panning"]
    page.get_by_role("button", name="Tổng kết & xuất", exact=True).evaluate("e=>e.click()")
    assert page.locator(".table-scroll").count() == 0
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    page.get_by_role("button", name="Quay lại danh mục", exact=True).click()
    page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")
    result = pan(page, -30, -30)
    assert result["beforeMove"]["panning"] and not result["after"]["panning"]
    return {"openPopoverMenu": menu, "unmountMethod": "Synthetic navigation click during trusted drag", "freshViewportCanPan": True}


def verify_checkpoint(root, frozen):
    after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [root / "src/App.tsx", root / "src/styles.css", Path(__file__).resolve()]}
    assert frozen == after, {"before": frozen, "after": after}
    return {"before": frozen, "after": after}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", choices=["msedge", "chrome"], default="msedge")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    frozen = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [root / "src/App.tsx", root / "src/styles.css", Path(__file__).resolve()]}
    (args.output / "tested-source-hashes.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    results, console = [], []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    server_log = (args.output / "vite.log").open("w", encoding="utf-8")
    server = subprocess.Popen(["node", str(root / "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", str(port), "--strictPort"], cwd=root, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 30
        while True:
            try:
                urllib.request.urlopen(url, timeout=1).close()
                break
            except OSError:
                if time.monotonic() >= deadline or server.poll() is not None:
                    raise RuntimeError("Local Vite server failed to start")
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel=args.browser, headless=True)
            print("BROWSER", args.browser, browser.version, flush=True)
            def fixture(page, count):
                if count != 150:
                    return
                def replace(route):
                    response = route.fetch()
                    body = response.text()
                    anchor = "const similar = ["
                    assert body.count(anchor) == 1, "Fixture module anchor changed"
                    injection = f"initial[0].name={json.dumps(LONG_NAME)};initial[0].specs={json.dumps(LONG_SPECS)};initial[0].customerPrice=999999999999999;"
                    injection += "for(let i=6;i<150;i++){const a=structuredClone(initial[i%6]);a.id='SYNTH-'+String(i+1).padStart(3,'0');initial.push(a);}\n"
                    route.fulfill(response=response, body=body.replace(anchor, injection + anchor))
                page.route("**/src/App.tsx", replace)
            def new_page(width, height, count):
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
                page = context.new_page()
                page.on("console", lambda m: console.append({"type": m.type, "text": m.text, "location": m.location}))
                page.on("pageerror", lambda e: console.append({"type": "pageerror", "text": str(e)}))
                page.on("response", lambda r: console.append({"type": "http-error", "status": r.status, "url": r.url}) if r.status >= 400 else None)
                page.add_init_script("""window.tableEvents=[];window.addEventListener('contextmenu',e=>{if(window.deferTableContext&&e.isTrusted){window.tableEvents.push({type:'harness-deferred-native-contextmenu',trusted:true});e.preventDefault();e.stopImmediatePropagation()}},true);for(const type of ['contextmenu','pointerdown','pointerup','pointercancel','lostpointercapture','blur','keydown'])window.addEventListener(type,e=>window.tableEvents.push({type,trusted:e.isTrusted,prevented:e.defaultPrevented,pointerId:e.pointerId,button:e.button,code:e.code,target:e.target?.tagName,focus:document.activeElement?.tagName}));""")
                fixture(page, count)
                page.goto(url)
                page.locator("tbody tr").nth(count - 1).wait_for(state="attached")
                page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")
                return page
            matrix = [(1440, 900), (1280, 800)] if not args.quick else [(1440, 900)]
            for width, height in matrix:
                for count in ([6, 150] if not args.quick else [150]):
                    for collapsed in ([False, True] if not args.quick else [False]):
                        for panel in ([True, False] if not args.quick else [True]):
                            name = f"{width}x{height}-{count}-sidebar-{'collapsed' if collapsed else 'expanded'}-panel-{'open' if panel else 'closed'}"
                            page = new_page(width, height, count)
                            if collapsed:
                                page.get_by_role("button", name="Thu gọn thanh điều hướng", exact=True).click()
                            if not panel:
                                page.get_by_role("button", name="Đóng panel", exact=True).click()
                            page.wait_for_function("document.getAnimations().every(a=>a.playState!=='running')")
                            page.screenshot(path=str(args.output / (name + "-before.png")))
                            run_case(results, name + "-geometry", lambda: verify_geometry(page, count))
                            run_case(results, name + "-pan", lambda: verify_pan(page, count))
                            page.screenshot(path=str(args.output / (name + "-after.png")))
                            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "context-keyboard-wheel", lambda: verify_context_and_keyboard(page))
            run_case(results, "cancellation", lambda: verify_release(page))
            run_case(results, "edges-return", lambda: verify_edges(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "excluded-interactive-targets", lambda: verify_excluded_targets(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "keyboard-full-name-and-hint", lambda: verify_full_name_and_hint(page))
            page.context.close()
            page = new_page(1440, 900, 6)
            run_case(results, "summary-and-version-unchanged", lambda: verify_summary(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "wheel-chains-to-page-at-boundary", lambda: verify_wheel_boundary(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "editing-conflicts-and-drafts", lambda: verify_conflicts(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "focused-button-keeps-native-space", lambda: verify_button_space(page))
            page.context.close()
            page = new_page(1440, 900, 150)
            run_case(results, "popover-and-unmount", lambda: verify_popover_and_unmount(page))
            page.context.close()
            for admitted in [True, False]:
                for order in ["before-pointerup", "after-pointerup"]:
                    for ending in ["pointerup", "escape", "blur", "pointercancel", "capture", "space"]:
                        page = new_page(1440, 900, 6)
                        run_case(results, f"context-order-{'accepted' if admitted else 'rejected'}-{order}-{ending}", lambda: verify_context_order(page, admitted, order, ending))
                        page.context.close()
            if not args.quick:
                for width, height, zoom in [(1152, 720, 125), (720, 450, 200)]:
                    page = new_page(width, height, 150)
                    run_case(results, f"css-viewport-equivalent-{zoom}percent", lambda: verify_geometry(page, 150))
                    run_case(results, f"css-viewport-pan-{zoom}percent", lambda: verify_pan(page, 150))
                    page.screenshot(path=str(args.output / f"css-viewport-equivalent-{zoom}percent.png"))
                    page.context.close()
            after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [root / "src/App.tsx", root / "src/styles.css", Path(__file__).resolve()]}
            run_case(results, "source-and-runner-unchanged-during-run", lambda: verify_checkpoint(root, frozen))
            summary = {"browser": args.browser, "version": browser.version, "testedSourceHashes": frozen, "hashesAfterRun": after, "zoom": "Equivalent CSS viewports; real browser zoom was not measured", "results": results}
            browser.close()
        (args.output / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.output / "console.json").write_text(json.dumps(console, ensure_ascii=False, indent=2), encoding="utf-8")
        print("RESULT", sum(r["status"] == "PASS" for r in results), "PASS", sum(r["status"] == "FAIL" for r in results), "FAIL", "0 SKIP", flush=True)
        return 1 if any(r["status"] == "FAIL" for r in results) or any(e["type"] == "pageerror" for e in console) else 0
    finally:
        server.terminate()
        server.wait(timeout=10)
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
