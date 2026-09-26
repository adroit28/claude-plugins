#!/usr/bin/env python3
"""Narration for a story: one take -> build/take_<tag>.wav, paced -> build/narration_<tag>_p<pace>.wav.

  tts.py <story.vN.json> [--voice free] [--pace 0.93]       one take, then pace
  tts.py <story> --from-take build/take_x.wav --pace 0.90   re-pace an existing take (no API call)
  tts.py --list [--lang en-IN] [--persona storyteller] [--gender male]
  tts.py <story> --audition en-in-tutor-1,en-in-storyteller-11 [--voice-tier free|paid] [--yes-paid]

Voices (--voice):
  free                    Gemini on the free key (GEMINI_FREE_KEY) with en-in-tutor-1, else Kokoro bm_george
  gemini:<voice>          Gemini on the free key          gemini-paid:<voice>   paid key (~Rs 0.65 per 30 s)
  kokoro:<voice>          local Kokoro-82M (setup.sh --kokoro)   say:<voice>   macOS say (last resort; Rishi is en_IN)
  own:<file>              your own recording (m4a/wav/mp3...), pace defaults to 1.0

One API call per run. Updates the story's narration.voice / pace / take / audio unless that
version is already rendered (then run the revise skill, which creates the next version first).
Keys: ~/.config/football-stories/.env (GEMINI_FREE_KEY, GEMINI_PAID_KEY). Stdlib only, except
the kokoro engine, which needs the venv python.
"""
import argparse, base64, json, pathlib, re, shutil, subprocess, sys, urllib.error, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CACHE, Story, duration, gemini_key

API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash-tts"
PAID_USD_PER_M_AUDIO = 9.0      # 2026 price for gemini-3.8-flash-tts output audio; doubles on 1 Jan 2027
USD_INR = 84.0
DEFAULT_GEMINI_VOICE = "en-in-tutor-1"
DEFAULT_KOKORO_VOICE = "bm_george"
KOKORO_DIR = CACHE / "kokoro"
TAIL = 0.75
LIMIT_S = 30.0


# ---------- text
def lexicon(story):
    p = story.shorts / "lexicon.json"
    return json.loads(p.read_text()) if p.exists() else {}

def tts_text(story, engine):
    """Joined script for the voice. `tts` wins over `text`; lexicon respellings fill in names on lines without `tts`."""
    lex = lexicon(story); parts = []
    for l in story.lines:
        t = l.get("tts")
        if t is None:
            t = l["text"]
            for name, e in lex.items():
                if e.get("respell"):
                    t = re.sub(r"\b%s\b" % re.escape(name), e["respell"], t)
        if engine != "gemini":      # only Gemini reads CAPS as emphasis and <tags> as directions
            t = re.sub(r"<[^>]+>", "...", t)
            t = re.sub(r"\b([A-Z]{2,}(?:'[A-Z]+)?)\b", lambda m: m.group(1).capitalize(), t)
        parts.append(t.strip())
    return " ".join(parts)


# ---------- engines
def gemini(text, style, voice, tier, out):
    key, where = gemini_key(tier)
    if not key:
        sys.exit("no %s Gemini key. Put GEMINI_%s_KEY=... in ~/.config/football-stories/.env" % (tier, tier.upper()))
    if where and "gemini-image" in str(where):
        print("note: using the paid key from %s (no GEMINI_PAID_KEY in ~/.config/football-stories/.env)" % where)
    body = {"model": MODEL,
            "input": [{"type": "user_input", "content": [{"type": "text", "text": text,
                       "annotations": [{"type": "speech_metadata", "style": style}]}]}],
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": voice}]}}
    req = urllib.request.Request(API + "/interactions", data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=180)
        resp, headers = json.load(r), dict(r.headers)
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:2000]
        (out.parent / "last-tts-error.json").write_text(json.dumps({"code": e.code, "headers": dict(e.headers), "body": msg}, indent=1))
        if e.code == 429:
            sys.exit("HTTP 429: %s tier rate limit reached (limits are per project, see AI Studio > Rate limits). %s" % (tier, msg[:300]))
        sys.exit("HTTP %s: %s" % (e.code, msg))
    audio = [c["data"] for s in resp.get("steps", []) if s.get("type") == "model_output"
             for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
    (out.parent / "last-tts-headers.json").write_text(json.dumps({"tier": tier, "voice": voice, "headers": headers,
                                                                  "usage": resp.get("usage") or resp.get("usage_metadata")}, indent=1))
    if not audio:
        (out.parent / "last-tts-response.json").write_text(json.dumps(resp, indent=1))
        sys.exit("no audio returned; response saved to build/last-tts-response.json")
    out.write_bytes(base64.b64decode(audio[-1]))
    usage = resp.get("usage") or resp.get("usage_metadata") or {}
    toks = next((v for k, v in usage.items() if "output" in k and isinstance(v, int)), None)
    if tier == "paid" and toks:
        usd = toks * PAID_USD_PER_M_AUDIO / 1e6
        print("paid call: %d output tokens ~ $%.4f (Rs %.2f)" % (toks, usd, usd * USD_INR))
    elif tier == "free":
        print("free tier call (free-tier prompts may be used to improve Google products)")
    print("usage:", json.dumps(usage))

def kokoro(text, voice, out):
    try:
        from kokoro_onnx import Kokoro
        import numpy as np, wave
    except ImportError:
        sys.exit("kokoro-onnx not installed: bash setup.sh --kokoro, then run this with the venv python")
    model, voices = KOKORO_DIR / "kokoro-v1.0.onnx", KOKORO_DIR / "voices-v1.0.bin"
    if not model.exists() or not voices.exists():
        sys.exit("Kokoro model files missing in %s: bash setup.sh --kokoro" % KOKORO_DIR)
    lang = "en-gb" if voice[:1] == "b" else "en-us"
    samples, sr = Kokoro(str(model), str(voices)).create(text, voice=voice, speed=1.0, lang=lang)
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

def say(text, voice, out):
    aiff = out.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    to_wav(aiff, out); aiff.unlink()

def to_wav(src, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "24000", "-sample_fmt", "s16", str(out)], check=True)

def pace(take, p, out):
    if abs(p - 1.0) < 1e-6:
        shutil.copyfile(take, out)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(take), "-af", "atempo=%s" % p, str(out)], check=True)


# ---------- voice resolution
def resolve(spec):
    """--voice value -> (engine, voice, tier, tag)."""
    if spec == "free":
        if gemini_key("free")[0]:
            return "gemini", DEFAULT_GEMINI_VOICE, "free", DEFAULT_GEMINI_VOICE
        if (KOKORO_DIR / "kokoro-v1.0.onnx").exists():
            print("no GEMINI_FREE_KEY configured: using Kokoro (%s). The same Gemini voice on the paid key costs ~Rs 0.65 per 30 s." % DEFAULT_KOKORO_VOICE)
            return "kokoro", DEFAULT_KOKORO_VOICE, None, "kokoro-" + DEFAULT_KOKORO_VOICE
        sys.exit("no free voice available: add GEMINI_FREE_KEY to ~/.config/football-stories/.env or run setup.sh --kokoro")
    eng, _, v = spec.partition(":")
    if eng in ("gemini", "gemini-free"):
        return "gemini", v or DEFAULT_GEMINI_VOICE, "free", v or DEFAULT_GEMINI_VOICE
    if eng == "gemini-paid":
        return "gemini", v or DEFAULT_GEMINI_VOICE, "paid", (v or DEFAULT_GEMINI_VOICE)
    if eng == "kokoro":
        return "kokoro", v or DEFAULT_KOKORO_VOICE, None, "kokoro-" + (v or DEFAULT_KOKORO_VOICE)
    if eng == "say":
        return "say", v or "Rishi", None, "say-" + (v or "Rishi")
    if eng == "own":
        if not v:
            sys.exit("own:<path to your recording>")
        return "own", v, None, "own-" + re.sub(r"[^A-Za-z0-9_-]+", "-", pathlib.Path(v).stem)
    sys.exit("unknown voice %r (free | gemini:<v> | gemini-paid:<v> | kokoro:<v> | say:<v> | own:<file>)" % spec)

def synth(engine, voice, tier, text, style, out):
    if engine == "gemini": gemini(text, style, voice, tier, out)
    elif engine == "kokoro": kokoro(text, voice, out)
    elif engine == "say": say(text, voice, out)
    elif engine == "own": to_wav(pathlib.Path(voice).expanduser(), out)


# ---------- list voices
def list_voices(a):
    tier = "paid" if not gemini_key("free")[0] else "free"
    key = gemini_key(tier)[0]
    if not key:
        sys.exit("listing Gemini voices needs any Gemini key")
    cache = CACHE / ("voices-%s.json" % a.lang)
    if cache.exists():
        vs = json.loads(cache.read_text())
    else:
        vs, tok = [], ""
        while True:
            u = "%s/voices?language_code=%s&page_size=1000%s" % (API, a.lang, "&page_token=" + tok if tok else "")
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"x-goog-api-key": key}), timeout=60))
            vs += r.get("voices", []); tok = r.get("nextPageToken") or r.get("next_page_token")
            if not tok: break
        cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(vs, indent=1))
    for v in vs:
        if a.persona and a.persona.lower() not in (v.get("id", "") + v.get("persona", "")).lower(): continue
        if a.gender and v.get("gender") != a.gender: continue
        print("%-24s %-6s %-6s %s | %s" % (v["id"], v.get("gender", ""), v.get("pitch", ""), v.get("persona", "")[:48], v.get("description", "")[:90]))
    print("(%d voices for %s; metadata call, no charge; cached in %s)" % (len(vs), a.lang, cache))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", nargs="?")
    ap.add_argument("--voice", default="free")
    ap.add_argument("--pace", type=float, help="atempo factor; default 0.93 (1.0 for own recordings)")
    ap.add_argument("--from-take", help="skip synthesis: pace and register this existing take")
    ap.add_argument("--list", action="store_true"); ap.add_argument("--lang", default="en-IN")
    ap.add_argument("--persona"); ap.add_argument("--gender")
    ap.add_argument("--audition", help="comma-separated Gemini voices; one short line each")
    ap.add_argument("--voice-tier", default="free", choices=["free", "paid"])
    ap.add_argument("--line", help="audition text (default: the story's first line)")
    ap.add_argument("--yes-paid", action="store_true", help="the user asked for paid audition takes")
    ap.add_argument("--no-update", action="store_true", help="do not write narration fields into the story")
    a = ap.parse_args()

    if a.list:
        return list_voices(a)
    if not a.story:
        ap.error("story path required")
    st = Story(a.story); st.build.mkdir(exist_ok=True)
    style = st.data["narration"].get("style", "")

    if a.audition:
        names = [v.strip() for v in a.audition.split(",") if v.strip()]
        if a.voice_tier == "paid" and not a.yes_paid:
            sys.exit("paid auditions cost one generation per voice (%d here); rerun with --yes-paid only if the user asked" % len(names))
        text = a.line or st.lines[0].get("tts", st.lines[0]["text"])
        for v in names:
            out = st.build / ("audition_%s.wav" % v)
            gemini(text, style, v, a.voice_tier, out); print("audition", out, "%.2fs" % duration(out))
        return

    if a.from_take:
        take = pathlib.Path(a.from_take)
        if not take.is_absolute():
            take = st.dir / take if (st.dir / take).exists() else take.resolve()
        if not take.exists():
            sys.exit("take not found: %s (give it relative to the story folder, e.g. build/take_<voice>.wav)" % a.from_take)
        m = re.match(r"take_(.+)\.wav$", take.name)
        tag = m.group(1) if m else take.stem
        engine, voice = st.data["narration"].get("voice", {}).get("engine", "unknown"), st.data["narration"].get("voice", {}).get("voice", tag)
        own = engine == "own"
    else:
        engine, voice, tier, tag = resolve(a.voice)
        own = engine == "own"
        take = st.build / ("take_%s.wav" % tag)
        text = tts_text(st, engine)
        print("engine %s  voice %s%s\ntext: %s" % (engine, voice, "  tier " + tier if tier else "", text))
        synth(engine, voice, tier, text, style, take)
        print("take", take, "%.2fs" % duration(take))

    p = a.pace if a.pace is not None else (1.0 if own else 0.93)
    out = st.build / ("narration_%s_p%d.wav" % (tag, round(p * 100)))
    pace(take, p, out)
    d = duration(out); total = d + TAIL
    print("narration", out, "%.2fs at pace %g -> video ~%.2fs" % (d, p, total))
    if total > LIMIT_S:
        n = len(st.script_words()); per = d / max(n, 1)
        print("WARNING: over %.0f s (channel rule 20-30 s). Cut about %d words from the script rather than speeding the voice up."
              % (LIMIT_S, int((total - LIMIT_S) / per) + 1))

    if a.no_update:
        return
    if st.rendered():
        print("note: %s is already rendered, so the story was not updated. Use the revise skill for a new version." % st.mp4.name)
        return
    n = st.data["narration"]
    if not a.from_take:
        n["voice"] = {"engine": engine, "voice": voice if engine != "own" else str(pathlib.Path(voice).expanduser())}
        if engine == "gemini": n["voice"].update({"model": MODEL, "tier": tier})
    n["pace"] = p
    n["take"] = str(take.relative_to(st.dir))
    n["audio"] = str(out.relative_to(st.dir))
    n.pop("words", None)
    st.save(); print("story updated:", st.path.name, "-> next: align.py")


if __name__ == "__main__":
    main()
