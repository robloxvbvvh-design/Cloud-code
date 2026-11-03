import * as THREE from 'three';
import { World } from './world.js';
import { Track } from './track.js';
import { Car, resolveCarCollisions } from './car.js';
import { Input } from './input.js';
import { ChaseCamera } from './camera.js';
import { Race } from './race.js';
import { Hud, fmtTime } from './hud.js';
import { BotAI } from './ai.js';
import { EngineAudio } from './audio.js';
import { CONFIG } from './config.js';

const canvas = document.getElementById('game');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const world = new World();
const track = new Track();
world.scene.add(track.group);
world.addDecor(track);

const input = new Input();
const chase = new ChaseCamera();
const hud = new Hud(track);
const audio = new EngineAudio();

// Машины: игрок + 3 бота
const player = new Car({ color: CONFIG.colors.player, name: 'Вы', isPlayer: true, track });
const bots = CONFIG.colors.bots.map((color, i) => new Car({ color, name: 'Бот ' + (i + 1), track }));
const cars = [player, ...bots];
cars.forEach((c) => world.scene.add(c.mesh));

const race = new Race(track);
const ai = new BotAI(track, race);

// ---- Состояния ----
let state = 'MENU';
let prevState = 'RACING';
let countdown = 3;
let lastShownCount = null;
let finishTimer = 0;
let autopilot = false; // отладка: игрок едет под управлением ИИ

const menuEl = document.getElementById('menu');
const finishEl = document.getElementById('finish');

function placeOnGrid() {
  const botSlots = [0, 1, 3, 2].filter((s) => s !== CONFIG.race.startGridSlotPlayer);
  const gp = track.getStartGrid(CONFIG.race.startGridSlotPlayer);
  player.reset(gp.position, gp.heading);
  bots.forEach((b, i) => {
    const g = track.getStartGrid(botSlots[i]);
    b.reset(g.position, g.heading);
    ai.setup(b);
  });
}

function startRace() {
  audio.start();
  placeOnGrid();
  race.reset(cars);
  ai.time = 0;
  input.reset();
  chase.snap();
  menuEl.classList.add('hidden');
  finishEl.classList.add('hidden');
  hud.show();
  hud.clearMessage();
  countdown = 3;
  lastShownCount = null;
  finishTimer = 0;
  state = 'COUNTDOWN';
}

function showMenu() {
  state = 'MENU';
  menuEl.classList.remove('hidden');
  finishEl.classList.add('hidden');
  hud.hide();
}

function showFinish() {
  const ps = race.state(player);
  document.getElementById('fin-place').textContent = `${race.playerPlace} из ${cars.length}`;
  document.getElementById('fin-total').textContent = fmtTime(ps.finishTime);
  document.getElementById('fin-best').textContent = fmtTime(race.bestLap(player));
  const tbl = document.getElementById('results');
  tbl.innerHTML = '';
  race.order.forEach((c, i) => {
    const s = race.state(c);
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${i + 1}</td><td style="color:#${c.color.toString(16).padStart(6, '0')}">${c.name}</td><td>${s.finished ? fmtTime(s.finishTime) : 'в пути'}</td>`;
    tbl.appendChild(tr);
  });
  finishEl.classList.remove('hidden');
}

function togglePause() {
  if (state === 'RACING') {
    prevState = state;
    state = 'PAUSED';
    hud.showMessage('ПАУЗА', { cls: 'small' });
  } else if (state === 'PAUSED') {
    state = prevState;
    hud.clearMessage();
  }
}

document.getElementById('btn-start').addEventListener('click', startRace);
document.getElementById('btn-again').addEventListener('click', startRace);
input.onPress('KeyC', () => chase.toggle());
input.onPress('KeyR', () => { if (state === 'RACING') player.resetToTrack(); });
input.onPress(['Escape', 'KeyP'], togglePause);
input.onPress('KeyM', () => audio.toggleMute());

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  chase.resize(w, h);
}
window.addEventListener('resize', resize);
resize();

// Стартовый вид для меню: камера у стартовой решётки
const menuFocus = track.getStartGrid(0);
function menuCamera(t) {
  const cam = chase.camera;
  const a = t * 0.1;
  cam.position.set(menuFocus.position.x + Math.cos(a) * 30, 9, menuFocus.position.z + Math.sin(a) * 30);
  cam.lookAt(menuFocus.position.x + 10, 1, menuFocus.position.z);
}

placeOnGrid();
race.reset(cars);
chase.snap();

// ---- Игровой цикл ----
let last = performance.now();
function loop(now) {
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  step(dt, now / 1000);
  renderer.render(world.scene, chase.camera);
  requestAnimationFrame(loop);
}

function step(dt, t) {
  if (state === 'COUNTDOWN') {
    countdown -= dt;
    const n = Math.ceil(countdown);
    if (countdown > 0 && n !== lastShownCount) {
      lastShownCount = n;
      hud.showMessage(String(n));
    }
    if (countdown <= 0) {
      state = 'RACING';
      hud.showMessage('СТАРТ!', { ms: 1 });
    }
  }

  if (state === 'RACING' || state === 'FINISHED') {
    ai.tick(dt);
    if (state === 'RACING') {
      if (autopilot) { if (!player.ai) ai.setup(player); player.update(dt, ai.getControls(player, dt, null)); }
      else player.update(dt, input.getControls(dt));
    }
    else player.update(dt, { throttle: 0, brake: 0.4, steer: 0, handbrake: false });
    for (const b of bots) b.update(dt, ai.getControls(b, dt, player));
    resolveCarCollisions(cars);
    const lapsBefore = race.state(player).lap;
    race.update(cars, dt);
    const ps = race.state(player);
    if (state === 'RACING') {
      if (ps.lap > lapsBefore && !ps.finished) {
        hud.showMessage(ps.lap === race.laps - 1 ? 'Последний круг!' : `Круг ${ps.lap + 1}`, { ms: 2, cls: 'small' });
      }
      if (race.wrongWay) hud.showMessage('НЕ ТУДА', { cls: 'warn small' });
      else if (hud.message.textContent === 'НЕ ТУДА') hud.clearMessage();
      if (race.playerFinished) {
        state = 'FINISHED';
        finishTimer = 1.8;
        hud.showMessage('ФИНИШ!', { ms: 0 });
      }
    } else if (state === 'FINISHED' && finishTimer > 0) {
      finishTimer -= dt;
      if (finishTimer <= 0) showFinish();
    }
  }

  if (state !== 'MENU') {
    if (state !== 'PAUSED') chase.update(player, dt);
    hud.tick(state === 'PAUSED' ? 0 : dt);
    hud.update(player, race, cars, audio.muted);
    audio.update(Math.min(1, player.speedKmh / (CONFIG.car.maxSpeed * 3.6)), input.isDown('KeyW', 'ArrowUp') ? 1 : 0, state === 'RACING' || state === 'FINISHED');
  } else {
    menuCamera(t);
  }
  world.update(player.position);
}

requestAnimationFrame(loop);

window.__game = {
  get state() { return state; },
  player, cars, bots, race, track, ai, world,
  startRace,
  get autopilot() { return autopilot; },
  set autopilot(v) { autopilot = !!v; },
  // Отладка/тесты: промотать симуляцию без рендера (шаг 1/60 с)
  simulate(seconds, dt = 1 / 60) {
    const n = Math.round(seconds / dt);
    for (let i = 0; i < n; i++) step(dt, performance.now() / 1000);
  },
};
