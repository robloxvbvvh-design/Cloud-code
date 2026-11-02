#!/usr/bin/env python3
"""video-forge: script -> storyboard -> voiceover -> SFX -> finished video.

Subcommands (all take a project directory that contains storyboard.json):
  check                       what is available (ffmpeg, TTS providers, fonts)
  voices  [--provider P] [--lang ru]   list voices for a provider
  tts     PROJECT             synthesize narration for every scene
  sfx     PROJECT             generate/collect sound effects used by scenes
  plan    PROJECT             compute timings, write storyboard.md
  render  PROJECT             build every scene clip and the final video
  all     PROJECT             tts + sfx + plan + render
  sfx-list                    names of built-in synthesized sound effects

Only ffmpeg is required. ElevenLabs/OpenAI are used when their API keys are set;
edge-tts (pip install edge-tts) is a free online fallback; espeak-ng is an
offline fallback; without any of them silent placeholders keep the pipeline going.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path

if os.environ.get("SSL_CERT_FILE"):  # let edge-tts trust a corporate/proxy CA bundle
    try:
        import certifi
        certifi.where = lambda: os.environ["SSL_CERT_FILE"]
    except ImportError:
        pass

# --------------------------------------------------------------------------- #
# Voices
# --------------------------------------------------------------------------- #
ELEVEN_VOICES = {  # classic premade ElevenLabs voices (name -> voice_id)
    "adam": "pNInz6obpgDQGcFmaJgB",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "antoni": "ErXwobaYiN019PkySvjV",
    "bella": "EXAVITQu4vr4xnSDxPL",
    "josh": "TxGEqnHWrfWFTfGW9XjX",
    "arnold": "VR6AewLTigWG4xSOukaG",
    "domi": "AZnzlk1XvdvUeBnXmlld",
    "elli": "MF3mGyEYCl7XYWbV9V3O",
    "sam": "yoZ06aMxZJJ28mfd3POQ",
}
OPENAI_VOICES = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
# Closest free edge-tts voice for each ElevenLabs name, per language.
EDGE_FALLBACK = {
    "ru": {"male": "ru-RU-DmitryNeural", "female": "ru-RU-SvetlanaNeural"},
    "en": {"male": "en-US-AndrewNeural", "female": "en-US-AvaNeural"},
    "uk": {"male": "uk-UA-OstapNeural", "female": "uk-UA-PolinaNeural"},
}
FEMALE_NAMES = {"rachel", "bella", "domi", "elli", "nova", "shimmer", "coral", "sage"}

# Named voice catalog (120 Russian-speaking voices: base voices, speaking manners, characters)
CATALOG_PATH = Path(__file__).resolve().parent.parent / "voices" / "catalog.json"


def _pitch(k: float, extra: str = "") -> str:
    return f"asetrate=44100*{k},aresample=44100,atempo={1 / k:.4f}" + ("," + extra if extra else "")


# Post-processing voice effects (ffmpeg audio filters), combinable: "deep,robot"
VOICE_EFFECTS = {
    "robot": "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75,"
             "aecho=0.8:0.5:15:0.3",
    "radio": "highpass=f=300,lowpass=f=3400,acompressor=threshold=0.1:ratio=6,volume=1.4",
    "phone": "highpass=f=400,lowpass=f=3000,aresample=8000,aresample=44100",
    "giant": _pitch(0.72, "aecho=0.8:0.6:60:0.3"),
    "gnome": _pitch(1.45),
    "chipmunk": _pitch(1.75),
    "monster": _pitch(0.6, "acrusher=bits=8:mix=0.25:mode=log,aecho=0.8:0.5:40:0.3"),
    "alien": _pitch(1.12, "vibrato=f=8:d=0.6,flanger=delay=3:depth=4:speed=1"),
    "cave": "aecho=0.8:0.85:280|560:0.45|0.25",
    "underwater": "lowpass=f=700,vibrato=f=3:d=0.25",
    "megaphone": "highpass=f=600,lowpass=f=3800,acrusher=bits=9:mix=0.35:mode=log,volume=1.3",
    "ghost": _pitch(0.92, "tremolo=f=5:d=0.35,aecho=0.8:0.9:450|900:0.45|0.3"),
    "elder": "vibrato=f=5.5:d=0.18,lowpass=f=6000",
    "child": _pitch(1.28),
    "villain": _pitch(0.82, "aecho=0.8:0.7:90:0.25"),
    "cartoon": _pitch(1.35, "vibrato=f=6:d=0.1"),
    "stadium": "aecho=0.8:0.7:110|230|350:0.35|0.25|0.15",
    "space": "aecho=0.8:0.9:900|1400:0.35|0.25,chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|1.3",
    "deep": _pitch(0.86),
    "bright": _pitch(1.12),
}


def _norm(name: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(name).lower().replace("ё", "е")).strip()


def load_catalog() -> list[dict]:
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []


def catalog_entry(name: str) -> dict | None:
    n = _norm(name)
    return next((c for c in load_catalog() if _norm(c["name"]) == n), None) if n else None


def expand_voice(base: dict, override: dict | None = None) -> dict:
    """Merge voice settings; a catalog name ("Артём энергичный", "Робот") expands to its
    provider/voice/rate/pitch/effect. Explicit fields in `override` still win."""
    override = override or {}
    name = override.get("voice", base.get("voice", ""))
    entry = catalog_entry(name)
    if not entry:
        return {**base, **override}
    keep = {k: v for k, v in base.items() if k not in ("provider", "voice", "rate", "pitch", "effect", "used")}
    fields = {k: entry[k] for k in ("provider", "voice", "rate", "pitch", "effect") if entry.get(k) is not None}
    return {**keep, **fields, **{k: v for k, v in override.items() if k != "voice"}, "label": entry["name"]}


FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

# --------------------------------------------------------------------------- #
# Built-in sound effects, synthesized with ffmpeg (no downloads needed)
# --------------------------------------------------------------------------- #
SFX_LIB = {
    "whoosh": ("anoisesrc=color=pink:d=0.9:a=0.9",
               "highpass=f=300,lowpass=f=4000,afade=t=in:d=0.45:curve=exp,afade=t=out:st=0.45:d=0.45"),
    "swoosh": ("anoisesrc=color=white:d=0.5:a=0.6",
               "bandpass=f=2500:w=2000,afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.3"),
    "impact": ("aevalsrc='0.9*sin(2*PI*(70-40*t)*t)*exp(-5*t)+0.3*(random(0)*2-1)*exp(-30*t)':d=1.2", ""),
    "boom": ("aevalsrc='sin(2*PI*(45-20*t)*t)*exp(-2.5*t)':d=2.5", "lowpass=f=300"),
    "ding": ("aevalsrc='0.5*sin(2*PI*1320*t)*exp(-3*t)+0.25*sin(2*PI*2640*t)*exp(-5*t)':d=1.5", ""),
    "chime": ("aevalsrc='0.3*sin(2*PI*1047*t)*exp(-2*t)+0.3*sin(2*PI*1319*(t-0.12))*gt(t,0.12)*exp(-2*(t-0.12))"
              "+0.3*sin(2*PI*1568*(t-0.24))*gt(t,0.24)*exp(-2*(t-0.24))':d=2", ""),
    "pop": ("aevalsrc='0.8*sin(2*PI*(900-4000*t)*t)*exp(-35*t)':d=0.2", ""),
    "click": ("aevalsrc='(random(0)*2-1)*exp(-400*t)':d=0.05", "highpass=f=1500"),
    "typing": ("aevalsrc='0.5*(random(0)*2-1)*lt(mod(t+0.03*sin(7*t),0.11),0.012)':d=2", "highpass=f=1200"),
    "riser": ("aevalsrc='0.5*(t/2)*sin(2*PI*(200*t+450*t*t))':d=2", "afade=t=out:st=1.85:d=0.15"),
    "drop": ("aevalsrc='0.6*sin(2*PI*(1200*t-280*t*t))*exp(-1.5*t)':d=2", ""),
    "glitch": ("aevalsrc='0.5*sgn(sin(2*PI*(80+400*random(0))*t))*lt(mod(t,0.09),0.05)':d=0.6", "lowpass=f=5000"),
    "heartbeat": ("aevalsrc='sin(2*PI*55*t)*(exp(-25*mod(t,0.9))+0.7*exp(-25*mod(t-0.22,0.9))*gt(t,0.22))':d=2.7",
                  "lowpass=f=150"),
    "applause": ("anoisesrc=color=white:d=3:a=0.5",
                 "bandpass=f=2000:w=3000,tremolo=f=11:d=0.8,afade=t=in:d=0.3,afade=t=out:st=2.2:d=0.8"),
    "wind": ("anoisesrc=color=brown:d=6:a=0.8", "lowpass=f=600,tremolo=f=0.3:d=0.6,afade=t=in:d=1,afade=t=out:st=5:d=1"),
    "rain": ("anoisesrc=color=pink:d=6:a=0.5", "highpass=f=800,lowpass=f=7000,afade=t=in:d=1,afade=t=out:st=5:d=1"),
    "roar": ("anoisesrc=color=brown:d=1.8:a=1",
             "bandpass=f=260:w=320,tremolo=f=26:d=0.6,volume=14,afade=t=in:d=0.25,afade=t=out:st=0.8:d=1.0"),
    "meow": ("aevalsrc='sin(PI*t/0.6)*(0.5*sin(2*PI*(550*t+95.5*(1-cos(5.236*t))))"
             "+0.25*sin(4*PI*(550*t+95.5*(1-cos(5.236*t))))+0.12*sin(6*PI*(550*t+95.5*(1-cos(5.236*t)))))':d=0.6", ""),
    "footstep": ("aevalsrc='sin(2*PI*(55-25*t)*t)*exp(-9*t)+0.2*(random(0)*2-1)*exp(-40*t)':d=0.6", "lowpass=f=400"),
    "portal": ("aevalsrc='0.4*sin(2*PI*(150*t+300*t*t))*(0.6+0.4*sin(2*PI*9*t))':d=1.6",
               "aecho=0.8:0.7:60:0.4,afade=t=in:d=0.3,afade=t=out:st=1.2:d=0.4"),
    "camera": ("aevalsrc='(random(0)*2-1)*(exp(-120*t)+0.8*exp(-120*(t-0.09))*gt(t,0.09))':d=0.3", "bandpass=f=3000:w=4000"),
}
# Music beds (chords of sines with slow movement)
MUSIC_LIB = {
    "pad": "0.12*(sin(2*PI*220*t)+sin(2*PI*277.18*t)+sin(2*PI*329.63*t))*(0.7+0.3*sin(2*PI*0.1*t))",
    "dark": "0.14*(sin(2*PI*110*t)+sin(2*PI*130.81*t)+0.6*sin(2*PI*164.81*t))*(0.6+0.4*sin(2*PI*0.07*t))",
    "bright": "0.10*(sin(2*PI*261.63*t)+sin(2*PI*329.63*t)+sin(2*PI*392*t)+0.5*sin(2*PI*523.25*t))*(0.75+0.25*sin(2*PI*0.2*t))",
}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str], quiet: bool = True) -> None:
    res = subprocess.run(cmd, capture_output=quiet, text=True)
    if res.returncode != 0:
        tail = (res.stderr or "")[-2500:] if quiet else ""
        die(f"command failed: {' '.join(cmd[:6])} ...\n{tail}")


def ffmpeg(*args: str) -> None:
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args])


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def load(project: Path) -> dict:
    sb = project / "storyboard.json"
    if not sb.exists():
        die(f"{sb} not found")
    data = json.loads(sb.read_text(encoding="utf-8"))
    if not data.get("scenes"):
        die("storyboard.json has no scenes")
    for i, s in enumerate(data["scenes"], 1):
        s.setdefault("id", i)
    return data


def save(project: Path, data: dict) -> None:
    (project / "storyboard.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def detect_lang(text: str) -> str:
    if re.search(r"[іїєґ]", text, re.I):
        return "uk"
    return "ru" if re.search(r"[а-яё]", text, re.I) else "en"


def font_path(data: dict | None = None) -> str:
    if data and data.get("font") and Path(data["font"]).exists():
        return data["font"]
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    out = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True, text=True).stdout
    return out or "DejaVuSans-Bold.ttf"


def resolution(data: dict) -> tuple[int, int]:
    preset = {"9:16": "1080x1920", "16:9": "1920x1080", "1:1": "1080x1080", "4:5": "1080x1350"}
    res = preset.get(str(data.get("format", "")), data.get("resolution", "1080x1920"))
    w, h = (int(x) for x in res.lower().split("x"))
    return w, h


def has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def http_post(url: str, headers: dict, body: dict, out: Path) -> None:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            out.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        die(f"{url} -> HTTP {e.code}: {e.read().decode(errors='ignore')[:500]}")


# --------------------------------------------------------------------------- #
# check / voices
# --------------------------------------------------------------------------- #
def available_providers() -> list[str]:
    p = []
    if os.environ.get("ELEVENLABS_API_KEY"):
        p.append("elevenlabs")
    if os.environ.get("OPENAI_API_KEY"):
        p.append("openai")
    if has_module("edge_tts"):
        p.append("edge")
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        p.append("espeak")
    p.append("silent")
    return p


def cmd_check(_args) -> None:
    print("ffmpeg      :", shutil.which("ffmpeg") or "MISSING (required)")
    print("ffprobe     :", shutil.which("ffprobe") or "MISSING (required)")
    print("font        :", font_path())
    print("ElevenLabs  :", "yes (ELEVENLABS_API_KEY set)" if os.environ.get("ELEVENLABS_API_KEY") else "no  (set ELEVENLABS_API_KEY)")
    print("OpenAI TTS  :", "yes (OPENAI_API_KEY set)" if os.environ.get("OPENAI_API_KEY") else "no  (set OPENAI_API_KEY)")
    print("edge-tts    :", "yes" if has_module("edge_tts") else "no  (pip install edge-tts)")
    print("espeak      :", shutil.which("espeak-ng") or shutil.which("espeak") or "no")
    print("providers   :", ", ".join(available_providers()))


def cmd_voices(args) -> None:
    if not args.provider:  # named catalog
        q = _norm(args.search or "")
        rows = [c for c in load_catalog()
                if (not args.gender or c["gender"] == args.gender[0].lower())
                and (not args.group or c["group"] == args.group)
                and (not q or q in _norm(c["name"] + " " + c["desc"] + " " + c["effect"]))]
        for c in rows:
            print(f"{c['name']:<26} {'муж' if c['gender'] == 'm' else 'жен'}  {c['group']:<9} {c['desc']}")
        total = len(load_catalog())
        print(f"\n{len(rows)} of {total} catalog voices (all speak Russian). Also: --provider edge "
              f"(300+ voices, 140+ languages), elevenlabs, openai. Effects: {', '.join(VOICE_EFFECTS)}")
        return
    prov = args.provider
    if prov == "elevenlabs":
        key = os.environ.get("ELEVENLABS_API_KEY")
        if key:
            req = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    for v in json.load(r).get("voices", []):
                        lab = v.get("labels") or {}
                        print(f"{v['name']:<28} {v['voice_id']}  {lab.get('gender', '')} {lab.get('accent', '')}")
                return
            except Exception as e:  # fall through to static list
                print(f"(could not query API: {e})")
        for n, vid in ELEVEN_VOICES.items():
            print(f"{n.capitalize():<10} {vid}")
    elif prov == "openai":
        print("\n".join(OPENAI_VOICES))
    elif prov == "edge":
        import edge_tts
        voices = asyncio.run(edge_tts.list_voices())
        for v in voices:
            if args.lang and not v["Locale"].lower().startswith(args.lang.lower()):
                continue
            ml = "  multilingual (speaks Russian too)" if "Multilingual" in v["ShortName"] else ""
            print(f"{v['ShortName']:<40} {v['Gender']:<7} {v['LocaleName']}{ml}")
    elif prov == "espeak":
        run([shutil.which("espeak-ng") or "espeak", "--voices"], quiet=False)
    else:
        print("silent: placeholder audio only")


# --------------------------------------------------------------------------- #
# TTS
# --------------------------------------------------------------------------- #
def resolve_voice(cfg: dict, text: str) -> tuple[str, str]:
    """Return (provider, voice) honoring the request and falling back sensibly."""
    want_p = (cfg.get("provider") or "auto").lower()
    voice = str(cfg.get("voice") or "")
    avail = available_providers()
    lang = cfg.get("lang") or detect_lang(text)
    if want_p == "auto":
        if voice.lower() in ELEVEN_VOICES or re.fullmatch(r"[A-Za-z0-9]{20}", voice):
            want_p = "elevenlabs"
        elif voice.lower() in OPENAI_VOICES:
            want_p = "openai"
        elif re.match(r"[a-z]{2}-[A-Z]{2}-", voice):
            want_p = "edge"
        else:
            want_p = avail[0]
    if want_p in avail:
        return want_p, voice
    # requested provider unavailable -> closest alternative
    gender = "female" if voice.lower() in FEMALE_NAMES or "female" in voice.lower() else "male"
    for alt in avail:
        if alt == "edge":
            v = EDGE_FALLBACK.get(lang, EDGE_FALLBACK["en"])[gender]
            print(f"  ! {want_p} unavailable -> edge-tts voice {v}")
            return "edge", v
        if alt in ("elevenlabs", "openai"):
            print(f"  ! {want_p} unavailable -> {alt}")
            return alt, ("adam" if alt == "elevenlabs" else ("nova" if gender == "female" else "onyx"))
        if alt == "espeak":
            print(f"  ! {want_p} unavailable -> espeak")
            return "espeak", lang
    print(f"  ! no TTS available -> silent placeholder")
    return "silent", ""


def tts_one(provider: str, voice: str, text: str, cfg: dict, out: Path) -> None:
    tmp = out.with_suffix(".raw")
    if provider == "elevenlabs":
        vid = ELEVEN_VOICES.get(voice.lower(), voice) or ELEVEN_VOICES["adam"]
        body = {
            "text": text,
            "model_id": cfg.get("model", "eleven_multilingual_v2"),
            "voice_settings": {"stability": cfg.get("stability", 0.45),
                               "similarity_boost": cfg.get("similarity", 0.8),
                               "style": cfg.get("style", 0.2), "use_speaker_boost": True},
        }
        http_post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
                  {"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"}, body, tmp)
    elif provider == "openai":
        body = {"model": cfg.get("model", "gpt-4o-mini-tts"), "voice": voice or "onyx", "input": text,
                "response_format": "mp3"}
        if cfg.get("instructions"):
            body["instructions"] = cfg["instructions"]
        http_post("https://api.openai.com/v1/audio/speech",
                  {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
                  body, tmp)
    elif provider == "edge":
        import edge_tts
        kw = {}
        if cfg.get("rate"):
            kw["rate"] = cfg["rate"]  # e.g. "+10%"
        if cfg.get("pitch"):
            kw["pitch"] = cfg["pitch"]  # e.g. "-5Hz"
        asyncio.run(edge_tts.Communicate(text, voice or "en-US-AndrewNeural", **kw).save(str(tmp)))
    elif provider == "espeak":
        exe = shutil.which("espeak-ng") or "espeak"
        run([exe, "-v", voice or "en", "-s", "160", "-w", str(tmp), text])
    else:  # silent placeholder sized to reading speed (~2.5 words/s)
        secs = max(1.5, len(text.split()) / 2.5)
        ffmpeg("-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono", "-t", f"{secs:.2f}", "-f", "wav", str(tmp))
    # normalize to 44.1k mono wav, trim leading/trailing silence, apply voice effects
    effects = cfg.get("effect") or ""
    effects = effects.split(",") if isinstance(effects, str) else list(effects)
    fx = []
    for e in (x.strip() for x in effects if x and x.strip()):
        if e not in VOICE_EFFECTS:
            die(f"unknown voice effect '{e}'. available: {', '.join(VOICE_EFFECTS)}")
        fx.append(VOICE_EFFECTS[e])
    chain = ("aresample=44100,silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
             "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
             + "".join(f + "," for f in fx) + "loudnorm=I=-16:TP=-1.5:LRA=11") if provider != "silent" else "anull"
    ffmpeg("-i", str(tmp), "-af", chain, "-ar", "44100", "-ac", "1", str(out))
    tmp.unlink(missing_ok=True)


def cmd_tts(args) -> None:
    project = Path(args.project)
    data = load(project)
    cfg = expand_voice({k: v for k, v in data.get("voice", {}).items() if k != "used"})
    vdir = project / "audio" / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    all_text = " ".join(s.get("narration", "") for s in data["scenes"])
    default = resolve_voice(cfg, all_text)
    print(f"TTS provider: {default[0]}  voice: {default[1] or '-'}")
    characters = data.get("characters", {})  # {"Name": {"provider": .., "voice": ..}}
    resolved: dict[str, tuple[str, str]] = {}
    used: dict[str, str] = {}
    for s in data["scenes"]:
        text = (s.get("narration") or "").strip()
        out = vdir / f"scene_{s['id']:02d}.wav"
        if not text:
            s.pop("voice_file", None)
            s["voice_duration"] = 0
            continue
        # per-scene voice: "speaker" picks a character, a "voice" dict overrides fields
        override = dict(characters.get(s.get("speaker", ""), {}))
        if isinstance(s.get("voice"), dict):
            override.update(s["voice"])
        scfg = expand_voice(cfg, override) if override else cfg
        if override:
            key = json.dumps(override, sort_keys=True, ensure_ascii=False)
            if key not in resolved:
                resolved[key] = resolve_voice(scfg, text)
            provider, voice = resolved[key]
        else:
            provider, voice = default
        used[s.get("speaker") or "narrator"] = f"{provider}:{voice}" + (f" ({scfg['label']})" if scfg.get("label") else "")
        sig = {k: scfg.get(k) for k in ("rate", "pitch", "effect", "model", "stability", "style", "instructions")}
        cache_key = f"{provider}:{voice}|{json.dumps(sig, sort_keys=True, ensure_ascii=False)}|{text}"
        if out.exists() and not args.force and s.get("voice_text") == cache_key:
            print(f"  scene {s['id']}: cached")
        else:
            print(f"  scene {s['id']}: synthesizing ({len(text)} chars)")
            err = None
            for attempt in range(8):  # online TTS hiccups are common; retry before giving up
                try:
                    tts_one(provider, voice, text, scfg, out)
                    err = None
                    break
                except (Exception, SystemExit) as e:
                    err = e
                    time.sleep(1.0 + attempt * 0.5)
            if err is not None and provider == "edge" and not s.get("speaker"):  # other voice, same locale
                loc = voice[:5]
                alts = [v for g in EDGE_FALLBACK.values() for v in g.values() if v.startswith(loc) and v != voice]
                for alt in alts:
                    try:
                        tts_one("edge", alt, text, scfg, out)
                        print(f"  ! {voice} failed for this scene -> used {alt}")
                        err = None
                        break
                    except (Exception, SystemExit):
                        pass
            if err is not None:
                e = err
                print(f"  ! {provider} failed ({str(e).strip()[:200]}) -> silent placeholder; fix and rerun with --force")
                tts_one("silent", "", text, scfg, out)
                cache_key = ""  # do not cache the placeholder
        s["voice_file"] = str(out.relative_to(project))
        s["voice_text"] = cache_key
        s["voice_duration"] = round(duration(out), 3)
    data.setdefault("voice", {})["used"] = used or {"narrator": f"{default[0]}:{default[1]}"}
    save(project, data)


# --------------------------------------------------------------------------- #
# SFX
# --------------------------------------------------------------------------- #
def sfx_file(project: Path, spec: dict) -> Path:
    sdir = project / "audio" / "sfx"
    sdir.mkdir(parents=True, exist_ok=True)
    name = spec.get("name", "")
    if spec.get("file"):
        p = Path(spec["file"])
        return p if p.is_absolute() else project / p
    if spec.get("prompt"):  # AI-generated effect (ElevenLabs), else nearest built-in
        slug = re.sub(r"[^a-z0-9]+", "_", spec["prompt"].lower())[:40]
        out = sdir / f"gen_{slug}.mp3"
        if out.exists():
            return out
        if os.environ.get("ELEVENLABS_API_KEY"):
            body = {"text": spec["prompt"]}
            if spec.get("length"):
                body["duration_seconds"] = spec["length"]
            http_post("https://api.elevenlabs.io/v1/sound-generation",
                      {"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "Content-Type": "application/json"}, body, out)
            return out
        name = name or "whoosh"
        print(f"  ! no ELEVENLABS_API_KEY for '{spec['prompt']}' -> built-in '{name}'")
    if name not in SFX_LIB:
        die(f"unknown sfx '{name}'. built-ins: {', '.join(SFX_LIB)}")
    out = sdir / f"{name}.wav"
    if not out.exists():
        src, flt = SFX_LIB[name]
        a = ["-f", "lavfi", "-i", src + (":s=44100" if src.startswith("aevalsrc") else ":r=44100")]
        if flt:
            a += ["-af", flt]
        ffmpeg(*a, "-ac", "1", str(out))
    return out


def cmd_sfx(args) -> None:
    project = Path(args.project)
    data = load(project)
    for s in data["scenes"]:
        for spec in s.get("sfx", []):
            f = sfx_file(project, spec)
            spec["resolved"] = str(f.relative_to(project)) if f.is_relative_to(project) else str(f)
            print(f"  scene {s['id']}: {spec.get('name') or spec.get('prompt') or spec.get('file')} -> {spec['resolved']}")
    save(project, data)


def cmd_sfx_list(_args) -> None:
    print("sound effects:", ", ".join(SFX_LIB))
    print("music beds   :", ", ".join(MUSIC_LIB))


# --------------------------------------------------------------------------- #
# plan (timings + storyboard.md)
# --------------------------------------------------------------------------- #
LEAD_IN = 0.35   # seconds of silence before narration in each scene
TAIL = 0.45      # seconds after narration


def scene_duration(s: dict) -> float:
    vd = float(s.get("voice_duration") or 0)
    need = vd + LEAD_IN + TAIL if vd else 0
    return round(max(need, float(s.get("duration") or 0), 1.5), 3)


def cmd_plan(args) -> None:
    project = Path(args.project)
    data = load(project)
    t = 0.0
    w, h = resolution(data)
    lines = [f"# {data.get('title', 'Video')}", "",
             f"Format: {w}x{h} · {data.get('fps', 30)} fps · voice: "
             f"{data.get('voice', {}).get('used', data.get('voice', {}))}", "",
             "| # | Time | Visual | On-screen text | Narration | SFX |", "|---|---|---|---|---|---|"]
    for s in data["scenes"]:
        d = scene_duration(s)
        s["start"], s["end"] = round(t, 3), round(t + d, 3)
        v = s.get("visual", {})
        vis = v.get("type", "text") + (f": {v.get('description') or v.get('source', '')}" if (v.get("description") or v.get("source")) else "")
        sfx = ", ".join(f"{x.get('name') or x.get('prompt') or Path(x.get('file', '')).name}@{x.get('at', 0)}s" for x in s.get("sfx", []))
        cell = lambda x: str(x or "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {s['id']} | {t:.1f}–{t + d:.1f}s | {cell(vis)} | {cell(v.get('caption'))} | "
                     f"{cell(s.get('narration'))} | {cell(sfx)} |")
        t += d
    lines += ["", f"**Total: {t:.1f} s**", ""]
    if (project / "storyboard.png").exists():
        lines += ["![storyboard](storyboard.png)", ""]
    (project / "storyboard.md").write_text("\n".join(lines), encoding="utf-8")
    save(project, data)
    print("\n".join(lines))


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+")


def wrap(text: str, fontsize: int, width: int) -> str:
    text = re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", text or "")).strip()  # drawtext has no color-emoji support
    chars = max(8, int(width * 0.78 / (fontsize * 0.6)))
    return "\n".join(textwrap.wrap(text, chars)) if text else ""


def drawtext(textfile: Path, font: str, size: int, color: str, y: str, box: bool,
             enable: str | None = None) -> str:
    p = (f"drawtext=fontfile='{font}':textfile='{textfile}':fontsize={size}:fontcolor={color}"
         f":line_spacing={int(size * 0.25)}:x=(w-text_w)/2:y={y}:borderw={max(2, size // 18)}:bordercolor=black@0.85")
    if box:
        p += f":box=1:boxcolor=black@0.45:boxborderw={size // 2}"
    if enable:
        p += f":enable='{enable}'"
    return p


def subtitle_chunks(text: str, max_words: int = 6) -> list[str]:
    parts = re.split(r"(?<=[.!?…,;:—])\s+", text.strip())
    out = []
    for p in parts:
        words = p.split()
        while words:
            out.append(" ".join(words[:max_words]))
            words = words[max_words:]
    return [c for c in out if c]


def build_scene(project: Path, data: dict, s: dict, font: str) -> Path:
    w, h = resolution(data)
    fps = int(data.get("fps", 30))
    d = scene_duration(s)
    v = s.get("visual", {})
    vt = v.get("type", "text")
    work = project / "build"
    work.mkdir(exist_ok=True)
    out = work / f"scene_{s['id']:02d}.mp4"
    inputs: list[str] = []
    pal = data.get("palette", ["#0f2027", "#2c5364"])
    c1, c2 = v.get("colors", [v.get("bg", pal[0]), pal[-1] if len(pal) > 1 else pal[0]])[:2]
    c1, c2 = c1.replace("#", "0x"), c2.replace("#", "0x")
    frames = int(d * fps) + 1

    src = v.get("source")
    srcp = (project / src) if src and not Path(src).is_absolute() else Path(src or "")
    if vt == "image" and srcp.exists():
        motion = v.get("motion", "zoom_in")
        z = {"zoom_in": "min(1+0.0009*on,1.25)", "zoom_out": "max(1.25-0.0009*on,1)", "none": "1"}.get(motion, "min(1+0.0009*on,1.25)")
        x = {"pan_left": f"(iw-iw/zoom)*(1-on/{frames})", "pan_right": f"(iw-iw/zoom)*on/{frames}"}.get(motion, "iw/2-(iw/zoom/2)")
        if motion in ("pan_left", "pan_right"):
            z = "1.2"
        inputs = ["-loop", "1", "-framerate", str(fps), "-t", f"{d}", "-i", str(srcp)]
        base = (f"[0:v]scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={fps},setsar=1")
    elif vt == "video" and srcp.exists():
        inputs = ["-stream_loop", "-1", "-t", f"{d}", "-i", str(srcp)]
        base = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1"
    else:
        if vt in ("image", "video"):
            print(f"  ! scene {s['id']}: source '{src}' not found -> text card")
        if vt == "color":
            inputs = ["-f", "lavfi", "-t", f"{d}", "-i", f"color=c={c1}:s={w}x{h}:r={fps}"]
        else:
            inputs = ["-f", "lavfi", "-t", f"{d}", "-i",
                      f"gradients=s={w}x{h}:r={fps}:c0={c1}:c1={c2}:x0=0:y0=0:x1={w}:y1={h}:speed=0.008"]
        base = "[0:v]setsar=1"
        if v.get("vignette", True):
            base += ",vignette=PI/5"

    filters = [base]
    tdir = work / "text"
    tdir.mkdir(exist_ok=True)
    caption = v.get("caption")
    if caption:
        size = int(v.get("font_size") or (h * (0.055 if vt in ("text", "color") else 0.042)))
        tf = tdir / f"cap_{s['id']:02d}.txt"
        tf.write_text(wrap(caption, size, w), encoding="utf-8")
        y = {"top": "h*0.12", "bottom": "h*0.70", "center": "(h-text_h)/2"}.get(
            v.get("caption_pos", "center" if vt in ("text", "color") else "top"), "(h-text_h)/2")
        filters.append(drawtext(tf, font, size, v.get("text_color", "white"), y, vt not in ("text", "color"),
                                f"gte(t,{LEAD_IN * 0.5})"))
    if data.get("subtitles", True) and s.get("narration"):
        chunks = subtitle_chunks(s["narration"])
        total_w = sum(len(c.split()) for c in chunks) or 1
        vd = float(s.get("voice_duration") or (d - LEAD_IN - TAIL))
        t0 = LEAD_IN
        size = int(h * 0.034)
        for i, c in enumerate(chunks):
            t1 = t0 + vd * len(c.split()) / total_w
            tf = tdir / f"sub_{s['id']:02d}_{i:02d}.txt"
            tf.write_text(wrap(c, size, w), encoding="utf-8")
            filters.append(drawtext(tf, font, size, "white", "h*0.82", True, f"between(t,{t0:.2f},{t1:.2f})"))
            t0 = t1
    fade = float(v.get("fade", 0.3))
    if fade:
        filters.append(f"fade=t=in:st=0:d={fade},fade=t=out:st={max(0, d - fade):.2f}:d={fade}")
    vchain = ",".join(filters) + f",format=yuv420p[v]"

    # ---- audio: voice + sfx on a silent bed of exact scene length ----
    a_inputs: list[str] = ["-f", "lavfi", "-t", f"{d}", "-i", "anullsrc=r=44100:cl=stereo"]
    a_labels = []
    idx = 2  # 0 = video, 1 = silence
    afilters = []
    if s.get("voice_file"):
        a_inputs += ["-i", str(project / s["voice_file"])]
        afilters.append(f"[{idx}:a]aformat=channel_layouts=stereo,adelay={int(LEAD_IN * 1000)}:all=1,"
                        f"volume={data.get('voice', {}).get('volume', 1.0)}[a{idx}]")
        a_labels.append(f"[a{idx}]")
        idx += 1
    for spec in s.get("sfx", []):
        f = spec.get("resolved") or ""
        fp = Path(f) if Path(f).is_absolute() else project / f
        if not f or not fp.exists():
            fp = sfx_file(project, spec)
        a_inputs += ["-i", str(fp)]
        at = int(float(spec.get("at", 0)) * 1000)
        afilters.append(f"[{idx}:a]aformat=channel_layouts=stereo,volume={spec.get('volume', 0.6)},"
                        f"adelay={at}:all=1[a{idx}]")
        a_labels.append(f"[a{idx}]")
        idx += 1
    mix = "".join(["[1:a]"] + a_labels)
    afilters.append(f"{mix}amix=inputs={1 + len(a_labels)}:duration=first:normalize=0,"
                    f"atrim=0:{d},afade=t=out:st={max(0, d - 0.15):.2f}:d=0.15[a]")
    fc = vchain + ";" + ";".join(afilters)
    ffmpeg(*inputs, *a_inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-t", f"{d}", "-r", str(fps), "-c:v", "libx264", "-preset", data.get("preset", "veryfast"),
           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", str(out))
    return out


def contact_sheet(project: Path, clips: list[Path], data: dict) -> None:
    w, h = resolution(data)
    tw = 360
    th = int(tw * h / w)
    frames = []
    for i, c in enumerate(clips):
        f = project / "build" / f"thumb_{i:02d}.png"
        ffmpeg("-ss", f"{duration(c) * 0.6:.2f}", "-i", str(c), "-frames:v", "1", "-vf", f"scale={tw}:{th}", str(f))
        frames.append(f)
    cols = min(4, len(frames))
    rows = (len(frames) + cols - 1) // cols
    ffmpeg("-framerate", "1", "-i", str(project / "build" / "thumb_%02d.png"), "-frames:v", "1",
           "-vf", f"tile={cols}x{rows}:padding=12:margin=12:color=0x111111", str(project / "storyboard.png"))


def cmd_render(args) -> None:
    project = Path(args.project)
    if not shutil.which("ffmpeg"):
        die("ffmpeg is required")
    data = load(project)
    font = font_path(data)
    only = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    clips = []
    for s in data["scenes"]:
        if only and s["id"] not in only:
            clips.append(project / "build" / f"scene_{s['id']:02d}.mp4")
            continue
        print(f"  rendering scene {s['id']} ({scene_duration(s):.1f}s)")
        clips.append(build_scene(project, data, s, font))
    lst = project / "build" / "concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    joined = project / "build" / "joined.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined))

    out = project / (data.get("output") or "final.mp4")
    music = data.get("music")
    if music:
        total = duration(joined)
        mvol = data.get("music_volume", 0.18)
        if isinstance(music, str) and music in MUSIC_LIB:
            m_in = ["-f", "lavfi", "-t", f"{total}", "-i", f"aevalsrc='{MUSIC_LIB[music]}':s=44100"]
        else:
            mp = Path(music) if Path(music).is_absolute() else project / music
            if not mp.exists():
                die(f"music file {mp} not found")
            m_in = ["-stream_loop", "-1", "-i", str(mp)]
        # duck music under narration with sidechain compression
        fc = (f"[1:a]aformat=channel_layouts=stereo,volume={mvol},afade=t=in:d=1.5,"
              f"afade=t=out:st={max(0, total - 2):.2f}:d=2,atrim=0:{total}[m];"
              f"[0:a]asplit=2[v1][v2];[m][v2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
              f"[v1][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
        ffmpeg("-i", str(joined), *m_in, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out))
    else:
        shutil.copy(joined, out)
    contact_sheet(project, clips, data)
    cmd_plan(argparse.Namespace(project=str(project)))
    print(f"\nDONE: {out}  ({duration(out):.1f}s)\nstoryboard: {project / 'storyboard.md'}, {project / 'storyboard.png'}")


def cmd_demo(args) -> None:
    """Synthesize a short sample with a catalog voice (or provider voice id)."""
    cfg = expand_voice({"voice": args.voice, **({"effect": args.effect} if args.effect else {})})
    if not cfg.get("label") and not args.effect and "-" not in args.voice and args.voice.lower() not in ELEVEN_VOICES \
            and args.voice.lower() not in OPENAI_VOICES:
        hits = [c["name"] for c in load_catalog() if _norm(args.voice) in _norm(c["name"])]
        die(f"voice '{args.voice}' not found. " + (f"Did you mean: {', '.join(hits[:10])}?" if hits else
                                                   "See: vf.py voices"))
    provider, voice = resolve_voice(cfg, args.text)
    out = Path(args.out or f"voice-demos/{re.sub(r'[^0-9A-Za-zА-Яа-яЁё]+', '_', args.voice)}.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(8):
        try:
            tts_one(provider, voice, args.text, cfg, out)
            break
        except (Exception, SystemExit):
            time.sleep(1.0 + attempt * 0.5)
    else:
        die("TTS failed, try again")
    print(f"{cfg.get('label', args.voice)} -> {provider}:{voice} rate={cfg.get('rate', '')} pitch={cfg.get('pitch', '')} "
          f"effect={cfg.get('effect') or '-'}\n{out}  ({duration(out):.1f}s)")


def cmd_all(args) -> None:
    cmd_tts(args)
    cmd_sfx(args)
    cmd_render(args)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("sfx-list").set_defaults(fn=cmd_sfx_list)
    p = sub.add_parser("voices", help="list the named voice catalog, or a provider's voices")
    p.add_argument("--provider", choices=["elevenlabs", "openai", "edge", "espeak", "silent"])
    p.add_argument("--lang", default="")
    p.add_argument("--gender", choices=["m", "f", "male", "female"])
    p.add_argument("--group", choices=["базовый", "манера", "персонаж"])
    p.add_argument("--search", default="", help="filter catalog by name/description/effect")
    p.set_defaults(fn=cmd_voices)
    p = sub.add_parser("demo", help="speak a sample with a voice: vf.py demo \"Артём энергичный\"")
    p.add_argument("voice")
    p.add_argument("--text", default="Привет! Так звучит мой голос. Давай сделаем крутое видео!")
    p.add_argument("--effect", default="", help="extra effect(s), e.g. robot or deep,cave")
    p.add_argument("--out", default="")
    p.set_defaults(fn=cmd_demo)
    for name, fn in [("tts", cmd_tts), ("sfx", cmd_sfx), ("plan", cmd_plan), ("render", cmd_render), ("all", cmd_all)]:
        p = sub.add_parser(name)
        p.add_argument("project")
        p.add_argument("--force", action="store_true", help="re-synthesize cached narration")
        p.add_argument("--scenes", default="", help="render only these scene ids, e.g. 2,3")
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
