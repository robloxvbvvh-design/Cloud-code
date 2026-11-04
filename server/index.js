'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { collect, checkKey } = require('./pool');

const PORT = Number(process.env.PORT || 3000);
const ROOT = path.join(__dirname, '..');
const PUBLIC = path.join(ROOT, 'public');
const DB_FILE = path.join(ROOT, 'data', 'db.json');
const REFRESH_MS = Number(process.env.REFRESH_MINUTES || 30) * 60 * 1000;

const DAY = 24 * 60 * 60 * 1000;
const TRIAL_DAYS = 3;
const MINUTES_PER_DAY = 1440;      // натапал 1440 минут -> можно вывести 1 день
const MAX_TAPS_PER_SEC = 15;       // защита от автокликера

const PLANS = {
  m1: { title: '1 месяц', days: 30, price: 199 },
  m3: { title: '3 месяца', days: 90, price: 499 },
  m12: { title: '12 месяцев', days: 365, price: 1490 },
};

// Скины чисто косметические — доход за клик всегда 1 минута.
const SKINS = [
  { id: 'default', title: 'Классика', price: 0, emoji: '🛡️' },
  { id: 'fire', title: 'Огонь', price: 60, emoji: '🔥' },
  { id: 'rocket', title: 'Ракета', price: 180, emoji: '🚀' },
  { id: 'cat', title: 'Котик', price: 360, emoji: '🐱' },
  { id: 'diamond', title: 'Алмаз', price: 720, emoji: '💎' },
  { id: 'crown', title: 'Корона', price: 1440, emoji: '👑' },
];

// ---------- хранилище ----------
let db = { users: {}, pool: [], poolUpdatedAt: 0 };
try { db = { ...db, ...JSON.parse(fs.readFileSync(DB_FILE, 'utf8')) }; } catch { /* первый запуск */ }
let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fs.mkdirSync(path.dirname(DB_FILE), { recursive: true });
    fs.writeFileSync(DB_FILE + '.tmp', JSON.stringify(db));
    fs.renameSync(DB_FILE + '.tmp', DB_FILE);
  }, 300);
}

// ---------- пул ключей ----------
let refreshing = false;
async function refreshPool() {
  if (refreshing) return;
  refreshing = true;
  try {
    const alive = await collect();
    if (alive.length) { db.pool = alive; db.poolUpdatedAt = Date.now(); save(); }
  } catch (e) { console.error('[pool] ошибка обновления', e); }
  refreshing = false;
}

// Сколько пользователей сейчас держат каждый ключ
function keyUsage() {
  const usage = new Map();
  for (const u of Object.values(db.users)) if (u.keyId) usage.set(u.keyId, (usage.get(u.keyId) || 0) + 1);
  return usage;
}

/** Выдаёт пользователю новый ключ: сначала никому не выданный, перед выдачей перепроверяет. */
async function issueKey(user) {
  const usage = keyUsage();
  const candidates = db.pool
    .filter(k => k.id !== user.keyId)
    .sort((a, b) => (usage.get(a.id) || 0) - (usage.get(b.id) || 0) || a.ping - b.ping);
  for (const k of candidates.slice(0, 15)) {
    const ping = await checkKey(k);
    if (ping === null) { db.pool = db.pool.filter(p => p.id !== k.id); continue; } // умер — выкидываем
    k.ping = ping; k.checkedAt = Date.now();
    user.keyId = k.id;
    user.key = k.uri;
    user.keyIssuedAt = Date.now();
    save();
    return k;
  }
  return null;
}

// ---------- пользователи ----------
function newUser(id) {
  return {
    id, createdAt: Date.now(), trial: 'pending', subEnds: 0,
    minutes: 0, tapsTotal: 0, lastTapAt: 0, skins: ['default'], skin: 'default',
    subToken: crypto.randomBytes(16).toString('hex'), payments: [],
  };
}
function isActive(u) { return u.subEnds > Date.now(); }
function extend(u, days) { u.subEnds = Math.max(u.subEnds, Date.now()) + days * DAY; }

function publicUser(u, host) {
  const k = db.pool.find(p => p.id === u.keyId);
  return {
    id: u.id, trial: u.trial, subEnds: u.subEnds, active: isActive(u),
    msLeft: Math.max(0, u.subEnds - Date.now()),
    minutes: u.minutes, tapsTotal: u.tapsTotal, skins: u.skins, skin: u.skin,
    payments: u.payments.slice(-10),
    key: isActive(u) ? u.key || null : null,
    keyServer: k ? { flag: k.flag, title: k.title, proto: k.proto, ping: k.ping } : null,
    subUrl: `${host}/sub/${u.subToken}`,
  };
}

// ---------- HTTP ----------
function send(res, code, body, type = 'application/json; charset=utf-8') {
  res.writeHead(code, { 'Content-Type': type, 'Cache-Control': 'no-store' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}
function readBody(req) {
  return new Promise(resolve => {
    let s = '';
    req.on('data', c => { s += c; if (s.length > 1e5) req.destroy(); });
    req.on('end', () => { try { resolve(JSON.parse(s || '{}')); } catch { resolve({}); } });
  });
}
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json', '.svg': 'image/svg+xml' };

const routes = {
  'GET /api/me': (u, b, h) => publicUser(u, h),

  'POST /api/trial': (u, b, h) => {
    if (u.trial !== 'pending') return { error: 'Пробный период уже использован' };
    if (b.accept) { u.trial = 'used'; extend(u, TRIAL_DAYS); } else u.trial = 'declined';
    return publicUser(u, h);
  },

  'GET /api/servers': () => ({
    updatedAt: db.poolUpdatedAt, refreshing, total: db.pool.length,
    servers: db.pool.slice(0, 50).map(k => ({ flag: k.flag, title: k.title, proto: k.proto, ping: k.ping })),
  }),

  'GET /api/plans': () => PLANS,

  // Фейковая оплата: деньги не списываются, подписка просто продлевается.
  'POST /api/pay': (u, b, h) => {
    const plan = PLANS[b.plan];
    if (!plan) return { error: 'Нет такого тарифа' };
    extend(u, plan.days);
    u.payments.push({ at: Date.now(), plan: b.plan, title: plan.title, price: plan.price, fake: true });
    return publicUser(u, h);
  },

  'POST /api/tap': (u, b, h) => {
    const now = Date.now();
    const elapsed = Math.max(1, (now - (u.lastTapAt || now - 1000)) / 1000);
    const allowed = Math.ceil(Math.min(elapsed, 5) * MAX_TAPS_PER_SEC);
    const n = Math.max(0, Math.min(Number(b.count) || 0, allowed));
    u.minutes += n;            // 1 клик = 1 минута, скины на это не влияют
    u.tapsTotal += n;
    u.lastTapAt = now;
    return publicUser(u, h);
  },

  'POST /api/withdraw': (u, b, h) => {
    const days = Math.floor(u.minutes / MINUTES_PER_DAY);
    if (days < 1) return { error: `Нужно минимум ${MINUTES_PER_DAY} минут (1 день)` };
    u.minutes -= days * MINUTES_PER_DAY;
    extend(u, days);
    return { ...publicUser(u, h), withdrawnDays: days };
  },

  'GET /api/skins': () => SKINS,

  'POST /api/skins/buy': (u, b, h) => {
    const s = SKINS.find(x => x.id === b.id);
    if (!s) return { error: 'Нет такого скина' };
    if (!u.skins.includes(s.id)) {
      if (u.minutes < s.price) return { error: 'Не хватает минут' };
      u.minutes -= s.price;
      u.skins.push(s.id);
    }
    u.skin = s.id;
    return publicUser(u, h);
  },

  'POST /api/key': async (u, b, h) => {
    if (!isActive(u)) return { error: 'Подписка не активна' };
    if (!db.pool.length) return { error: 'Серверы ещё проверяются, попробуйте через минуту' };
    const k = await issueKey(u);
    if (!k) return { error: 'Не нашлось рабочего сервера, попробуйте позже' };
    return publicUser(u, h);
  },
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  const proto = req.headers['x-forwarded-proto'] || 'http';
  const host = `${proto}://${req.headers['x-forwarded-host'] || req.headers.host}`;

  // Подписка для клиентов (Happ, Hiddify, v2RayTun, INCY): base64 со списком ключей.
  const sub = url.pathname.match(/^\/sub\/([a-f0-9]{32})$/);
  if (sub) {
    const u = Object.values(db.users).find(x => x.subToken === sub[1]);
    if (!u) return send(res, 404, 'not found', 'text/plain');
    const body = isActive(u) && u.key ? u.key : '';
    res.writeHead(200, {
      'Content-Type': 'text/plain; charset=utf-8',
      'profile-title': 'base64:' + Buffer.from('TapVPN').toString('base64'),
      'profile-update-interval': '1',
      'subscription-userinfo': `upload=0; download=0; total=0; expire=${Math.floor(u.subEnds / 1000)}`,
    });
    return res.end(Buffer.from(body).toString('base64'));
  }

  const handler = routes[`${req.method} ${url.pathname}`];
  if (handler) {
    const uid = String(req.headers['x-user'] || '');
    if (!/^[a-zA-Z0-9-]{8,64}$/.test(uid)) return send(res, 400, { error: 'нет X-User' });
    const user = db.users[uid] || (db.users[uid] = newUser(uid));
    const body = req.method === 'POST' ? await readBody(req) : {};
    const out = await handler(user, body, host);
    save();
    return send(res, out && out.error ? 400 : 200, out);
  }

  // Статика
  let file = path.normalize(path.join(PUBLIC, url.pathname === '/' ? 'index.html' : url.pathname));
  if (!file.startsWith(PUBLIC)) return send(res, 403, 'forbidden', 'text/plain');
  fs.readFile(file, (err, data) => {
    if (err) return send(res, 404, 'not found', 'text/plain');
    send(res, 200, data, MIME[path.extname(file)] || 'application/octet-stream');
  });
});

server.listen(PORT, () => {
  console.log(`VPN запущен: http://localhost:${PORT}`);
  if (Date.now() - db.poolUpdatedAt > REFRESH_MS) refreshPool();
  setInterval(refreshPool, REFRESH_MS);
});
