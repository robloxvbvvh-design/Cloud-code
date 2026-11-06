'use strict';
/* ===== Утилиты ===== */
const $ = (s, e = document) => e.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const LPU = 4, HEART_MS = 5 * 60e3, MAX_H = 5, KEY = 'lingo-clone-v1';
const dayStr = (d = new Date()) => { const z = new Date(d - d.getTimezoneOffset() * 6e4); return z.toISOString().slice(0, 10); };
const monday = () => { const d = new Date(); d.setDate(d.getDate() - (d.getDay() + 6) % 7); return dayStr(d); };
const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = Math.random() * (i + 1) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; };
const rot = (a, n) => a.map((_, i) => a[(i + n) % a.length]);
const norm = s => s.toLowerCase().replace(/[’`]/g, "'").normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[¿?¡!.,;:]/g, '').replace(/\s+/g, ' ').trim();

/* ===== Состояние ===== */
const fresh = () => ({ course: null, prog: {}, xp: 0, gems: 50, streak: 0, lastDay: null, daily: {}, goal: 30,
  hearts: MAX_H, hts: 0, ach: {}, sound: true, name: 'Ученик', week: monday(), weekXp: 0, lessons: 0, perfect: 0 });
let S;
try { S = Object.assign(fresh(), JSON.parse(localStorage.getItem(KEY) || '{}')); } catch { S = fresh(); }
if (S.week !== monday()) { S.week = monday(); S.weekXp = 0; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
let tab = 'learn';

function syncHearts() {
  if (S.hearts >= MAX_H) { S.hearts = MAX_H; S.hts = 0; return; }
  const g = Math.floor((Date.now() - S.hts) / HEART_MS);
  if (g > 0) { S.hearts = Math.min(MAX_H, S.hearts + g); S.hts = S.hearts >= MAX_H ? 0 : S.hts + g * HEART_MS; save(); }
}
function loseHeart() { if (S.hearts >= MAX_H) S.hts = Date.now(); S.hearts = Math.max(0, S.hearts - 1); save(); }
function curStreak() { const y = new Date(); y.setDate(y.getDate() - 1); return S.lastDay === dayStr() || S.lastDay === dayStr(y) ? S.streak : 0; }

/* ===== Звук и речь ===== */
let actx;
function tone(seq) {
  if (!S.sound) return;
  try {
    actx = actx || new (window.AudioContext || window.webkitAudioContext)();
    let t = actx.currentTime;
    for (const [f, d] of seq) {
      const o = actx.createOscillator(), g = actx.createGain();
      o.type = 'triangle'; o.frequency.value = f; o.connect(g); g.connect(actx.destination);
      g.gain.setValueAtTime(.15, t); g.gain.exponentialRampToValueAtTime(.001, t + d);
      o.start(t); o.stop(t + d); t += d * .9;
    }
  } catch {}
}
const sOk = () => tone([[660, .12], [880, .2]]), sBad = () => tone([[220, .2], [160, .3]]), sWin = () => tone([[523, .12], [659, .12], [784, .12], [1046, .35]]);
function speak(text) {
  try {
    if (!window.speechSynthesis) return false;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text); u.lang = COURSES[S.course].speech; u.rate = .85;
    speechSynthesis.speak(u); return true;
  } catch { return false; }
}
function toast(msg) {
  const t = document.createElement('div'); t.className = 'toast'; t.textContent = msg;
  $('#toasts').append(t); setTimeout(() => t.remove(), 3500);
}

/* ===== Достижения ===== */
const ACH = [
  { id: 'first', icon: '🌱', t: 'Первый шаг', d: 'Пройдите первый урок', f: s => s.lessons >= 1 },
  { id: 'l10', icon: '📚', t: 'Прилежный', d: 'Пройдите 10 уроков', f: s => s.lessons >= 10 },
  { id: 'perfect', icon: '🎯', t: 'Без ошибок', d: 'Пройдите урок без единой ошибки', f: s => s.perfect >= 1 },
  { id: 'p5', icon: '💎', t: 'Перфекционист', d: '5 идеальных уроков', f: s => s.perfect >= 5 },
  { id: 'xp100', icon: '⚡', t: 'Разгон', d: 'Наберите 100 XP', f: s => s.xp >= 100 },
  { id: 'xp500', icon: '🚀', t: 'Ракета', d: 'Наберите 500 XP', f: s => s.xp >= 500 },
  { id: 's3', icon: '🔥', t: 'Огонёк', d: 'Серия 3 дня', f: s => s.streak >= 3 },
  { id: 's7', icon: '🌋', t: 'Неделя огня', d: 'Серия 7 дней', f: s => s.streak >= 7 },
  { id: 'unit', icon: '🏆', t: 'Раздел пройден', d: 'Завершите любой раздел', f: s => Object.values(s.prog).some(n => n >= LPU) }
];
function checkAch() { for (const a of ACH) if (!S.ach[a.id] && a.f(S)) { S.ach[a.id] = dayStr(); S.gems += 10; toast(`${a.icon} Достижение: ${a.t} (+10 💎)`); } }

/* ===== Генератор упражнений ===== */
function buildLesson(code, g, practice) {
  const C = COURSES[code], ui = Math.floor(g / LPU), li = g % LPU, U = C.units[ui];
  const allW = C.units.flatMap(u => u.w), allP = C.units.flatMap(u => u.p);
  const W = rot(U.w, li * 2), P = rot(U.p, li);
  const others = (w, k, idx) => shuffle(allW.filter(x => x[0] !== w[0])).slice(0, 3).map(x => x[idx]);
  const choose = (w, rev) => ({ t: 'choose', q: rev ? `Как будет «${w[1]}»?` : `Как переводится «${w[0]}»?`, say: rev ? null : w[0],
    a: w[rev ? 0 : 1], opts: shuffle([w[rev ? 0 : 1], ...others(w, 0, rev ? 0 : 1)]) });
  const listen = w => ({ t: 'listen', q: 'Что вы слышите?', say: w[0], a: w[0], hint: w[1], opts: shuffle([w[0], ...others(w, 0, 0)]) });
  const type = (w, rev) => ({ t: 'type', q: rev ? `Переведите: «${w[0]}»` : `Напишите на языке «${C.name}»: «${w[1]}»`, say: rev ? w[0] : null, a: w[rev ? 1 : 0] });
  const build = (p, rev) => {
    const a = p[rev ? 1 : 0], q = p[rev ? 0 : 1], toks = a.split(' ');
    const pool = allP.flatMap(x => x[rev ? 1 : 0].split(' ')).filter(x => !toks.includes(x));
    const extra = shuffle([...new Set(pool)]).slice(0, 3);
    return { t: 'build', q: rev ? 'Переведите на русский' : 'Переведите на изучаемый язык', src: q, say: rev ? q : null, a, bank: shuffle([...toks, ...extra]) };
  };
  const match = ws => ({ t: 'match', q: 'Найдите пары', pairs: ws.map(w => [w[0], w[1]]) });
  const alt = li % 2;
  const list = [
    choose(W[0], false), choose(W[1], true), listen(W[2]), match(W.slice(0, 5)), type(W[3], alt === 1),
    build(P[0], false), choose(W[4], alt === 1), build(P[1], true), type(W[5], alt === 0), build(P[2], false)
  ];
  return list;
}

/* ===== Урок ===== */
let L = null;
function startLesson(g, practice = false) {
  syncHearts();
  if (!practice && S.hearts <= 0) return heartsModal();
  L = { g, practice, q: buildLesson(S.course, g, practice).map(e => ({ ...e })), i: 0, miss: 0, n0: 10, state: 'ask' };
  $('#lesson').classList.remove('hidden');
  showIntro();
}
function showIntro() {
  const C = COURSES[S.course], ui = Math.floor(L.g / LPU), li = L.g % LPU, U = C.units[ui];
  const W = rot(U.w, li * 2).slice(0, 6), P = rot(U.p, li);
  L.intro = true;
  const card = (a, b) => `<div class="learn"><button class="spk sm" data-act="say" data-t="${esc(a)}" aria-label="Озвучить">🔊</button><div class="grow"><b>${esc(a)}</b><div class="muted">${esc(b)}</div></div></div>`;
  $('#lesson').innerHTML = `<div class="l-top"><button class="x" data-act="quit" aria-label="Выйти">✕</button><div class="bar"><i style="width:0"></i></div><div class="l-hearts">${L.practice ? '🎓' : '❤️ ' + S.hearts}</div></div>
    <div class="l-main"><h2 class="q">📖 Новые слова</h2><p class="muted">Сначала запомните слова, потом будут задания. Нажмите 🔊, чтобы послушать.</p>
    <div class="card">${W.map(w => card(w[0], w[1])).join('')}</div><h3>Фразы</h3><div class="card">${P.map(p => card(p[0], p[1])).join('')}</div></div>
    <div class="l-foot"><button class="btn" data-act="introgo">Начать урок</button></div>`;
}
function introGo() { L.intro = false; showEx(); }
function closeLesson() { L = null; $('#lesson').classList.add('hidden'); $('#lesson').innerHTML = ''; render(); }
function lessonShell(inner) {
  const pct = Math.min(100, Math.round(L.i / L.q.length * 100));
  return `<div class="l-top"><button class="x" data-act="quit" aria-label="Выйти">✕</button>
    <div class="bar"><i style="width:${pct}%"></i></div>
    <div class="l-hearts">${L.practice ? '🎓' : '❤️'} ${L.practice ? '' : S.hearts}</div></div>
    <div class="l-main">${inner}</div><div class="l-foot" id="foot"></div>`;
}
function speakBtn(txt) { return `<button class="spk" data-act="say" data-t="${esc(txt)}" aria-label="Озвучить">🔊</button>`; }
function showEx() {
  const e = L.q[L.i];
  if (!e) return finishLesson();
  L.state = 'ask'; L.sel = null; L.built = []; L.mp = { a: null, done: 0, bad: 0 };
  let h = `<h2 class="q">${esc(e.q)}</h2>`;
  if (e.t === 'choose' || e.t === 'listen') {
    if (e.say) h += `<div class="say">${speakBtn(e.say)}${e.t === 'choose' ? `<span class="word">${esc(e.say)}</span>` : ''}</div>`;
    h += `<div class="opts">${e.opts.map((o, i) => `<button class="opt" data-act="pick" data-i="${i}"><kbd>${i + 1}</kbd>${esc(o)}</button>`).join('')}</div>`;
  } else if (e.t === 'build') {
    h += `<div class="say">${e.say ? speakBtn(e.say) : ''}<span class="bubble">${esc(e.src)}</span></div>
      <div class="line" id="line"></div><div class="bank" id="bank">${e.bank.map((b, i) => `<button class="chip" data-act="chip" data-i="${i}">${esc(b)}</button>`).join('')}</div>`;
  } else if (e.t === 'type') {
    h += `${e.say ? `<div class="say">${speakBtn(e.say)}</div>` : ''}<input id="inp" class="inp" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Введите ответ…">`;
  } else if (e.t === 'match') {
    const L1 = shuffle(e.pairs.map(p => p[0])), R = shuffle(e.pairs.map(p => p[1]));
    h += `<div class="match"><div>${L1.map(x => `<button class="opt m" data-act="m" data-s="0" data-v="${esc(x)}">${esc(x)}</button>`).join('')}</div>
      <div>${R.map(x => `<button class="opt m" data-act="m" data-s="1" data-v="${esc(x)}">${esc(x)}</button>`).join('')}</div></div>`;
  }
  $('#lesson').innerHTML = lessonShell(h);
  if (e.t === 'listen' || (e.t === 'choose' && e.say)) speak(e.say);
  else if (e.t === 'build' && e.say) speak(e.say);
  renderFoot();
  const inp = $('#inp'); if (inp) { inp.focus(); inp.oninput = () => renderFoot(); }
}
function canCheck() {
  const e = L.q[L.i];
  if (e.t === 'choose' || e.t === 'listen') return L.sel !== null;
  if (e.t === 'build') return L.built.length > 0;
  if (e.t === 'type') return ($('#inp')?.value || '').trim().length > 0;
  return false;
}
function renderFoot(fb) {
  const f = $('#foot'); if (!f) return;
  const e = L.q[L.i];
  if (fb) {
    f.className = 'l-foot ' + (fb.ok ? 'good' : 'bad');
    f.innerHTML = `<div class="fb"><b>${fb.ok ? '✔ ' + pick(['Отлично!', 'Верно!', 'Так держать!', 'Великолепно!']) : '✖ Неверно'}</b>
      ${fb.ok ? '' : `<div>Правильный ответ: <b>${esc(fb.ans)}</b></div>`}</div><button class="btn ${fb.ok ? '' : 'red'}" data-act="next">Продолжить</button>`;
    return;
  }
  f.className = 'l-foot';
  if (e.t === 'match') { f.innerHTML = `<span class="muted">Соедините слова с переводами</span>`; return; }
  f.innerHTML = `<button class="btn ghost" data-act="skip">${e.t === 'listen' ? 'Не могу слушать' : 'Пропустить'}</button>
    <button class="btn" data-act="check" ${canCheck() ? '' : 'disabled'}>Проверить</button>`;
}
const pick = a => a[Math.random() * a.length | 0];
function answerEx(ok, ans) {
  const e = L.q[L.i];
  L.state = 'fb';
  document.querySelectorAll('.opt,.chip,.inp').forEach(x => x.disabled = true);
  if (ok) sOk(); else {
    sBad(); L.miss++;
    if (!e.retry) { L.q.push({ ...e, retry: true }); }
    if (!L.practice) loseHeart();
    const hh = $('.l-hearts'); if (hh) hh.textContent = '❤️ ' + S.hearts;
  }
  renderFoot({ ok, ans });
}
function check() {
  const e = L.q[L.i];
  if (L.state !== 'ask' || !canCheck()) return;
  let ok, ans = e.a;
  if (e.t === 'choose' || e.t === 'listen') {
    ok = e.opts[L.sel] === e.a;
    document.querySelectorAll('.opt').forEach((b, i) => { if (e.opts[i] === e.a) b.classList.add('right'); else if (i === L.sel) b.classList.add('wrong'); });
  } else if (e.t === 'build') ok = norm(L.built.map(i => e.bank[i]).join(' ')) === norm(e.a);
  else ok = norm($('#inp').value) === norm(e.a);
  answerEx(ok, ans);
}
function next() {
  if (L.state !== 'fb') return;
  if (!L.practice && S.hearts <= 0) { const m = L; L = null; $('#lesson').classList.add('hidden'); render(); return heartsModal(true); }
  L.i++; showEx();
}
function finishLesson() {
  const perfect = L.miss === 0, first = !L.practice && L.g === (S.prog[S.course] || 0);
  const xp = L.practice ? 5 : 10 + (perfect ? 5 : 0) + (first ? 0 : -3), gems = L.practice ? 0 : 5 + (perfect ? 5 : 0);
  const day = dayStr(), y = new Date(); y.setDate(y.getDate() - 1);
  if (S.lastDay !== day) { S.streak = S.lastDay === dayStr(y) ? S.streak + 1 : 1; S.lastDay = day; }
  S.xp += xp; S.weekXp += xp; S.gems += gems; S.daily[day] = (S.daily[day] || 0) + xp;
  S.lessons++; if (perfect) S.perfect++;
  if (L.practice) S.hearts = Math.min(MAX_H, S.hearts + 1);
  if (first) S.prog[S.course] = L.g + 1;
  checkAch(); save(); sWin();
  const acc = Math.max(0, Math.round((10 / (10 + L.miss)) * 100));
  $('#lesson').innerHTML = `<div class="done"><div class="trophy">${perfect ? '🏆' : '🎉'}</div><h1>Урок пройден!</h1>
    <div class="stats"><div class="st xp"><small>ВСЕГО XP</small><b>⚡ ${xp}</b></div>
    <div class="st ac"><small>ТОЧНОСТЬ</small><b>🎯 ${acc}%</b></div>
    <div class="st gm"><small>КРИСТАЛЛЫ</small><b>💎 ${gems}</b></div></div>
    <p class="muted">${S.daily[day] >= S.goal ? '🎯 Дневная цель выполнена!' : `До цели дня: ${S.goal - S.daily[day]} XP`} · 🔥 серия ${S.streak}</p>
    <div class="l-foot"><button class="btn" data-act="quit-done">Продолжить</button></div></div>`;
  confetti();
}
function confetti() {
  for (let i = 0; i < 40; i++) {
    const c = document.createElement('i'); c.className = 'conf';
    c.style.cssText = `left:${Math.random() * 100}%;background:hsl(${Math.random() * 360},80%,60%);animation-delay:${Math.random() * .6}s;animation-duration:${1.8 + Math.random() * 1.5}s`;
    $('#lesson').append(c); setTimeout(() => c.remove(), 4000);
  }
}

/* ===== Модальные окна ===== */
function modal(html) { const m = $('#modal'); m.innerHTML = `<div class="mbg" data-act="close"></div><div class="mbox">${html}</div>`; m.classList.remove('hidden'); }
function closeModal() { $('#modal').classList.add('hidden'); $('#modal').innerHTML = ''; }
function heartsModal(lost) {
  syncHearts();
  const left = S.hearts >= MAX_H ? 0 : Math.max(0, HEART_MS - (Date.now() - S.hts));
  modal(`<div class="big">💔</div><h2>${lost ? 'Сердца закончились' : 'Нет сердец'}</h2>
    <p class="muted">Следующее сердце через ${Math.ceil(left / 60000)} мин. Вы можете потренироваться или купить сердца.</p>
    <button class="btn" data-act="practice">Тренировка: +1 ❤️ бесплатно</button>
    <button class="btn blue" data-act="buy" ${S.gems < 50 ? 'disabled' : ''}>Восстановить все за 50 💎</button>
    <button class="btn ghost" data-act="close">Не сейчас</button>`);
}
function courseModal() {
  modal(`<h2>Я хочу выучить…</h2><div class="courses">${Object.entries(COURSES).map(([k, c]) =>
    `<button class="course" data-act="course" data-k="${k}"><span>${c.flag}</span>${c.name}</button>`).join('')}</div>`);
}

/* ===== Экраны ===== */
function ringSvg(p) { const r = 15, c = 2 * Math.PI * r; return `<svg viewBox="0 0 36 36" width="38" height="38"><circle cx="18" cy="18" r="${r}" fill="none" stroke="#e5e5e5" stroke-width="4"/><circle cx="18" cy="18" r="${r}" fill="none" stroke="#ffc800" stroke-width="4" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - Math.min(1, p))}" transform="rotate(-90 18 18)"/></svg>`; }
function topbar() {
  const c = COURSES[S.course];
  const left = S.hearts >= MAX_H ? '' : ` <small>${Math.ceil(Math.max(0, HEART_MS - (Date.now() - S.hts)) / 60000)}м</small>`;
  return `<div class="stats-bar"><button class="pill" data-act="chcourse">${c.flag}</button>
    <span class="pill fire">🔥 ${curStreak()}</span><span class="pill gem">💎 ${S.gems}</span><span class="pill heart">❤️ ${S.hearts}${left}</span></div>`;
}
function learnView() {
  const C = COURSES[S.course], done = S.prog[S.course] || 0, today = S.daily[dayStr()] || 0;
  let h = `<div class="goal"><div>${ringSvg(today / S.goal)}</div><div><b>Цель дня</b><div class="muted">${today}/${S.goal} XP</div></div></div><div class="path">`;
  C.units.forEach((u, ui) => {
    h += `<div class="unit" style="background:${C.color}"><div><small>РАЗДЕЛ ${ui + 1}</small><h3>${u.title}</h3></div><span>${u.icon}</span></div>`;
    for (let li = 0; li < LPU; li++) {
      const g = ui * LPU + li, st = g < done ? 'done' : g === done ? 'cur' : 'lock';
      const off = [0, 44, 0, -44][li];
      h += `<div class="node-row" style="transform:translateX(${off}px)">${st === 'cur' ? '<div class="start">НАЧАТЬ</div>' : ''}
        <button class="node ${st}" style="--c:${C.color}" data-act="${st === 'lock' ? 'locked' : 'lesson'}" data-g="${g}" aria-label="Урок ${g + 1}">${st === 'done' ? '✔' : st === 'cur' ? '⭐' : '🔒'}</button></div>`;
    }
  });
  const total = C.units.length * LPU;
  if (done >= total) h += `<div class="unit" style="background:#58cc02"><div><h3>🏆 Курс пройден!</h3><small>Повторяйте уроки или выберите другой язык</small></div></div>`;
  return h + '</div>';
}
function leagueView() {
  let seed = +monday().replace(/-/g, ''); const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const names = ['Алиса', 'Boris', 'Maria', 'Дима', 'Sofia', 'Ivan', 'Катя', 'Max', 'Лена', 'Oleg', 'Nina', 'Артём', 'Eva', 'Роман', 'Zoe', 'Тимур', 'Anya', 'Leo', 'Вера'];
  const rows = names.map(n => ({ n, x: Math.floor(rnd() * 380) + 20 })).concat([{ n: S.name + ' (вы)', x: S.weekXp, me: 1 }]).sort((a, b) => b.x - a.x);
  const rank = rows.findIndex(r => r.me) + 1;
  return `<h2 class="title">🥉 Бронзовая лига</h2><p class="muted">Топ-10 переходят в серебряную лигу. Ваше место: <b>${rank}</b></p><div class="card">${rows.slice(0, 15).map((r, i) =>
    `<div class="row ${r.me ? 'me' : ''} ${i < 10 ? 'up' : ''}"><b class="rk">${i + 1}</b><span class="av">${r.n[0]}</span><span class="grow">${esc(r.n)}</span><b>${r.x} XP</b></div>`).join('')}</div>`;
}
function achView() {
  return `<h2 class="title">Достижения</h2><div class="card">${ACH.map(a => {
    const got = S.ach[a.id]; return `<div class="row ${got ? '' : 'off'}"><span class="ico">${a.icon}</span><span class="grow"><b>${a.t}</b><div class="muted">${a.d}</div></span>${got ? '✅' : '🔒'}</div>`;
  }).join('')}</div>`;
}
function profileView() {
  const last7 = [...Array(7)].map((_, i) => { const d = new Date(); d.setDate(d.getDate() - 6 + i); return [d.toLocaleDateString('ru', { weekday: 'short' }), S.daily[dayStr(d)] || 0]; });
  const mx = Math.max(S.goal, ...last7.map(x => x[1]));
  return `<h2 class="title">Профиль</h2><div class="card prof"><div class="avatar">${esc(S.name[0] || '?')}</div>
    <div class="grow"><input id="name" class="inp sm" value="${esc(S.name)}" maxlength="20"></div></div>
    <div class="grid"><div class="card st"><b>🔥 ${curStreak()}</b><small>серия</small></div><div class="card st"><b>⚡ ${S.xp}</b><small>всего XP</small></div>
    <div class="card st"><b>📚 ${S.lessons}</b><small>уроков</small></div><div class="card st"><b>🎯 ${S.perfect}</b><small>идеальных</small></div></div>
    <div class="card"><b>XP за неделю</b><div class="chart">${last7.map(([d, v]) => `<div><i style="height:${Math.round(v / mx * 90)}px"></i><small>${d}</small></div>`).join('')}</div></div>
    <div class="card"><b>Дневная цель</b><div class="goals">${[10, 20, 30, 50].map(g => `<button class="chipbtn ${S.goal === g ? 'on' : ''}" data-act="goal" data-g="${g}">${g} XP</button>`).join('')}</div></div>
    <div class="card row"><span class="grow">Звуковые эффекты</span><button class="chipbtn ${S.sound ? 'on' : ''}" data-act="sound">${S.sound ? 'Вкл' : 'Выкл'}</button></div>
    <button class="btn ghost" data-act="reset">Сбросить прогресс</button>`;
}
function render() {
  if (!S.course) { $('#app').innerHTML = `<div class="welcome"><div class="logo">🦉</div><h1>Lingo</h1><p>Учите языки играя: уроки, серии, кристаллы и лиги.</p></div>`; return courseModal(); }
  syncHearts();
  const tabs = [['learn', '🏠', 'Учиться'], ['league', '🏆', 'Лига'], ['ach', '🎖️', 'Награды'], ['prof', '👤', 'Профиль']];
  const body = { learn: learnView, league: leagueView, ach: achView, prof: profileView }[tab]();
  $('#app').innerHTML = `<nav class="nav"><div class="brand">Lingo</div>${tabs.map(([k, i, t]) => `<button class="${tab === k ? 'on' : ''}" data-act="tab" data-k="${k}"><span>${i}</span><em>${t}</em></button>`).join('')}</nav>
    <main><div class="content">${tab === 'learn' ? topbar() : ''}${body}</div></main>`;
  const nm = $('#name'); if (nm) nm.onchange = () => { S.name = nm.value.trim() || 'Ученик'; save(); render(); };
}

/* ===== События ===== */
document.addEventListener('click', ev => {
  const el = ev.target.closest('[data-act]'); if (!el) return;
  const d = el.dataset, act = d.act, e = L && L.q[L.i];
  switch (act) {
    case 'tab': tab = d.k; render(); break;
    case 'course': S.course = d.k; if (!(S.course in S.prog)) S.prog[S.course] = 0; save(); closeModal(); render(); break;
    case 'chcourse': courseModal(); break;
    case 'close': closeModal(); break;
    case 'locked': el.classList.add('shake'); setTimeout(() => el.classList.remove('shake'), 400); toast('Сначала пройдите предыдущие уроки 🔒'); break;
    case 'lesson': startLesson(+d.g); break;
    case 'practice': closeModal(); startLesson(Math.max(0, (S.prog[S.course] || 1) - 1), true); break;
    case 'buy': if (S.gems >= 50) { S.gems -= 50; S.hearts = MAX_H; S.hts = 0; save(); closeModal(); render(); toast('❤️ Сердца восстановлены!'); } break;
    case 'quit': modal(`<div class="big">🦉</div><h2>Выйти из урока?</h2><p class="muted">Весь прогресс урока будет потерян.</p><button class="btn" data-act="close">Продолжить урок</button><button class="btn red" data-act="quit-yes">Выйти</button>`); break;
    case 'quit-yes': closeModal(); closeLesson(); break;
    case 'quit-done': closeLesson(); break;
    case 'introgo': introGo(); break;
    case 'say': speak(d.t); break;
    case 'pick': if (L.state !== 'ask') break; L.sel = +d.i; document.querySelectorAll('.opt').forEach(b => b.classList.toggle('sel', b === el)); renderFoot(); break;
    case 'chip': {
      if (L.state !== 'ask') break;
      const i = +d.i, at = L.built.indexOf(i);
      if (at >= 0) L.built.splice(at, 1); else L.built.push(i);
      $('#line').innerHTML = L.built.map(j => `<button class="chip" data-act="chip" data-i="${j}">${esc(e.bank[j])}</button>`).join('');
      document.querySelectorAll('#bank .chip').forEach(b => b.classList.toggle('used', L.built.includes(+b.dataset.i)));
      renderFoot(); break;
    }
    case 'm': {
      if (L.state !== 'ask' || el.classList.contains('ok')) break;
      const mp = L.mp, side = d.s;
      if (!mp.a) { mp.a = el; el.classList.add('sel'); if (side === '0') speak(d.v); break; }
      if (mp.a === el) { el.classList.remove('sel'); mp.a = null; break; }
      if (mp.a.dataset.s === side) { mp.a.classList.remove('sel'); mp.a = el; el.classList.add('sel'); break; }
      const l = side === '1' ? mp.a : el, r = side === '1' ? el : mp.a;
      const good = e.pairs.some(p => p[0] === l.dataset.v && p[1] === r.dataset.v);
      const a = mp.a; mp.a = null; a.classList.remove('sel');
      if (good) {
        sOk(); [l, r].forEach(b => b.classList.add('ok')); mp.done++;
        if (mp.done === e.pairs.length) { L.state = 'fb'; if (mp.bad && !L.practice) { loseHeart(); $('.l-hearts').textContent = '❤️ ' + S.hearts; } if (mp.bad) L.miss++; setTimeout(() => { L.state = 'fb'; renderFoot({ ok: true }); }, 250); }
      } else { sBad(); mp.bad++; [a, el].forEach(b => b.classList.add('wrong')); setTimeout(() => [a, el].forEach(b => b.classList.remove('wrong')), 450); }
      break;
    }
    case 'check': check(); break;
    case 'skip': if (L.state === 'ask') { answerEx(false, e.t === 'build' ? e.a : e.a); } break;
    case 'next': next(); break;
    case 'goal': S.goal = +d.g; save(); render(); break;
    case 'sound': S.sound = !S.sound; save(); render(); break;
    case 'reset': if (confirm('Сбросить весь прогресс?')) { S = fresh(); save(); tab = 'learn'; render(); } break;
  }
});
document.addEventListener('keydown', ev => {
  if (!L) return;
  if (ev.key === 'Enter') { ev.preventDefault(); if (L.intro) introGo(); else if (L.state === 'fb') next(); else check(); }
  else if (!L.intro && /^[1-4]$/.test(ev.key) && L.state === 'ask' && document.activeElement?.id !== 'inp') $(`.opt[data-i="${+ev.key - 1}"]`)?.click();
});
setInterval(() => { if (!L && S.course && tab === 'learn' && S.hearts < MAX_H && $('#modal').classList.contains('hidden')) render(); }, 30000);
render();
