// Настоящая проверка ключей через Xray-core: ключ поднимается как SOCKS-прокси
// и через него запрашивается http://cp.cloudflare.com/generate_204 (ждём ответ 204).
// Включается, если задан XRAY_PATH (путь к бинарнику xray).
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');

const XRAY_PATH = process.env.XRAY_PATH || '';
const BASE_PORT = Number(process.env.XRAY_BASE_PORT || 20000);
const BATCH = 40;
const TEST_HOST = 'cp.cloudflare.com';

function b64decode(s) {
  s = s.trim().replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Buffer.from(s, 'base64').toString('utf8');
}

function streamSettings(q, host, defaults = {}) {
  const network = q.type || q.net || 'tcp';
  const security = q.security || defaults.security || 'none';
  const s = { network, security };
  const sni = q.sni || q.host || host;
  if (security === 'tls') s.tlsSettings = { serverName: sni, allowInsecure: true, fingerprint: q.fp || 'chrome', alpn: q.alpn ? q.alpn.split(',') : undefined };
  if (security === 'reality') s.realitySettings = { serverName: q.sni, fingerprint: q.fp || 'chrome', publicKey: q.pbk, shortId: q.sid || '', spiderX: q.spx || '' };
  if (network === 'ws') s.wsSettings = { path: q.path || '/', headers: { Host: q.host || sni } };
  if (network === 'grpc') s.grpcSettings = { serviceName: q.serviceName || q.path || '' };
  if (network === 'httpupgrade') s.httpupgradeSettings = { path: q.path || '/', host: q.host || sni };
  if (network === 'xhttp' || network === 'splithttp') { s.network = 'xhttp'; s.xhttpSettings = { path: q.path || '/', host: q.host || sni, mode: q.mode || 'auto' }; }
  return s;
}

/** URI ключа -> outbound для Xray. */
function toOutbound(uri) {
  const proto = uri.slice(0, uri.indexOf('://'));
  if (proto === 'vmess') {
    const j = JSON.parse(b64decode(uri.slice(8)));
    return {
      protocol: 'vmess',
      settings: { vnext: [{ address: j.add, port: Number(j.port), users: [{ id: j.id, alterId: Number(j.aid || 0), security: j.scy || 'auto' }] }] },
      streamSettings: streamSettings({ type: j.net, security: j.tls === 'tls' ? 'tls' : 'none', sni: j.sni, host: j.host, path: j.path, fp: j.fp, alpn: j.alpn }, j.add),
    };
  }
  if (proto === 'ss') {
    let rest = uri.slice(5).split('#')[0].split('?')[0].replace(/\/$/, '');
    if (!rest.includes('@')) rest = b64decode(rest);
    const at = rest.lastIndexOf('@');
    let userinfo = rest.slice(0, at);
    if (!userinfo.includes(':')) userinfo = b64decode(decodeURIComponent(userinfo));
    const [method, ...pw] = userinfo.split(':');
    const hp = rest.slice(at + 1); const i = hp.lastIndexOf(':');
    return { protocol: 'shadowsocks', settings: { servers: [{ address: hp.slice(0, i).replace(/[[\]]/g, ''), port: Number(hp.slice(i + 1)), method, password: pw.join(':') }] } };
  }
  const u = new URL(uri);
  const q = Object.fromEntries(u.searchParams);
  const host = u.hostname.replace(/[[\]]/g, '');
  const port = Number(u.port || 443);
  const user = decodeURIComponent(u.username);
  if (proto === 'vless') {
    return {
      protocol: 'vless',
      settings: { vnext: [{ address: host, port, users: [{ id: user, encryption: q.encryption || 'none', flow: q.flow || '' }] }] },
      streamSettings: streamSettings(q, host),
    };
  }
  if (proto === 'trojan') {
    return { protocol: 'trojan', settings: { servers: [{ address: host, port, password: user }] }, streamSettings: streamSettings(q, host, { security: 'tls' }) };
  }
  throw new Error('unsupported ' + proto);
}

// Минимальный SOCKS5-клиент: CONNECT + HTTP GET, ждём "HTTP/1.1 204".
function probeViaSocks(port, timeout) {
  return new Promise(resolve => {
    const start = Date.now();
    const sock = net.connect(port, '127.0.0.1');
    let stage = 0, buf = Buffer.alloc(0);
    const done = ok => { clearTimeout(t); sock.destroy(); resolve(ok ? Date.now() - start : null); };
    const t = setTimeout(() => done(false), timeout);
    sock.on('error', () => done(false));
    sock.on('connect', () => sock.write(Buffer.from([5, 1, 0])));
    sock.on('data', d => {
      buf = Buffer.concat([buf, d]);
      if (stage === 0 && buf.length >= 2) {
        if (buf[1] !== 0) return done(false);
        buf = Buffer.alloc(0); stage = 1;
        const h = Buffer.from(TEST_HOST);
        sock.write(Buffer.concat([Buffer.from([5, 1, 0, 3, h.length]), h, Buffer.from([0, 80])]));
      } else if (stage === 1 && buf.length >= 10) {
        if (buf[1] !== 0) return done(false);
        buf = Buffer.alloc(0); stage = 2;
        sock.write(`GET /generate_204 HTTP/1.1\r\nHost: ${TEST_HOST}\r\nConnection: close\r\n\r\n`);
      } else if (stage === 2 && buf.length >= 12) {
        done(/^HTTP\/1\.[01] 204/.test(buf.toString('latin1', 0, 12)));
      }
    });
  });
}

async function checkBatch(keys, timeout) {
  const inbounds = [], outbounds = [], rules = [], idx = [];
  keys.forEach((k, i) => {
    try {
      const ob = toOutbound(k.uri);
      ob.tag = 'o' + i;
      outbounds.push(ob);
      inbounds.push({ tag: 'i' + i, listen: '127.0.0.1', port: BASE_PORT + i, protocol: 'socks', settings: { udp: false } });
      rules.push({ type: 'field', inboundTag: ['i' + i], outboundTag: 'o' + i });
      idx.push(i);
    } catch { /* ключ не разобрался */ }
  });
  const result = new Array(keys.length).fill(null);
  if (!idx.length) return result;
  const cfgFile = path.join(os.tmpdir(), `tapvpn-xray-${process.pid}.json`);
  fs.writeFileSync(cfgFile, JSON.stringify({ log: { loglevel: 'none' }, inbounds, outbounds, routing: { rules } }));
  const proc = spawn(XRAY_PATH, ['run', '-c', cfgFile], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 1500));
  const pings = await Promise.all(idx.map(i => probeViaSocks(BASE_PORT + i, timeout)));
  idx.forEach((i, j) => { result[i] = pings[j]; });
  proc.kill();
  await new Promise(r => proc.once('exit', r).once('error', r));
  fs.rmSync(cfgFile, { force: true });
  return result;
}

/** Проверяет ключи через Xray. Возвращает массив пингов (мс) или null для нерабочих. */
async function xrayCheck(keys, timeout = 8000) {
  const out = [];
  for (let i = 0; i < keys.length; i += BATCH) out.push(...await checkBatch(keys.slice(i, i + BATCH), timeout));
  return out;
}

module.exports = { enabled: Boolean(XRAY_PATH), xrayCheck, toOutbound };
