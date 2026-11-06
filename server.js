// «Ии Матвей ТТ» — сервер: регистрация по e-mail-коду + генерация видео.
const express = require("express");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");
const nodemailer = require("nodemailer");

const PORT = process.env.PORT || 3000;
const DATA = path.join(__dirname, "data");
const VIDEOS = path.join(DATA, "videos");
const UPLOADS = path.join(DATA, "uploads");
[VIDEOS, UPLOADS].forEach((d) => fs.mkdirSync(d, { recursive: true }));

// ---------- Почта ----------
// Задайте SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS (и при желании MAIL_FROM).
// Например для Gmail: smtp.gmail.com / 465 / ваш@gmail.com / пароль приложения.
const smtpOn = !!process.env.SMTP_HOST;
const transport = smtpOn
  ? nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: +(process.env.SMTP_PORT || 465),
      secure: +(process.env.SMTP_PORT || 465) === 465,
      auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
    })
  : null;

async function sendCode(email, code) {
  if (!smtpOn) {
    console.log(`[DEV] Код для ${email}: ${code}  (SMTP не настроен — письмо не отправлено)`);
    return false;
  }
  await transport.sendMail({
    from: process.env.MAIL_FROM || `"Ии Матвей ТТ" <${process.env.SMTP_USER}>`,
    to: email,
    subject: `Код входа: ${code}`,
    text: `Ваш код для входа в «Ии Матвей ТТ»: ${code}\nКод действует 10 минут.`,
    html: `<div style="font-family:sans-serif"><h2>Ии Матвей ТТ</h2><p>Ваш код для входа:</p><p style="font-size:32px;letter-spacing:6px"><b>${code}</b></p><p>Код действует 10 минут.</p></div>`,
  });
  return true;
}

// ---------- Хранилища в памяти ----------
const codes = new Map(); // email -> {hash, exp, tries, last}
const sessions = new Map(); // token -> email
const jobs = new Map(); // id -> job

const sha = (s) => crypto.createHash("sha256").update(s).digest("hex");
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const app = express();
app.use(express.json({ limit: "12mb" }));
app.use(express.static(path.join(__dirname, "public")));

function auth(req, res, next) {
  const token = (req.headers.authorization || "").replace("Bearer ", "") || req.query.token;
  const email = sessions.get(token);
  if (!email) return res.status(401).json({ error: "Нужно войти" });
  req.email = email;
  next();
}

app.post("/api/send-code", async (req, res) => {
  const email = String(req.body.email || "").trim().toLowerCase();
  if (!EMAIL_RE.test(email)) return res.status(400).json({ error: "Неверный e-mail" });
  const prev = codes.get(email);
  if (prev && Date.now() - prev.last < 30000)
    return res.status(429).json({ error: "Подождите 30 секунд перед повторной отправкой" });
  const code = String(crypto.randomInt(0, 1000000)).padStart(6, "0");
  codes.set(email, { hash: sha(code), exp: Date.now() + 10 * 60000, tries: 0, last: Date.now() });
  try {
    const sent = await sendCode(email, code);
    // В режиме без SMTP возвращаем код, чтобы приложение можно было проверить локально.
    res.json({ ok: true, sent, devCode: sent ? undefined : code });
  } catch (e) {
    console.error("Ошибка отправки почты:", e.message);
    res.status(502).json({ error: "Не удалось отправить письмо. Проверьте настройки SMTP." });
  }
});

app.post("/api/verify", (req, res) => {
  const email = String(req.body.email || "").trim().toLowerCase();
  const code = String(req.body.code || "").trim();
  const rec = codes.get(email);
  if (!rec || rec.exp < Date.now()) return res.status(400).json({ error: "Код истёк, запросите новый" });
  if (++rec.tries > 5) {
    codes.delete(email);
    return res.status(429).json({ error: "Слишком много попыток, запросите новый код" });
  }
  if (sha(code) !== rec.hash) return res.status(400).json({ error: "Неверный код" });
  codes.delete(email);
  const token = crypto.randomBytes(24).toString("hex");
  sessions.set(token, email);
  res.json({ token, email });
});

app.get("/api/me", auth, (req, res) => res.json({ email: req.email }));

const QUALITY = { "480p": 480, "720p": 720, "1080p": 1080, "1440p": 1440, "4K": 2160 };

app.post("/api/generate", auth, (req, res) => {
  const prompt = String(req.body.prompt || "").trim();
  const duration = Math.min(30, Math.max(3, parseInt(req.body.duration, 10) || 10));
  const quality = QUALITY[req.body.quality] ? req.body.quality : "1080p";
  const aspect = req.body.aspect === "9:16" ? "9:16" : "16:9";
  const audio = !!req.body.audio;
  if (prompt.length < 3) return res.status(400).json({ error: "Напишите запрос" });
  if (prompt.length > 600) return res.status(400).json({ error: "Запрос слишком длинный" });
  if ([...jobs.values()].some((j) => j.email === req.email && j.status === "running"))
    return res.status(429).json({ error: "Дождитесь окончания текущей генерации" });

  const id = crypto.randomBytes(8).toString("hex");
  let characterPath = null;
  const m = /^data:image\/(png|jpeg|webp);base64,(.+)$/.exec(req.body.character || "");
  if (m) {
    characterPath = path.join(UPLOADS, `${id}.${m[1]}`);
    fs.writeFileSync(characterPath, Buffer.from(m[2], "base64"));
  }
  const out = path.join(VIDEOS, `${id}.mp4`);
  const job = { id, email: req.email, status: "running", progress: 0, stage: "Придумываю кадры…" };
  jobs.set(id, job);

  const cfg = { prompt, duration, height: QUALITY[quality], aspect, audio, character: characterPath, out };
  const py = spawn("python3", ["-I", path.join(__dirname, "engine", "render.py"), JSON.stringify(cfg)]);
  let err = "";
  py.stdout.on("data", (d) => {
    for (const line of String(d).split("\n")) {
      const p = /^PROGRESS ([\d.]+)/.exec(line);
      if (p) {
        job.progress = +p[1];
        job.stage = job.progress < 0.99 ? "Рисую кадры и склеиваю…" : "Финальное кодирование…";
      }
    }
  });
  py.stderr.on("data", (d) => (err += d));
  py.on("close", (code) => {
    if (characterPath) fs.rm(characterPath, () => {});
    if (code === 0) {
      job.status = "done";
      job.progress = 1;
      job.url = `/api/video/${id}`;
    } else {
      job.status = "error";
      job.error = "Ошибка генерации";
      console.error("render error:", err.slice(-800));
    }
  });
  res.json({ id });
});

app.get("/api/job/:id", auth, (req, res) => {
  const j = jobs.get(req.params.id);
  if (!j || j.email !== req.email) return res.status(404).json({ error: "Не найдено" });
  const { status, progress, stage, url, error } = j;
  res.json({ status, progress, stage, url, error });
});

app.get("/api/video/:id", auth, (req, res) => {
  const j = jobs.get(req.params.id);
  if (!j || j.email !== req.email || j.status !== "done") return res.sendStatus(404);
  res.sendFile(path.join(VIDEOS, `${j.id}.mp4`));
});

app.listen(PORT, () => {
  console.log(`Ии Матвей ТТ: http://localhost:${PORT}`);
  console.log(smtpOn ? "Почта: SMTP включён" : "Почта: SMTP не настроен — коды печатаются в консоль (DEV)");
});
