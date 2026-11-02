"""Measure the shell in explicitly emulated mobile touch and desktop contexts."""

import argparse
import hashlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright


sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("shell", Path(__file__).with_name("shell-reflow.browser.py"))
shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell)
MOBILE = [(749, 654), (749, 750), (832, 575), (832, 671), (411, 814), (411, 870), (320, 640), (390, 844)]
DESKTOP = [(768, 1024), (1024, 768), (1280, 800), (1440, 900)]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def measure(page):
    return page.evaluate("""() => {
      const box=e=>e?.getBoundingClientRect().toJSON();
      return {innerWidth,innerHeight,dpr:devicePixelRatio,visualViewport:{width:visualViewport.width,height:visualViewport.height,scale:visualViewport.scale},screen:{width:screen.width,height:screen.height},maxTouchPoints:navigator.maxTouchPoints,coarse:matchMedia('(pointer:coarse)').matches,userAgent:navigator.userAgent,viewportMeta:document.querySelector('meta[name=viewport]').content,documentWidth:document.documentElement.scrollWidth,boxes:Object.fromEntries(['.sidebar','.sidebar-card','.topbar','.page-header','.app-main','.page','.grid-area','.table-scroll','.asset-drawer'].map(s=>[s,box(document.querySelector(s))])),targets:[...document.querySelectorAll('.sidebar button,.topbar button,.header-actions button')].map(e=>({name:e.getAttribute('aria-label')||e.textContent,disabled:e.disabled,box:box(e),hit:(()=>{const r=box(e);return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})()}))};
    }""")


def snapshot(page):
    return page.evaluate("""() => ({route:document.querySelector('h1').textContent,selected:document.querySelector('.drawer-eyebrow')?.textContent,search:document.querySelector('.grid-toolbar input')?.value,filter:document.querySelector('.grid-toolbar select')?.value,fields:[...document.querySelectorAll('.asset-drawer input')].map(e=>e.value),price:document.querySelector('.proposed-price')?.textContent,stats:document.querySelector('.stats-strip')?.textContent,notice:document.querySelector('.notice')?.textContent,nav:document.querySelector('.sidebar').className})""")


def settle(page):
    page.evaluate("() => Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))")
    page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")


def toggle(page):
    return page.locator('.sidebar button[aria-expanded]')


def native_scroll(page, context):
    viewport = page.locator('.table-scroll')
    viewport.evaluate("e=>{e.scrollLeft=0;e.scrollTop=0;e.scrollIntoView({block:'center'})}")
    r = viewport.bounding_box()
    top, bottom = max(0, r['y']), min(page.viewport_size['height'], r['y'] + r['height'])
    x, y = r['x'] + r['width'] - 15, top + (bottom - top) * .7
    state = lambda: viewport.evaluate("e=>({x:e.scrollLeft,y:e.scrollTop,width:e.clientWidth,height:e.clientHeight,scrollWidth:e.scrollWidth,scrollHeight:e.scrollHeight,pan:e.classList.contains('panning')})")
    before = state()
    cdp = context.new_cdp_session(page)
    events = []
    page.evaluate("window.foldTouch=[];for(const type of ['touchstart','touchmove','touchend','pointercancel'])document.addEventListener(type,e=>window.foldTouch.push({type,trusted:e.isTrusted,prevented:e.defaultPrevented}),{passive:true})")
    for dx, dy in [(-min(180, r['width'] - 30), 0), (0, -min(150, bottom-top-20))]:
        cdp.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for step in range(1, 13):
            cdp.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x+dx*step/12,'y':y+dy*step/12}]})
            time.sleep(.016)
        cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
        page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        events.append(state())
    result = {'method':'Chromium CDP trusted touchStart/touchMove/touchEnd; no DOM scroll assignment after gesture start','before':before,'afterHorizontal':events[0],'afterVertical':events[1],'events':page.evaluate('window.foldTouch')}
    for dx,dy in [(-10000,0),(0,-12000)]:
        cdp.send('Input.synthesizeScrollGesture',{'x':x,'y':y,'xDistance':dx,'yDistance':dy,'speed':8000,'gestureSourceType':'touch','preventFling':True})
    result['nativeTouchEnd']=state()
    result['extentGesture']='CDP synthesizeScrollGesture, gestureSourceType touch; xDistance -10000 then yDistance -12000; speed 8000; preventFling true'
    result['lastCell']=viewport.locator('tbody tr').last.locator('td').last.bounding_box()
    result['lastHeader']=viewport.locator('th').last.bounding_box()
    cdp.detach()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--phase', choices=['baseline','candidate'], required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--interactions-only', action='store_true')
    parser.add_argument('--baseline-source', action='store_true')
    args = parser.parse_args()
    out = args.output / args.phase
    out.mkdir(parents=True, exist_ok=True)
    os.environ['TMP'] = os.environ['TEMP'] = str(args.scratch.resolve())
    root = Path(__file__).resolve().parents[1]
    frozen = shell.hashes(root)
    results, interactions, console, fixtures = [], [], [], []
    if args.resume:
        results = json.loads((out/'matrix.json').read_text(encoding='utf-8'))
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        port = s.getsockname()[1]
    log = (out/'vite.log').open('w', encoding='utf-8')
    baseline='45d310d3e2f97ce06474eeca6f955ef36b871228'
    if args.baseline_source:
        prefix='prototypes/ux-g1-15-v02-fluent-react/'
        sources={p:subprocess.check_output(['git','show',baseline+':'+prefix+p],cwd=root) for p in ['src/App.tsx','src/styles.css']}
        save(out/'served-source.json',{'mode':'Exact F01A git blobs loaded by a Vite pre-load plugin; no worktree source replacement','commit':baseline,'sha256':{p:hashlib.sha256(v).hexdigest() for p,v in sources.items()}})
        script="import {createServer} from 'vite';const sources="+json.dumps({str(root/p).replace('\\','/'):v.decode() for p,v in sources.items()})+";const server=await createServer({root:process.cwd(),server:{host:'127.0.0.1',port:"+str(port)+",strictPort:true},plugins:[{name:'fold-f01a-source',enforce:'pre',load(id){return sources[id.replaceAll('\\\\','/').split('?')[0]];}}]});await server.listen();server.printUrls();"
        server=subprocess.Popen(['node','--input-type=module'],cwd=root,stdin=subprocess.PIPE,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        server.stdin.write(script.encode())
        server.stdin.close()
    else:
        save(out/'served-source.json',{'mode':'Candidate worktree files','sha256':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in ['src/App.tsx','src/styles.css']}})
        server = subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(port),'--strictPort'], cwd=root, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic()+45
        while True:
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}').close()
                break
            except OSError:
                if time.monotonic()>deadline or server.poll() is not None:
                    raise RuntimeError('Vite failed to become ready')
                time.sleep(.1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='msedge', headless=True)
            save(out/'environment.json', {'browser':browser.version,'physicalFold7Verified':False,'label':'EMULATED MOBILE; Windows Edge Chromium, mobile/touch/DPR; Android OS, physical display, native bars, IME and safe-area NOT verified'})
            def new_page(w,h,count,mobile):
                context = browser.new_context(viewport={'width':w,'height':h},is_mobile=mobile,has_touch=mobile,device_scale_factor=2.625 if mobile else 1)
                page = context.new_page()
                page.on('pageerror', lambda e:console.append(str(e)))
                if count==150:
                    def replace(route):
                        response=route.fetch()
                        body=response.text()
                        anchor='const similar = ['
                        assert body.count(anchor)==1
                        injection='initial.push(...Array.from({length:144},(_,i)=>({...initial[i%6],id:`TS-${String(i+7).padStart(3,"0")}`})));\n'
                        fixtures.append({'originalSha256':hashlib.sha256(body.encode()).hexdigest(),'fixtureSha256':hashlib.sha256(body.replace(anchor,injection+anchor).encode()).hexdigest(),'injection':injection})
                        route.fulfill(response=response,body=body.replace(anchor,injection+anchor))
                    page.route('**/src/App.tsx',replace)
                page.goto(f'http://127.0.0.1:{port}',timeout=60000)
                try:
                    page.locator('tbody tr').nth(count-1).wait_for(state='attached')
                except Exception:
                    page.screenshot(path=str(out/f'load-failure-{w}-{h}-{count}.png'),scale='css')
                    save(out/f'load-failure-{w}-{h}-{count}.json',{'text':page.locator('body').inner_text(),'rows':page.locator('tbody tr').count(),'console':console})
                    raise
                settle(page)
                return context,page
            for mobile, sizes in [(True,MOBILE),(False,DESKTOP)]:
                if args.interactions_only:
                    continue
                for w,h in sizes:
                    prefix=f'{"touch" if mobile else "desktop"}-{w}x{h}-'
                    if sum(r['case'].startswith(prefix) for r in results)==12:
                        continue
                    for count in [6,150]:
                        for expanded in [True,False]:
                            context,page=new_page(w,h,count,mobile)
                            if count==6 and expanded:
                                save(out/f'default-{w}x{h}.json',measure(page))
                                page.screenshot(path=str(out/f'default-{w}x{h}.png'),scale='css')
                            if (toggle(page).get_attribute('aria-expanded')=='true')!=expanded:
                                toggle(page).tap() if mobile else toggle(page).click()
                            for route,panel in [('workbench','open'),('workbench','closed'),('summary','NA')]:
                                name=f'{"touch" if mobile else "desktop"}-{w}x{h}-{count}-{"expanded" if expanded else "compact"}-{route}-{panel}'
                                if panel=='closed':
                                    button=page.get_by_role('button',name='Đóng panel',exact=True)
                                    button.tap() if mobile else button.click()
                                if route=='summary':
                                    button=page.locator('.sidebar').get_by_role('button',name='Tổng kết & phiên bản',exact=True)
                                    button.tap() if mobile else button.click()
                                settle(page)
                                page.evaluate('window.scrollTo(0,0)')
                                g=measure(page)
                                isolated=shell.shell_only(page)
                                errors=[]
                                for selector in ['.sidebar','.sidebar-card','.topbar','.page-header','.app-main','.page']:
                                    r=g['boxes'][selector]
                                    if r['x']<-.5 or r['right']>w+.5:errors.append(selector+' exceeds CSS viewport')
                                if isolated['documentWidth']>w+1:errors.append('shell-only page overflow')
                                if mobile:
                                    if not g['coarse'] or g['maxTouchPoints']<1:errors.append('INVALID MOBILE INPUT PROFILE')
                                    for target in g['targets']:
                                        if not target['disabled'] and (target['box']['width']<43.5 or target['box']['height']<43.5):errors.append('touch target under 44px: '+target['name'])
                                save(out/(name+'.json'),{'geometry':g,'shellOnly':isolated,'errors':errors})
                                page.screenshot(path=str(out/(name+'.png')),full_page=not mobile,scale='css')
                                results.append({'case':name,'status':'FAIL' if errors else 'PASS','errors':errors,'documentWidth':g['documentWidth'],'sidebarHeight':g['boxes']['.sidebar']['height'],'headerY':g['boxes']['.page-header']['y']})
                            context.close()
                    save(out/'matrix.json',results)
                    print(f'MATRIX {w}x{h}: {len(results)} cases recorded',flush=True)
            for w,h in MOBILE[:6]+[(390,844),(1440,900)]:
                context,page=new_page(w,h,150,w<1000)
                item={'viewport':[w,h]}
                try:
                    item['nativeTouch']=native_scroll(page,context) if w<1000 else {'NA':'desktop regression'}
                    if w<1000:
                        page.screenshot(path=str(out/f'touch-end-{w}x{h}.png'),scale='css')
                    page.locator('.grid-toolbar input').fill('TS-')
                    page.locator('.grid-toolbar select').select_option('unviewed')
                    page.locator('.asset-link').nth(1).tap() if w<1000 else page.locator('.asset-link').nth(1).click()
                    price=page.get_by_role('spinbutton',name='Đơn giá đề xuất — nhân viên quyết định',exact=True)
                    price.fill('123456789')
                    before=snapshot(page)
                    page.set_viewport_size({'width':832 if w==749 else 749,'height':575})
                    settle(page)
                    item['orientation']={'before':before,'after':snapshot(page)}
                    item['orientation']['preserved']=before==item['orientation']['after']
                    page.set_viewport_size({'width':w,'height':h})
                    page.set_viewport_size({'width':w,'height':max(240,h-280)})
                    price.focus()
                    item['keyboardReducedLayoutSimulation']={'label':'layout viewport reduced by 280 CSS px; not a native Android visualViewport/IME test','geometry':measure(page),'input':price.bounding_box(),'draft':snapshot(page)}
                    page.screenshot(path=str(out/f'keyboard-{w}x{h}.png'))
                    page.set_viewport_size({'width':w,'height':h})
                    before=snapshot(page)
                    toggle(page).tap() if w<1000 else toggle(page).click()
                    after=snapshot(page)
                    item['navTapDraft']={'before':before,'after':after,'draftPreserved':before['price']==after['price'] and before['stats']==after['stats'] and before['fields']==after['fields']}
                    toggle(page).focus()
                    page.keyboard.press('Space')
                    item['keyboardToggle']={'focused':toggle(page).evaluate('e=>e===document.activeElement'),'expanded':toggle(page).get_attribute('aria-expanded')}
                    page.keyboard.press('Enter')
                    page.keyboard.press('Escape')
                    item['escape']={'focused':toggle(page).evaluate('e=>e===document.activeElement'),'expanded':toggle(page).get_attribute('aria-expanded')}
                    page.locator('.sidebar').get_by_role('button',name='Tổng kết & phiên bản',exact=True).tap() if w<1000 else page.locator('.sidebar').get_by_role('button',name='Tổng kết & phiên bản',exact=True).click()
                    page.wait_for_function("document.activeElement===document.querySelector('h1')")
                    page.locator('.sidebar').get_by_role('button',name='Phân tích danh mục',exact=True).tap() if w<1000 else page.locator('.sidebar').get_by_role('button',name='Phân tích danh mục',exact=True).click()
                    page.wait_for_function("document.activeElement===document.querySelector('h1')")
                    item['routeReturn']=snapshot(page)
                except Exception:
                    item['error']=traceback.format_exc()
                interactions.append(item)
                save(out/'interactions.json',interactions)
                context.close()
            browser.close()
        after=shell.hashes(root)
        save(out/'source-integrity.json',{'before':frozen,'after':after,'unchanged':frozen==after})
        save(out/'console.json',console)
        save(out/'fixtures.json',fixtures)
        print(json.dumps({'cases':len(results),'pass':sum(r['status']=='PASS' for r in results),'fail':sum(r['status']=='FAIL' for r in results),'sourceUnchanged':frozen==after,'interactionErrors':sum('error' in r for r in interactions)}),flush=True)
        interaction_failures=[r for r in interactions if 'error' in r or not r['orientation']['preserved'] or (r['viewport'][0]<1000 and not r['navTapDraft']['draftPreserved']) or not r['keyboardToggle']['focused'] or not r['escape']['focused']]
        save(out/'interaction-failures.json',interaction_failures)
        return int(frozen!=after or bool(console) or (args.phase=='candidate' and (any(r['status']=='FAIL' for r in results) or bool(interaction_failures))))
    finally:
        server.terminate()
        server.wait(timeout=15)
        log.close()
        save(out/'cleanup.json',{'pid':server.pid,'exit':server.returncode})


if __name__=='__main__':
    raise SystemExit(main())
