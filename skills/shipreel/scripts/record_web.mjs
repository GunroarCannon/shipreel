// Zero-dependency web recorder: drives system Chrome/Edge over CDP (Node >= 22 built-in WebSocket).
// Default mode is virtual time: a page clock shim plus one JPEG per frame, encoded at exactly --fps.
// Capture can be slower than realtime; playback matches the page clock. --realtime keeps a live
// screencast (ack-before-write) and reports mode "screencast" plus a capture-fps warn when it was choppy.
// Usually called through: python clip.py record-web <project> --id X --url URL [--steps steps.json] [--portrait]
//
// steps.json: [ {"goto":"https://..."}, {"wait":800}, {"waitFor":"#app"}, {"click":"text=Play"}, {"click":[200,640]},
//   {"hover":".card"}, {"type":"hello world","into":"#search","delay":70}, {"press":"Enter"}, {"key":"ArrowRight","hold":600},
//   {"scroll":900,"ms":1200}, {"scrollTo":"#pricing"}, {"move":[100,200],"ms":400}, {"drag":[[100,500],[300,500]],"ms":700},
//   {"eval":"document.body.classList.add('demo')"}, {"mark":"boss-appears"}, {"shot":"hero.png"} ]
// "mark" records the current video time -> printed in the result JSON so plans can cut on exact moments
// without anyone looking at frames. HTML5 <video>/<audio> follow the wall clock and will look wrong here.
import { spawn, execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true]);
  return acc;
}, []));
function num(name, def) {
  if (args[name] === undefined || args[name] === true) return def;
  const n = +args[name];
  return Number.isFinite(n) ? n : def;
}
const W = num("w", 390), H = num("h", 844), SCALE = num("scale", 2), FPS = Math.max(1, Math.round(num("fps", 30)));
const DUR = num("dur", 20), SETTLE_MS = num("settle", 700), LEAD_MS = num("lead", 400), TAIL_MS = num("tail", 1200);
const out = path.resolve(args.out || "web.mp4");
const steps = args.steps ? JSON.parse(fs.readFileSync(args.steps, "utf8")) : [];
const chrome = args.chrome;
const wantVirtual = !args.realtime;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "shipreel-web-"));
const framesDir = path.join(tmp, "f"); fs.mkdirSync(framesDir);
fs.mkdirSync(path.dirname(out), { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const framesOf = (ms) => Math.max(0, Math.round(ms * FPS / 1000));
const maxFrames = Math.max(1, Math.round(DUR * FPS));

let proc = null, ws = null;
function fatal(msg) { const e = new Error(msg); e.fatal = true; return e; }

const flags = ["--remote-debugging-port=0", `--user-data-dir=${path.join(tmp, "prof")}`, "--no-first-run", "--no-default-browser-check",
  "--hide-scrollbars", "--mute-audio", "--disable-extensions", "--disable-background-networking", "--force-color-profile=srgb",
  "--disable-frame-rate-limit", "--disable-gpu-vsync", "--disable-background-timer-throttling",
  "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
  `--window-size=${W},${H}`, `--force-device-scale-factor=${SCALE}`, "about:blank"];
if (!args.headed) flags.unshift("--headless=new");
proc = spawn(chrome, flags, { stdio: "ignore" });

async function devtoolsPort() {
  const f = path.join(tmp, "prof", "DevToolsActivePort");
  for (let i = 0; i < 150; i++) { if (fs.existsSync(f)) { const p = fs.readFileSync(f, "utf8").split("\n")[0].trim(); if (p) return p; } await sleep(100); }
  throw new Error("chrome did not start (DevToolsActivePort missing)");
}
const port = await devtoolsPort();
let pages = [];
for (let i = 0; i < 50 && !pages.length; i++) { pages = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).filter((t) => t.type === "page"); if (!pages.length) await sleep(100); }
ws = new WebSocket(pages[0].webSocketDebuggerUrl);
await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let seq = 0; const pending = new Map(); const handlers = {};
ws.onmessage = (ev) => {
  const m = JSON.parse(typeof ev.data === "string" ? ev.data : ev.data.toString());
  if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method && handlers[m.method]) handlers[m.method](m.params);
};
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
async function evaluate(expr) {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) {
    const d = r.exceptionDetails;
    throw new Error(d.exception?.description || d.text || "page eval failed");
  }
  return r.result?.value;
}

const SHIM = `(() => { try {
  const FPS = ${FPS};
  const frameMs = 1000 / FPS;
  let ticks = 0;
  const now = () => ticks * 1000 / FPS;
  const realSetTimeout = window.setTimeout.bind(window);
  const rafQ = []; let rafId = 1;
  window.requestAnimationFrame = (cb) => { const id = rafId++; rafQ.push({ id, cb }); return id; };
  window.cancelAnimationFrame = (id) => { const i = rafQ.findIndex((x) => x.id === id); if (i >= 0) rafQ.splice(i, 1); };
  const timers = []; let timerId = 1;
  const arm = (fn, ms, interval) => {
    const id = timerId++;
    const delay = Number.isFinite(+ms) ? Math.max(0, +ms) : 0;
    const every = interval ? (delay || frameMs) : null;
    timers.push({ id, fn, at: now() + (every == null ? delay : every), interval: every });
    return id;
  };
  window.setTimeout = (fn, ms) => arm(fn, ms, false);
  window.setInterval = (fn, ms) => arm(fn, ms, true);
  const clear = (id) => { const t = timers.find((x) => x.id === id); if (t) t.cleared = true; };
  window.clearTimeout = clear; window.clearInterval = clear;
  const RealDate = Date; const wall0 = RealDate.now();
  function SRDate(...a) {
    if (new.target) return a.length ? new RealDate(...a) : new RealDate(wall0 + now());
    return new RealDate(wall0 + now()).toString();
  }
  SRDate.prototype = RealDate.prototype; SRDate.now = () => wall0 + now();
  SRDate.parse = RealDate.parse; SRDate.UTC = RealDate.UTC; SRDate.prototype.constructor = SRDate;
  window.Date = SRDate;
  const perfNow = () => now();
  try { Object.defineProperty(performance, "now", { configurable: true, value: perfNow }); }
  catch (e) { try { Performance.prototype.now = perfNow; } catch (e2) {} }
  const pinned = new WeakMap();
  function pinAll() {
    let list = []; try { list = document.getAnimations(); } catch (e) { return; }
    const t = now();
    for (const a of list) {
      try {
        if (!pinned.has(a)) {
          const ct = a.currentTime == null ? 0 : a.currentTime;
          pinned.set(a, t - ct);
          try { a.pause(); } catch (e) {}
        }
        a.currentTime = t - pinned.get(a);
      } catch (e) {}
    }
  }
  window.__sr_pin = pinAll;
  document.addEventListener("animationstart", () => pinAll(), true);
  function armPause() {
    const el = document.documentElement;
    if (!el) { realSetTimeout(armPause, 16); return; }
    if (!document.getElementById("__sr_pause")) {
      const st = document.createElement("style"); st.id = "__sr_pause";
      st.textContent = "*,*::before,*::after{animation-play-state:paused !important}html{scroll-behavior:auto !important}";
      (document.head || el).appendChild(st);
    }
    try {
      const mo = new MutationObserver(() => pinAll());
      mo.observe(el, { subtree: true, childList: true, attributes: true, attributeFilter: ["style", "class"] });
    } catch (e) {}
    pinAll();
  }
  armPause();
  const origAnimate = Element.prototype.animate;
  Element.prototype.animate = function () { const anim = origAnimate.apply(this, arguments); try { pinAll(); } catch (e) {} return anim; };
  function fireTimers() {
    let guard = 0;
    while (guard++ < 10000) {
      const t = now();
      const due = timers.filter((tm) => !tm.cleared && tm.at <= t + 1e-6);
      if (!due.length) break;
      for (const tm of due) {
        if (tm.cleared) continue;
        if (tm.interval == null) tm.cleared = true; else tm.at += tm.interval;
        try { tm.fn(); } catch (e) {}
      }
      for (let i = timers.length - 1; i >= 0; i--) if (timers[i].cleared) timers.splice(i, 1);
    }
  }
  function fireRAF() {
    const q = rafQ.splice(0, rafQ.length); const t = now();
    for (const item of q) { try { item.cb(t); } catch (e) {} }
  }
  window.__sr_advance = (tickTarget) => {
    let guard = 0;
    while (ticks < tickTarget && guard++ < 100000) { ticks += 1; fireTimers(); fireRAF(); pinAll(); }
  };
  window.__sr_ticks = () => ticks;
  window.__sr_ok = true;
} catch (e) { window.__sr_error = String(e && e.message || e); } })();`;

await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: !!args.mobile });
if (args.mobile) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
if (args.dark) await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
if (wantVirtual) await send("Page.addScriptToEvaluateOnNewDocument", { source: SHIM });
if (!args["no-cursor"]) {
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `(() => { const s = () => {
    if (document.getElementById('__sr_cur')) return; const c = document.createElement('div'); c.id='__sr_cur';
    c.style.cssText='position:fixed;left:-50px;top:-50px;width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,.92);border:2px solid #111;box-shadow:0 2px 8px rgba(0,0,0,.45);z-index:2147483647;pointer-events:none;transform:translate(-50%,-50%);transition:transform .08s';
    document.documentElement.appendChild(c);
    addEventListener('mousemove', e => { c.style.left=e.clientX+'px'; c.style.top=e.clientY+'px'; }, true);
    addEventListener('mousedown', e => { c.style.transform='translate(-50%,-50%) scale(.7)'; const r=document.createElement('div');
      r.style.cssText='position:fixed;left:'+e.clientX+'px;top:'+e.clientY+'px;width:16px;height:16px;border-radius:50%;border:3px solid rgba(255,255,255,.95);transform:translate(-50%,-50%) scale(1);opacity:1;z-index:2147483646;pointer-events:none;transition:transform .45s ease-out,opacity .45s';
      document.documentElement.appendChild(r); requestAnimationFrame(()=>{ r.style.transform='translate(-50%,-50%) scale(4)'; r.style.opacity='0'; }); setTimeout(()=>r.remove(),500); }, true);
    addEventListener('mouseup', () => { c.style.transform='translate(-50%,-50%) scale(1)'; }, true); };
    document.readyState === 'loading' ? addEventListener('DOMContentLoaded', s) : s(); })();` });
}

function loaded() {
  return new Promise((r) => { handlers["Page.loadEventFired"] = () => r(); setTimeout(r, 15000); });
}
let nav = loaded(); await send("Page.navigate", { url: args.url }); await nav;

const marks = {}; let mouse = [W / 2, H / 2];
const ease = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
const KEYS = { Enter: 13, Tab: 9, Escape: 27, Backspace: 8, Space: 32, " ": 32, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, Shift: 16, Control: 17 };
async function key(k, type) {
  const code = KEYS[k] ?? k.toUpperCase().charCodeAt(0);
  const codeName = k.length === 1 ? `Key${k.toUpperCase()}` : k === " " ? "Space" : k;
  await send("Input.dispatchKeyEvent", { type, key: k, code: codeName, windowsVirtualKeyCode: code, nativeVirtualKeyCode: code, ...(type === "keyDown" && k === "Enter" ? { text: "\r" } : {}) });
}
function centerJs(sel) {
  const behavior = "'instant'";
  return sel.startsWith("text=")
    ? `(() => { const t=${JSON.stringify(sel.slice(5))}.toLowerCase(); const it=document.evaluate("//*[not(self::script)][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"+JSON.stringify(sel.slice(5).toLowerCase())+")]",document,null,7,null); let best=null; for(let i=0;i<it.snapshotLength;i++){const e=it.snapshotItem(i); const r=e.getBoundingClientRect(); if(r.width&&r.height&&(!best||r.width*r.height<best.a)) best={e,a:r.width*r.height};} if(!best) return null; best.e.scrollIntoView({block:'center',behavior:${behavior}}); const r=best.e.getBoundingClientRect(); return [r.x+r.width/2,r.y+r.height/2]; })()`
    : `(() => { const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return null; e.scrollIntoView({block:'center',behavior:${behavior}}); const r=e.getBoundingClientRect(); return [r.x+r.width/2,r.y+r.height/2]; })()`;
}

// the element's box as fractions of the viewport (= of the recorded frame), measured without scrolling; null if missing or off-screen
function rectJs(sel) {
  const find = sel.startsWith("text=")
    ? `(() => { const t=${JSON.stringify(sel.slice(5).toLowerCase())}; const it=document.evaluate("//*[not(self::script)][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"+JSON.stringify(sel.slice(5).toLowerCase())+")]",document,null,7,null); let best=null; for(let i=0;i<it.snapshotLength;i++){const e=it.snapshotItem(i); const r=e.getBoundingClientRect(); if(r.width&&r.height&&(!best||r.width*r.height<best.a)) best={e,a:r.width*r.height};} return best&&best.e; })()`
    : `document.querySelector(${JSON.stringify(sel)})`;
  return `(() => { const e=${find}; if(!e) return null; const r=e.getBoundingClientRect(); const W=innerWidth,H=innerHeight; if(!r.width||!r.height||r.right<=0||r.bottom<=0||r.left>=W||r.top>=H) return null; const x=Math.max(0,r.left),y=Math.max(0,r.top),x2=Math.min(W,r.right),y2=Math.min(H,r.bottom); return [x/W,y/H,(x2-x)/W,(y2-y)/H,r.width*r.height>0?((x2-x)*(y2-y))/(r.width*r.height):0]; })()`;
}
const targets = {};
function noteTarget(s, t, r) {
  if (!r) { console.error(`target not visible: ${JSON.stringify(s)} (scroll it into view first, or fix the selector)`); return; }
  const pad = (s.pad ?? 0) / W, padY = (s.pad ?? 0) / H;
  const r4 = (n) => +n.toFixed(4);
  targets[s.target] = { t: +t.toFixed(2), sel: s.sel, box: [r4(Math.max(0, r[0] - pad)), r4(Math.max(0, r[1] - padY)), r4(Math.min(1, r[2] + 2 * pad)), r4(Math.min(1, r[3] + 2 * padY))], visible: r4(r[4]) };
}

let mode = wantVirtual ? "virtual" : "screencast";
let captured = 0;
let virtualTicks = 0;
let warn;

async function advanceTo(tick) {
  const got = await evaluate(`(() => { if (typeof __sr_advance !== "function") throw new Error("clock shim missing"); __sr_advance(${tick}); const el = document.documentElement; if (el) el.getBoundingClientRect(); return __sr_ticks(); })()`);
  if (!(got >= tick)) throw fatal("clock shim stalled");
  virtualTicks = tick;
}
async function pump(n) { if (n > 0) await advanceTo(virtualTicks + n); }
async function captureOne() {
  if (captured >= maxFrames) return false;
  await advanceTo(virtualTicks + 1);
  const shot = await send("Page.captureScreenshot", { format: "jpeg", quality: 80, fromSurface: true });
  fs.writeFileSync(path.join(framesDir, `${String(captured).padStart(6, "0")}.jpg`), Buffer.from(shot.data, "base64"));
  captured++;
  if (captured % 30 === 0) console.error(`virtual ${(captured / FPS).toFixed(1)}s`);
  return true;
}
async function captureN(n) {
  const k = Math.max(0, Math.min(n, maxFrames - captured));
  for (let i = 0; i < k; i++) { if (!(await captureOne())) break; }
}
async function centerVirtual(sel) {
  const js = centerJs(sel);
  const deadline = virtualTicks + framesOf(8000);
  const wallEnd = Date.now() + 45000;
  while (Date.now() < wallEnd && virtualTicks < deadline) {
    const c = await evaluate(js);
    if (c) return c;
    if (!(await captureOne())) break;
  }
  throw new Error(`selector not found: ${sel}`);
}
async function moveToVirtual(x, y, ms = 450) {
  const [sx, sy] = mouse; const k = Math.max(4, framesOf(ms) || 4);
  for (let i = 1; i <= k; i++) {
    if (captured >= maxFrames) break;
    const e = ease(i / k);
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: sx + (x - sx) * e, y: sy + (y - sy) * e });
    await captureOne();
  }
  mouse = [x, y];
}
async function clickVirtual(x, y) {
  await moveToVirtual(x, y);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await captureN(2);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  await captureN(6);
}

async function runVirtual() {
  const state = await evaluate(`({ok: typeof window.__sr_advance === "function" && !window.__sr_error, err: window.__sr_error || ""})`);
  if (!state?.ok) {
    if (state?.err) throw fatal("clock shim failed: " + state.err);
    console.error("clock shim missing after navigation; falling back to screencast");
    mode = "screencast";
    return false;
  }
  await pump(framesOf(SETTLE_MS));
  if (!steps.length) {
    await captureN(maxFrames);
    return true;
  }
  await captureN(framesOf(LEAD_MS));
  for (const s of steps) {
    if (captured >= maxFrames) break;
    try {
      if (s.goto) {
        nav = loaded(); await send("Page.navigate", { url: s.goto }); await nav;
        const again = await evaluate(`typeof window.__sr_advance === "function" && !window.__sr_error`);
        if (!again) throw fatal("clock shim missing after goto");
        virtualTicks = 0;
        await pump(framesOf(SETTLE_MS));
      } else if (s.wait) await captureN(framesOf(s.wait));
      else if (s.waitFor) await centerVirtual(s.waitFor);
      else if (s.click) { const [x, y] = Array.isArray(s.click) ? s.click : await centerVirtual(s.click); await clickVirtual(x, y); }
      else if (s.hover) { const [x, y] = Array.isArray(s.hover) ? s.hover : await centerVirtual(s.hover); await moveToVirtual(x, y, s.ms || 500); }
      else if (s.move) await moveToVirtual(s.move[0], s.move[1], s.ms || 450);
      else if (s.type !== undefined) {
        if (s.into) { const [x, y] = await centerVirtual(s.into); await clickVirtual(x, y); }
        const per = Math.max(1, framesOf(s.delay ?? 65));
        for (const ch of String(s.type)) { await send("Input.insertText", { text: ch }); await captureN(per); }
      } else if (s.press) { await key(s.press, "keyDown"); await captureN(Math.max(1, framesOf(40))); await key(s.press, "keyUp"); }
      else if (s.key) { await key(s.key, "keyDown"); await captureN(Math.max(1, framesOf(s.hold || 120))); await key(s.key, "keyUp"); }
      else if (s.scroll) {
        const n = Math.max(1, framesOf(s.ms || 900));
        const y0 = await evaluate("scrollY") || 0;
        for (let i = 1; i <= n && captured < maxFrames; i++) {
          const e = ease(i / n);
          await evaluate(`scrollTo(0, ${y0 + (+s.scroll) * e})`);
          await captureOne();
        }
      } else if (s.scrollTo) {
        await evaluate(`document.querySelector(${JSON.stringify(s.scrollTo)})?.scrollIntoView({behavior:'instant',block:'center'})`);
        await captureN(Math.max(1, framesOf(s.ms || 900)));
      } else if (s.drag) {
        const [[x1, y1], [x2, y2]] = s.drag; await moveToVirtual(x1, y1, 200);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: x1, y: y1, button: "left", clickCount: 1 });
        const k = Math.max(4, framesOf(s.ms || 600));
        for (let i = 1; i <= k && captured < maxFrames; i++) {
          const e = ease(i / k);
          const x = x1 + (x2 - x1) * e, y = y1 + (y2 - y1) * e;
          await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "left", buttons: 1 });
          await captureOne();
        }
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x2, y: y2, button: "left", clickCount: 1 });
        mouse = [x2, y2];
      } else if (s.eval) { await evaluate(s.eval); await captureOne(); }
      else if (s.mark) marks[s.mark] = +(captured / FPS).toFixed(3);
      else if (s.target) {
        let r = await evaluate(rectJs(s.sel));
        for (let i = 0; !r && i < 30 && captured < maxFrames; i++) { await captureOne(); r = await evaluate(rectJs(s.sel)); }
        noteTarget(s, captured / FPS, r);
      }
      else if (s.shot) {
        const r = await send("Page.captureScreenshot", { format: "png" });
        fs.writeFileSync(path.resolve(path.dirname(out), s.shot), Buffer.from(r.data, "base64"));
      }
    } catch (e) {
      if (e.fatal) throw e;
      console.error(`step failed: ${JSON.stringify(s)} -> ${e.message}`);
      if (s.required) throw e;
    }
  }
  await captureN(framesOf(TAIL_MS));
  return true;
}

async function runScreencast() {
  const frames = []; let t0 = null; let n = 0; const hashes = new Set();
  let writeChain = Promise.resolve();
  handlers["Page.screencastFrame"] = (f) => {
    const ts = f.metadata?.timestamp || 0; if (t0 === null) t0 = ts;
    const data = Buffer.from(f.data, "base64");
    const file = path.join(framesDir, `${String(n++).padStart(6, "0")}.jpg`);
    frames.push({ file, t: ts - t0 });
    hashes.add(crypto.createHash("sha1").update(data).digest("hex"));
    send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
    writeChain = writeChain.then(() => fs.promises.writeFile(file, data));
  };
  await send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: Math.round(W * SCALE), maxHeight: Math.round(H * SCALE), everyNthFrame: 1 });
  const start = Date.now(); const now = () => (Date.now() - start) / 1000;
  async function moveTo(x, y, ms = 450) {
    const [sx, sy] = mouse; const k = Math.max(4, Math.round(ms / 16));
    for (let i = 1; i <= k; i++) { const e = ease(i / k); await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: sx + (x - sx) * e, y: sy + (y - sy) * e }); await sleep(ms / k); }
    mouse = [x, y];
  }
  async function center(sel) {
    const js = centerJs(sel);
    for (let i = 0; i < 30; i++) { const c = await evaluate(js); if (c) return c; await sleep(150); }
    throw new Error(`selector not found: ${sel}`);
  }
  async function click(x, y) {
    await moveTo(x, y);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 }); await sleep(70);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  await sleep(LEAD_MS);
  for (const s of steps) {
    if (now() > DUR) break;
    try {
      if (s.goto) { const pl = loaded(); await send("Page.navigate", { url: s.goto }); await pl; await sleep(SETTLE_MS); }
      else if (s.wait) await sleep(s.wait);
      else if (s.waitFor) await center(s.waitFor);
      else if (s.click) { const [x, y] = Array.isArray(s.click) ? s.click : await center(s.click); await click(x, y); }
      else if (s.hover) { const [x, y] = Array.isArray(s.hover) ? s.hover : await center(s.hover); await moveTo(x, y, s.ms || 500); }
      else if (s.move) await moveTo(s.move[0], s.move[1], s.ms || 450);
      else if (s.type !== undefined) {
        if (s.into) { const [x, y] = await center(s.into); await click(x, y); }
        for (const ch of String(s.type)) { await send("Input.insertText", { text: ch }); await sleep(s.delay ?? 65); }
      } else if (s.press) { await key(s.press, "keyDown"); await sleep(40); await key(s.press, "keyUp"); }
      else if (s.key) { await key(s.key, "keyDown"); await sleep(s.hold || 120); await key(s.key, "keyUp"); }
      else if (s.scroll) {
        const ms = s.ms || 900;
        await evaluate(`new Promise(r=>{const y0=scrollY,d=${+s.scroll},t0=performance.now();const f=t=>{const k=Math.min(1,(t-t0)/${ms});const e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;scrollTo(0,y0+d*e);k<1?requestAnimationFrame(f):r()};requestAnimationFrame(f)})`);
      } else if (s.scrollTo) await evaluate(`document.querySelector(${JSON.stringify(s.scrollTo)})?.scrollIntoView({behavior:'smooth',block:'center'})`), await sleep(s.ms || 900);
      else if (s.drag) {
        const [[x1, y1], [x2, y2]] = s.drag; await moveTo(x1, y1);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: x1, y: y1, button: "left", clickCount: 1 });
        const k = 20; for (let i = 1; i <= k; i++) { const e = ease(i / k); await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x1 + (x2 - x1) * e, y: y1 + (y2 - y1) * e, button: "left", buttons: 1 }); await sleep((s.ms || 600) / k); }
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x2, y: y2, button: "left", clickCount: 1 }); mouse = [x2, y2];
      } else if (s.eval) await evaluate(s.eval);
      else if (s.mark) marks[s.mark] = +now().toFixed(2);
      else if (s.target) {
        let r = await evaluate(rectJs(s.sel));
        for (let i = 0; !r && i < 10; i++) { await sleep(150); r = await evaluate(rectJs(s.sel)); }
        noteTarget(s, now(), r);
      }
      else if (s.shot) { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(path.resolve(path.dirname(out), s.shot), Buffer.from(r.data, "base64")); }
    } catch (e) { console.error(`step failed: ${JSON.stringify(s)} -> ${e.message}`); if (s.required) throw e; }
  }
  const tailMs = steps.length ? TAIL_MS : Math.max(0, DUR - now()) * 1000;
  await sleep(Math.min(tailMs, DUR * 1000));
  const total = Math.min(now(), DUR + 2);
  await send("Page.stopScreencast").catch(() => {});
  await sleep(200);
  await writeChain;
  const measured = total > 0 ? Math.round((hashes.size / total) * 10) / 10 : 0;
  if (measured < 20) warn = `capture fps ${measured} < 20 (requested ${FPS}); screencast was choppy, re-record`;
  return { frames, total, measured };
}

function encodeImage2(count) {
  const ow = Math.round(W * SCALE / 2) * 2, oh = Math.round(H * SCALE / 2) * 2;
  const pattern = path.join(framesDir, "%06d.jpg").replace(/\\/g, "/");
  try {
    execFileSync("ffmpeg", ["-y", "-v", "error", "-framerate", String(FPS), "-start_number", "0", "-i", pattern,
      "-frames:v", String(count), "-vf", `scale=${ow}:${oh}:flags=lanczos,format=yuv420p`,
      "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", out],
      { stdio: ["ignore", "ignore", "pipe"] });
  } catch (e) {
    throw new Error((e.stderr && e.stderr.toString() || e.message || "ffmpeg failed").slice(-500));
  }
}
function encodeConcat(frames, total) {
  let list = "";
  for (let i = 0; i < frames.length; i++) {
    const d = (i + 1 < frames.length ? frames[i + 1].t : Math.max(frames[i].t + 1 / FPS, total)) - frames[i].t;
    list += `file '${frames[i].file.replace(/\\/g, "/")}'\nduration ${Math.max(d, 0.001).toFixed(4)}\n`;
  }
  list += `file '${frames[frames.length - 1].file.replace(/\\/g, "/")}'\n`;
  const lst = path.join(tmp, "list.txt"); fs.writeFileSync(lst, list);
  const ow = Math.round(W * SCALE / 2) * 2, oh = Math.round(H * SCALE / 2) * 2;
  try {
    execFileSync("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
      "-vf", `fps=${FPS},scale=${ow}:${oh}:flags=lanczos,format=yuv420p`,
      "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", out],
      { stdio: ["ignore", "ignore", "pipe"] });
  } catch (e) {
    throw new Error((e.stderr && e.stderr.toString() || e.message || "ffmpeg failed").slice(-500));
  }
}

async function shutdown() {
  try { if (ws) ws.close(); } catch { /* already closed */ }
  if (proc) {
    const exited = new Promise((r) => proc.once("exit", r));
    try { proc.kill(); } catch { /* already gone */ }
    await Promise.race([exited, sleep(3000)]);
  }
  try { fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 }); } catch { /* OS temp cleans it */ }
}

try {
  let frameCount = 0, dur = 0, fpsOut = FPS;
  if (mode === "virtual") {
    const stayed = await runVirtual();
    if (stayed) {
      if (!captured) { console.error("no frames captured"); await shutdown(); process.exit(2); }
      encodeImage2(captured);
      frameCount = captured;
      dur = +(captured / FPS).toFixed(3);
      fpsOut = FPS;
    }
  }
  if (mode === "screencast") {
    const sc = await runScreencast();
    if (!sc.frames.length) { console.error("no frames captured"); await shutdown(); process.exit(2); }
    encodeConcat(sc.frames, sc.total);
    frameCount = sc.frames.length;
    dur = +sc.total.toFixed(3);
    fpsOut = sc.measured;
  }
  await shutdown();
  const result = { ok: true, out, frames: frameCount, dur, marks, mode, fps: fpsOut };
  if (Object.keys(targets).length) result.targets = targets;
  if (warn) result.warn = warn;
  console.log(JSON.stringify(result));
  process.exit(0);
} catch (e) {
  console.error(e && e.message ? e.message : e);
  await shutdown();
  process.exit(1);
}
