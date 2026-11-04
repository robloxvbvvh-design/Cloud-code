'use strict';
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

// Анонимный ID устройства
let uid = localStorage.getItem('uid');
if (!uid) { uid = crypto.randomUUID(); localStorage.setItem('uid', uid); }

let me = null, skins = [], plans = {}, selectedPlan = 'm1';
const DAY_MIN = 1440;

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? 'POST' : 'GET',
    headers: { 'X-User': uid, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (data.error) { toast(data.error); throw new Error(data.error); }
  return data;
}

function toast(text) {
  const t = $('#toast'); t.textContent = text; t.classList.add('show');
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 2200);
}

function fmtLeft(ms) {
  if (ms <= 0) return me.subEnds ? 'Подписка закончилась' : 'Нет подписки';
  const d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5) % 24, m = Math.floor(ms / 6e4) % 60;
  return d > 0 ? `${d} дн. ${h} ч.` : `${h} ч. ${m} мин.`;
}
const fmtDate = t => t ? new Date(t).toLocaleString('ru-RU', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }) : '—';
const pingClass = p => p < 150 ? 'good' : p < 400 ? 'mid' : 'bad';

// ---------- рендер ----------
function render() {
  if (!me) return;
  const left = me.subEnds - Date.now();
  const on = left > 0;
  $('#statusBadge').textContent = on ? 'Активна' : 'Нет подписки';
  $('#statusBadge').className = 'badge ' + (on ? 'on' : 'off');
  $('#timeLeft').textContent = fmtLeft(left);
  $('#subUntil').textContent = on ? `до ${fmtDate(me.subEnds)}` : 'Оформите подписку или натапайте минуты';

  // подключение
  $('#keyServer').textContent = me.keyServer && me.key
    ? `${me.keyServer.flag} ${me.keyServer.title} · ${me.keyServer.proto.toUpperCase()} · ${me.keyServer.ping} мс`
    : on ? 'Ключ ещё не выдан' : 'Нужна активная подписка';
  $('#newKeyBtn').textContent = me.key ? 'Выдать новый ключ' : 'Получить ключ';
  $('#newKeyBtn').disabled = !on;
  $('#subUrl').textContent = me.subUrl;

  // тапалка
  $('#minutes').textContent = me.minutes.toLocaleString('ru-RU');
  const inDay = me.minutes % DAY_MIN;
  const days = Math.floor(me.minutes / DAY_MIN);
  $('#progressBar').style.width = (days ? 100 : inDay / DAY_MIN * 100) + '%';
  $('#progressText').textContent = days ? `Можно вывести: ${days} дн.` : `${inDay} / ${DAY_MIN} до 1 дня`;
  $('#withdrawBtn').disabled = days < 1;
  const skin = skins.find(s => s.id === me.skin) || { emoji: '🛡️' };
  $('#tapEmoji').textContent = skin.emoji;
  $('#tapBtn').className = 'tap-btn ' + me.skin;
  $('#skins').innerHTML = skins.map(s => {
    const owned = me.skins.includes(s.id);
    return `<button class="skin ${me.skin === s.id ? 'sel' : ''}" data-skin="${s.id}">
      <div class="e">${s.emoji}</div><div>${s.title}</div>
      <div class="muted small">${me.skin === s.id ? 'Выбран' : owned ? 'Выбрать' : s.price + ' мин'}</div></button>`;
  }).join('');

  // кабинет
  $('#pId').textContent = me.id.slice(0, 8);
  $('#pStatus').textContent = on ? (me.payments.length ? 'Подписка' : 'Активна') : 'Не активна';
  $('#pUntil').textContent = on ? fmtDate(me.subEnds) : '—';
  $('#pTaps').textContent = me.tapsTotal.toLocaleString('ru-RU');
  $('#pServer').textContent = me.keyServer ? `${me.keyServer.flag} ${me.keyServer.title}` : '—';
  $('#payments').innerHTML = me.payments.length
    ? me.payments.slice().reverse().map(p => `<li><span class="grow">${p.title}<div class="muted small">${fmtDate(p.at)}</div></span><b>${p.price} ₽</b><span class="muted small">демо</span></li>`).join('')
    : '<li class="muted">Платежей пока нет</li>';
}

async function loadServers() {
  try {
    const s = await api('/api/servers');
    $('#serversMeta').textContent = s.total ? `рабочих: ${s.total}` : s.refreshing ? 'проверяем…' : '';
    $('#servers').innerHTML = s.servers.length
      ? s.servers.map(k => `<li><span class="flag">${k.flag}</span><span class="grow">${k.title}<div class="muted small">${k.proto.toUpperCase()}</div></span><span class="ping ${pingClass(k.ping)}">${k.ping} мс</span></li>`).join('')
      : '<li class="muted">Серверы проверяются, обновите через минуту…</li>';
    if (!s.servers.length) setTimeout(loadServers, 15000);
  } catch { /* toast уже показан */ }
}

// ---------- навигация ----------
function openTab(name) {
  $$('.page').forEach(p => p.classList.toggle('active', p.dataset.page === name));
  $$('.tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
}
$$('.tabs button').forEach(b => b.onclick = () => openTab(b.dataset.tab));
$('#goConnect').onclick = () => openTab('connect');
$$('[data-close]').forEach(b => b.onclick = () => b.closest('.modal').classList.remove('open'));

// ---------- пробный период ----------
$('#trialAccept').onclick = async () => {
  me = await api('/api/trial', { accept: true });
  $('#trialModal').classList.remove('open'); render(); toast('Пробный период на 3 дня активирован 🎉');
};
$('#trialDecline').onclick = async () => {
  me = await api('/api/trial', { accept: false });
  $('#trialModal').classList.remove('open'); render();
};

// ---------- оплата (демо) ----------
function renderPlans() {
  $('#plans').innerHTML = Object.entries(plans).map(([id, p]) =>
    `<button class="plan ${id === selectedPlan ? 'sel' : ''}" data-plan="${id}"><span><b>${p.title}</b><div class="muted small">${Math.round(p.price / p.days * 30)} ₽/мес</div></span><b>${p.price} ₽</b></button>`).join('');
}
$('#plans').onclick = e => { const b = e.target.closest('.plan'); if (b) { selectedPlan = b.dataset.plan; renderPlans(); } };
$('#buyBtn').onclick = () => { renderPlans(); $('#payModal').classList.add('open'); };
$('#payBtn').onclick = async () => {
  const btn = $('#payBtn'); btn.disabled = true; btn.textContent = 'Обработка платежа…';
  await new Promise(r => setTimeout(r, 1200));
  try {
    me = await api('/api/pay', { plan: selectedPlan });
    $('#payModal').classList.remove('open'); render(); toast('Оплата прошла ✅ (демо)');
  } finally { btn.disabled = false; btn.textContent = 'Оплатить'; }
};

// ---------- тапалка ----------
let pending = 0, flushing = false;
$('#tapBtn').addEventListener('pointerdown', e => {
  pending++; me.minutes++; me.tapsTotal++; render();
  const p = document.createElement('div');
  p.className = 'plus'; p.textContent = '+1 мин';
  p.style.left = e.clientX - 25 + 'px'; p.style.top = e.clientY - 20 + 'px';
  document.body.appendChild(p); setTimeout(() => p.remove(), 800);
  if (navigator.vibrate) navigator.vibrate(8);
});
async function flushTaps() {
  if (!pending || flushing) return;
  flushing = true;
  const count = pending; pending = 0;
  try { const r = await api('/api/tap', { count }); me = { ...r, minutes: r.minutes + pending, tapsTotal: r.tapsTotal + pending }; render(); }
  catch { /* ignore */ }
  flushing = false;
}
setInterval(flushTaps, 1000);

$('#withdrawBtn').onclick = async () => {
  await flushTaps();
  const r = await api('/api/withdraw', {});
  me = r; render(); toast(`+${r.withdrawnDays} дн. к подписке 🎉`);
};
$('#skins').onclick = async e => {
  const b = e.target.closest('.skin'); if (!b) return;
  await flushTaps();
  me = await api('/api/skins/buy', { id: b.dataset.skin }); render();
};

// ---------- подключение ----------
$('#newKeyBtn').onclick = async () => {
  const btn = $('#newKeyBtn'); btn.disabled = true; btn.textContent = 'Проверяем сервер…';
  try { me = await api('/api/key', {}); toast('Новый рабочий ключ выдан ✅'); } catch { /* toast */ }
  render();
};

async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch { const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); }
  toast('Скопировано');
}
$('#copySub').onclick = () => copy(me.subUrl);
$('#copyKey').onclick = () => me.key ? copy(me.key) : toast('Сначала получите ключ');

// Диплинки для импорта подписки в приложения
const DEEPLINKS = {
  happ: u => `happ://add/${u}`,
  incy: u => `incy://import/${u}`,
  v2raytun: u => `v2raytun://import/${u}`,
  hiddify: u => `hiddify://import/${u}#TapVPN`,
};
$$('.app').forEach(b => b.onclick = async () => {
  if (!me.active) return toast('Нужна активная подписка');
  if (!me.key) { try { me = await api('/api/key', {}); render(); } catch { return; } }
  copy(me.subUrl);
  location.href = DEEPLINKS[b.dataset.app](me.subUrl);
});

// ---------- старт ----------
(async () => {
  [me, skins, plans] = await Promise.all([api('/api/me'), api('/api/skins'), api('/api/plans')]);
  render();
  if (me.trial === 'pending') $('#trialModal').classList.add('open');
  loadServers();
  setInterval(() => { render(); }, 30000);
  setInterval(loadServers, 120000);
})();
