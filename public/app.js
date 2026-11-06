const $ = s => document.querySelector(s);
let token = localStorage.getItem('koli_token') || '', cfg = null, image = null, pollT = null, email = '';

async function api(path, opts = {}) {
  const r = await fetch(path, { ...opts, headers: { 'content-type': 'application/json', authorization: 'Bearer ' + token },
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { if (r.status === 401 && token) logout(true); throw new Error(d.error || 'Ошибка'); }
  return d;
}
const msg = (el, t, ok) => { el.textContent = t || ''; el.className = 'msg' + (ok ? ' ok' : ''); };

// --- заставка ---
setTimeout(() => { $('#splash').classList.add('out'); start(); }, 3300);
async function start() {
  if (token) { try { await openStudio(); return; } catch {} }
  $('#auth').classList.remove('hidden');
}

// --- вход ---
async function sendCode() {
  email = $('#email').value.trim();
  $('#send').disabled = true; msg($('#auth-msg'), '');
  try {
    const d = await api('/api/send-code', { method: 'POST', body: { email } });
    $('#sent-to').textContent = email;
    $('#step-email').classList.add('hidden'); $('#step-code').classList.remove('hidden');
    $('#code').focus();
    if (d.dev) msg($('#auth-msg'), 'Почта не настроена: код смотрите в консоли сервера', true);
  } catch (e) { msg($('#auth-msg'), e.message); }
  $('#send').disabled = false;
}
$('#send').onclick = sendCode;
$('#email').onkeydown = e => e.key === 'Enter' && sendCode();
$('#back').onclick = () => { $('#step-code').classList.add('hidden'); $('#step-email').classList.remove('hidden'); msg($('#auth-msg'), ''); };
async function verify() {
  $('#verify').disabled = true;
  try {
    const d = await api('/api/verify', { method: 'POST', body: { email, code: $('#code').value } });
    token = d.token; localStorage.setItem('koli_token', token);
    $('#auth').classList.add('hidden'); await openStudio();
  } catch (e) { msg($('#auth-msg'), e.message); }
  $('#verify').disabled = false;
}
$('#verify').onclick = verify;
$('#code').oninput = e => { e.target.value = e.target.value.replace(/\D/g, ''); if (e.target.value.length === 6) verify(); };
function logout(silent) {
  if (!silent) api('/api/logout', { method: 'POST' }).catch(() => {});
  token = ''; localStorage.removeItem('koli_token'); clearInterval(pollT);
  $('#studio').classList.add('hidden'); $('#auth').classList.remove('hidden');
  $('#step-code').classList.add('hidden'); $('#step-email').classList.remove('hidden'); $('#code').value = '';
}
$('#logout').onclick = () => logout();

// --- студия ---
async function openStudio() {
  cfg = await api('/api/config');
  $('#who').textContent = cfg.email;
  $('#demo-note').classList.toggle('hidden', cfg.live);
  $('#len').max = cfg.maxSeconds;
  const q = $('#quality'); q.innerHTML = '';
  cfg.qualities.forEach(v => { const b = document.createElement('button'); b.textContent = v; b.type = 'button';
    b.onclick = () => { q.dataset.v = v; [...q.children].forEach(c => c.classList.toggle('on', c === b)); }; q.append(b); });
  q.children[1].click();
  $('#studio').classList.remove('hidden');
  loadList(); pollT = setInterval(loadList, 3000);
}
$('#len').oninput = e => $('#len-v').textContent = e.target.value;
$('#drop').onclick = e => { if (e.target.id !== 'rm') $('#img').click(); };
$('#img').onchange = e => {
  const f = e.target.files[0]; if (!f) return;
  if (f.size > 8e6) return msg($('#make-msg'), 'Фото больше 8 МБ');
  const r = new FileReader();
  r.onload = () => { image = r.result; $('#preview').src = image; $('#preview').classList.remove('hidden'); $('#rm').classList.remove('hidden'); $('#drop-txt').textContent = f.name; };
  r.readAsDataURL(f);
};
$('#rm').onclick = () => { image = null; $('#img').value = ''; $('#preview').classList.add('hidden'); $('#rm').classList.add('hidden'); $('#drop-txt').textContent = 'Загрузить фото персонажа'; };
$('#make').onclick = async () => {
  $('#make').disabled = true; msg($('#make-msg'), '');
  try {
    await api('/api/videos', { method: 'POST', body: { prompt: $('#prompt').value, seconds: +$('#len').value, quality: $('#quality').dataset.v, audio: $('#audio').checked, image } });
    msg($('#make-msg'), 'Видео создаётся…', true); loadList();
  } catch (e) { msg($('#make-msg'), e.message); }
  $('#make').disabled = false;
};
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function loadList() {
  let l; try { l = await api('/api/videos'); } catch { return; }
  $('#list').innerHTML = l.map(v => {
    let body = '';
    if (v.status === 'working') body = `<div class="bar"><i style="width:${v.progress}%"></i></div>`;
    else if (v.status === 'done') body = `<video controls playsinline src="/video/${v.id}.mp4?t=${token}"></video>`;
    
    else body = `<div class="msg">${esc(v.error || 'Ошибка')}</div>`;
    return `<div class="vid"><div>${esc(v.prompt)}</div><div class="meta">${v.seconds} с · ${v.quality} · ${v.audio ? 'со звуком' : 'без звука'}</div>${body}</div>`;
  }).join('');
}
