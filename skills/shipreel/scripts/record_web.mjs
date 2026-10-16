// Zero-dependency web recorder: drives system Chrome/Edge over CDP (Node >= 22 built-in WebSocket),
// captures a screencast (JPEG frames + timestamps) and encodes a constant-fps MP4 with ffmpeg.
// Usually called through: python clip.py record-web <project> --id X --url URL [--steps steps.json] [--portrait]
//
// steps.json: [ {"goto":"https://..."}, {"wait":800}, {"waitFor":"#app"}, {"click":"text=Play"}, {"click":[200,640]},
//   {"hover":".card"}, {"type":"hello world","into":"#search","delay":70}, {"press":"Enter"}, {"key":"ArrowRight","hold":600},
//   {"scroll":900,"ms":1200}, {"scrollTo":"#pricing"}, {"move":[100,200],"ms":400}, {"drag":[[100,500],[300,500]],"ms":700},
//   {"eval":"document.body.classList.add('demo')"}, {"mark":"boss-appears"}, {"shot":"hero.png"} ]
// "mark" records the current video time -> printed in the result JSON so plans can cut on exact moments
// without anyone looking at frames.
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith("--")) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true]);
  return acc;
}, []));
const W = +args.w || 390, H = +args.h || 844, SCALE = +args.scale || 2, FPS = +args.fps || 30, DUR = +args.dur || 20;
const out = path.resolve(args.out || "web.mp4");
const steps = args.steps ? JSON.parse(fs.readFileSync(args.steps, "utf8")) : [];
const chrome = args.chrome;
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "shipreel-web-"));
const framesDir = path.join(tmp, "f"); fs.mkdirSync(framesDir);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const flags = [`--remote-debugging-port=0`, `--user-data-dir=${path.join(tmp, "prof")}`, "--no-first-run", "--no-default-browser-check",
  "--hide-scrollbars", "--mute-audio", "--disable-extensions", "--disable-background-networking", "--force-color-profile=srgb",
  `--window-size=${W},${H}`, `--force-device-scale-factor=${SCALE}`, "about:blank"];
if (!args.headed) flags.unshift("--headless=new");
const proc = spawn(chrome, flags, { stdio: "ignore" });

async function devtoolsPort() {
  const f = path.join(tmp, "prof", "DevToolsActivePort");
  for (let i = 0; i < 150; i++) { if (fs.existsSync(f)) { const p = fs.readFileSync(f, "utf8").split("\n")[0].trim(); if (p) return p; } await sleep(100); }
  throw new Error("chrome did not start (DevToolsActivePort missing)");
}
const port = await devtoolsPort();
let pages = [];
for (let i = 0; i < 50 && !pages.length; i++) { pages = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).filter((t) => t.type === "page"); if (!pages.length) await sleep(100); }
const ws = new WebSocket(pages[0].webSocketDebuggerUrl);
await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
let seq = 0; const pending = new Map(); const handlers = {};
ws.onmessage = (ev) => {
  const m = JSON.parse(typeof ev.data === "string" ? ev.data : ev.data.toString());
  if (m.id && pending.has(m.id)) { const { res, rej } = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
  else if (m.method && handlers[m.method]) handlers[m.method](m.params);
};
const send = (method, params = {}) => new Promise((res, rej) => { const id = ++seq; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const evaluate = async (expr) => (await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true })).result?.value;

await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: !!args.mobile });
if (args.mobile) await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
if (args.dark) await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
if (!args["no-cursor"]) {
  // visible fake cursor + click ripple (headless has no cursor); pointer-events none so it never blocks clicks
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

// navigate first (not recorded), then start the screencast
const loaded = () => new Promise((r) => { handlers["Page.loadEventFired"] = () => r(); setTimeout(r, 15000); });
let p = loaded(); await send("Page.navigate", { url: args.url }); await p; await sleep(+args.settle || 700);

const frames = []; let t0 = null; let n = 0;
handlers["Page.screencastFrame"] = async (f) => {
  const ts = f.metadata.timestamp; if (t0 === null) t0 = ts;
  const file = path.join(framesDir, `${String(n++).padStart(6, "0")}.jpg`);
  fs.writeFileSync(file, Buffer.from(f.data, "base64")); frames.push({ file, t: ts - t0 });
  send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
};
await send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: Math.round(W * SCALE), maxHeight: Math.round(H * SCALE), everyNthFrame: 1 });
const start = Date.now(); const now = () => (Date.now() - start) / 1000;
const marks = {}; let mouse = [W / 2, H / 2];
const ease = (x) => (x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2);
async function moveTo(x, y, ms = 450) {
  const [sx, sy] = mouse; const k = Math.max(4, Math.round(ms / 16));
  for (let i = 1; i <= k; i++) { const e = ease(i / k); await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: sx + (x - sx) * e, y: sy + (y - sy) * e }); await sleep(ms / k); }
  mouse = [x, y];
}
async function center(sel) {
  const js = sel.startsWith("text=")
    ? `(() => { const t=${JSON.stringify(sel.slice(5))}.toLowerCase(); const it=document.evaluate("//*[not(self::script)][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"+JSON.stringify(t)+")]",document,null,7,null); let best=null; for(let i=0;i<it.snapshotLength;i++){const e=it.snapshotItem(i); const r=e.getBoundingClientRect(); if(r.width&&r.height&&(!best||r.width*r.height<best.a)) best={e,a:r.width*r.height};} if(!best) return null; best.e.scrollIntoView({block:'center'}); const r=best.e.getBoundingClientRect(); return [r.x+r.width/2,r.y+r.height/2]; })()`
    : `(() => { const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return null; e.scrollIntoView({block:'center'}); const r=e.getBoundingClientRect(); return [r.x+r.width/2,r.y+r.height/2]; })()`;
  for (let i = 0; i < 30; i++) { const c = await evaluate(js); if (c) return c; await sleep(150); }
  throw new Error(`selector not found: ${sel}`);
}
const KEYS = { Enter: 13, Tab: 9, Escape: 27, Backspace: 8, Space: 32, " ": 32, ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, Shift: 16, Control: 17 };
async function key(k, type) {
  const code = KEYS[k] ?? k.toUpperCase().charCodeAt(0);
  const codeName = k.length === 1 ? `Key${k.toUpperCase()}` : k === " " ? "Space" : k;
  await send("Input.dispatchKeyEvent", { type, key: k, code: codeName, windowsVirtualKeyCode: code, nativeVirtualKeyCode: code, ...(type === "keyDown" && k === "Enter" ? { text: "\r" } : {}) });
}
async function click(x, y) {
  await moveTo(x, y);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 }); await sleep(70);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

await sleep(+args.lead || 400);
for (const s of steps) {
  if (now() > DUR) break;
  try {
    if (s.goto) { const pl = loaded(); await send("Page.navigate", { url: s.goto }); await pl; }
    else if (s.wait) await sleep(s.wait);
    else if (s.waitFor) await center(s.waitFor);
    else if (s.click) { const [x, y] = Array.isArray(s.click) ? s.click : await center(s.click); await click(x, y); }
    else if (s.hover) { const [x, y] = Array.isArray(s.hover) ? s.hover : await center(s.hover); await moveTo(x, y, s.ms || 500); }
    else if (s.move) await moveTo(s.move[0], s.move[1], s.ms || 450);
    else if (s.type !== undefined) {
      if (s.into) { const [x, y] = await center(s.into); await click(x, y); }
      for (const ch of String(s.type)) { await send("Input.insertText", { text: ch }); await sleep(s.delay ?? 65); }
    }
    else if (s.press) { await key(s.press, "keyDown"); await sleep(40); await key(s.press, "keyUp"); }
    else if (s.key) { await key(s.key, "keyDown"); await sleep(s.hold || 120); await key(s.key, "keyUp"); }
    else if (s.scroll) {
      const ms = s.ms || 900;
      await evaluate(`new Promise(r=>{const y0=scrollY,d=${s.scroll},t0=performance.now();const f=t=>{const k=Math.min(1,(t-t0)/${ms});const e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;scrollTo(0,y0+d*e);k<1?requestAnimationFrame(f):r()};requestAnimationFrame(f)})`);
    }
    else if (s.scrollTo) await evaluate(`document.querySelector(${JSON.stringify(s.scrollTo)})?.scrollIntoView({behavior:'smooth',block:'center'})`), await sleep(s.ms || 900);
    else if (s.drag) {
      const [[x1, y1], [x2, y2]] = s.drag; await moveTo(x1, y1);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: x1, y: y1, button: "left", clickCount: 1 });
      const k = 20; for (let i = 1; i <= k; i++) { const e = ease(i / k); await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: x1 + (x2 - x1) * e, y: y1 + (y2 - y1) * e, button: "left", buttons: 1 }); await sleep((s.ms || 600) / k); }
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: x2, y: y2, button: "left", clickCount: 1 }); mouse = [x2, y2];
    }
    else if (s.eval) await evaluate(s.eval);
    else if (s.mark) marks[s.mark] = +now().toFixed(2);
    else if (s.shot) { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(path.resolve(path.dirname(out), s.shot), Buffer.from(r.data, "base64")); }
  } catch (e) { console.error(`step failed: ${JSON.stringify(s)} -> ${e.message}`); if (s.required) throw e; }
}
const tailMs = Math.max(0, (args.steps ? (+args.tail || 1200) / 1000 : DUR) - (args.steps ? 0 : now())) * 1000;
await sleep(Math.min(tailMs, DUR * 1000));
const total = Math.min(now(), DUR + 2);
await send("Page.stopScreencast").catch(() => {});
await sleep(200);
ws.close();
const exited = new Promise((r) => proc.once("exit", r)); proc.kill(); await Promise.race([exited, sleep(3000)]);

if (!frames.length) { console.error("no frames captured"); process.exit(2); }
// constant-fps mp4 from variable-timestamp frames (concat demuxer with per-frame durations)
let list = "";
for (let i = 0; i < frames.length; i++) {
  const d = (i + 1 < frames.length ? frames[i + 1].t : Math.max(frames[i].t + 1 / FPS, total)) - frames[i].t;
  list += `file '${frames[i].file.replace(/\\/g, "/")}'\nduration ${Math.max(d, 0.001).toFixed(4)}\n`;
}
list += `file '${frames[frames.length - 1].file.replace(/\\/g, "/")}'\n`;
const lst = path.join(tmp, "list.txt"); fs.writeFileSync(lst, list);
execFileSync("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf", `fps=${FPS},scale=${Math.round(W * SCALE / 2) * 2}:${Math.round(H * SCALE / 2) * 2}:flags=lanczos,format=yuv420p`,
  "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", out]);
try { fs.rmSync(tmp, { recursive: true, force: true, maxRetries: 8, retryDelay: 250 }); } catch { /* chrome may still hold the profile; OS temp cleans it */ }
console.log(JSON.stringify({ ok: true, out, frames: frames.length, dur: +total.toFixed(2), marks }));
process.exit(0);
