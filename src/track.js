import * as THREE from 'three';
import { CONFIG } from './config.js';

const T = CONFIG.track;

export class Track {
  constructor() {
    this.N = T.samples;
    this.halfWidth = T.halfWidth;
    this.wallOffset = T.wallOffset;
    this.window = T.searchWindow;

    const pts = T.points.map(([x, z]) => new THREE.Vector3(x, 0, z));
    this.curve = new THREE.CatmullRomCurve3(pts, true, 'centripetal');
    this.length = this.curve.getLength();
    this.spacing = this.length / this.N;

    // Сэмплы равномерно по длине дуги.
    // Соглашение: heading 0 = +Z, forward = (sin h, 0, cos h).
    // normal — «правая» сторона (как её видит водитель): (-tz, 0, tx).
    this.samples = [];
    for (let i = 0; i < this.N; i++) {
      const u = i / this.N;
      const pos = this.curve.getPointAt(u);
      pos.y = 0;
      const tangent = this.curve.getTangentAt(u);
      tangent.y = 0;
      tangent.normalize();
      const normal = new THREE.Vector3(-tangent.z, 0, tangent.x);
      this.samples.push({ pos, tangent, normal, heading: Math.atan2(tangent.x, tangent.z) });
    }
    this.points2D = this.samples.map((s) => ({ x: s.pos.x, z: s.pos.z }));

    this.group = new THREE.Group();
    this._build();
  }

  wrap(i) {
    const n = this.N;
    return ((i % n) + n) % n;
  }

  getSample(i) {
    return this.samples[this.wrap(Math.round(i))];
  }

  // Ближайший сэмпл; signed distance по normal (+ = справа от оси).
  findNearest(pos, hintIndex = null) {
    const S = this.samples;
    let best = -1, bd = Infinity;
    const test = (i) => {
      const p = S[i].pos;
      const dx = pos.x - p.x, dz = pos.z - p.z;
      const d2 = dx * dx + dz * dz;
      if (d2 < bd) { bd = d2; best = i; }
    };
    if (hintIndex == null) {
      for (let i = 0; i < this.N; i++) test(i);
    } else {
      for (let k = -this.window; k <= this.window; k++) test(this.wrap(hintIndex + k));
    }
    const s = S[best];
    const distance = (pos.x - s.pos.x) * s.normal.x + (pos.z - s.pos.z) * s.normal.z;
    return { index: best, distance, point: s.pos, sample: s };
  }

  // Слот 0..3: решётка 2x2 позади стартовой линии.
  getStartGrid(slot) {
    const row = slot >> 1, col = slot & 1;
    const back = 8 + row * 9; // метров позади линии
    const s = this.getSample(-Math.round(back / this.spacing));
    const lane = col ? 3.2 : -3.2;
    const position = new THREE.Vector3(
      s.pos.x + s.normal.x * lane, 0, s.pos.z + s.normal.z * lane
    );
    return { position, heading: s.heading, index: this.wrap(-Math.round(back / this.spacing)) };
  }

  // ---------- геометрия ----------
  // Лента вдоль трассы по профилю [[offset, y], ...]; colorFn(i, j) -> Color|null.
  _ribbon(profile, colorFn, material) {
    const pos = [], col = [];
    const S = this.samples, N = this.N;
    for (let i = 0; i < N; i++) {
      const a = S[i], b = S[(i + 1) % N];
      for (let j = 0; j < profile.length - 1; j++) {
        const c = colorFn(i, j);
        if (!c) continue;
        const [o0, y0] = profile[j], [o1, y1] = profile[j + 1];
        const A = [a.pos.x + a.normal.x * o0, y0, a.pos.z + a.normal.z * o0];
        const B = [a.pos.x + a.normal.x * o1, y1, a.pos.z + a.normal.z * o1];
        const C = [b.pos.x + b.normal.x * o0, y0, b.pos.z + b.normal.z * o0];
        const D = [b.pos.x + b.normal.x * o1, y1, b.pos.z + b.normal.z * o1];
        pos.push(...A, ...C, ...B, ...B, ...C, ...D);
        for (let k = 0; k < 6; k++) col.push(c.r, c.g, c.b);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals();
    return new THREE.Mesh(g, material);
  }

  _build() {
    const hw = this.halfWidth, wo = this.wallOffset, wh = T.wallHeight;
    const mat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const asphalt = [new THREE.Color(0x2b2e3d), new THREE.Color(0x2e3142)];
    const white = new THREE.Color(0xf2f2f2), red = new THREE.Color(0xd8213a);
    const yellow = new THREE.Color(0xe8e8ff);

    const road = this._ribbon([[-hw, 0.02], [hw, 0.02]], (i) => asphalt[(i >> 3) & 1], mat);
    road.receiveShadow = true;
    this.group.add(road);

    const curbColor = (i) => (((i >> 2) & 1) ? red : white);
    const curbL = this._ribbon([[-hw - 1, 0.03], [-hw, 0.03]], curbColor, mat);
    const curbR = this._ribbon([[hw, 0.03], [hw + 1, 0.03]], curbColor, mat);
    curbL.receiveShadow = curbR.receiveShadow = true;
    this.group.add(curbL, curbR);

    // Центральная пунктирная разметка
    const dash = this._ribbon([[-0.15, 0.035], [0.15, 0.035]], (i) => (((i / 5) | 0) % 2 === 0 ? yellow : null), mat);
    this.group.add(dash);

    // Отбойники
    const wallA = new THREE.Color(0x1a8cff), wallB = new THREE.Color(0xff2e97);
    const wallColor = (i, j) => (j === 1 ? (((i >> 3) & 1) ? wallA : wallB) : (((i >> 3) & 1) ? new THREE.Color(0x14203a) : new THREE.Color(0x2a1430)));
    const wallMat = new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, emissive: 0x151a33 });
    const wR = this._ribbon([[wo, 0], [wo, wh], [wo + 0.6, wh], [wo + 0.6, 0]], wallColor, wallMat);
    const wL = this._ribbon([[-wo, 0], [-wo, wh], [-wo - 0.6, wh], [-wo - 0.6, 0]], wallColor, wallMat);
    this.group.add(wR, wL);

    // Стартовая линия (шахматная полоса)
    const s0 = this.samples[0];
    const pos = [], col = [];
    const cols = 14, rows = 2;
    const blk = new THREE.Color(0x101018);
    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < rows; r++) {
        const o0 = -hw + c * (2 * hw / cols), o1 = o0 + 2 * hw / cols;
        const t0 = (r - 1) * 1.0, t1 = t0 + 1.0;
        const P = (o, t) => [s0.pos.x + s0.normal.x * o + s0.tangent.x * t, 0.05, s0.pos.z + s0.normal.z * o + s0.tangent.z * t];
        pos.push(...P(o0, t0), ...P(o0, t1), ...P(o1, t0), ...P(o1, t0), ...P(o0, t1), ...P(o1, t1));
        const cc = (c + r) % 2 ? white : blk;
        for (let k = 0; k < 6; k++) col.push(cc.r, cc.g, cc.b);
      }
    }
    const sg = new THREE.BufferGeometry();
    sg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    sg.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    sg.computeVertexNormals();
    const startLine = new THREE.Mesh(sg, mat);
    startLine.receiveShadow = true;
    this.group.add(startLine);

    // Арка над стартом
    const arch = new THREE.Group();
    const pillarMat = new THREE.MeshLambertMaterial({ color: 0x2a2f48 });
    const neon = new THREE.MeshBasicMaterial({ color: 0x19e6ff });
    const px = wo - 0.7;
    for (const side of [-1, 1]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.6, 7, 0.6), pillarMat);
      p.position.set(side * px, 3.5, 0);
      p.castShadow = true;
      arch.add(p);
    }
    const beam = new THREE.Mesh(new THREE.BoxGeometry(2 * px + 0.6, 0.9, 0.7), pillarMat);
    beam.position.set(0, 7, 0);
    beam.castShadow = true;
    arch.add(beam);
    const strip = new THREE.Mesh(new THREE.BoxGeometry(2 * px, 0.25, 0.8), neon);
    strip.position.set(0, 7, 0);
    arch.add(strip);
    arch.position.copy(s0.pos);
    arch.rotation.y = s0.heading;
    this.group.add(arch);
  }
}
