#!/usr/bin/env python3
"""Narration for a story: one take -> build/take_<voice>.wav, paced -> build/narration_<voice>_p<pace>.wav.

  tts.py <story.vN.json> [--voice gemini:en-in-commercial-1] [--pace 1.0]   one take, then pace
  tts.py <story> --audition en-in-commercial-1,en-in-tutor-1,en-in-assistant-9 [--lines 2]
  tts.py <story> --from-take build/take_x.wav --pace 0.97                   re-pace an existing take (no API call)
  tts.py --list [--lang en-IN] [--persona commercial] [--gender male]

Voices (--voice; default = channel.json "voice", else gemini:en-in-commercial-1):
  gemini:<voice>          Gemini TTS on the free key (GEMINI_FREE_KEY)
  gemini-paid:<voice>     same voice on the paid key, only when the user asks (~Rs 0.65 per 30 s)
  own:<file>              the user's own recording (m4a/wav/mp3...)
  say:<voice>             macOS say (last resort; Rishi is en_IN)

The spoken text is each line's `tts`, else its `text`; style = narration.style, else channel.json
"style". Gemini reads CAPS as emphasis and <short pause> / ... as pauses. One API call per run
(an audition is one call per voice). Updates narration.voice / pace / take / audio unless this
version is already rendered (then use the revise skill, which makes the next version first).
Keys: ~/.config/facts-shorts/.env (falls back to ~/.config/football-stories/.env). Stdlib only.
"""
import argparse, base64, json, pathlib, re, shutil, subprocess, sys, urllib.error, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CACHE, Story, channel, duration, gemini_key

API = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash-tts"
PAID_USD_PER_M_AUDIO = 9.0      # 2026 price for gemini-3.8-flash-tts output audio
USD_INR = 88.0
DEFAULT_VOICE = "en-in-commercial-1"


def line_text(l, engine):
    t = l.get("tts") or l["text"]
    if engine != "gemini":      # only Gemini reads CAPS as emphasis and <tags> as directions
        t = re.sub(r"<[^>]+>", "...", t)
        t = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).capitalize(), t)
    return t.strip()


def gemini(text, style, voice, tier, out):
    key, where = gemini_key(tier)
    if not key:
        sys.exit("no %s Gemini key. Put GEMINI_%s_KEY=... in ~/.config/facts-shorts/.env" % (tier, tier.upper()))
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
        (out.parent / "last-tts-error.json").write_text(json.dumps({"code": e.code, "body": msg}, indent=1))
        if e.code == 429:
            sys.exit("HTTP 429: %s tier rate limit reached (limits are per project, see AI Studio > Rate limits). %s" % (tier, msg[:300]))
        sys.exit("HTTP %s: %s" % (e.code, msg))
    audio = [c["data"] for s in resp.get("steps", []) if s.get("type") == "model_output"
             for c in s.get("content", []) if c.get("type") == "audio" and c.get("data")]
    usage = resp.get("usage") or resp.get("usage_metadata") or {}
    (out.parent / "last-tts-headers.json").write_text(json.dumps({"tier": tier, "voice": voice, "usage": usage}, indent=1))
    if not audio:
        (out.parent / "last-tts-response.json").write_text(json.dumps(resp, indent=1))
        sys.exit("no audio returned; response saved to build/last-tts-response.json")
    out.write_bytes(base64.b64decode(audio[-1]))
    toks = next((v for k, v in usage.items() if "output" in k and isinstance(v, int)), None)
    if tier == "paid" and toks:
        usd = toks * PAID_USD_PER_M_AUDIO / 1e6
        print("paid call: %d output tokens ~ $%.4f (Rs %.2f)" % (toks, usd, usd * USD_INR))
    elif tier == "free":
        print("free tier call (free-tier prompts may be used to improve Google products)")


def to_wav(src, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "24000", "-sample_fmt", "s16", str(out)], check=True)


def say(text, voice, out):
    aiff = out.with_suffix(".aiff")
    subprocess.run(["say", "-v", voice, "-o", str(aiff), text], check=True)
    to_wav(aiff, out); aiff.unlink()


def pace(take, p, out):
    if abs(p - 1.0) < 1e-6:
        shutil.copyfile(take, out)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(take), "-af", "atempo=%s" % p, str(out)], check=True)


def resolve(spec):
    """--voice value -> (engine, voice, tier, tag)."""
    eng, _, v = spec.partition(":")
    if eng in ("gemini", "gemini-free"):
        return "gemini", v or DEFAULT_VOICE, "free", v or DEFAULT_VOICE
    if eng == "gemini-paid":
        return "gemini", v or DEFAULT_VOICE, "paid", (v or DEFAULT_VOICE)
    if eng == "say":
        return "say", v or "Rishi", None, "say-" + (v or "Rishi")
    if eng == "own":
        if not v:
            sys.exit("own:<path to your recording>")
        return "own", v, None, "own-" + re.sub(r"[^A-Za-z0-9_-]+", "-", pathlib.Path(v).stem)
    sys.exit("unknown voice %r (gemini:<v> | gemini-paid:<v> | own:<file> | say:<v>)" % spec)


def list_voices(a):
    tier = "free" if gemini_key("free")[0] else "paid"
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
    ap.add_argument("--voice"); ap.add_argument("--pace", type=float, help="atempo factor; default channel.json pace (1.0)")
    ap.add_argument("--from-take", help="skip synthesis: pace and register this existing take")
    ap.add_argument("--list", action="store_true"); ap.add_argument("--lang", default="en-IN")
    ap.add_argument("--persona"); ap.add_argument("--gender")
    ap.add_argument("--audition", help="comma-separated Gemini voices; the first --lines lines each (free key)")
    ap.add_argument("--lines", type=int, default=2, help="lines per audition (default 2)")
    ap.add_argument("--voice-tier", default="free", choices=["free", "paid"])
    ap.add_argument("--yes-paid", action="store_true", help="the user asked for paid audition takes")
    ap.add_argument("--no-update", action="store_true", help="do not write narration fields into the story")
    a = ap.parse_args()

    if a.list:
        return list_voices(a)
    if not a.story:
        ap.error("story path required")
    st = Story(a.story); st.build.mkdir(exist_ok=True)
    ch = channel(st.root)
    style = st.data["narration"].get("style") or ch["style"]
    limit = st.data.get("length", {}).get("max", ch["length"]["max"])

    if a.audition:
        names = [v.strip() for v in a.audition.split(",") if v.strip()]
        if a.voice_tier == "paid" and not a.yes_paid:
            sys.exit("paid auditions cost one generation per voice (%d here); rerun with --yes-paid only if the user asked" % len(names))
        text = " ".join(line_text(l, "gemini") for l in st.lines[:a.lines])
        print("audition text: %s" % text)
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
        engine, voice, tier = None, None, None
    else:
        engine, voice, tier, tag = resolve(a.voice or ch["voice"])
        take = st.build / ("take_%s.wav" % tag)
        if take.exists():
            n = 2
            while (st.build / ("take_%s_%d.wav" % (tag, n))).exists(): n += 1
            tag = "%s_%d" % (tag, n); take = st.build / ("take_%s.wav" % tag)   # never overwrite a take
        text = " ".join(line_text(l, engine) for l in st.lines)
        print("engine %s  voice %s%s\ntext: %s" % (engine, voice, "  tier " + tier if tier else "", text))
        if engine == "gemini": gemini(text, style, voice, tier, take)
        elif engine == "say": say(text, voice, take)
        else: to_wav(pathlib.Path(voice).expanduser(), take)
        print("take", take, "%.2fs" % duration(take))

    p = a.pace if a.pace is not None else ch["pace"]
    out = st.build / ("narration_%s_p%d.wav" % (tag, round(p * 100)))
    pace(take, p, out)
    d = duration(out)
    print("narration", out, "%.2fs at pace %g (channel length %s-%s s; the 3 s like & subscribe card comes on top)"
          % (d, p, ch["length"]["min"], limit))
    if d > limit:
        n = len(st.script_words()); per = d / max(n, 1)
        print("WARNING: over %g s. Cut about %d words from the script rather than speeding the voice up." % (limit, int((d - limit) / per) + 1))
    elif d < ch["length"]["min"] - 3:
        print("note: under %g s; fine if the story is complete." % ch["length"]["min"])

    if a.no_update:
        return
    if st.rendered():
        print("note: %s is already rendered, so the story was not updated. Use the revise skill for a new version." % st.mp4.name)
        return
    n = st.data["narration"]
    if engine:
        n["voice"] = {"engine": engine, "voice": voice if engine != "own" else str(pathlib.Path(voice).expanduser())}
        if engine == "gemini": n["voice"].update({"model": MODEL, "tier": tier})
    n["pace"] = p
    n["take"] = str(take.relative_to(st.dir))
    n["audio_raw"] = str(out.relative_to(st.dir))
    for k in ("audio", "words"): n.pop(k, None)
    st.save(); print("story updated:", st.path.name, "-> next: segalign.py")


if __name__ == "__main__":
    main()
