"""Локальный видео-воркер Коли. Бесплатно, на вашей видеокарте NVIDIA.
Модель: Lightricks LTX-Video (открытая, через diffusers). Запуск: см. worker/README.md
WORKER_MOCK=1 — проверка связки без видеокарты (рисует тестовое видео через ffmpeg)."""
import base64, io, json, os, subprocess, threading, queue, uuid, tempfile, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MOCK = os.environ.get("WORKER_MOCK") == "1"
HF = os.environ.get("BACKEND") == "hf"   # бесплатный облачный GPU: публичный Space Lightricks/LTX-2-3 (видео со звуком)
HF_SPACE = os.environ.get("HF_SPACE", "Lightricks/LTX-2-3")
MODEL = os.environ.get("LTX_MODEL", "Lightricks/LTX-Video")
OUT = os.path.join(tempfile.gettempdir(), "koli-worker"); os.makedirs(OUT, exist_ok=True)
SIZES = {"720p": 1280, "1080p": 1920, "1440p": 2560, "4K": 3840}  # итоговая ширина (апскейл ffmpeg)
FPS = 24
jobs, q = {}, queue.Queue()
pipes = {}

def get_pipe(kind):
    if kind in pipes: return pipes[kind]
    import torch
    from diffusers import LTXPipeline, LTXImageToVideoPipeline
    cls = LTXImageToVideoPipeline if kind == "i2v" else LTXPipeline
    p = cls.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
    p.enable_model_cpu_offload()      # работает на картах от ~12 ГБ
    if hasattr(p, "vae"): p.vae.enable_tiling()
    pipes[kind] = p
    return p

def upscale(src, dst, width, audio_note=None):
    h = int(width * 9 / 16) // 2 * 2
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                    f"scale={width}:{h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-map", "0:v", "-map", "0:a?", "-c:a", "aac", dst], check=True)

def run(job):
    j = jobs[job["id"]]; raw = os.path.join(OUT, job["id"] + "_raw.mp4"); fin = os.path.join(OUT, job["id"] + ".mp4")
    secs = max(1, min(10, int(job["seconds"])))
    frames = 8 * round(secs * FPS / 8) + 1          # LTX требует 8n+1 кадров
    if MOCK:
        for i in range(5):
            import time; time.sleep(0.5); j["progress"] = 20 * (i + 1)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=size=768x432:rate={FPS}", "-t", str(secs), "-pix_fmt", "yuv420p", raw], check=True)
    elif HF:
        from gradio_client import Client, handle_file
        kw = {"token": os.environ["HF_TOKEN"]} if os.environ.get("HF_TOKEN") else {}
        img = None
        if job.get("image"):
            ip = os.path.join(OUT, job["id"] + ".img"); open(ip, "wb").write(base64.b64decode(job["image"])); img = handle_file(ip)
        j["progress"] = 10
        prompt = "Cinematic live-action film, photorealistic real people, natural motion. " + job["prompt"]
        if job.get("audio"): prompt += " Natural synchronized sound and dialogue."
        res = Client(HF_SPACE, **kw).predict(img, prompt, float(secs), False, 10, True, 576, 1024, api_name="/generate_video")
        path = res[0] if isinstance(res, (list, tuple)) else res
        if isinstance(path, dict): path = path.get("video") or path.get("path")
        import shutil; shutil.copy(path, raw)
    else:
        import torch
        from diffusers.utils import export_to_video, load_image
        prompt = ("Cinematic live-action film footage, photorealistic real people, natural motion, film lighting. " + job["prompt"])
        neg = "worst quality, blurry, jittery, distorted, cartoon, anime, 3d render, watermark"
        steps = 40
        def cb(pipe, i, t, kw): j["progress"] = int(5 + 90 * (i + 1) / steps); return kw
        kw = dict(prompt=prompt, negative_prompt=neg, width=768, height=512, num_frames=frames,
                  num_inference_steps=steps, callback_on_step_end=cb, generator=torch.Generator().manual_seed(int.from_bytes(os.urandom(4), "big")))
        if job.get("image"):
            from PIL import Image
            img = Image.open(io.BytesIO(base64.b64decode(job["image"]))).convert("RGB").resize((768, 512))
            frames_out = get_pipe("i2v")(image=img, **kw).frames[0]
        else:
            frames_out = get_pipe("t2v")(**kw).frames[0]
        export_to_video(frames_out, raw, fps=FPS)
    upscale(raw, fin, SIZES.get(job["quality"], 1920))
    os.remove(raw)
    j["status"], j["progress"] = "done", 100

def loop():
    while True:
        job = q.get()
        try: run(job)
        except Exception as e:
            traceback.print_exc(); jobs[job["id"]].update(status="error", error=str(e)[:300])

class H(BaseHTTPRequestHandler):
    def _j(self, c, o): b = json.dumps(o).encode(); self.send_response(c); self.send_header("content-type", "application/json"); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if self.path != "/generate": return self._j(404, {})
        n = int(self.headers.get("content-length", 0)); job = json.loads(self.rfile.read(n)); job["id"] = uuid.uuid4().hex
        jobs[job["id"]] = {"status": "working", "progress": 0}; q.put(job); self._j(200, {"id": job["id"]})
    def do_GET(self):
        p = self.path.split("/")
        if p[1:2] == ["status"] and p[2] in jobs: return self._j(200, jobs[p[2]])
        if p[1:2] == ["result"] and p[2] in jobs and jobs[p[2]]["status"] == "done":
            d = open(os.path.join(OUT, p[2] + ".mp4"), "rb").read()
            self.send_response(200); self.send_header("content-type", "video/mp4"); self.send_header("content-length", str(len(d))); self.end_headers(); return self.wfile.write(d)
        self._j(404, {})
    def log_message(self, *a): pass

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    port = int(os.environ.get("WORKER_PORT", 8188))
    print(f"Воркер Коли на :{port} ({'MOCK' if MOCK else MODEL})")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
