import { CONFIG } from './config.js';

const R = CONFIG.race;

function freshState() {
  return {
    lap: 0, // завершённых кругов
    cp: 0, // сколько чекпоинтов пройдено на текущем круге (3 = осталась только финишная линия)
    lapStartTime: 0,
    lapTimes: [],
    finished: false,
    finishTime: 0,
    prevIndex: null,
    place: 0,
  };
}

export class Race {
  constructor(track) {
    this.track = track;
    this.N = track.N;
    this.laps = CONFIG.laps;
    this.states = new Map();
    this.time = 0;
    this.order = [];
    this.player = null;
    this.playerFinished = false;
    this.playerPlace = 0;
    this.lastLapEvent = null; // {car, lap, time} для HUD
    this.wrongWay = false;
  }

  reset(cars) {
    this.states.clear();
    for (const c of cars) {
      const s = freshState();
      s.prevIndex = c.trackIndex;
      this.states.set(c, s);
      if (c.isPlayer) this.player = c;
    }
    this.time = 0;
    this.playerFinished = false;
    this.playerPlace = 0;
    this.order = cars.slice();
    this.wrongWay = false;
    this.lastLapEvent = null;
  }

  state(car) { return this.states.get(car); }

  update(cars, dt) {
    this.time += dt;
    const N = this.N;
    for (const car of cars) {
      const s = this.states.get(car);
      if (!s || s.finished) continue;
      const idx = car.trackIndex;
      const prev = s.prevIndex;
      s.prevIndex = idx;

      if (s.cp < R.checkpoints.length) {
        const cp = R.checkpoints[s.cp];
        if (idx >= cp && idx <= cp + R.checkpointWindow) s.cp++;
      } else if (prev > N * 0.9 && idx < N * 0.1) {
        // Пересечение финишной линии вперёд после всех чекпоинтов
        const lapTime = this.time - s.lapStartTime;
        s.lapTimes.push(lapTime);
        s.lapStartTime = this.time;
        s.lap++;
        s.cp = 0;
        this.lastLapEvent = { car, lap: s.lap, time: lapTime };
        if (s.lap >= this.laps) {
          s.finished = true;
          s.finishTime = this.time;
        }
      }
    }

    // Рейтинг
    this.order = cars.slice().sort((a, b) => this._cmp(a, b));
    this.order.forEach((c, i) => { this.states.get(c).place = i + 1; });

    if (this.player) {
      const ps = this.states.get(this.player);
      if (ps.finished && !this.playerFinished) {
        this.playerFinished = true;
        this.playerPlace = ps.place;
      }
      this.wrongWay = this._isWrongWay(this.player);
    }
  }

  _cmp(a, b) {
    const sa = this.states.get(a), sb = this.states.get(b);
    if (sa.finished && sb.finished) return sa.finishTime - sb.finishTime;
    if (sa.finished) return -1;
    if (sb.finished) return 1;
    return this.progress(b) - this.progress(a);
  }

  // Непрерывный прогресс в сэмплах: круги * N + индекс (до первого пересечения старта — отрицательный).
  progress(car) {
    const s = this.states.get(car);
    if (!s) return 0;
    let idx = car.trackIndex;
    if (s.cp === 0 && idx > this.N * 0.9) idx -= this.N;
    return s.lap * this.N + idx;
  }

  _isWrongWay(car) {
    if (car.speed < 5) return false;
    const t = this.track.getSample(car.trackIndex).tangent;
    const dot = Math.sin(car.heading) * t.x + Math.cos(car.heading) * t.z;
    return dot < Math.cos((120 * Math.PI) / 180);
  }

  getPosition(car) { return this.states.get(car).place; }
  getLap(car) { return Math.min(this.states.get(car).lap + 1, this.laps); }
  currentLapTime(car) {
    const s = this.states.get(car);
    return s.finished ? s.lapTimes[s.lapTimes.length - 1] : this.time - s.lapStartTime;
  }
  bestLap(car) {
    const t = this.states.get(car).lapTimes;
    return t.length ? Math.min(...t) : null;
  }
  totalTime(car) {
    const s = this.states.get(car);
    return s.finished ? s.finishTime : this.time;
  }
}
