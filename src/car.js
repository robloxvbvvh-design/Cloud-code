import * as THREE from 'three';
import { CONFIG } from './config.js';

const C = CONFIG.car;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export class Car {
  constructor({ color = 0xff3355, name = 'Car', isPlayer = false, track }) {
    this.name = name;
    this.color = color;
    this.isPlayer = isPlayer;
    this.track = track;

    this.position = new THREE.Vector3();
    this.heading = 0; // 0 = +Z
    this.velocity = new THREE.Vector3();
    this.trackIndex = 0;
    this.trackDistance = 0;
    this.offroad = false;
    this.steerVisual = 0;
    this.vF = 0;
    this.vL = 0;
    this.wheelSpin = 0;

    this._buildMesh();
  }

  get speedKmh() { return Math.abs(this.vF) * 3.6; }
  get speed() { return Math.hypot(this.velocity.x, this.velocity.z); }

  _buildMesh() {
    const g = new THREE.Group();
    const bodyGroup = new THREE.Group();
    g.add(bodyGroup);
    const paint = new THREE.MeshLambertMaterial({ color: this.color, emissive: new THREE.Color(this.color).multiplyScalar(0.25) });
    const dark = new THREE.MeshLambertMaterial({ color: 0x10131c });
    const glass = new THREE.MeshLambertMaterial({ color: 0x0a1020, emissive: 0x0a1a2a });

    const body = new THREE.Mesh(new THREE.BoxGeometry(2, 0.6, 4), paint);
    body.position.y = 0.55;
    const nose = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.3, 1.2), paint);
    nose.position.set(0, 0.45, 1.9);
    const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.5, 1.9), glass);
    cabin.position.set(0, 1.1, -0.3);
    const spoilerBar = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.1, 0.5), dark);
    spoilerBar.position.set(0, 1.15, -1.9);
    for (const sx of [-0.8, 0.8]) {
      const st = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.35, 0.1), dark);
      st.position.set(sx, 0.95, -1.9);
      bodyGroup.add(st);
    }
    // Фары и стоп-сигналы
    const headMat = new THREE.MeshBasicMaterial({ color: 0xfff6c0 });
    const tailMat = new THREE.MeshBasicMaterial({ color: 0xff1122 });
    for (const sx of [-0.7, 0.7]) {
      const h = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.18, 0.1), headMat);
      h.position.set(sx, 0.6, 2.02);
      const t = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.18, 0.1), tailMat);
      t.position.set(sx, 0.65, -2.02);
      bodyGroup.add(h, t);
    }
    bodyGroup.add(body, nose, cabin, spoilerBar);
    bodyGroup.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    this.bodyGroup = bodyGroup;

    // Колёса
    const wheelGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.35, 14);
    wheelGeo.rotateZ(Math.PI / 2);
    const wheelMat = new THREE.MeshLambertMaterial({ color: 0x15161c });
    const hubMat = new THREE.MeshBasicMaterial({ color: 0x9aa0b8 });
    this.wheels = [];
    this.frontPivots = [];
    const pos = [[-1.05, 1.3, true], [1.05, 1.3, true], [-1.05, -1.3, false], [1.05, -1.3, false]];
    for (const [x, z, front] of pos) {
      const pivot = new THREE.Group();
      pivot.position.set(x, 0.4, z);
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.castShadow = true;
      // Метка на колесе, чтобы вращение было видно
      const mark = new THREE.Mesh(new THREE.BoxGeometry(0.37, 0.12, 0.12), hubMat);
      mark.position.set(0, 0, 0.3);
      wheel.add(mark);
      pivot.add(wheel);
      g.add(pivot);
      this.wheels.push(wheel);
      if (front) this.frontPivots.push(pivot);
    }
    this.mesh = g;
  }

  // Поставить машину на позицию/курс, обнулить скорость.
  reset(position, heading) {
    this.position.copy(position);
    this.position.y = 0;
    this.heading = heading;
    this.velocity.set(0, 0, 0);
    this.vF = this.vL = 0;
    this.steerVisual = 0;
    const n = this.track.findNearest(this.position, null);
    this.trackIndex = n.index;
    this.trackDistance = n.distance;
    this.offroad = false;
    this.syncMesh(0);
  }

  // Вернуть на ближайшую точку трассы (по оси) с правильным курсом.
  resetToTrack() {
    const n = this.track.findNearest(this.position, null);
    const s = n.sample;
    this.reset(s.pos, s.heading);
  }

  update(dt, controls) {
    const track = this.track;
    const h = this.heading;
    // forward = (sin h, cos h); right (с точки зрения водителя) = (-cos h, sin h)
    const fx = Math.sin(h), fz = Math.cos(h);
    const rx = -Math.cos(h), rz = Math.sin(h);
    let vF = this.velocity.x * fx + this.velocity.z * fz;
    let vL = this.velocity.x * rx + this.velocity.z * rz;

    const throttle = clamp(controls.throttle || 0, 0, 1);
    const brake = clamp(controls.brake || 0, 0, 1);
    const steer = clamp(controls.steer || 0, -1, 1);
    const handbrake = !!controls.handbrake;

    const offroad = Math.abs(this.trackDistance) > track.halfWidth;
    this.offroad = offroad;
    const maxSpeed = C.maxSpeed * (offroad ? C.offroadFactor : 1);

    // Газ / тормоз / задний ход
    vF += C.accel * throttle * dt;
    if (brake > 0) {
      if (vF > 0.5) vF = Math.max(0, vF - C.brakeForce * brake * dt);
      else vF = Math.max(-C.maxReverse, vF - C.accel * brake * dt);
    }

    // Сопротивление
    vF -= vF * (C.drag + (offroad ? C.offroadDrag : 0)) * dt;
    if (Math.abs(vF) > 0.01) {
      const roll = C.rolling * dt;
      vF = Math.abs(vF) <= roll ? 0 : vF - Math.sign(vF) * roll;
    }
    if (vF > maxSpeed) vF = offroad ? maxSpeed + (vF - maxSpeed) * Math.exp(-4 * dt) : maxSpeed;
    vF = Math.max(vF, -C.maxReverse);

    // Руление: steer > 0 = поворот направо
    const speedFactor = clamp(Math.abs(vF) / 8, 0, 1) * (1 - 0.45 * Math.min(1, Math.abs(vF) / C.maxSpeed));
    let steerRate = C.maxSteer * steer * speedFactor;
    if (vF < 0) steerRate = -steerRate;
    this.heading -= steerRate * dt; // heading растёт против часовой => вправо это минус

    // Сцепление (дрифт)
    const grip = handbrake ? C.handbrakeGrip : C.grip;
    vL *= Math.exp(-grip * dt);
    if (handbrake) vF *= 1 - 0.6 * dt;

    // Новая ориентация для сборки скорости: используем старый базис (скорость мировая)
    this.velocity.x = fx * vF + rx * vL;
    this.velocity.z = fz * vF + rz * vL;
    this.position.x += this.velocity.x * dt;
    this.position.z += this.velocity.z * dt;

    // Трасса, обочина, стены
    const n = track.findNearest(this.position, this.trackIndex);
    this.trackIndex = n.index;
    this.trackDistance = n.distance;
    const lim = track.wallOffset - 1;
    if (Math.abs(n.distance) > lim) {
      const sgn = Math.sign(n.distance);
      const s = n.sample;
      // Вытолкнуть на границу
      this.position.x = s.pos.x + s.normal.x * lim * sgn;
      this.position.z = s.pos.z + s.normal.z * lim * sgn;
      // Составляющая скорости вдоль нормали (наружу)
      const vn = (this.velocity.x * s.normal.x + this.velocity.z * s.normal.z) * sgn;
      if (vn > 0) {
        this.velocity.x -= s.normal.x * vn * sgn;
        this.velocity.z -= s.normal.z * vn * sgn;
        // сильный удар — общая скорость x0.6, касание вдоль стены — мягкое трение
        const k = vn > 3 ? C.wallRestitutionSpeed : Math.max(0, 1 - 1.2 * dt);
        this.velocity.x *= k;
        this.velocity.z *= k;
      }
    }

    // Пересчёт для HUD/визуала
    const nfx = Math.sin(this.heading), nfz = Math.cos(this.heading);
    this.vF = this.velocity.x * nfx + this.velocity.z * nfz;
    this.vL = this.velocity.x * -Math.cos(this.heading) + this.velocity.z * Math.sin(this.heading);

    this.steerVisual += (steer - this.steerVisual) * Math.min(1, 10 * dt);
    this.syncMesh(dt);
  }

  syncMesh(dt) {
    this.mesh.position.copy(this.position);
    this.mesh.rotation.y = this.heading;
    // Крен от бокового скольжения
    const targetRoll = clamp(this.vL * 0.012, -0.12, 0.12);
    this.bodyGroup.rotation.z += (targetRoll - this.bodyGroup.rotation.z) * Math.min(1, 8 * dt);
    this.wheelSpin += (this.vF * dt) / 0.4;
    for (const w of this.wheels) w.rotation.x = this.wheelSpin;
    for (const p of this.frontPivots) p.rotation.y = -this.steerVisual * 0.45;
  }
}

// Столкновения машин: окружности радиуса C.radius.
export function resolveCarCollisions(cars) {
  const minD = C.radius * 2;
  for (let i = 0; i < cars.length; i++) {
    for (let j = i + 1; j < cars.length; j++) {
      const a = cars[i], b = cars[j];
      let dx = a.position.x - b.position.x, dz = a.position.z - b.position.z;
      let d = Math.hypot(dx, dz);
      if (d >= minD) continue;
      if (d < 1e-4) { dx = 1; dz = 0; d = 1; }
      const nx = dx / d, nz = dz / d;
      const push = (minD - d) / 2;
      a.position.x += nx * push; a.position.z += nz * push;
      b.position.x -= nx * push; b.position.z -= nz * push;
      // Относительная скорость вдоль линии центров
      const rel = (a.velocity.x - b.velocity.x) * nx + (a.velocity.z - b.velocity.z) * nz;
      if (rel < 0) {
        const j2 = -(1 + 0.5) * rel / 2; // равные массы, коэффициент 0.5
        a.velocity.x += nx * j2; a.velocity.z += nz * j2;
        b.velocity.x -= nx * j2; b.velocity.z -= nz * j2;
      }
      a.mesh.position.copy(a.position);
      b.mesh.position.copy(b.position);
    }
  }
}
