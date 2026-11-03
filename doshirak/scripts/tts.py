"""Озвучка сцен через edge-tts + пословные таймкоды -> work/voice_*.mp3, work/timing.json"""
import ssl, asyncio, json, subprocess, sys
import edge_tts.communicate as c

c._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")  # прокси-CA
VOICE, RATE = "ru-RU-DmitryNeural", "+8%"
SCENES = json.load(open(sys.argv[1], encoding="utf-8"))

async def one(i, text):
    words = []
    out = open(f"work/voice_{i}.mp3", "wb")
    async for ch in c.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary").stream():
        if ch["type"] == "audio":
            out.write(ch["data"])
        elif ch["type"] == "WordBoundary":
            words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    out.close()
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", f"work/voice_{i}.mp3"]))
    return {"dur": dur, "words": words}

async def main():
    res = [await one(i, s["text"]) for i, s in enumerate(SCENES)]
    json.dump(res, open("work/timing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print([round(r["dur"], 2) for r in res], [len(r["words"]) for r in res])

asyncio.run(main())
