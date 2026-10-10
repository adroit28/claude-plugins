// sfxprobe.mjs <anim dir> <duration s>   ->  one JSON line: [{"at":1.2,"src":"boom","vol":0.5}, ...]
// Finds every <Sfx at src> a Scene draws by bundling src/Scene.tsx with the Short's own esbuild and calling
// Scene.Overlays({t}) at many times, walking the returned element tree (children props, no rendering). anim.py's
// sfx check uses it to warn when a sound's peak lands on a HOT caption word. Browser-only modules get tiny shims.
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import fs from "node:fs";
import path from "node:path";

const [dir, durS] = process.argv.slice(2);
const dur = Number(durS) || 60;
const req = createRequire(path.join(dir, "package.json"));
const esbuild = req("esbuild");
const tmp = path.join(dir, "out", "sfxprobe");
fs.mkdirSync(tmp, { recursive: true });
const entry = path.join(tmp, "entry.tsx");
const root = path.join(dir, "src").replaceAll("\\", "/");
fs.writeFileSync(entry, `
import * as Scene from "${root}/Scene";
import { Sfx } from "${root}/kit/props";
const found = new Map();
const walk = (n) => {
  if (!n || typeof n !== "object") return;
  if (Array.isArray(n)) return n.forEach(walk);
  if (n.type === Sfx) { const { at, src, vol } = n.props; found.set(at + ":" + src, { at, src, vol }); return; }
  if (n.props && n.props.children) walk(n.props.children);
};
for (let t = 0; t <= ${dur} + 3.2; t += 0.1) { try { walk(Scene.Overlays({ t })); } catch (e) {} }
process.stdout.write(JSON.stringify([...found.values()].sort((a, b) => a.at - b.at)) + "\\n", () => process.exit(0));
`);
const shim = `
const noop = () => {}; const ctx2d = new Proxy({}, { get: () => noop });
const el = () => ({ style: {}, getContext: () => ctx2d, setAttribute: noop, appendChild: noop, addEventListener: noop, getElementsByTagName: () => [], childNodes: [] });
globalThis.window = globalThis; Object.defineProperty(globalThis, "navigator", { value: { userAgent: "node" }, configurable: true });
globalThis.document = { createElement: el, createElementNS: el, getElementsByTagName: () => [], addEventListener: noop, body: el(), documentElement: el(), fonts: { add: noop, check: () => true } };
globalThis.requestAnimationFrame = noop; globalThis.Image = class {};`;
const out = path.join(tmp, "probe.mjs");
try {
  await esbuild.build({ entryPoints: [entry], bundle: true, outfile: out, format: "esm", platform: "node", jsx: "automatic", logLevel: "silent",
    loader: { ".json": "json", ".png": "dataurl", ".jpg": "dataurl", ".wav": "dataurl", ".ttf": "dataurl" }, banner: { js: shim + "\nimport { createRequire as __cr } from 'node:module'; const require = __cr(import.meta.url);" } });
  await import(pathToFileURL(out).href);
} catch (e) {
  console.error(String(e && e.message || e).split("\n")[0]);
  process.exit(1);
}
