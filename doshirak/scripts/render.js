// Покадровый рендер scenes.html (GSAP-таймлайн) -> ffmpeg. Режимы: stills | video
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "..");
const TIMING = JSON.parse(fs.readFileSync(path.join(root, "work/timing.json"), "utf8"));
const FPS = 30, mode = process.argv[2] || "video";

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.addInitScript(t => { window.TIMING = t; }, TIMING);
  await page.goto("file://" + path.join(root, "scenes.html"));
  await page.waitForFunction(() => typeof window.seek === "function");
  const total = await page.evaluate(() => window.TOTAL);
  if (mode === "stills") {
    const ts = process.argv.slice(3).map(Number);
    for (const t of ts) {
      await page.evaluate(t => window.seek(t), t);
      await page.screenshot({ path: path.join(root, `work/still_${t}.png`) });
    }
  } else {
    const n = Math.ceil(total * FPS);
    const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg",
      "-i", "-", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
      path.join(root, "work/video_noaudio.mp4")], { stdio: ["pipe", "inherit", "inherit"] });
    for (let f = 0; f < n; f++) {
      await page.evaluate(t => window.seek(t), f / FPS);
      const buf = await page.screenshot({ type: "jpeg", quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
      if (f % 150 === 0) console.log(`кадр ${f}/${n}`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on("close", r));
  }
  console.log("total", total.toFixed(2));
  await browser.close();
})();
