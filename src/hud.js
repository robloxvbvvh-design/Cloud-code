import { CONFIG } from './config.js';

export function fmtTime(t) {
  if (t == null || !isFinite(t)) return '--:--.---';
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  return String(m).padStart(2, '0') + ':' + s.toFixed(3).padStart(6, '0');
}

export class Hud {
  constructor(track) {
    this.track = track;
    const $ = (id) => document.getElementById(id);
    this.root = $('hud');
    this.speed = $('speed');
    this.lap = $('lap');
    this.place = $('place');
    this.lapTime = $('laptime');
    this.bestLap = $('bestlap');
    this.message = $('message');
    this.mute = $('mute');
    this.canvas = $('minimap');
    this.ctx = this.canvas.getContext('2d');
    this.msgTimer = 0;
    this._buildMapBase();
  }

  show() { this.root.classList.remove('hidden'); }
  hide() { this.root.classList.add('hidden'); }

  _buildMapBase() {
    const pts = this.track.points2D;
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (const p of pts) {
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
      minZ = Math.min(minZ, p.z); maxZ = Math.max(maxZ, p.z);
    }
    const size = this.canvas.width;
    const pad = 14;
    const scale = (size - 2 * pad) / Math.max(maxX - minX, maxZ - minZ);
    const ox = (size - (maxX - minX) * scale) / 2, oy = (size - (maxZ - minZ) * scale) / 2;
    // Вид сверху: x вправо, z вниз (корректная ориентация без зеркалирования)
    this.mapPt = (x, z) => [ox + (x - minX) * scale, oy + (z - minZ) * scale];

    const base = document.createElement('canvas');
    base.width = base.height = size;
    const c = base.getContext('2d');
    c.lineJoin = 'round';
    c.lineWidth = 7; c.strokeStyle = 'rgba(25,230,255,0.25)';
    c.beginPath();
    pts.forEach((p, i) => { const [x, y] = this.mapPt(p.x, p.z); i ? c.lineTo(x, y) : c.moveTo(x, y); });
    c.closePath(); c.stroke();
    c.lineWidth = 2.5; c.strokeStyle = '#19e6ff'; c.stroke();
    // стартовая линия
    const [sx, sy] = this.mapPt(pts[0].x, pts[0].z);
    c.fillStyle = '#fff'; c.fillRect(sx - 5, sy - 1.5, 10, 3);
    this.mapBase = base;
  }

  drawMinimap(cars) {
    const c = this.ctx, size = this.canvas.width;
    c.clearRect(0, 0, size, size);
    c.drawImage(this.mapBase, 0, 0);
    const sorted = cars.slice().sort((a, b) => (a.isPlayer ? 1 : 0) - (b.isPlayer ? 1 : 0));
    for (const car of sorted) {
      const [x, y] = this.mapPt(car.position.x, car.position.z);
      c.fillStyle = '#' + car.color.toString(16).padStart(6, '0');
      c.beginPath();
      c.arc(x, y, car.isPlayer ? 5.5 : 3.8, 0, Math.PI * 2);
      c.fill();
      if (car.isPlayer) { c.strokeStyle = '#fff'; c.lineWidth = 1.5; c.stroke(); }
    }
  }

  showMessage(text, { ms = 0, cls = '' } = {}) {
    this.message.textContent = text;
    this.message.className = cls;
    this.msgTimer = ms;
  }

  clearMessage() { this.message.textContent = ''; this.msgTimer = 0; }

  tick(dt) {
    if (this.msgTimer > 0) {
      this.msgTimer -= dt;
      if (this.msgTimer <= 0) this.clearMessage();
    }
  }

  update(player, race, cars, muted) {
    this.speed.textContent = Math.round(player.speedKmh);
    this.lap.textContent = `${race.getLap(player)}/${race.laps}`;
    this.place.textContent = `${race.getPosition(player)}/${cars.length}`;
    this.lapTime.textContent = fmtTime(race.currentLapTime(player));
    this.bestLap.textContent = fmtTime(race.bestLap(player));
    this.mute.textContent = muted ? 'Звук: выкл (M)' : 'Звук: вкл (M)';
    this.drawMinimap(cars);
  }
}
