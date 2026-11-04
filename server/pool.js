// Сбор публичных VPN-ключей с GitHub и их проверка.
'use strict';
const net = require('net');
const tls = require('tls');
const xray = require('./xray');

// Публичные агрегаторы бесплатных конфигов на GitHub (raw-ссылки).
const SOURCES = [
  'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt',
  'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt',
  'https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub1.txt',
  'https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub2.txt',
  'https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt',
];

const PROTOCOLS = ['vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'hy2://'];
const MAX_CANDIDATES = Number(process.env.MAX_CANDIDATES || 1500);
const CHECK_TIMEOUT = Number(process.env.CHECK_TIMEOUT || 4000);
const CONCURRENCY = Number(process.env.CHECK_CONCURRENCY || 64);

function b64decode(s) {
  s = s.trim().replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Buffer.from(s, 'base64').toString('utf8');
}

function decodeName(s) {
  try { return decodeURIComponent(s); } catch { return s; }
}

// Разбор ключа -> {proto, host, port, tls, sni, name, uri}
function parseKey(uri) {
  uri = uri.trim();
  const proto = uri.slice(0, uri.indexOf('://'));
  try {
    if (proto === 'vmess') {
      const j = JSON.parse(b64decode(uri.slice(8)));
      return {
        proto, uri, host: String(j.add), port: Number(j.port),
        tls: j.tls === 'tls', sni: j.sni || j.host || j.add, name: j.ps || '',
      };
    }
    if (proto === 'ss') {
      let rest = uri.slice(5);
      let name = '';
      const hashAt = rest.indexOf('#');
      if (hashAt >= 0) { name = decodeName(rest.slice(hashAt + 1)); rest = rest.slice(0, hashAt); }
      rest = rest.split('?')[0].replace(/\/$/, '');
      if (!rest.includes('@')) rest = b64decode(rest);
      const hp = rest.slice(rest.lastIndexOf('@') + 1);
      const i = hp.lastIndexOf(':');
      return { proto, uri, host: hp.slice(0, i).replace(/[[\]]/g, ''), port: Number(hp.slice(i + 1)), tls: false, name };
    }
    if (['vless', 'trojan', 'hysteria2', 'hy2'].includes(proto)) {
      const u = new URL(uri);
      const sec = u.searchParams.get('security') || (proto === 'trojan' ? 'tls' : 'none');
      return {
        proto, uri, host: u.hostname.replace(/[[\]]/g, ''), port: Number(u.port || 443),
        // hysteria2 работает по UDP — TCP-проверка для него не подходит
        udp: proto.startsWith('hy'),
        tls: sec === 'tls' || sec === 'reality',
        sni: u.searchParams.get('sni') || u.searchParams.get('host') || u.hostname,
        name: decodeName(u.hash.slice(1)),
      };
    }
  } catch { /* битый ключ */ }
  return null;
}

async function fetchSource(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  let text = await res.text();
  // Некоторые подписки целиком в base64
  if (!PROTOCOLS.some(p => text.includes(p))) {
    try { text = b64decode(text.replace(/\s+/g, '')); } catch { /* ignore */ }
  }
  return text.split(/\r?\n/).map(s => s.trim()).filter(s => PROTOCOLS.some(p => s.startsWith(p)));
}

// Быстрая проверка: TCP-подключение + TLS-рукопожатие (для tls/reality). Возвращает пинг в мс или null.
function quickCheck(k) {
  return new Promise(resolve => {
    const start = Date.now();
    let done = false;
    const finish = (ok, sock) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (sock) sock.destroy();
      resolve(ok ? Date.now() - start : null);
    };
    const timer = setTimeout(() => finish(false, sock), CHECK_TIMEOUT);
    let sock;
    if (k.tls) {
      const servername = net.isIP(k.sni) ? undefined : k.sni;
      sock = tls.connect({ host: k.host, port: k.port, servername, rejectUnauthorized: false }, () => finish(true, sock));
    } else {
      sock = net.connect({ host: k.host, port: k.port }, () => finish(true, sock));
    }
    sock.on('error', () => finish(false, sock));
  });
}

/** Полная проверка одного ключа: быстрый чек, затем (если есть Xray) реальный трафик через ключ. */
async function checkKey(k) {
  const ping = await quickCheck(k);
  if (ping === null || !xray.enabled) return ping;
  return (await xray.xrayCheck([k]))[0];
}

/** Если "отвечает" заведомо несуществующий адрес — сеть перехватывает соединения и быстрая проверка врёт. */
async function networkIsIntercepted() {
  const fake = await quickCheck({ host: '203.0.113.7', port: 443, tls: true, sni: 'example.com' });
  return fake !== null;
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let i = 0;
  await Promise.all(Array.from({ length: limit }, async () => {
    while (i < items.length) { const idx = i++; out[idx] = await fn(items[idx]); }
  }));
  return out;
}

const COUNTRY = [
  [/🇳🇱|netherlands|amsterdam/i, '🇳🇱', 'Нидерланды'], [/🇩🇪|germany|frankfurt/i, '🇩🇪', 'Германия'],
  [/🇫🇮|finland|helsinki/i, '🇫🇮', 'Финляндия'], [/🇺🇸|united states|\busa?\b/i, '🇺🇸', 'США'],
  [/🇬🇧|united kingdom|london/i, '🇬🇧', 'Великобритания'], [/🇫🇷|france|paris/i, '🇫🇷', 'Франция'],
  [/🇸🇪|sweden|stockholm/i, '🇸🇪', 'Швеция'], [/🇵🇱|poland|warsaw/i, '🇵🇱', 'Польша'],
  [/🇹🇷|turkey|istanbul/i, '🇹🇷', 'Турция'], [/🇰🇿|kazakhstan|almaty/i, '🇰🇿', 'Казахстан'],
  [/🇷🇺|russia|moscow/i, '🇷🇺', 'Россия'], [/🇱🇻|latvia|riga/i, '🇱🇻', 'Латвия'],
  [/🇪🇪|estonia|tallinn/i, '🇪🇪', 'Эстония'], [/🇯🇵|japan|tokyo/i, '🇯🇵', 'Япония'],
  [/🇸🇬|singapore/i, '🇸🇬', 'Сингапур'], [/🇨🇦|canada/i, '🇨🇦', 'Канада'],
];
function country(name) {
  for (const [re, flag, title] of COUNTRY) if (re.test(name)) return { flag, title };
  return { flag: '🌐', title: 'Сервер' };
}

/** Собирает ключи из всех источников и оставляет только прошедшие проверку. */
async function collect(log = console.log) {
  const lines = [];
  for (const src of SOURCES) {
    try { const l = await fetchSource(src); lines.push(...l); log(`[pool] ${l.length} ключей из ${src}`); }
    catch (e) { log(`[pool] источник недоступен: ${e.message}`); }
  }
  const seen = new Set();
  const candidates = [];
  for (const line of lines) {
    const k = parseKey(line);
    if (!k || k.udp || !k.host || !(k.port > 0 && k.port < 65536)) continue;
    const id = `${k.proto}|${k.host}|${k.port}`;
    if (seen.has(id)) continue;
    seen.add(id);
    k.id = id;
    candidates.push(k);
    if (candidates.length >= MAX_CANDIDATES) break;
  }
  log(`[pool] проверяю ${candidates.length} уникальных серверов…`);
  if (await networkIsIntercepted()) {
    log('[pool] ВНИМАНИЕ: сеть перехватывает соединения (прокси/песочница) — быстрая проверка недостоверна.' +
      (xray.enabled ? ' Решение примет только Xray.' : ' Задайте XRAY_PATH или запустите на обычном сервере.'));
  }
  const pings = await mapLimit(candidates, CONCURRENCY, quickCheck);
  let alive = candidates
    .map((k, i) => ({ ...k, ping: pings[i], ...country(k.name), checkedAt: Date.now() }))
    .filter(k => k.ping !== null);
  log(`[pool] прошли быструю проверку: ${alive.length} из ${candidates.length}`);
  if (xray.enabled) {
    log(`[pool] реальная проверка через Xray (${alive.length} шт.)…`);
    const real = await xray.xrayCheck(alive);
    alive = alive.map((k, i) => ({ ...k, ping: real[i], verified: 'xray' })).filter(k => k.ping !== null);
  }
  alive.sort((a, b) => a.ping - b.ping);
  log(`[pool] рабочих: ${alive.length} из ${candidates.length}` + (xray.enabled ? ' (проверено Xray)' : ' (TCP/TLS-проверка)'));
  return alive;
}

module.exports = { collect, checkKey, quickCheck, parseKey, networkIsIntercepted, SOURCES };
