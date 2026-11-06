// Коли — сервер без внешних зависимостей (nodemailer опционален).
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// --- .env ---
try {
  for (const l of fs.readFileSync(path.join(__dirname, '.env'), 'utf8').split('\n')) {
    const m = l.match(/^\s*([A-Z_]+)\s*=\s*(.*)\s*$/);
    if (m && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^"|"$/g, '');
  }
} catch {}

const PORT = process.env.PORT || 3000;
const PUB = path.join(__dirname, 'public');
const DB = path.join(__dirname, 'data', 'db.json');
fs.mkdirSync(path.join(__dirname, 'data', 'videos'), { recursive: true });

let db = { users: {}, sessions: {}, videos: {} };
try { db = JSON.parse(fs.readFileSync(DB, 'utf8')); } catch {}
const save = () => fs.writeFileSync(DB, JSON.stringify(db));
const codes = new Map(); // email -> {hash, exp, tries, last}
const sha = s => crypto.createHash('sha256').update(s).digest('hex');

// --- почта ---
let mailer = null;
if (process.env.SMTP_HOST) {
  try {
    mailer = require('nodemailer').createTransport({
      host: process.env.SMTP_HOST, port: +process.env.SMTP_PORT || 465,
      secure: (+process.env.SMTP_PORT || 465) === 465,
      auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
    });
  } catch { console.warn('nodemailer не установлен: npm install'); }
}
async function sendCode(email, code) {
  if (!mailer) { console.log(`\n[DEV] Код для ${email}: ${code}\n`); return false; }
  await mailer.sendMail({
    from: process.env.SMTP_FROM || process.env.SMTP_USER, to: email,
    subject: `Коли: ваш код ${code}`,
    text: `Ваш код входа в Коли: ${code}\nОн действует 10 минут.`,
  });
  return true;
}

// --- видео ---
const OPTS = { maxSeconds: 10, qualities: ['720p', '1080p', '1440p', '4K'] };
if (process.env.BACKEND === 'hf' && !process.env.LOCAL_WORKER_URL) { // встроенный воркер на бесплатном облачном GPU
  process.env.LOCAL_WORKER_URL = 'http://127.0.0.1:8188';
  const w = require('child_process').spawn(process.env.PYTHON || 'python3', [path.join(__dirname, 'worker', 'worker.py')], { stdio: 'inherit', env: process.env });
  w.on('error', e => console.error('Воркер не запустился:', e.message));
  process.on('exit', () => w.kill());
}
const WORKER = (process.env.LOCAL_WORKER_URL || '').replace(/\/$/, '');
const live = !!(process.env.GEMINI_API_KEY || WORKER);

function buildPrompt(v) {
  return `Cinematic live-action footage, photorealistic real people, natural motion, film lighting, shallow depth of field, not animation or cartoon. ${v.prompt}` +
    (v.audio ? ' Include natural synchronized sound: ambient audio, effects and dialogue/music where fitting.' : ' No audio.');
}

async function runVideo(id) {
  const v = db.videos[id];
  const set = (p) => { Object.assign(v, p); save(); };
  try {
    if (WORKER) { // локальный бесплатный воркер
      let image;
      if (v.imageFile) image = fs.readFileSync(path.join(__dirname, 'data', v.imageFile)).toString('base64');
      const r = await fetch(WORKER + '/generate', { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ prompt: v.prompt, seconds: v.seconds, quality: v.quality, audio: v.audio, image }) });
      if (!r.ok) throw new Error('Воркер недоступен: ' + r.status);
      const { id: wid } = await r.json();
      for (;;) {
        await new Promise(r => setTimeout(r, 2000));
        const st = await (await fetch(`${WORKER}/status/${wid}`)).json();
        if (st.status === 'error') throw new Error(st.error || 'Ошибка воркера');
        set({ progress: st.progress || 0 });
        if (st.status === 'done') break;
      }
      const f = await fetch(`${WORKER}/result/${wid}`);
      fs.writeFileSync(path.join(__dirname, 'data', 'videos', id + '.mp4'), Buffer.from(await f.arrayBuffer()));
      return set({ status: 'done', progress: 100 });
    }
    if (!live) { // демо: имитация процесса, без реального видео
      for (let i = 1; i <= 10; i++) { await new Promise(r => setTimeout(r, 600)); set({ progress: i * 10 }); }
      return set({ status: 'demo', progress: 100 });
    }
    const base = 'https://generativelanguage.googleapis.com/v1beta';
    const key = process.env.GEMINI_API_KEY;
    const model = process.env.VEO_MODEL || 'veo-3.1-generate-preview';
    const inst = { prompt: buildPrompt(v) };
    if (v.imageFile) {
      const b = fs.readFileSync(path.join(__dirname, 'data', v.imageFile));
      inst.image = { bytesBase64Encoded: b.toString('base64'), mimeType: v.imageMime };
    }
    // Veo поддерживает ограниченные длительности (обычно 4/6/8 с) — берём ближайшую.
    const dur = [4, 6, 8].reduce((a, b) => Math.abs(b - v.seconds) < Math.abs(a - v.seconds) ? b : a);
    const res = await fetch(`${base}/models/${model}:predictLongRunning`, {
      method: 'POST', headers: { 'x-goog-api-key': key, 'content-type': 'application/json' },
      body: JSON.stringify({ instances: [inst], parameters: { durationSeconds: dur, resolution: v.quality.toLowerCase(), aspectRatio: '16:9' } }),
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 300)}`);
    let op = await res.json();
    for (let i = 0; !op.done && i < 120; i++) {
      await new Promise(r => setTimeout(r, 5000));
      set({ progress: Math.min(95, 5 + i * 3) });
      op = await (await fetch(`${base}/${op.name}`, { headers: { 'x-goog-api-key': key } })).json();
    }
    if (!op.done) throw new Error('Время ожидания истекло');
    if (op.error) throw new Error(op.error.message);
    const uri = op.response?.generateVideoResponse?.generatedSamples?.[0]?.video?.uri;
    if (!uri) throw new Error('Модель не вернула видео (возможно, сработал фильтр безопасности)');
    const f = await fetch(uri, { headers: { 'x-goog-api-key': key } });
    fs.writeFileSync(path.join(__dirname, 'data', 'videos', id + '.mp4'), Buffer.from(await f.arrayBuffer()));
    set({ status: 'done', progress: 100 });
  } catch (e) { set({ status: 'error', error: String(e.message || e) }); }
}

// --- HTTP ---
const MIME = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.mp4': 'video/mp4' };
const json = (res, code, o) => { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(o)); };
const body = req => new Promise((ok, no) => {
  let n = 0; const c = [];
  req.on('data', d => { n += d.length; if (n > 12e6) { no(new Error('big')); req.destroy(); } else c.push(d); });
  req.on('end', () => { try { ok(JSON.parse(Buffer.concat(c) || '{}')); } catch { ok({}); } });
});
const authed = req => {
  const t = (req.headers.authorization || '').replace('Bearer ', '');
  const s = db.sessions[sha(t)];
  return s ? s.email : null;
};
const okEmail = e => typeof e === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e) && e.length < 200;

http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  try {
    if (req.method === 'POST' && url.pathname === '/api/send-code') {
      const email = String((await body(req)).email || '').trim().toLowerCase();
      if (!okEmail(email)) return json(res, 400, { error: 'Введите корректный адрес почты' });
      const prev = codes.get(email);
      if (prev && Date.now() - prev.last < 30000) return json(res, 429, { error: 'Подождите 30 секунд перед повторной отправкой' });
      const code = String(crypto.randomInt(100000, 1000000));
      codes.set(email, { hash: sha(email + code), exp: Date.now() + 6e5, tries: 0, last: Date.now() });
      let sent;
      try { sent = await sendCode(email, code); } catch (e) { console.error(e); return json(res, 502, { error: 'Не удалось отправить письмо' }); }
      return json(res, 200, { ok: true, dev: !sent });
    }
    if (req.method === 'POST' && url.pathname === '/api/verify') {
      const b = await body(req);
      const email = String(b.email || '').trim().toLowerCase();
      const c = codes.get(email);
      if (!c || c.exp < Date.now()) return json(res, 400, { error: 'Код истёк, запросите новый' });
      if (++c.tries > 5) { codes.delete(email); return json(res, 429, { error: 'Слишком много попыток' }); }
      if (c.hash !== sha(email + String(b.code || '').trim())) return json(res, 400, { error: 'Неверный код' });
      codes.delete(email);
      const isNew = !db.users[email];
      if (isNew) db.users[email] = { created: Date.now() };
      const token = crypto.randomBytes(32).toString('hex');
      db.sessions[sha(token)] = { email, at: Date.now() };
      save();
      return json(res, 200, { token, email, isNew });
    }
    if (url.pathname.startsWith('/api/')) {
      const email = authed(req);
      if (!email) return json(res, 401, { error: 'Нужен вход' });
      if (req.method === 'GET' && url.pathname === '/api/config') return json(res, 200, { ...OPTS, live, email });
      if (req.method === 'POST' && url.pathname === '/api/logout') {
        delete db.sessions[sha((req.headers.authorization || '').replace('Bearer ', ''))]; save(); return json(res, 200, {});
      }
      if (req.method === 'POST' && url.pathname === '/api/videos') {
        const b = await body(req);
        const prompt = String(b.prompt || '').trim();
        if (prompt.length < 3) return json(res, 400, { error: 'Опишите, что снять' });
        const seconds = Math.min(OPTS.maxSeconds, Math.max(1, Math.round(+b.seconds || 5)));
        const quality = OPTS.qualities.includes(b.quality) ? b.quality : '1080p';
        const id = crypto.randomBytes(8).toString('hex');
        const v = { id, email, prompt: prompt.slice(0, 2000), seconds, quality, audio: !!b.audio, status: 'working', progress: 0, created: Date.now() };
        const m = /^data:(image\/(png|jpeg|webp));base64,(.+)$/.exec(b.image || '');
        if (m) { v.imageFile = `videos/${id}.img`; v.imageMime = m[1]; fs.writeFileSync(path.join(__dirname, 'data', v.imageFile), Buffer.from(m[3], 'base64')); }
        db.videos[id] = v; save(); runVideo(id);
        return json(res, 200, { id });
      }
      if (req.method === 'GET' && url.pathname === '/api/videos') {
        const list = Object.values(db.videos).filter(v => v.email === email).sort((a, b) => b.created - a.created)
          .map(({ imageFile, imageMime, email, ...r }) => r);
        return json(res, 200, list);
      }
    }
    if (req.method === 'GET' && url.pathname.startsWith('/video/')) { // видео: токен в query (для <video>)
      const t = url.searchParams.get('t') || '';
      const s = db.sessions[sha(t)];
      const id = path.basename(url.pathname, '.mp4');
      if (!s || db.videos[id]?.email !== s.email) { res.writeHead(403); return res.end(); }
      const f = path.join(__dirname, 'data', 'videos', id + '.mp4');
      if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
      const size = fs.statSync(f).size, r = /bytes=(\d+)-(\d*)/.exec(req.headers.range || '');
      if (r) {
        const a = +r[1], z = r[2] ? +r[2] : size - 1;
        res.writeHead(206, { 'content-type': 'video/mp4', 'accept-ranges': 'bytes', 'content-range': `bytes ${a}-${z}/${size}`, 'content-length': z - a + 1 });
        return fs.createReadStream(f, { start: a, end: z }).pipe(res);
      }
      res.writeHead(200, { 'content-type': 'video/mp4', 'content-length': size, 'accept-ranges': 'bytes' });
      return fs.createReadStream(f).pipe(res);
    }
    // статика
    let p = path.normalize(url.pathname === '/' ? '/index.html' : url.pathname);
    const f = path.join(PUB, p);
    if (!f.startsWith(PUB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end('Not found'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  } catch (e) { console.error(e); json(res, 500, { error: 'Ошибка сервера' }); }
}).listen(PORT, () => console.log(`Коли: http://localhost:${PORT}  (${WORKER ? 'локальный воркер' : live ? 'Veo' : 'демо-режим'}, ${mailer ? 'SMTP' : 'код в консоли'})`));
