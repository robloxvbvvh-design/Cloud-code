// Smoke-тест: node tests/smoke.mjs
// Поднимает python3 -m http.server, открывает игру в Chromium (Playwright) и проверяет основное.
// Если CDN недоступен, укажите локальную копию three: THREE_LOCAL=/path/to/three.module.js
// (или положите её в node_modules/three/build/three.module.js). Сам index.html всегда использует CDN.
import { createRequire } from 'module';
import { spawn } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 8765;
const results = [];
let failed = false;

function check(name, ok, info = '') {
  results.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${info ? '  (' + info + ')' : ''}`);
  if (!ok) failed = true;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, timeout = 40000, step = 250) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await fn()) return true;
    await sleep(step);
  }
  return false;
}

const server = spawn('python3', ['-m', 'http.server', String(PORT)], { cwd: root, stdio: 'ignore' });
let browser;
try {
  const up = await waitFor(async () => {
    try { return (await fetch(`http://localhost:${PORT}/index.html`)).ok; } catch { return false; }
  }, 10000, 200);
  if (!up) throw new Error('http.server не поднялся');

  browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1100, height: 650 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('requestfailed', (r) => errors.push('requestfailed: ' + r.url()));

  const localThree = process.env.THREE_LOCAL || path.join(root, 'node_modules/three/build/three.module.js');
  if (existsSync(localThree)) {
    const body = readFileSync(localThree);
    await page.route('**/three.module.js', (route) => route.fulfill({ body, contentType: 'text/javascript' }));
    console.log('three.js отдаётся из локальной копии:', localThree);
  }

  await page.goto(`http://localhost:${PORT}/`);
  check('__game создан', await waitFor(() => page.evaluate(() => !!window.__game), 15000));
  check('меню видно до старта', await page.evaluate(() => !document.getElementById('menu').classList.contains('hidden')));
  check('state === MENU', (await page.evaluate(() => __game.state)) === 'MENU');

  // --- Старт и отсчёт ---
  await page.click('#btn-start');
  check('после клика state === COUNTDOWN', (await page.evaluate(() => __game.state)) === 'COUNTDOWN');
  check('в отсчёте машины стоят', (await page.evaluate(() => __game.player.speedKmh)) < 1);
  check('отсчёт заканчивается (RACING)', await waitFor(async () => (await page.evaluate(() => __game.state)) === 'RACING'));

  // --- Газ 3 секунды ---
  const botsBefore = await page.evaluate(() => __game.bots.map((b) => [b.position.x, b.position.z]));
  await page.keyboard.down('KeyW');
  await sleep(3000);
  const afterGas = await page.evaluate(() => ({
    state: __game.state,
    speed: __game.player.speedKmh,
    bots: __game.bots.map((b) => [b.position.x, b.position.z]),
  }));
  check('state === RACING', afterGas.state === 'RACING');
  check('скорость игрока > 0', afterGas.speed > 0, afterGas.speed.toFixed(1) + ' км/ч');
  const moved = afterGas.bots.every((p, i) => Math.hypot(p[0] - botsBefore[i][0], p[1] - botsBefore[i][1]) > 1);
  check('позиции ботов изменились', moved);

  await page.screenshot({ path: path.join(root, 'tests', 'screenshot.png') });
  check('HUD виден', await page.evaluate(() => !document.getElementById('hud').classList.contains('hidden') && document.getElementById('speed').textContent !== ''));

  await page.keyboard.press('Escape');
  check('Esc ставит паузу', (await page.evaluate(() => __game.state)) === 'PAUSED');
  await page.keyboard.press('Escape');
  check('Esc снимает паузу', (await page.evaluate(() => __game.state)) === 'RACING');
  await page.keyboard.up('KeyW');

  // --- ИИ: прогресс ботов за ~10 с игрового времени (детерминированная перемотка без рендера) ---
  await page.evaluate(() => { __game.startRace(); __game.simulate(3.5); });
  check('после перемотки отсчёта state === RACING', (await page.evaluate(() => __game.state)) === 'RACING');
  const samples = [];
  for (let k = 0; k < 11; k++) {
    samples.push(await page.evaluate(() => __game.bots.map((b) => __game.race.progress(b))));
    await page.evaluate(() => __game.simulate(1));
  }
  const resets = await page.evaluate(() => __game.bots.map((b) => b.ai.resets));
  for (let i = 0; i < 3; i++) {
    const total = samples[10][i] - samples[0][i];
    let monotone = true;
    for (let k = 1; k < samples.length; k++) if (samples[k][i] <= samples[k - 1][i]) monotone = false;
    check(`бот ${i + 1}: прогресс растёт каждую секунду`, monotone);
    check(`бот ${i + 1}: проехал > 250 сэмплов за 10 с`, total > 250, `прогресс +${Math.round(total)} из 1000`);
    check(`бот ${i + 1}: без сбросов из-за застревания`, resets[i] === 0, `сбросов: ${resets[i]}`);
  }

  // --- Логика кругов: нельзя засчитать круг без чекпоинтов / задом через финиш ---
  const raceLogic = await page.evaluate(async () => {
    const { Race } = await import('/src/race.js');
    const r = new Race(__game.track);
    const car = { trackIndex: 990, isPlayer: true, heading: 0, speed: 0 };
    r.reset([car]);
    car.trackIndex = 5; r.update([car], 0.1); // срезали: через финиш без чекпоинтов
    const cut = r.state(car).lap;
    car.trackIndex = 995; r.update([car], 0.1); // назад через финиш и снова вперёд
    car.trackIndex = 5; r.update([car], 0.1);
    const back = r.state(car).lap;
    for (const idx of [100, 260, 510, 760, 990, 4]) { car.trackIndex = idx; r.update([car], 0.1); }
    return { cut, back, honest: r.state(car).lap };
  });
  check('круг не засчитывается без чекпоинтов / задом', raceLogic.cut === 0 && raceLogic.back === 0, JSON.stringify(raceLogic));
  check('честный круг засчитывается', raceLogic.honest === 1);

  // --- Полная гонка на автопилоте: финиш и «Ещё раз» ---
  await page.evaluate(() => { __game.startRace(); __game.autopilot = true; __game.simulate(3.5); });
  await page.evaluate(() => __game.simulate(110));
  check('игрок финиширует (FINISHED)', (await page.evaluate(() => __game.state)) === 'FINISHED');
  check('показан экран результатов', await waitFor(() => page.evaluate(() => !document.getElementById('finish').classList.contains('hidden')), 15000));
  const place = await page.evaluate(() => __game.race.playerPlace);
  check('место игрока 1..4', place >= 1 && place <= 4, 'место ' + place);
  await page.click('#btn-again');
  const again = await page.evaluate(() => ({ s: __game.state, lap: __game.race.state(__game.player).lap }));
  check('«Ещё раз» перезапускает гонку', again.s === 'COUNTDOWN' && again.lap === 0);

  check('нет ошибок в консоли', errors.length === 0, errors.join('; '));
} catch (e) {
  check('исключение теста', false, String((e && e.stack) || e));
}

console.log('\n' + results.join('\n'));
if (browser) await browser.close();
server.kill();
console.log(failed ? '\nSMOKE: FAILED' : '\nSMOKE: OK');
process.exit(failed ? 1 : 0);
