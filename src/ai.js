import { CONFIG } from './config.js';

const A = CONFIG.ai;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const wrapAngle = (a) => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const rand = (a, b) => a + Math.random() * (b - a);

export class BotAI {
  constructor(track, race) {
    this.track = track;
    this.race = race;
    this.time = 0;
  }

  // Параметры бота (вызывать при старте гонки)
  setup(bot) {
    bot.ai = {
      skill: rand(A.skillMin, A.skillMax),
      lane: rand(-A.laneMax, A.laneMax),
      phase: rand(0, Math.PI * 2),
      lookahead: Math.round(rand(A.lookaheadMin, A.lookaheadMax)),
      stuckT: 0,
      resets: 0,
    };
  }

  _angleBetween(i, j) {
    const a = this.track.getSample(i).tangent, b = this.track.getSample(j).tangent;
    return Math.acos(clamp(a.x * b.x + a.z * b.z, -1, 1));
  }

  getControls(bot, dt, player) {
    const track = this.track;
    const p = bot.ai;
    const idx = bot.trackIndex;

    // Цель: точка впереди со смещением по полосе
    const lane = clamp(p.lane + Math.sin(this.time * 0.35 + p.phase) * 0.8, -A.laneMax, A.laneMax);
    const ts = track.getSample(idx + p.lookahead);
    const tx = ts.pos.x + ts.normal.x * lane;
    const tz = ts.pos.z + ts.normal.z * lane;
    const desired = Math.atan2(tx - bot.position.x, tz - bot.position.z);
    const diff = wrapAngle(desired - bot.heading);
    // steer > 0 = направо, а положительный diff = цель левее
    const steer = clamp(-diff * 2.5, -1, 1);

    // Скорость по кривизне впереди
    const curv = Math.max(
      this._angleBetween(idx + 10, idx + 40),
      this._angleBetween(idx + 30, idx + 70)
    );
    let rubber = 1;
    if (player && this.race) {
      const d = (this.race.progress(bot) - this.race.progress(player)) / track.N;
      if (d > A.rubberFar) rubber = A.rubberSlow;
      else if (d < -A.rubberFar) rubber = A.rubberFast;
    }
    const target = CONFIG.car.maxSpeed * p.skill * rubber * (1 - 0.45 * clamp(curv / 1.2, 0, 1));
    const v = bot.vF;
    let throttle = 0, brake = 0;
    if (v < target) throttle = 1;
    else brake = clamp((v - target) / 8, 0, 1);

    // Не газовать при большом угле до цели
    if (Math.abs(diff) > 1.0) throttle *= 0.5;

    // Застревание
    if (Math.abs(bot.vF) < A.stuckSpeed) p.stuckT += dt; else p.stuckT = 0;
    if (p.stuckT > A.stuckTime) {
      bot.resetToTrack();
      p.stuckT = 0;
      p.resets++;
    }

    return { throttle, brake, steer, handbrake: false };
  }

  tick(dt) { this.time += dt; }
}
