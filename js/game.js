/* Пернатый Отряд — оригинальный 3D шутер с курицами (Three.js r128).
   Все модели собираются из примитивов кодом; статика карты сливается
   в один меш (1 draw call), поэтому игра быстро работает на телефонах. */
(function () {
'use strict';
const T = THREE;
const $ = (id) => document.getElementById(id);
const rand = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const isTouch = ('ontouchstart' in window) || navigator.maxTouchPoints > 0;
if (isTouch) document.body.classList.add('touch');

/* =====================================================================
   DATA
   ===================================================================== */
const WEAPONS = {
  pistol:   { name: 'Пистолет',       slot: 2, dmg: 20, rate: .24, spread: .012, mag: 12,  reload: 1.1, price: 0 },
  revolver: { name: 'Револьвер',      slot: 2, dmg: 48, rate: .55, spread: .006, mag: 6,   reload: 1.8, price: 450, heavy: 1 },
  smg:      { name: 'ПП «Шершень»',   slot: 1, dmg: 13, rate: .075, spread: .03, mag: 32,  reload: 1.6, price: 0 },
  rifle:    { name: 'Штурмовая',      slot: 1, dmg: 21, rate: .105, spread: .016, mag: 30, reload: 1.9, price: 1200 },
  shotgun:  { name: 'Дробовик',       slot: 1, dmg: 13, rate: .8, spread: .075, mag: 6,    reload: 2.2, price: 900, pellets: 8, heavy: 1, range: 30 },
  sniper:   { name: 'Снайперка',      slot: 1, dmg: 100, rate: 1.15, spread: .05, mag: 5,  reload: 2.5, price: 1800, zoom: 3.2, range: 220, heavy: 1 },
  minigun:  { name: 'Миниган',        slot: 1, dmg: 11, rate: .045, spread: .045, mag: 150, reload: 3.6, price: 3200, slow: .72 },
  rocket:   { name: 'Базука',         slot: 1, dmg: 130, rate: 1.3, spread: 0, mag: 1,     reload: 2.3, price: 3800, rocket: 1, splash: 4.5, slow: .85 },
};
const HATS = {
  none: { name: 'Без шапки', price: 0 }, cap: { name: 'Кепка', price: 250 }, helmet: { name: 'Каска', price: 500 },
  cowboy: { name: 'Ковбойская', price: 600 }, headphones: { name: 'Наушники', price: 650 }, chef: { name: 'Колпак', price: 700 },
  santa: { name: 'Новогодняя', price: 750 }, top: { name: 'Цилиндр', price: 900 }, wizard: { name: 'Шляпа мага', price: 1000 },
  viking: { name: 'Викинг', price: 1300 }, crown: { name: 'Корона', price: 2500 },
};
const GLASSES = {
  none: { name: 'Без очков', price: 0 }, shades: { name: 'Тёмные очки', price: 400 },
  goggles: { name: 'Лётные очки', price: 600 }, pixel: { name: 'Пиксельные', price: 800 },
};
const FEATHERS = {
  white: { name: 'Белые', c: 0xf4f1ea, price: 0 }, brown: { name: 'Рыжие', c: 0xc0702f, price: 300 },
  black: { name: 'Чёрные', c: 0x34343a, price: 500 }, blue: { name: 'Небесные', c: 0x7ec8f0, price: 700 },
  pink: { name: 'Розовые', c: 0xf5a3c7, price: 700 }, mint: { name: 'Мятные', c: 0x93e0b5, price: 700 },
  gold: { name: 'Золотые', c: 0xf2c230, price: 2000 },
};
const ARMOR = [
  { name: 'Без брони', val: 0, price: 0, c: 0 }, { name: 'Лёгкий жилет', val: 25, price: 500, c: 0x6b7d4a },
  { name: 'Бронежилет', val: 50, price: 1100, c: 0x3d4a2c }, { name: 'Тяжёлая броня', val: 100, price: 2200, c: 0x2b2f36 },
];
const MAPS = {
  farm:   { name: 'Ферма',   ground: 0x7cc456, ground2: 0x6bb348, path: 0xcfae70, sky: 0x8fd3ff, fog: 0xc4e8ff, tree: 'round',  wall: 0xead6ad, roof: 0xb5462f, barn: 0xc23b2b, hill: 0x69ad4a },
  desert: { name: 'Пустыня', ground: 0xe8c98a, ground2: 0xdcb877, path: 0xc59a62, sky: 0xffd7a3, fog: 0xffe6c4, tree: 'cactus', wall: 0xdba66c, roof: 0xa86a3c, barn: 0xb85c38, hill: 0xd2a96b },
  snow:   { name: 'Снежная', ground: 0xf2f6fa, ground2: 0xe1eaf2, path: 0xb7c4cf, sky: 0xb9d4ec, fog: 0xdde9f3, tree: 'pine',   wall: 0xa0724a, roof: 0xf7fbff, barn: 0x9b3b33, hill: 0xe8eef5 },
};
const TEAM_COL = [0x3d8bff, 0xff4d4d];
const BOT_NAMES = ['Желток', 'Пеструшка', 'Гребешок', 'Клювокрыл', 'Цыпа', 'Наседка', 'Бройлер', 'Кудах', 'Ряба-77', 'Пёрышко',
  'Омлет', 'Шпора', 'Хохлатка', 'Зёрнышко', 'Капитан Кур', 'Несушка', 'Петруха', 'Пушок', 'Яйцелоб', 'Курочка-ряба'];
const WIN_SCORE = 200, MATCH_TIME = 300, KILL_PTS = 3, ZONE_R = 7, HALF = 55;

/* =====================================================================
   SAVE
   ===================================================================== */
const SAVE_KEY = 'featherSquad.v1';
const DEFAULT = {
  coins: 500, owned: { pistol: 1, smg: 1, 'hat:none': 1, 'gl:none': 1, 'col:white': 1 },
  eq: { prim: 'smg', sec: 'pistol', hat: 'none', gl: 'none', col: 'white' }, armor: 0, map: 'farm',
  sens: 1, quality: isTouch ? 'med' : 'high', fps: true, sound: true, stats: { kills: 0, wins: 0, games: 0 },
};
const clone = (o) => JSON.parse(JSON.stringify(o));
function loadSave() {
  try {
    const s = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (s && typeof s === 'object') {
      const d = clone(DEFAULT);
      return Object.assign(d, s, {
        eq: Object.assign(d.eq, s.eq || {}), stats: Object.assign(d.stats, s.stats || {}), owned: Object.assign(d.owned, s.owned || {}),
      });
    }
  } catch (e) { /* ignore */ }
  return clone(DEFAULT);
}
let S = loadSave();
function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(S)); } catch (e) { /* ignore */ } }

/* =====================================================================
   RENDERER / SCENES
   ===================================================================== */
const canvas = $('c');
const renderer = new T.WebGLRenderer({ canvas, antialias: !isTouch, powerPreference: 'high-performance' });
renderer.setClearColor(0x8fd3ff);
const scene = new T.Scene();
const camera = new T.PerspectiveCamera(70, 1, 0.1, 320);
scene.add(new T.HemisphereLight(0xffffff, 0x6b7a5a, 0.78));
const sun = new T.DirectionalLight(0xffffff, 0.72); sun.position.set(30, 60, 20); scene.add(sun);

const menuScene = new T.Scene();
const menuCam = new T.PerspectiveCamera(38, 1, 0.1, 120);
menuScene.add(new T.HemisphereLight(0xffffff, 0x6b7a5a, 0.85));
const msun = new T.DirectionalLight(0xffffff, 0.65); msun.position.set(5, 10, 8); menuScene.add(msun);

function pixelRatio() {
  const dpr = window.devicePixelRatio || 1;
  return S.quality === 'low' ? Math.min(dpr, 0.75) : S.quality === 'med' ? Math.min(dpr, 1.25) : Math.min(dpr, 2);
}
function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setPixelRatio(pixelRatio());
  renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  menuCam.aspect = w / h;
  if (w > h) menuCam.setViewOffset(w, h, -w * (game.state === 'shop' ? 0.3 : 0.2), 0, w, h);
  else menuCam.setViewOffset(w, h, 0, -h * 0.12, w, h);
  menuCam.updateProjectionMatrix();
  checkRotate();
}

/* =====================================================================
   GEOMETRY HELPERS
   ===================================================================== */
const G = {
  box: new T.BoxGeometry(1, 1, 1), sph: new T.SphereGeometry(1, 14, 10), sphLo: new T.SphereGeometry(1, 8, 6),
  cyl: new T.CylinderGeometry(1, 1, 1, 12), cylLo: new T.CylinderGeometry(1, 1, 1, 7), cone: new T.ConeGeometry(1, 1, 12),
  cone4: new T.ConeGeometry(1, 1, 4), cone8: new T.ConeGeometry(1, 1, 8), taper: new T.CylinderGeometry(0.6, 1, 1, 8),
  prism: new T.CylinderGeometry(1, 1, 1, 3), plane: new T.PlaneGeometry(1, 1), torus: new T.TorusGeometry(0.4, 0.045, 6, 18, Math.PI),
  circle: new T.CircleGeometry(1, 16), ring: new T.RingGeometry(ZONE_R - 0.25, ZONE_R + 0.15, 56),
  column: new T.CylinderGeometry(ZONE_R, ZONE_R, 6, 40, 1, true), octa: new T.OctahedronGeometry(1, 0),
};
G.prism.rotateZ(Math.PI / 2); G.prism.rotateX(-Math.PI / 2); // ridge along X, apex up, y ∈ [-.5, 1]
G.plane.rotateX(-Math.PI / 2); G.circle.rotateX(-Math.PI / 2); G.ring.rotateX(-Math.PI / 2);
const mats = {};
function M(c) { return mats[c] || (mats[c] = new T.MeshLambertMaterial({ color: c })); }
function P(geo, c, sx, sy, sz, x, y, z, parent, rx, ry, rz) {
  const m = new T.Mesh(geo, typeof c === 'number' ? M(c) : c);
  m.scale.set(sx, sy, sz); m.position.set(x, y, z);
  if (rx || ry || rz) m.rotation.set(rx || 0, ry || 0, rz || 0);
  if (parent) parent.add(m);
  return m;
}
function mulberry32(a) {
  return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
/** Merge every mesh of a group into one vertex-coloured mesh (1 draw call). */
function mergeGroup(group) {
  group.updateMatrixWorld(true);
  let count = 0; const parts = [];
  group.traverse((o) => {
    if (!o.isMesh) return;
    const g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    g.applyMatrix4(o.matrixWorld);
    parts.push({ g, c: o.material.color }); count += g.attributes.position.count;
  });
  const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), col = new Float32Array(count * 3);
  let off = 0;
  for (const { g, c } of parts) {
    const p = g.attributes.position.array, n = g.attributes.normal.array;
    pos.set(p, off * 3); nor.set(n, off * 3);
    const vc = g.attributes.position.count;
    for (let i = 0; i < vc; i++) { const k = (off + i) * 3; col[k] = c.r; col[k + 1] = c.g; col[k + 2] = c.b; }
    off += vc; g.dispose();
  }
  const geo = new T.BufferGeometry();
  geo.setAttribute('position', new T.BufferAttribute(pos, 3));
  geo.setAttribute('normal', new T.BufferAttribute(nor, 3));
  geo.setAttribute('color', new T.BufferAttribute(col, 3));
  geo.computeBoundingSphere();
  return new T.Mesh(geo, new T.MeshLambertMaterial({ vertexColors: true }));
}

/* =====================================================================
   MODELS: hats, glasses, chicken, guns
   ===================================================================== */
function buildHat(id) {
  const g = new T.Group();
  switch (id) {
    case 'cap': P(G.sph, 0xe53935, .37, .2, .37, 0, .2, 0, g); P(G.box, 0xe53935, .34, .03, .28, 0, .22, .36, g); P(G.sphLo, 0xffffff, .05, .05, .05, 0, .4, 0, g); break;
    case 'helmet': P(G.sph, 0x55663a, .42, .3, .44, 0, .14, 0, g); P(G.cyl, 0x4a5832, .44, .05, .46, 0, .12, 0, g); P(G.box, 0x3b4628, .5, .04, .06, 0, .3, .28, g, .3); break;
    case 'cowboy': P(G.cyl, 0x8b5a2b, .64, .04, .64, 0, .26, 0, g); P(G.cyl, 0x8b5a2b, .3, .3, .3, 0, .42, 0, g); P(G.cyl, 0x3a2412, .31, .07, .31, 0, .31, 0, g); P(G.sphLo, 0x7a4d22, .3, .1, .3, 0, .57, 0, g); break;
    case 'headphones': { const t = new T.Mesh(G.torus, M(0x222228)); t.position.y = .02; g.add(t);
      for (const s of [-1, 1]) { P(G.cyl, 0xe53935, .15, .1, .15, s * .38, -.02, 0, g, 0, 0, Math.PI / 2); P(G.cyl, 0x222228, .12, .06, .12, s * .44, -.02, 0, g, 0, 0, Math.PI / 2); } break; }
    case 'chef': P(G.cyl, 0xffffff, .3, .32, .3, 0, .4, 0, g); P(G.sph, 0xffffff, .4, .22, .4, 0, .62, 0, g); break;
    case 'santa': P(G.cone, 0xd62828, .34, .62, .34, 0, .58, -.04, g, -.35); P(G.cyl, 0xffffff, .38, .1, .38, 0, .27, 0, g); P(G.sphLo, 0xffffff, .09, .09, .09, 0, .83, -.24, g); break;
    case 'top': P(G.cyl, 0x1b1b1f, .52, .04, .52, 0, .27, 0, g); P(G.cyl, 0x1b1b1f, .3, .52, .3, 0, .55, 0, g); P(G.cyl, 0xb71c1c, .31, .08, .31, 0, .35, 0, g); break;
    case 'wizard': P(G.cyl, 0x4a2a8a, .62, .04, .62, 0, .27, 0, g); P(G.cone, 0x4a2a8a, .44, .9, .44, 0, .74, 0, g, -.12); P(G.cone4, 0xffd54a, .07, .1, .07, .2, .55, .3, g); P(G.sphLo, 0xffd54a, .06, .06, .06, -.15, .7, .22, g); break;
    case 'viking': P(G.sph, 0x9aa3ad, .41, .3, .41, 0, .14, 0, g); P(G.cyl, 0x8a6a3a, .42, .06, .42, 0, .12, 0, g);
      for (const s of [-1, 1]) P(G.cone, 0xf3ead2, .08, .38, .08, s * .43, .3, 0, g, 0, 0, -s * .9); break;
    case 'crown': P(G.cyl, 0xf5c518, .3, .16, .3, 0, .33, 0, g);
      for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2; P(G.cone4, 0xf5c518, .07, .16, .07, Math.sin(a) * .26, .48, Math.cos(a) * .26, g); P(G.sphLo, i % 2 ? 0xe53935 : 0x2e86ff, .04, .04, .04, Math.sin(a) * .3, .33, Math.cos(a) * .3, g); } break;
  }
  return g;
}
function buildGlasses(id) {
  const g = new T.Group();
  switch (id) {
    case 'shades': for (const s of [-1, 1]) P(G.box, 0x111114, .17, .1, .05, s * .12, .08, .33, g); P(G.box, 0x111114, .1, .03, .04, 0, .1, .34, g);
      for (const s of [-1, 1]) P(G.box, 0x111114, .03, .03, .25, s * .25, .1, .2, g); break;
    case 'goggles': P(G.cyl, 0x6b4a2a, .375, .08, .375, 0, .08, 0, g);
      for (const s of [-1, 1]) { P(G.cyl, 0x8a8f99, .1, .06, .1, s * .13, .08, .34, g, Math.PI / 2); P(G.cyl, 0x8fd3ff, .08, .062, .08, s * .13, .08, .345, g, Math.PI / 2); } break;
    case 'pixel': P(G.box, 0x050505, .5, .045, .04, 0, .12, .34, g);
      for (const s of [-1, 1]) { P(G.box, 0x050505, .18, .08, .04, s * .12, .07, .34, g); P(G.box, 0x050505, .09, .04, .04, s * .08, .02, .34, g); P(G.box, 0xffffff, .04, .04, .045, s * .17, .09, .345, g); } break;
  }
  return g;
}
const shadowMat = new T.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.22, depthWrite: false });
function buildChicken(look) {
  const root = new T.Group(), body = new T.Group(); root.add(body);
  const fc = (FEATHERS[look.col] || FEATHERS.white).c;
  P(G.sph, fc, .56, .58, .62, 0, .85, 0, body); // egg-shaped body
  P(G.sph, fc, .42, .3, .4, 0, .62, .2, body);    // belly
  P(G.sph, fc, .13, .34, .2, 0, 1.12, -.5, body, -.55);
  P(G.sph, fc, .11, .28, .17, .16, 1.05, -.48, body, -.55, 0, -.4);
  P(G.sph, fc, .11, .28, .17, -.16, 1.05, -.48, body, -.55, 0, .4);
  const head = new T.Group(); head.position.set(0, 1.45, .18); body.add(head);
  P(G.sph, fc, .36, .36, .36, 0, 0, 0, head);
  P(G.cone, 0xffa31a, .11, .26, .11, 0, -.03, .44, head, Math.PI / 2);
  for (const s of [-1, 1]) { P(G.sphLo, 0x141414, .065, .075, .04, s * .15, .08, .31, head); P(G.sphLo, 0xffffff, .022, .022, .02, s * .135, .11, .345, head); }
  P(G.sphLo, 0xe8322b, .08, .11, .08, 0, .36, .14, head); P(G.sphLo, 0xe8322b, .09, .13, .09, 0, .41, 0, head); P(G.sphLo, 0xe8322b, .08, .1, .08, 0, .36, -.13, head);
  P(G.sphLo, 0xe8322b, .055, .09, .05, 0, -.2, .33, head);
  if (look.hat && look.hat !== 'none') head.add(buildHat(look.hat));
  if (look.gl && look.gl !== 'none') head.add(buildGlasses(look.gl));
  const wingL = new T.Group(); wingL.position.set(.5, .95, 0); body.add(wingL);
  P(G.sph, fc, .13, .3, .4, 0, -.1, 0, wingL, 0, 0, -.2);
  const wingR = new T.Group(); wingR.position.set(-.5, .95, 0); body.add(wingR);
  P(G.sph, fc, .13, .3, .4, 0, -.1, .05, wingR, -.6, 0, .2);
  const legs = [];
  for (const s of [-1, 1]) {
    const leg = new T.Group(); leg.position.set(s * .2, .42, 0); root.add(leg);
    P(G.cylLo, 0xffa31a, .05, .4, .05, 0, -.2, 0, leg);
    P(G.box, 0xffa31a, .16, .05, .26, 0, -.39, .07, leg);
    legs.push(leg);
  }
  if (look.armor) {
    const ac = ARMOR[look.armor].c;
    P(G.cyl, ac, .6, .46, .65, 0, .84, 0, body);
    P(G.box, ac, .2, .16, .1, .18, .78, .63, body); P(G.box, ac, .2, .16, .1, -.18, .78, .63, body);
    P(G.box, 0x1d1d1d, .62, .05, .05, 0, 1.05, .58, body);
  }
  const gun = new T.Group(); gun.position.set(-.45, .98, .38); body.add(gun);
  const sh = new T.Mesh(G.circle, shadowMat); sh.scale.set(.6, 1, .6); sh.position.y = .03; root.add(sh);
  return { root, body, head, wingL, wingR, legL: legs[1], legR: legs[0], gun, shadow: sh };
}
const flashMat = new T.MeshBasicMaterial({ color: 0xffe066 });
function buildGun(id) {
  const g = new T.Group(); let muz = .3;
  const D = 0x2d2f33, D2 = 0x44474d, W = 0x8a5a2b;
  const barrel = (r, len, z, y, c) => P(G.cylLo, c || D, r, len, r, 0, y || 0, z, g, Math.PI / 2);
  switch (id) {
    case 'pistol': P(G.box, D, .08, .12, .32, 0, .02, .1, g); P(G.box, D2, .07, .17, .09, 0, -.1, -.02, g, .3); muz = .27; break;
    case 'revolver': barrel(.035, .32, .23, .03, 0x9aa0a6); P(G.cyl, 0x9aa0a6, .07, .12, .07, 0, .01, .04, g, Math.PI / 2); P(G.box, W, .07, .17, .09, 0, -.1, -.06, g, .4); muz = .39; break;
    case 'smg': P(G.box, D, .1, .14, .45, 0, 0, .14, g); P(G.box, D2, .06, .22, .08, 0, -.15, .16, g); barrel(.025, .15, .42); P(G.box, D2, .07, .08, .2, 0, .02, -.16, g); muz = .5; break;
    case 'rifle': P(G.box, D, .09, .13, .6, 0, 0, .15, g); P(G.box, W, .1, .1, .28, 0, -.01, .38, g); P(G.box, D2, .07, .2, .09, 0, -.15, .12, g, .35);
      P(G.box, W, .08, .15, .26, 0, -.03, -.22, g); barrel(.025, .2, .6); P(G.box, D, .03, .06, .03, 0, .09, .5, g); muz = .7; break;
    case 'shotgun': barrel(.045, .78, .36, .03); P(G.box, W, .1, .09, .28, 0, -.05, .36, g); P(G.box, D, .09, .13, .22, 0, 0, 0, g); P(G.box, W, .08, .15, .3, 0, -.04, -.24, g, -.1); muz = .76; break;
    case 'sniper': barrel(.035, .95, .5); P(G.box, 0x3b4a2c, .09, .13, .5, 0, 0, .08, g); P(G.cylLo, 0x111111, .05, .38, .05, 0, .12, .12, g, Math.PI / 2);
      P(G.box, 0x3b4a2c, .08, .16, .3, 0, -.03, -.3, g); P(G.box, D2, .06, .14, .07, 0, -.13, .12, g); muz = .98; break;
    case 'minigun': P(G.cyl, D2, .14, .4, .14, 0, 0, .05, g, Math.PI / 2);
      for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2; barrel(.03, .6, .5, Math.sin(a) * .08, D); g.children[g.children.length - 1].position.x = Math.cos(a) * .08; }
      P(G.cyl, D, .13, .05, .13, 0, 0, .7, g, Math.PI / 2); P(G.box, 0x6b5a2a, .16, .14, .18, .12, -.12, -.05, g); muz = .82; break;
    case 'rocket': P(G.cyl, 0x4f6b3a, .11, 1.1, .11, 0, .05, .18, g, Math.PI / 2); P(G.cyl, 0x3b5029, .14, .15, .14, 0, .05, .72, g, Math.PI / 2);
      P(G.cone8, 0x6c7d4b, .1, .22, .1, 0, .05, .85, g, Math.PI / 2); P(G.box, D, .06, .16, .08, 0, -.11, .1, g); P(G.box, D, .05, .08, .12, 0, .19, .2, g); muz = .9; break;
  }
  g.userData.muz = muz;
  return g;
}

/* =====================================================================
   AUDIO (synthesised, no files)
   ===================================================================== */
let AC = null, master = null, noiseBuf = null;
function initAudio() {
  if (AC) { if (AC.state === 'suspended') AC.resume(); return; }
  try {
    AC = new (window.AudioContext || window.webkitAudioContext)();
    master = AC.createGain(); master.gain.value = 0.45; master.connect(AC.destination);
    noiseBuf = AC.createBuffer(1, AC.sampleRate, AC.sampleRate);
    const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  } catch (e) { AC = null; }
}
function sfx(type, pos) {
  if (!AC || !S.sound || AC.state !== 'running') return;
  let vol = 1;
  if (pos && game.player) { const d = pos.distanceTo(game.player.pos); vol = clamp(1 - d / 55, 0, 1); vol *= vol; if (vol < 0.03) return; }
  const t = AC.currentTime;
  const env = (g, a, dur) => { g.gain.setValueAtTime(a * vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur); };
  const noise = (freq, dur, a, q) => {
    const s = AC.createBufferSource(); s.buffer = noiseBuf; const f = AC.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = freq; f.Q.value = q || 0.7;
    const g = AC.createGain(); env(g, a, dur); s.connect(f); f.connect(g); g.connect(master); s.start(t, Math.random() * 0.5); s.stop(t + dur);
  };
  const tone = (f0, f1, dur, a, type2) => {
    const o = AC.createOscillator(); o.type = type2 || 'sine'; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    const g = AC.createGain(); env(g, a, dur); o.connect(g); g.connect(master); o.start(t); o.stop(t + dur);
  };
  switch (type) {
    case 'shot': noise(2600, .12, .5); tone(180, 60, .08, .25, 'square'); break;
    case 'heavy': noise(1400, .3, .8); tone(120, 40, .2, .4, 'square'); break;
    case 'boom': noise(500, .9, 1.2, 1); tone(80, 25, .7, .8); break;
    case 'hit': tone(1400, 900, .05, .25, 'square'); break;
    case 'kill': tone(700, 1400, .12, .3, 'square'); break;
    case 'cluck': tone(900, 500, .07, .25, 'sawtooth'); setTimeout(() => sfx('cluck2', pos), 90); break;
    case 'cluck2': tone(1100, 600, .1, .2, 'sawtooth'); break;
    case 'pickup': tone(600, 1200, .15, .3); break;
    case 'reload': noise(4000, .05, .3, 4); setTimeout(() => sfx('click', pos), 250); break;
    case 'click': noise(5000, .04, .3, 6); break;
    case 'engine': tone(70, 50, .25, .15, 'sawtooth'); break;
    case 'buy': tone(800, 1600, .1, .3); setTimeout(() => sfx('pickup'), 100); break;
  }
}

/* =====================================================================
   WORLD
   ===================================================================== */
let world = null;
function buildWorld(mapId) {
  const th = MAPS[mapId] || MAPS.farm;
  if (world) { scene.remove(world.root); world.merged.geometry.dispose(); }
  const root = new T.Group(), stat = new T.Group(), cols = [];
  const rng = mulberry32(mapId.length * 7919 + 13);
  renderer.setClearColor(th.sky); scene.fog = new T.Fog(th.fog, 55, 160);
  const box = (x, y, z, w, h, d, c, col = true) => { P(G.box, c, w, h, d, x, y + h / 2, z, stat); if (col) cols.push({ x0: x - w / 2, x1: x + w / 2, z0: z - d / 2, z1: z + d / 2, y0: y, y1: y + h }); };
  const solid = (x, z, w, d, h, y0 = 0) => cols.push({ x0: x - w / 2, x1: x + w / 2, z0: z - d / 2, z1: z + d / 2, y0, y1: y0 + h });
  const blocked = (x, z, m) => cols.some((c) => x > c.x0 - m && x < c.x1 + m && z > c.z0 - m && z < c.z1 + m && c.y1 < 30);

  // ground, patches, roads
  P(G.plane, th.ground, 420, 1, 420, 0, 0, 0, stat);
  for (let i = 0; i < 36; i++) { const r = rand(2, 6); P(G.cyl, th.ground2, r, .02, r * rand(.6, 1.2), rand(-52, 52), .01, rand(-52, 52), stat); }
  P(G.box, th.path, 5, .03, 112, 0, .015, 0, stat); P(G.box, th.path, 112, .03, 5, 0, .015, 0, stat);
  // boundary walls (tall invisible colliders) + fence visuals
  cols.push({ x0: -HALF - 3, x1: -HALF, z0: -70, z1: 70, y0: 0, y1: 40 }, { x0: HALF, x1: HALF + 3, z0: -70, z1: 70, y0: 0, y1: 40 },
    { x0: -70, x1: 70, z0: -HALF - 3, z1: -HALF, y0: 0, y1: 40 }, { x0: -70, x1: 70, z0: HALF, z1: HALF + 3, y0: 0, y1: 40 });
  const fc = mapId === 'snow' ? 0x6b4a2e : 0x9c6b3e;
  for (const s of [-1, 1]) {
    for (let i = -HALF; i <= HALF; i += 4) { P(G.box, fc, .25, 1.5, .25, i, .75, s * HALF, stat); P(G.box, fc, .25, 1.5, .25, s * HALF, .75, i, stat); }
    for (const y of [.55, 1.15]) { P(G.box, fc, HALF * 2, .14, .1, 0, y, s * HALF, stat); P(G.box, fc, .1, .14, HALF * 2, s * HALF, y, 0, stat); }
  }
  // distant hills
  for (let i = 0; i < 18; i++) { const a = i / 18 * Math.PI * 2, r = rand(95, 120), sz = rand(18, 30); P(G.sphLo, th.hill, sz, sz * rand(.3, .5), sz, Math.cos(a) * r, 0, Math.sin(a) * r, stat); }

  // ---- building blocks ----
  function house(x, z, w, d, h, wallC, roofC) {
    box(x, 0, z, w, h, d, wallC);
    const rh = h * .5, sy = rh / 1.5;
    P(G.prism, roofC, w + .7, sy, (d / 2 + .45) / .866, x, h + .5 * sy, z, stat);
    const dz = z > 0 ? -1 : 1, fz = z + dz * (d / 2 + .05);
    P(G.box, 0x5a3a22, 1.2, 2.1, .12, x, 1.05, fz, stat);
    for (const sx of [-1, 1]) { P(G.box, 0x9fd8ff, 1.1, .9, .12, x + sx * w * .3, h * .58, fz, stat); P(G.box, 0xffffff, 1.3, .12, .14, x + sx * w * .3, h * .58 - .5, fz, stat); }
    for (const sx of [-1, 1]) P(G.box, 0x9fd8ff, .12, .9, 1.1, x + sx * (w / 2 + .05), h * .58, z, stat);
    P(G.box, 0x8a4a3a, .7, 1.6, .7, x + w * .25, h + rh * .6, z - d * .15, stat);
  }
  function barn(x, z, w, d, h) {
    box(x, 0, z, w, h, d, th.barn);
    const rh = h * .55, sy = rh / 1.5;
    P(G.prism, 0x5a2a22, d + .8, sy, (w / 2 + .5) / .866, x, h + .5 * sy, z, stat, 0, Math.PI / 2);
    const dz = z > 0 ? -1 : 1, fz = z + dz * (d / 2 + .06);
    P(G.box, 0x9e2c22, 4, 3.6, .1, x, 1.8, fz, stat); P(G.box, 0xffffff, 4.2, .2, .14, x, 3.65, fz, stat); P(G.box, 0xffffff, .2, 3.6, .14, x, 1.8, fz, stat);
    for (const r of [-.73, .73]) P(G.box, 0xffffff, .18, 5, .13, x, 1.8, fz, stat, 0, 0, r);
    P(G.box, 0xffffff, 1.4, 1.2, .12, x, h + .9, fz - dz * .2, stat);
  }
  function tower(x, z) {
    for (const a of [-1, 1]) for (const b of [-1, 1]) box(x + a * 1.3, 0, z + b * 1.3, .3, 5, .3, 0x7a5232);
    for (const b of [-1, 1]) { P(G.box, 0x6a4628, 2.8, .14, .14, x, 2.4, z + b * 1.3, stat, 0, 0, .9); P(G.box, 0x6a4628, .14, .14, 2.8, x + b * 1.3, 2.4, z, stat, .9); }
    box(x, 5, z, 3.4, .3, 3.4, 0x8a5e3a);
    for (const b of [-1, 1]) { P(G.box, 0x7a5232, 3.4, .7, .12, x, 5.65, z + b * 1.65, stat); P(G.box, 0x7a5232, .12, .7, 3.4, x + b * 1.65, 5.65, z, stat); }
    for (const a of [-1, 1]) for (const b of [-1, 1]) P(G.box, 0x7a5232, .15, 1.8, .15, x + a * 1.55, 6.1, z + b * 1.55, stat);
    P(G.cone4, th.roof === 0xf7fbff ? 0xf7fbff : 0x6b3a26, 2.8, 1.4, 2.8, x, 7.7, z, stat, 0, Math.PI / 4);
  }
  function crate(x, z, s, y = 0) { box(x, y, z, s, s, s, rng() > .5 ? 0xb07a3c : 0x9c6a30); P(G.box, 0x7a4f22, s * 1.02, s * .12, s * 1.02, x, y + s * .5, z, stat); P(G.box, 0x7a4f22, s * 1.02, s * 1.02, s * .12, x, y + s * .5, z, stat); }
  function cluster(x, z) { crate(x, z, 1.4); crate(x + 1.5, z + .2, 1.4); crate(x + .6, z, 1.2, 1.4); crate(x + .3, z + 1.5, 1.2); }
  function barrel(x, z) { P(G.cyl, 0xc0392b, .45, 1.1, .45, x, .55, z, stat); P(G.cyl, 0x7a1f17, .47, .07, .47, x, .3, z, stat); P(G.cyl, 0x7a1f17, .47, .07, .47, x, .8, z, stat); solid(x, z, .9, .9, 1.1); }
  function sandbags(x, z, w, d) { box(x, 0, z, w, 1.1, d, 0xc8b27a); for (let i = 0; i < Math.max(w, d) * 1.4; i++) { const t = (i + .5) / (Math.max(w, d) * 1.4) - .5; P(G.sphLo, 0xbfa76c, w > d ? .45 : .55, .22, w > d ? .55 : .45, x + (w > d ? t * w : 0), 1.1, z + (w > d ? 0 : t * d), stat); } }
  function wreck(x, z, rot, c) {
    const g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = rot ? Math.PI / 2 : 0; stat.add(g);
    P(G.box, c, 2, .8, 4, 0, .75, 0, g); P(G.box, c, 1.8, .7, 2, 0, 1.5, -.3, g); P(G.box, 0x9fd8ff, 1.82, .5, 1.6, 0, 1.5, -.3, g);
    for (const a of [-1, 1]) for (const b of [-1, 1]) P(G.cyl, 0x222222, .42, .3, .42, a * 1, .42, b * 1.3, g, 0, 0, Math.PI / 2);
    solid(x, z, rot ? 4 : 2, rot ? 2 : 4, 1.85);
  }
  function lamp(x, z) { P(G.cylLo, 0x555b66, .08, 5, .08, x, 2.5, z, stat); P(G.box, 0x555b66, .9, .1, .12, x + .4, 5, z, stat); P(G.box, 0xfff2a8, .3, .12, .25, x + .8, 4.92, z, stat); solid(x, z, .25, .25, 5); }
  function tree(x, z, big) {
    const k = big ? 1.4 : 1;
    if (th.tree === 'round') {
      P(G.cylLo, 0x7a4f2a, .25 * k, 2.2 * k, .25 * k, x, 1.1 * k, z, stat);
      P(G.sphLo, 0x4caf50, 1.5 * k, 1.3 * k, 1.5 * k, x, 2.9 * k, z, stat); P(G.sphLo, 0x3e9b43, 1.1 * k, 1 * k, 1.1 * k, x + .7 * k, 3.5 * k, z + .3 * k, stat); P(G.sphLo, 0x58bd5c, 1 * k, .9 * k, 1 * k, x - .6 * k, 3.6 * k, z - .4 * k, stat);
    } else if (th.tree === 'pine') {
      P(G.cylLo, 0x6a4428, .25 * k, 1.6 * k, .25 * k, x, .8 * k, z, stat);
      for (let i = 0; i < 3; i++) { const r = (1.7 - i * .45) * k, y = (1.6 + i * 1.1) * k; P(G.cone8, 0x2e7d4f, r, 1.6 * k, r, x, y + .8 * k, z, stat); P(G.cone8, 0xffffff, r * .7, .7 * k, r * .7, x, y + 1.3 * k, z, stat); }
    } else {
      const c = 0x3f9b4a; P(G.cylLo, c, .35 * k, 3 * k, .35 * k, x, 1.5 * k, z, stat); P(G.sphLo, c, .35 * k, .35 * k, .35 * k, x, 3 * k, z, stat);
      P(G.cylLo, c, .2 * k, .8 * k, .2 * k, x + .5 * k, 1.5 * k, z, stat, 0, 0, Math.PI / 2); P(G.cylLo, c, .2 * k, 1 * k, .2 * k, x + .85 * k, 2 * k, z, stat);
      P(G.cylLo, c, .2 * k, .6 * k, .2 * k, x - .45 * k, 1.9 * k, z, stat, 0, 0, Math.PI / 2); P(G.cylLo, c, .2 * k, .8 * k, .2 * k, x - .7 * k, 2.3 * k, z, stat);
    }
    solid(x, z, .8 * k, .8 * k, 6);
  }
  function rock(x, z, s) { P(G.sphLo, 0x9a9a9a, s, s * .7, s * .9, x, s * .3, z, stat, 0, rng() * 3); solid(x, z, s * 1.6, s * 1.5, s * .95); }
  function hay(x, z) { P(G.cyl, 0xe3c15a, .7, 1.4, .7, x, .7, z, stat, 0, 0, Math.PI / 2); P(G.cyl, 0xcfa944, .72, .1, .72, x, .7, z, stat, 0, 0, Math.PI / 2); solid(x, z, 1.4, 1.4, 1.4); }
  function snowman(x, z) { P(G.sphLo, 0xffffff, .8, .8, .8, x, .7, z, stat); P(G.sphLo, 0xffffff, .55, .55, .55, x, 1.75, z, stat); P(G.sphLo, 0xffffff, .38, .38, .38, x, 2.5, z, stat); P(G.cone8, 0xff7a1a, .07, .35, .07, x, 2.5, z + .5, stat, Math.PI / 2); P(G.cyl, 0x1b1b1f, .3, .4, .3, x, 2.95, z, stat); solid(x, z, 1.4, 1.4, 3); }

  // ---- center capture zone ----
  P(G.cyl, 0xdfe3e8, ZONE_R, .08, ZONE_R, 0, .04, 0, stat);
  P(G.cyl, 0xc4c9d0, ZONE_R * .55, .1, ZONE_R * .55, 0, .05, 0, stat);
  P(G.cylLo, 0xeeeeee, .09, 5, .09, 0, 2.5, 0, stat); P(G.sphLo, 0xffd54a, .16, .16, .16, 0, 5.05, 0, stat); solid(0, 0, .3, .3, 5);

  // ---- mirrored sides ----
  for (const s of [-1, 1]) {
    const tc = s < 0 ? 0x5c86c8 : 0xc86a6a;
    P(G.cyl, tc, 5.5, .04, 5.5, 0, .02, s * 49, stat); P(G.cyl, th.ground, 4.8, .05, 4.8, 0, .025, s * 49, stat);
    house(-32, s * 34, 9, 7, 4.5, th.wall, th.roof);
    if (mapId === 'farm') barn(32, s * 36, 11, 9, 5.5); else house(32, s * 36, 10, 8, 5, th.wall, th.roof);
    house(-43, s * 12, 7, 6, 4, th.wall, th.roof);
    tower(17, s * 20);
    cluster(-9, s * 15); cluster(9, s * 30); cluster(-21, s * 23); cluster(25, s * 8); cluster(38, s * 22);
    sandbags(-5, s * 9.5, 5, 1); sandbags(6, s * 10.5, 4, 1); sandbags(0, s * 18, 1, 3.5);
    wreck(-15, s * 5, true, s < 0 ? 0x2e86de : 0xe67e22);
    barrel(13, s * 13); barrel(14, s * 14.1); barrel(12.8, s * 14.4);
    rock(-30, s * 4, 2.2); lamp(3, s * 26); lamp(-3, s * 40);
    if (mapId === 'farm') { hay(35, s * 14); hay(36.5, s * 14.2); hay(-26, s * 45); }
    if (mapId === 'snow') { snowman(-24, s * 14); snowman(28, s * 46); }
    if (mapId === 'desert') { rock(36, s * 14, 1.6); rock(-25, s * 45, 1.8); }
  }
  // windmills (blades are dynamic)
  const blades = [];
  for (const sx of [-1, 1]) {
    const x = sx * 47, z = sx * 2;
    P(G.taper, mapId === 'desert' ? 0xd2b48c : 0xd9d2c3, 1.5, 9, 1.5, x, 4.5, z, stat); P(G.cone8, 0x8a4a3a, 1.3, 1.5, 1.3, x, 9.7, z, stat); solid(x, z, 2.6, 2.6, 9);
    const b = new T.Group(); b.position.set(x - sx * 1.25, 8.6, z);
    P(G.sphLo, 0x5a3a22, .35, .35, .35, 0, 0, 0, b);
    for (let i = 0; i < 4; i++) { const arm = new T.Group(); arm.rotation.x = i * Math.PI / 2; b.add(arm); P(G.box, 0xf3ead2, .08, 3.6, .7, 0, 2, .2, arm); P(G.box, 0x6b4a2a, .1, 3.8, .1, 0, 2, 0, arm); }
    root.add(b); blades.push(b);
  }
  // trees: mirrored for fairness
  let placed = 0, guard = 0;
  while (placed < 16 && guard++ < 600) {
    const x = (rng() * 2 - 1) * 51, z = 6 + rng() * 45;
    if (Math.abs(x) < 5 || (Math.abs(x) < 12 && z > 40) || Math.hypot(x, z) < 14 || blocked(x, z, 3) || blocked(-x, z, 3)) continue;
    tree(x, z, rng() > .7); tree(-x, -z, rng() > .7); placed++;
  }
  // decoration outside fence
  for (let i = 0; i < 46; i++) { const a = rng() * Math.PI * 2, r = 62 + rng() * 25; const x = Math.cos(a) * r, z = Math.sin(a) * r; tree(x, z, rng() > .5); cols.pop(); }

  const merged = mergeGroup(stat);
  root.add(merged);
  // dynamic zone visuals
  const ringMat = new T.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .9, depthWrite: false });
  const ring = new T.Mesh(G.ring, ringMat); ring.position.y = .12; root.add(ring);
  const colMat = new T.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .1, depthWrite: false, side: T.DoubleSide });
  const column = new T.Mesh(G.column, colMat); column.position.y = 3; root.add(column);
  const flag = P(G.box, new T.MeshLambertMaterial({ color: 0xffffff }), 1.5, .95, .05, .78, 4.45, 0, root);
  scene.add(root);
  world = { root, merged, cols, blades, ring, ringMat, colMat, flag, theme: th };
  buildMinimapBase();
}

/* =====================================================================
   COLLISION / RAYS
   ===================================================================== */
const ACT_H = 1.75;
function collideCircle(p, y, r, h) {
  let pushed = false;
  for (const c of world.cols) {
    if (y >= c.y1 - 0.36 || y + h <= c.y0) continue;
    if (p.x < c.x0 - r || p.x > c.x1 + r || p.z < c.z0 - r || p.z > c.z1 + r) continue;
    const cx = clamp(p.x, c.x0, c.x1), cz = clamp(p.z, c.z0, c.z1);
    const dx = p.x - cx, dz = p.z - cz, d2 = dx * dx + dz * dz;
    if (d2 >= r * r) continue;
    pushed = true;
    if (d2 > 1e-8) { const d = Math.sqrt(d2), k = (r - d) / d; p.x += dx * k; p.z += dz * k; }
    else {
      const l = p.x - c.x0, rr = c.x1 - p.x, f = p.z - c.z0, b = c.z1 - p.z, m = Math.min(l, rr, f, b);
      if (m === l) p.x = c.x0 - r; else if (m === rr) p.x = c.x1 + r; else if (m === f) p.z = c.z0 - r; else p.z = c.z1 + r;
    }
  }
  return pushed;
}
function groundAt(x, z, y) {
  let g = 0;
  for (const c of world.cols) if (x > c.x0 - .2 && x < c.x1 + .2 && z > c.z0 - .2 && z < c.z1 + .2 && c.y1 <= y + .36 && c.y1 > g) g = c.y1;
  return g;
}
function rayBox(o, d, c, maxT) {
  let tmin = 0, tmax = maxT;
  const ax = [[o.x, d.x, c.x0, c.x1], [o.y, d.y, c.y0, c.y1], [o.z, d.z, c.z0, c.z1]];
  for (let i = 0; i < 3; i++) {
    const [oo, dd, lo, hi] = ax[i];
    if (Math.abs(dd) < 1e-9) { if (oo < lo || oo > hi) return Infinity; continue; }
    let t1 = (lo - oo) / dd, t2 = (hi - oo) / dd; if (t1 > t2) { const tt = t1; t1 = t2; t2 = tt; }
    if (t1 > tmin) tmin = t1; if (t2 < tmax) tmax = t2; if (tmin > tmax) return Infinity;
  }
  return tmin;
}
function raySphere(o, d, cx, cy, cz, r) {
  const ox = o.x - cx, oy = o.y - cy, oz = o.z - cz;
  const b = ox * d.x + oy * d.y + oz * d.z, c = ox * ox + oy * oy + oz * oz - r * r, h = b * b - c;
  if (h < 0) return Infinity; const t = -b - Math.sqrt(h); return t >= 0 ? t : Infinity;
}
function rayWorld(o, d, maxT) {
  let best = maxT;
  for (const c of world.cols) { if (c.y1 > 30) continue; const t = rayBox(o, d, c, best); if (t < best) best = t; }
  if (d.y < -1e-6) { const t = -o.y / d.y; if (t < best) best = t; }
  return best;
}
function headPos(a) { return { x: a.pos.x + Math.sin(a.yaw) * .18, y: a.pos.y + 1.45, z: a.pos.z + Math.cos(a.yaw) * .18 }; }
function traceShot(o, d, range, shooter) {
  let best = rayWorld(o, d, range), hit = null, head = false;
  for (const a of game.actors) {
    if (!a.alive || a === shooter || a.team === shooter.team) continue;
    const hp = headPos(a);
    let t = raySphere(o, d, hp.x, hp.y, hp.z, .37); if (t < best) { best = t; hit = a; head = true; }
    t = raySphere(o, d, a.pos.x, a.pos.y + .82, a.pos.z, .62); if (t < best) { best = t; hit = a; head = false; }
  }
  return { t: best, actor: hit, head };
}
const _v1 = new T.Vector3(), _v2 = new T.Vector3(), _v3 = new T.Vector3();
function los(a, b) {
  _v1.set(a.pos.x, a.pos.y + 1.4, a.pos.z); _v2.set(b.pos.x, b.pos.y + 1.1, b.pos.z);
  const dist = _v1.distanceTo(_v2); _v3.subVectors(_v2, _v1).divideScalar(dist);
  for (const c of world.cols) { if (c.y1 > 30) continue; if (rayBox(_v1, _v3, c, dist) < dist) return false; }
  return true;
}

/* =====================================================================
   EFFECTS (pooled)
   ===================================================================== */
const FX = { parts: [], tracers: [], booms: [] };
(function initFX() {
  for (let i = 0; i < 110; i++) { const m = new T.Mesh(G.box, new T.MeshBasicMaterial({ color: 0xffffff })); m.visible = false; scene.add(m); FX.parts.push({ m, v: new T.Vector3(), life: 0, max: 1, drag: 0, spin: 0 }); }
  const tm = new T.MeshBasicMaterial({ color: 0xfff1a0, transparent: true, opacity: .85 });
  for (let i = 0; i < 28; i++) { const m = new T.Mesh(G.box, tm); m.visible = false; scene.add(m); FX.tracers.push({ m, life: 0 }); }
  for (let i = 0; i < 6; i++) { const m = new T.Mesh(G.sphLo, new T.MeshBasicMaterial({ color: 0xff9a2e, transparent: true, depthWrite: false })); m.visible = false; scene.add(m); FX.booms.push({ m, life: 0, r: 1 }); }
})();
let partIdx = 0, trIdx = 0;
function burst(x, y, z, color, n, speed, life, size, drag) {
  for (let i = 0; i < n; i++) {
    const p = FX.parts[partIdx = (partIdx + 1) % FX.parts.length];
    p.m.material.color.setHex(Array.isArray(color) ? color[i % color.length] : color);
    p.m.position.set(x, y, z); p.v.set(rand(-1, 1), rand(.2, 1.3), rand(-1, 1)).multiplyScalar(speed);
    p.life = p.max = life * rand(.7, 1.2); p.drag = drag || 0; p.spin = rand(-8, 8);
    if (drag) p.m.scale.set(size * 1.6, size * .25, size); else p.m.scale.setScalar(size);
    p.size = size; p.m.visible = true;
  }
}
function tracer(a, b) {
  const t = FX.tracers[trIdx = (trIdx + 1) % FX.tracers.length];
  const len = a.distanceTo(b); if (len < .1) return;
  t.m.position.copy(a).add(b).multiplyScalar(.5); t.m.lookAt(b); t.m.scale.set(.035, .035, len); t.m.visible = true; t.life = .055;
}
function boom(x, y, z, r) {
  const b = FX.booms.find((q) => q.life <= 0) || FX.booms[0];
  b.m.position.set(x, y, z); b.life = .45; b.r = r; b.m.visible = true;
  burst(x, y + .3, z, [0x444444, 0x777777, 0xff9a2e, 0xffd24a], 18, 9, .8, .3);
  sfx('boom', b.m.position);
  if (game.player) { const d = game.player.pos.distanceTo(b.m.position); game.shake = Math.max(game.shake, clamp(1 - d / 25, 0, 1) * .5); }
}
function updateFX(dt) {
  for (const p of FX.parts) {
    if (p.life <= 0) continue;
    p.life -= dt; if (p.life <= 0) { p.m.visible = false; continue; }
    if (p.drag) { p.v.multiplyScalar(1 - p.drag * dt); p.v.y -= 2.5 * dt; p.m.rotation.x += p.spin * dt; p.m.rotation.z += p.spin * .7 * dt; }
    else p.v.y -= 16 * dt;
    p.m.position.addScaledVector(p.v, dt);
    if (p.m.position.y < .05) { p.m.position.y = .05; p.v.multiplyScalar(.4); }
    if (!p.drag) p.m.scale.setScalar(p.size * (p.life / p.max));
  }
  for (const t of FX.tracers) if (t.life > 0) { t.life -= dt; if (t.life <= 0) t.m.visible = false; }
  for (const b of FX.booms) {
    if (b.life <= 0) continue; b.life -= dt;
    if (b.life <= 0) { b.m.visible = false; continue; }
    const k = 1 - b.life / .45; b.m.scale.setScalar(b.r * (.3 + k * .8)); b.m.material.opacity = (1 - k) * .85;
  }
}

/* =====================================================================
   GAME STATE
   ===================================================================== */
const game = { state: 'menu', actors: [], player: null, cars: [], pickups: [], projs: [], scores: [0, 0], zone: { v: 0, owner: -1 },
  timeLeft: MATCH_TIME, earned: 0, shake: 0, lastLook: 0, time: 0 };
const input = { mx: 0, mz: 0, fire: false, aim: false, keys: {}, jump: false };

function makeActor(team, isPlayer, look, name, loadout, armorLvl) {
  const a = {
    team, isPlayer, name, look, pos: new T.Vector3(), vy: 0, onGround: true, yaw: 0, pitch: 0, hp: 100, maxHp: 100,
    armor: 0, maxArmor: ARMOR[armorLvl].val, alive: true, respawn: 0, weapons: loadout.map((id) => ({ id, ammo: WEAPONS[id].mag })),
    cur: 0, cd: 0, reload: 0, kills: 0, deaths: 0, grenades: 2, walk: 0, flash: 0, car: null, spawnProt: 0, lastShot: -9,
    speedH: 0, killedBy: '', hurt: 0, sndT: 0,
  };
  a.m = buildChicken(Object.assign({}, look, { armor: armorLvl }));
  scene.add(a.m.root);
  if (!isPlayer) {
    const mk = new T.Mesh(G.octa, new T.MeshBasicMaterial({ color: TEAM_COL[team] }));
    mk.scale.set(.16, .24, .16); mk.position.y = 2.35; a.m.root.add(mk); a.marker = mk;
    a.bot = { think: 0, target: null, goal: new T.Vector3(), strafe: 1, strafeT: 0, react: 0, avoid: 1, stuck: 0, detour: 0, detourDir: new T.Vector3(), lastPos: new T.Vector3(), skill: rand(.6, 1), jumpT: rand(2, 6) };
  }
  equipGun(a);
  return a;
}
function equipGun(a) {
  const h = a.m.gun; while (h.children.length) h.remove(h.children[0]);
  const g = buildGun(a.weapons[a.cur].id); h.add(g); a.gunModel = g;
  const f = new T.Mesh(G.sphLo, flashMat); f.scale.set(.12, .12, .2); f.position.z = g.userData.muz + .08; f.visible = false; g.add(f); a.flashM = f;
}
function spawnActor(a) {
  const s = a.team === 0 ? -1 : 1;
  for (let i = 0; i < 20; i++) {
    a.pos.set(rand(-5, 5), 0, s * rand(46.5, 51));
    if (!game.actors.some((b) => b !== a && b.alive && b.pos.distanceTo(a.pos) < 1.3)) break;
  }
  a.yaw = a.team === 0 ? 0 : Math.PI; a.pitch = 0; a.hp = a.maxHp; a.armor = a.maxArmor; a.alive = true; a.vy = 0; a.reload = 0;
  a.weapons.forEach((w) => (w.ammo = WEAPONS[w.id].mag)); a.grenades = 2; a.m.root.visible = true; a.spawnProt = 2; a.cd = .3;
  a.m.root.rotation.set(0, a.yaw, 0);
  if (a.bot) { a.bot.target = null; a.bot.think = 0; a.bot.lastPos.copy(a.pos); }
}

/* ---------- cars ---------- */
function makeCar(x, z, yaw, color) {
  const g = new T.Group();
  P(G.box, color, 2.1, .55, 3.6, 0, .75, 0, g); P(G.box, color, 2, .35, 1.2, 0, 1.15, 1.1, g);
  P(G.box, 0x222222, 2.15, .12, 3.7, 0, .5, 0, g); P(G.box, 0x3a3a3a, .9, .5, .8, 0, 1.2, -.2, g);
  for (const s of [-1, 1]) { P(G.box, 0x333333, .1, 1.1, .1, s * .95, 1.55, .2, g); P(G.box, 0xfff6c0, .35, .2, .08, s * .65, .85, 1.82, g); }
  P(G.box, 0x333333, 2, .1, .1, 0, 2.1, .2, g); P(G.box, 0x9fd8ff, 1.8, .6, .06, 0, 1.6, .55, g, -.3);
  const wheels = [];
  for (const a of [-1, 1]) for (const b of [-1, 1]) { const w = new T.Group(); w.position.set(a * 1.1, .5, b * 1.25); g.add(w); P(G.cyl, 0x1e1e1e, .5, .38, .5, 0, 0, 0, w, 0, 0, Math.PI / 2); P(G.cyl, 0xbbbbbb, .25, .4, .25, 0, 0, 0, w, 0, 0, Math.PI / 2); wheels.push(w); }
  const sh = new T.Mesh(G.circle, shadowMat); sh.scale.set(1.6, 1, 2.2); sh.position.y = .03; g.add(sh);
  scene.add(g);
  return { m: g, pos: new T.Vector3(x, 0, z), yaw, speed: 0, driver: null, wheels, home: { x, z, yaw }, sndT: 0 };
}
function enterCar(a, c) { a.car = c; c.driver = a; a.yaw = c.yaw; a.pitch = -.15; sfx('engine', c.pos); }
function exitCar(a) {
  const c = a.car; if (!c) return; c.driver = null; a.car = null;
  const rx = -Math.cos(c.yaw), rz = Math.sin(c.yaw);
  a.pos.set(c.pos.x - rx * 2, 0, c.pos.z - rz * 2); collideCircle(a.pos, 0, .45, ACT_H); a.pos.y = groundAt(a.pos.x, a.pos.z, 3);
}
function updateCar(c, dt) {
  const a = c.driver;
  if (a) {
    const thr = input.mz, st = input.mx;
    c.speed += thr * 20 * dt;
    c.speed *= 1 - (thr === 0 ? 1.6 : .55) * dt;
    c.speed = clamp(c.speed, -9, 26);
    c.yaw -= st * dt * clamp(c.speed / 7, -1, 1) * 2.1;
    c.sndT -= dt; if (c.sndT <= 0 && Math.abs(c.speed) > 1) { c.sndT = .22; sfx('engine'); }
  } else c.speed *= 1 - 2.5 * dt;
  if (Math.abs(c.speed) > .01) {
    c.pos.x += Math.sin(c.yaw) * c.speed * dt; c.pos.z += Math.cos(c.yaw) * c.speed * dt;
    if (collideCircle(c.pos, 0, 1.6, 1.2)) c.speed *= .55;
    if (a && Math.abs(c.speed) > 5) for (const e of game.actors) {
      if (!e.alive || e.team === a.team || e.car) continue;
      if (Math.hypot(e.pos.x - c.pos.x, e.pos.z - c.pos.z) < 2) damage(e, 250, a, 'car', false);
    }
  }
  for (const w of c.wheels) w.rotation.x += c.speed * dt / .5;
  c.m.position.copy(c.pos); c.m.rotation.y = c.yaw;
  if (a) { a.pos.set(c.pos.x, c.pos.y, c.pos.z); a.m.root.position.set(c.pos.x - Math.sin(c.yaw) * .2, .55, c.pos.z - Math.cos(c.yaw) * .2); a.m.root.rotation.y = c.yaw; }
}

/* ---------- pickups ---------- */
function makePickup(type, x, z) {
  const g = new T.Group();
  if (type === 'med') { P(G.box, 0xe53935, .8, .55, .55, 0, 0, 0, g); P(G.box, 0xffffff, .5, .14, .57, 0, 0, 0, g); P(G.box, 0xffffff, .14, .4, .57, 0, 0, 0, g); P(G.box, 0xb71c1c, .3, .08, .1, 0, .32, 0, g); }
  else { P(G.box, 0x55663a, .8, .45, .55, 0, 0, 0, g); P(G.sphLo, 0x3b4a2c, .17, .2, .17, -.15, .38, 0, g); P(G.sphLo, 0x3b4a2c, .17, .2, .17, .17, .38, 0, g); P(G.box, 0xffd54a, .82, .08, .57, 0, .05, 0, g); }
  g.position.set(x, .8, z); scene.add(g);
  return { type, pos: new T.Vector3(x, 0, z), m: g, cd: 0 };
}
function updatePickups(dt) {
  for (const p of game.pickups) {
    if (p.cd > 0) { p.cd -= dt; if (p.cd <= 0) p.m.visible = true; continue; }
    p.m.rotation.y += dt * 1.6; p.m.position.y = .8 + Math.sin(game.time * 3 + p.pos.x) * .12;
    for (const a of game.actors) {
      if (!a.alive || a.car || Math.hypot(a.pos.x - p.pos.x, a.pos.z - p.pos.z) > 1.3 || a.pos.y > 1.5) continue;
      if (p.type === 'med' && a.hp < a.maxHp) { a.hp = Math.min(a.maxHp, a.hp + 50); }
      else if (p.type === 'nade' && a.grenades < 4) { a.grenades = Math.min(4, a.grenades + 2); a.armor = Math.min(a.maxArmor, a.armor + 25); }
      else continue;
      p.cd = 20; p.m.visible = false;
      if (a.isPlayer) { sfx('pickup'); banner(p.type === 'med' ? '+50 здоровья' : '+2 гранаты', '#9be38a'); }
      break;
    }
  }
}

/* ---------- projectiles ---------- */
function spawnProj(type, owner, from, dir) {
  const g = new T.Group();
  if (type === 'rocket') { P(G.cylLo, 0x6c7d4b, .08, .5, .08, 0, 0, 0, g, Math.PI / 2); P(G.cone8, 0xd84315, .08, .2, .08, 0, 0, .34, g, Math.PI / 2); }
  else { P(G.sphLo, 0x3b4a2c, .14, .17, .14, 0, 0, 0, g); P(G.box, 0x999999, .06, .08, .06, 0, .17, 0, g); }
  g.position.copy(from); scene.add(g);
  const v = dir.clone().multiplyScalar(type === 'rocket' ? 42 : 17); if (type === 'nade') v.y += 4.5;
  game.projs.push({ type, owner, pos: from.clone(), v, m: g, t: 0 });
}
function explode(p, owner, dmg, radius) {
  boom(p.x, p.y, p.z, radius);
  for (const a of game.actors) {
    if (!a.alive) continue;
    const d = Math.hypot(a.pos.x - p.x, a.pos.y + .8 - p.y, a.pos.z - p.z);
    if (d > radius || (a.team === owner.team && a !== owner)) continue;
    const k = 1 - d / radius; damage(a, dmg * (.35 + .65 * k) * (a === owner ? .5 : 1), owner, owner.weapons ? 'boom' : 'boom', false);
    if (!a.car) a.vy = Math.max(a.vy, 6 * k);
  }
}
function updateProjs(dt) {
  for (let i = game.projs.length - 1; i >= 0; i--) {
    const p = game.projs[i]; p.t += dt;
    let hit = false;
    if (p.type === 'nade') {
      p.v.y -= 22 * dt;
      const ox = p.pos.x, oz = p.pos.z;
      p.pos.addScaledVector(p.v, dt);
      for (const c of world.cols) if (p.pos.x > c.x0 && p.pos.x < c.x1 && p.pos.z > c.z0 && p.pos.z < c.z1 && p.pos.y > c.y0 && p.pos.y < c.y1) {
        if (oz > c.z0 && oz < c.z1 && !(ox > c.x0 && ox < c.x1)) p.v.x *= -.4; else if (ox > c.x0 && ox < c.x1 && !(oz > c.z0 && oz < c.z1)) p.v.z *= -.4; else { p.v.y = Math.abs(p.v.y) * .3; p.pos.y = c.y1 + .1; }
        p.pos.x = ox; p.pos.z = oz; break;
      }
      if (p.pos.y < .15) { p.pos.y = .15; p.v.y = Math.abs(p.v.y) * .35; p.v.x *= .7; p.v.z *= .7; }
      p.m.rotation.x += dt * 8;
      if (p.t > 2) { explode(p.pos, p.owner, 115, 5.5); hit = true; }
    } else {
      const step = p.v.length() * dt; _v1.copy(p.v).normalize();
      const tr = traceShot(p.pos, _v1, step, p.owner);
      if (tr.t < step || p.t > 4) { p.pos.addScaledVector(_v1, Math.min(tr.t, step)); explode(p.pos, p.owner, WEAPONS.rocket.dmg, WEAPONS.rocket.splash); hit = true; }
      else { p.pos.addScaledVector(p.v, dt); if (Math.random() < .6) burst(p.pos.x, p.pos.y, p.pos.z, [0xaaaaaa, 0xffb74d], 1, .5, .35, .18); }
      p.m.lookAt(_v2.copy(p.pos).add(p.v));
    }
    p.m.position.copy(p.pos);
    if (hit) { scene.remove(p.m); game.projs.splice(i, 1); }
  }
}

/* ---------- combat ---------- */
function startReload(a) {
  const ws = a.weapons[a.cur], w = WEAPONS[ws.id];
  if (a.reload > 0 || ws.ammo >= w.mag) return;
  a.reload = w.reload; if (a.isPlayer) sfx('reload');
}
function switchWeapon(a, idx) {
  if (idx === undefined) idx = 1 - a.cur;
  if (idx === a.cur || !a.weapons[idx]) return;
  a.cur = idx; a.reload = 0; a.cd = .35; equipGun(a);
  if (a.isPlayer) { input.aim = false; sfx('click'); }
}
const _o = new T.Vector3(), _d = new T.Vector3(), _sd = new T.Vector3(), _mz = new T.Vector3(), _end = new T.Vector3();
function fire(a, origin, dir) {
  const ws = a.weapons[a.cur], w = WEAPONS[ws.id];
  if (!a.alive || a.car || a.reload > 0 || a.cd > 0) return;
  if (ws.ammo <= 0) { startReload(a); return; }
  a.cd = w.rate; ws.ammo--; a.flash = .05; a.lastShot = game.time; a.spawnProt = 0;
  a.m.root.updateMatrixWorld(true);
  _mz.set(0, 0, a.gunModel.userData.muz + .05); a.gunModel.localToWorld(_mz);
  if (w.rocket) {
    const from = _mz.clone(); const t = traceShot(origin, dir, 200, a).t; _end.copy(origin).addScaledVector(dir, t);
    spawnProj('rocket', a, from, _end.sub(from).normalize());
  } else {
    let spread = w.spread;
    if (a.isPlayer) { if (input.aim) spread *= w.zoom ? 0 : .45; if (!a.onGround) spread *= 1.6; }
    else spread += .035 * (1.5 - a.bot.skill);
    for (let i = 0; i < (w.pellets || 1); i++) {
      _sd.set(dir.x + rand(-1, 1) * spread, dir.y + rand(-1, 1) * spread, dir.z + rand(-1, 1) * spread).normalize();
      const r = traceShot(origin, _sd, w.range || 120, a);
      _end.copy(origin).addScaledVector(_sd, r.t);
      if (i < 3) tracer(_mz, _end);
      if (r.actor) {
        let dmg = w.dmg * (r.head ? 1.7 : 1);
        if (w.range && r.t > w.range * .5) dmg *= .6;
        if (!a.isPlayer && r.actor.isPlayer) dmg *= .65;
        damage(r.actor, dmg, a, ws.id, r.head);
      } else if (r.t < (w.range || 120)) burst(_end.x, _end.y + .05, _end.z, world.theme.ground2, 2, 2.5, .3, .1);
    }
  }
  sfx(w.heavy || w.rocket ? 'heavy' : 'shot', a.isPlayer ? null : a.pos);
  if (a.isPlayer) { a.pitch = Math.min(1.2, a.pitch + (w.heavy ? .03 : .008)); game.shake = Math.max(game.shake, w.heavy ? .12 : .04); }
  if (ws.ammo <= 0) startReload(a);
}
function throwNade(a, dir) {
  if (!a.alive || a.car || a.grenades <= 0 || a.cd > 0) return;
  a.grenades--; a.cd = .4; _o.set(a.pos.x, a.pos.y + 1.6, a.pos.z);
  spawnProj('nade', a, _o.clone(), dir.clone());
}
function damage(t, dmg, src, wid, head) {
  if (!t.alive || game.state !== 'play' || t.spawnProt > 0) return;
  if (t.armor > 0) { const ab = Math.min(t.armor, dmg * .6); t.armor -= ab; dmg -= ab; }
  t.hp -= dmg; t.hurt = .2;
  burst(t.pos.x, t.pos.y + 1, t.pos.z, [FEATHERS[t.look.col].c, 0xffffff], head ? 5 : 3, 3, .9, .16, 2.5);
  if (src && src.isPlayer && t !== src) { hitMark(t.hp <= 0); sfx(t.hp <= 0 ? 'kill' : 'hit'); }
  if (t.isPlayer) { game.hurtFlash = .5; }
  if (t.bot && src && src.team !== t.team && (!t.bot.target || Math.random() < .5)) { t.bot.target = src; t.bot.react = Math.min(t.bot.react, .2); }
  if (t.hp <= 0) kill(t, src, wid, head);
}
const WICON = { pistol: '🔫', revolver: '🔫', smg: '🔫', rifle: '🔫', shotgun: '🔫', sniper: '🎯', minigun: '🔫', rocket: '🚀', boom: '💥', car: '🚙' };
function kill(t, src, wid, head) {
  t.alive = false; t.hp = 0; t.deaths++; t.respawn = 4; t.killedBy = src && src !== t ? src.name : '';
  if (t.car) exitCar(t);
  const fc = FEATHERS[t.look.col].c;
  burst(t.pos.x, t.pos.y + .9, t.pos.z, [fc, fc, 0xffffff, 0xe8322b], 26, 5, 2.4, .22, 2.2);
  t.m.root.visible = false; sfx('cluck', t.pos);
  if (src && src !== t) {
    src.kills++; game.scores[src.team] += KILL_PTS;
    if (src.isPlayer) { earn(25); game.pKills++; }
  }
  addFeed(src, t, wid, head);
}
function earn(n) { game.earned += n; S.coins += n; }

/* ---------- player ---------- */
function playerAim() {
  const a = game.player;
  _d.set(Math.sin(a.yaw) * Math.cos(a.pitch), Math.sin(a.pitch), Math.cos(a.yaw) * Math.cos(a.pitch));
  const hx = a.pos.x - camera.position.x, hy = a.pos.y + 1.5 - camera.position.y, hz = a.pos.z - camera.position.z;
  const t = Math.max(0, hx * _d.x + hy * _d.y + hz * _d.z);
  _o.copy(camera.position).addScaledVector(_d, t);
  return _o;
}
function updatePlayer(a, dt) {
  if (!a.alive) return;
  let mx = input.mx, mz = input.mz;
  const k = input.keys;
  if (k.KeyW || k.ArrowUp) mz += 1; if (k.KeyS || k.ArrowDown) mz -= 1; if (k.KeyA || k.ArrowLeft) mx -= 1; if (k.KeyD || k.ArrowRight) mx += 1;
  const ml = Math.hypot(mx, mz); if (ml > 1) { mx /= ml; mz /= ml; }
  input.mx2 = mx; input.mz2 = mz;
  if (a.car) {
    const saveX = input.mx, saveZ = input.mz; input.mx = mx; input.mz = mz; updateCar(a.car, dt); input.mx = saveX; input.mz = saveZ;
    if (game.time - game.lastLook > .9) { let d = a.car.yaw - a.yaw; d = Math.atan2(Math.sin(d), Math.cos(d)); a.yaw += d * Math.min(1, dt * 3); }
    return;
  }
  const w = WEAPONS[a.weapons[a.cur].id];
  const sp = 6.4 * (w.slow || 1) * (input.aim ? .6 : 1);
  const fx = Math.sin(a.yaw), fz = Math.cos(a.yaw), rx = -Math.cos(a.yaw), rz = Math.sin(a.yaw);
  moveActor(a, (fx * mz + rx * mx) * sp * dt, (fz * mz + rz * mx) * sp * dt);
  if ((input.jump || k.Space) && a.onGround) { a.vy = 8.6; a.onGround = false; }
  input.jump = false;
  if (input.fire) { const o = playerAim(); fire(a, o.clone(), _d.clone()); }
}
function moveActor(a, dx, dz) {
  a.pos.x += dx; a.pos.z += dz;
  collideCircle(a.pos, a.pos.y, .45, ACT_H);
  for (const c of game.cars) {
    if (c.driver === a) continue;
    const ex = a.pos.x - c.pos.x, ez = a.pos.z - c.pos.z, d = Math.hypot(ex, ez);
    if (d < 1.9 && d > 1e-4 && a.pos.y < 1.6) { a.pos.x = c.pos.x + ex / d * 1.9; a.pos.z = c.pos.z + ez / d * 1.9; }
  }
}

/* ---------- bots ---------- */
function blockedAhead(x, z, y) {
  for (const c of world.cols) if (y < c.y1 - .36 && x > c.x0 - .5 && x < c.x1 + .5 && z > c.z0 - .5 && z < c.z1 + .5) return true;
  return false;
}
function angDiff(a, b) { let d = b - a; return Math.atan2(Math.sin(d), Math.cos(d)); }
function updateBot(a, dt) {
  if (!a.alive) return;
  const b = a.bot;
  b.think -= dt; b.react -= dt; b.strafeT -= dt; b.jumpT -= dt;
  if (b.think <= 0) {
    b.think = .25 + Math.random() * .2;
    let best = null, bd = 1e9;
    for (const e of game.actors) {
      if (e.team === a.team || !e.alive) continue;
      const d = a.pos.distanceTo(e.pos); if (d > 55 || d > bd) continue;
      if (los(a, e)) { best = e; bd = d; }
    }
    if (best !== b.target) { b.react = .35 + Math.random() * .45 * (1.6 - b.skill); }
    b.target = best;
    const ownZone = game.zone.owner === a.team && Math.abs(game.zone.v) >= 1;
    if (a.pos.distanceTo(b.goal) < 2.5 || Math.random() < .04 || b.goal.lengthSq() === 0) {
      const r = ownZone && Math.random() < .5 ? rand(8, 16) : rand(0, 5), an = Math.random() * Math.PI * 2;
      b.goal.set(Math.cos(an) * r, 0, Math.sin(an) * r);
    }
  }
  const t = b.target && b.target.alive ? b.target : null;
  let gx = b.goal.x - a.pos.x, gz = b.goal.z - a.pos.z;
  if (t) {
    const ex = t.pos.x - a.pos.x, ez = t.pos.z - a.pos.z, d = Math.hypot(ex, ez) || 1;
    if (b.strafeT <= 0) { b.strafe = Math.random() < .5 ? -1 : 1; b.strafeT = rand(.6, 1.6); }
    const want = a.weapons[a.cur].id === 'shotgun' ? 6 : 14;
    const fwd = d > want + 6 ? 1 : d < want - 6 ? -1 : 0;
    const inZone = Math.hypot(a.pos.x, a.pos.z) < ZONE_R;
    const gl0 = Math.hypot(gx, gz) || 1, gk = inZone ? 0 : .5 / gl0;
    gx = (ex / d) * fwd + (-ez / d) * b.strafe * .8 + gx * gk;
    gz = (ez / d) * fwd + (ex / d) * b.strafe * .8 + gz * gk;
  }
  let gl = Math.hypot(gx, gz);
  let mx = 0, mz = 0;
  if (gl > .3) { mx = gx / gl; mz = gz / gl; }
  if (b.detour > 0) { b.detour -= dt; mx = b.detourDir.x; mz = b.detourDir.z; }
  else if (gl > .3 && blockedAhead(a.pos.x + mx * 1.3, a.pos.z + mz * 1.3, a.pos.y)) {
    const c = Math.cos(b.avoid * 1.3), s = Math.sin(b.avoid * 1.3);
    let nx = mx * c - mz * s, nz = mx * s + mz * c;
    if (blockedAhead(a.pos.x + nx * 1.3, a.pos.z + nz * 1.3, a.pos.y)) { b.avoid = -b.avoid; nx = mx * c + mz * s; nz = -mx * s + mz * c; }
    mx = nx; mz = nz;
  }
  const w = WEAPONS[a.weapons[a.cur].id];
  const sp = 5.6 * (w.slow || 1) * (t ? .85 : 1);
  moveActor(a, mx * sp * dt, mz * sp * dt);
  // stuck detection
  b.stuck += dt;
  if (b.stuck > .8) {
    if (a.pos.distanceTo(b.lastPos) < .8 && (mx || mz)) {
      const an = Math.random() * Math.PI * 2; b.detourDir.set(Math.cos(an), 0, Math.sin(an)); b.detour = rand(.6, 1.2); b.avoid = -b.avoid;
      if (a.onGround) a.vy = 8.6;
    }
    b.stuck = 0; b.lastPos.copy(a.pos);
  }
  if (b.jumpT <= 0) { b.jumpT = rand(3, 8); if (t && a.onGround && Math.random() < .5) a.vy = 8.6; }
  // aim
  let dyaw, dpitch = 0;
  if (t) {
    const ex = t.pos.x - a.pos.x, ez = t.pos.z - a.pos.z, ey = t.pos.y + .9 - (a.pos.y + 1.3);
    dyaw = Math.atan2(ex, ez); dpitch = Math.atan2(ey, Math.hypot(ex, ez));
  } else dyaw = (mx || mz) ? Math.atan2(mx, mz) : a.yaw;
  const err = angDiff(a.yaw, dyaw);
  a.yaw += clamp(err, -6 * dt, 6 * dt) ; a.pitch += (dpitch - a.pitch) * Math.min(1, dt * 6);
  if (t && b.react <= 0 && Math.abs(err) < .2) {
    const ws = a.weapons[a.cur];
    if (ws.ammo <= 0 && a.weapons.length > 1 && Math.random() < .01) switchWeapon(a);
    _o.set(a.pos.x, a.pos.y + 1.3, a.pos.z);
    const lead = .08 * (t.speedH || 0);
    _d.set(t.pos.x - _o.x + rand(-lead, lead), t.pos.y + .9 - _o.y, t.pos.z - _o.z + rand(-lead, lead)).normalize();
    if (a.grenades > 0 && Math.random() < .002 && a.pos.distanceTo(t.pos) > 8 && a.pos.distanceTo(t.pos) < 20) { _d.y += .25; throwNade(a, _d.normalize()); }
    else fire(a, _o.clone(), _d.clone());
  }
}

/* ---------- per-actor shared update ---------- */
function updateActor(a, dt) {
  if (!a.alive) {
    a.respawn -= dt;
    if (a.respawn <= 0) spawnActor(a);
    return;
  }
  a.cd -= dt; a.spawnProt -= dt; a.flash -= dt; a.hurt -= dt;
  if (a.reload > 0) { a.reload -= dt; if (a.reload <= 0) { a.reload = 0; a.weapons[a.cur].ammo = WEAPONS[a.weapons[a.cur].id].mag; } }
  const r = a.m.root;
  if (!a.car) {
    a.vy -= 24 * dt; a.pos.y += a.vy * dt;
    const g = groundAt(a.pos.x, a.pos.z, a.pos.y);
    if (a.pos.y <= g) { a.pos.y = g; a.vy = 0; a.onGround = true; } else a.onGround = a.pos.y - g < .05;
    const px = r.position.x, pz = r.position.z;
    a.speedH = Math.hypot(a.pos.x - px, a.pos.z - pz) / Math.max(dt, 1e-4);
    r.position.copy(a.pos); r.rotation.y = a.yaw;
  } else a.speedH = Math.abs(a.car.speed);
  const moving = a.car ? 0 : clamp(a.speedH / 6, 0, 1);
  a.walk += dt * (6 + a.speedH * 1.6) * (moving > .05 ? 1 : 0);
  const sw = Math.sin(a.walk) * .8 * moving;
  a.m.legL.rotation.x = a.onGround ? sw : -.5; a.m.legR.rotation.x = a.onGround ? -sw : .3;
  a.m.body.position.y = Math.abs(Math.cos(a.walk)) * .08 * moving;
  a.m.body.rotation.z = Math.sin(a.walk) * .06 * moving;
  a.m.wingL.rotation.z = a.onGround ? -.1 * moving : -.9 + Math.sin(game.time * 30) * .4;
  a.m.head.rotation.x = -a.pitch * .45; a.m.gun.rotation.x = -a.pitch;
  a.m.shadow.position.y = .03 - a.pos.y + groundAt(a.pos.x, a.pos.z, a.pos.y);
  if (a.flashM) a.flashM.visible = a.flash > 0;
  r.visible = a.spawnProt > 0 ? Math.floor(game.time * 12) % 2 === 0 : true;
  if (a.isPlayer && camDist < .5) r.visible = false;
}

/* ---------- zone ---------- */
function updateZone(dt) {
  const n = [0, 0];
  for (const a of game.actors) if (a.alive && !a.car && Math.hypot(a.pos.x, a.pos.z) < ZONE_R && a.pos.y < 3) n[a.team]++;
  const z = game.zone, prev = z.owner;
  if (n[0] > 0 && n[1] === 0) z.v = Math.min(1, z.v + dt * .1 * Math.min(n[0], 3));
  else if (n[1] > 0 && n[0] === 0) z.v = Math.max(-1, z.v - dt * .1 * Math.min(n[1], 3));
  if (z.v >= 1) z.owner = 0; else if (z.v <= -1) z.owner = 1;
  if (z.owner === 0 && z.v <= 0) z.owner = -1; if (z.owner === 1 && z.v >= 0) z.owner = -1;
  if (z.owner !== prev) {
    if (z.owner >= 0) { banner(z.owner === 0 ? 'Точка захвачена!' : 'Враги захватили точку!', z.owner === 0 ? '#7fb2ff' : '#ff8a8a'); if (z.owner === 0 && n[0] > 0 && game.player.alive && Math.hypot(game.player.pos.x, game.player.pos.z) < ZONE_R) earn(20); }
    else banner('Точка потеряна', '#ffffff');
  }
  if (z.owner >= 0) game.scores[z.owner] += dt * 2;
  z.contested = n[0] > 0 && n[1] > 0; z.n = n;
  const col = z.owner === 0 ? TEAM_COL[0] : z.owner === 1 ? TEAM_COL[1] : 0xffffff;
  world.ringMat.color.setHex(z.contested ? 0xffc928 : col); world.colMat.color.setHex(col); world.flag.material.color.setHex(col);
  world.ring.rotation.y += dt * .3; world.colMat.opacity = .08 + Math.sin(game.time * 3) * .03;
}

/* =====================================================================
   CAMERA
   ===================================================================== */
let camDist = 3.4;
function updateCamera(dt) {
  const a = game.player;
  const w = WEAPONS[a.weapons[a.cur].id];
  const scoped = input.aim && w.zoom && a.alive && !a.car;
  const wantDist = a.car ? 7.5 : scoped ? 0 : input.aim ? 2.1 : 3.4;
  camDist += (wantDist - camDist) * Math.min(1, dt * 14);
  if (scoped && camDist < .3) camDist = 0;
  const fov = scoped ? 70 / w.zoom : input.aim ? 58 : 70;
  if (Math.abs(camera.fov - fov) > .1) { camera.fov += (fov - camera.fov) * Math.min(1, dt * 14); camera.updateProjectionMatrix(); }
  const d = _d.set(Math.sin(a.yaw) * Math.cos(a.pitch), Math.sin(a.pitch), Math.cos(a.yaw) * Math.cos(a.pitch));
  const rx = -Math.cos(a.yaw), rz = Math.sin(a.yaw);
  const side = a.car ? 0 : camDist < .5 ? 0 : .75;
  const base = _v1.set(a.pos.x + rx * side, (a.car ? 1.6 : a.pos.y + 1.6), a.pos.z + rz * side);
  if (!a.alive) base.y += 1.5;
  let dist = camDist;
  if (dist > 0) {
    _v2.copy(d).negate();
    const hit = rayWorld(base, _v2, dist + .3);
    if (hit < dist + .3) dist = Math.max(.3, hit - .3);
  }
  camera.position.copy(base).addScaledVector(d, -dist);
  if (camera.position.y < .3) camera.position.y = .3;
  if (game.shake > 0) { camera.position.x += rand(-1, 1) * game.shake * .3; camera.position.y += rand(-1, 1) * game.shake * .3; game.shake = Math.max(0, game.shake - dt * 2); }
  camera.lookAt(_v2.copy(camera.position).add(d));
  $('scope').classList.toggle('on', !!scoped && camDist === 0);
  crossEl.style.display = scoped && camDist === 0 ? 'none' : '';
}

/* =====================================================================
   HUD
   ===================================================================== */
const crossEl = $('cross');
const hudCache = {};
function setT(id, v) { if (hudCache[id] !== v) { hudCache[id] = v; $(id).textContent = v; } }
function setS(id, prop, v) { const k = id + prop; if (hudCache[k] !== v) { hudCache[k] = v; $(id).style[prop] = v; } }
let hitT = 0, bannerT = 0, mmT = 0;
function hitMark(killed) { const h = $('hitmark'); h.classList.add('on'); h.classList.toggle('kill', !!killed); hitT = .18; }
function banner(text, color) { const b = $('banner'); b.textContent = text; b.style.color = color || '#fff'; b.classList.add('on'); bannerT = 2; }
function addFeed(src, t, wid, head) {
  const el = document.createElement('div');
  const nm = (a) => `<span class="${a.team === 0 ? 'b' : 'r'}">${a.name}</span>`;
  el.innerHTML = (src && src !== t ? nm(src) + ' ' : '') + (WICON[wid] || '💥') + (head ? ' 🎯' : '') + ' ' + nm(t);
  if ((src && src.isPlayer) || t.isPlayer) el.classList.add('me');
  const kf = $('killfeed'); kf.prepend(el); while (kf.children.length > 5) kf.lastChild.remove();
  setTimeout(() => el.remove(), 4500);
}
function updateHUD(dt) {
  const a = game.player, ws = a.weapons[a.cur], w = WEAPONS[ws.id];
  setT('sBlue', Math.floor(game.scores[0])); setT('sRed', Math.floor(game.scores[1]));
  const tl = Math.max(0, Math.ceil(game.timeLeft)); setT('timer', Math.floor(tl / 60) + ':' + String(tl % 60).padStart(2, '0'));
  const z = game.zone;
  setS('capFill', 'left', (z.v >= 0 ? 50 : 50 + z.v * 50) + '%'); setS('capFill', 'width', Math.abs(z.v) * 50 + '%');
  setS('capFill', 'background', z.v >= 0 ? '#3d8bff' : '#ff4d4d');
  setT('capText', z.contested ? 'Точка оспаривается!' : z.owner === 0 ? 'Точка наша · +2/сек' : z.owner === 1 ? 'Точка у врага' : 'Точка свободна');
  setS('hpFill', 'width', Math.max(0, a.hp) + '%'); setT('hpText', Math.max(0, Math.ceil(a.hp)));
  setS('arFill', 'width', a.maxArmor ? (a.armor / a.maxArmor * 100) + '%' : '0%');
  setT('wName', a.reload > 0 ? 'Перезарядка…' : w.name);
  setT('ammo', String(ws.ammo)); setT('ammoMax', '/' + w.mag);
  setT('nades', '💣×' + a.grenades);
  if (hitT > 0) { hitT -= dt; if (hitT <= 0) $('hitmark').classList.remove('on'); }
  if (bannerT > 0) { bannerT -= dt; if (bannerT <= 0) $('banner').classList.remove('on'); }
  game.hurtFlash = Math.max(0, (game.hurtFlash || 0) - dt);
  setS('vignette', 'opacity', String(Math.min(1, game.hurtFlash * 1.6 + (a.alive && a.hp < 35 ? .45 : 0))));
  // death screen
  const dead = $('dead');
  if (!a.alive) { dead.style.display = 'block'; setT('deadT', String(Math.max(1, Math.ceil(a.respawn)))); setT('deadBy', a.killedBy ? 'Вас подстрелил ' + a.killedBy : ''); }
  else if (dead.style.display !== 'none') dead.style.display = 'none';
  // car button
  let near = null;
  if (a.alive && !a.car) for (const c of game.cars) if (!c.driver && Math.hypot(c.pos.x - a.pos.x, c.pos.z - a.pos.z) < 3.4) near = c;
  game.nearCar = near;
  const btn = $('btnCar'), show = !!(near || a.car);
  if (btn.style.display !== (show ? 'block' : 'none')) btn.style.display = show ? 'block' : 'none';
  if (show) setT('btnCar', a.car ? 'ВЫЙТИ [E]' : 'СЕСТЬ [E]');
  // touch aim button state
  $('tAim').classList.toggle('act', input.aim);
  mmT -= dt; if (mmT <= 0) { mmT = .1; drawMinimap(); }
}

/* ---------- minimap ---------- */
let mmBase = null;
const MMW = 120, mmS = (v) => (v + HALF + 2) / (HALF * 2 + 4) * MMW;
function buildMinimapBase() {
  mmBase = document.createElement('canvas'); mmBase.width = mmBase.height = MMW;
  const g = mmBase.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0)'; g.clearRect(0, 0, MMW, MMW);
  g.fillStyle = 'rgba(255,255,255,.18)'; g.fillRect(mmS(-2.5), 0, mmS(2.5) - mmS(-2.5), MMW); g.fillRect(0, mmS(-2.5), MMW, mmS(2.5) - mmS(-2.5));
  g.fillStyle = 'rgba(255,255,255,.55)';
  for (const c of world.cols) if (c.y1 < 30 && c.y0 < 3) g.fillRect(mmS(c.x0), mmS(c.z0), Math.max(1, mmS(c.x1) - mmS(c.x0)), Math.max(1, mmS(c.z1) - mmS(c.z0)));
}
const mmCtx = $('minimap').getContext('2d');
function drawMinimap() {
  const g = mmCtx, p = game.player;
  g.clearRect(0, 0, MMW, MMW); g.drawImage(mmBase, 0, 0);
  const z = game.zone; g.beginPath(); g.arc(mmS(0), mmS(0), ZONE_R / (HALF * 2 + 4) * MMW, 0, 7);
  g.fillStyle = z.owner === 0 ? 'rgba(61,139,255,.6)' : z.owner === 1 ? 'rgba(255,77,77,.6)' : 'rgba(255,255,255,.35)'; g.fill();
  for (const c of game.cars) { g.fillStyle = '#ffc928'; g.fillRect(mmS(c.pos.x) - 2, mmS(c.pos.z) - 2, 4, 4); }
  for (const a of game.actors) {
    if (!a.alive || a.isPlayer) continue;
    if (a.team !== p.team && game.time - a.lastShot > 1.5) continue;
    g.fillStyle = a.team === 0 ? '#7fb2ff' : '#ff6b6b'; g.beginPath(); g.arc(mmS(a.pos.x), mmS(a.pos.z), 2.6, 0, 7); g.fill();
  }
  if (p.alive) {
    g.save(); g.translate(mmS(p.pos.x), mmS(p.pos.z)); g.rotate(-p.yaw + Math.PI);
    g.fillStyle = '#ffc928'; g.beginPath(); g.moveTo(0, -6); g.lineTo(4, 4); g.lineTo(-4, 4); g.closePath(); g.fill(); g.restore();
  }
}

/* =====================================================================
   MATCH FLOW
   ===================================================================== */
function randomLook() {
  const pick = (o) => { const k = Object.keys(o); return k[Math.floor(Math.random() * k.length)]; };
  return { col: pick(FEATHERS), hat: Math.random() < .75 ? pick(HATS) : 'none', gl: Math.random() < .4 ? pick(GLASSES) : 'none' };
}
function clearMatch() {
  for (const a of game.actors) scene.remove(a.m.root);
  for (const c of game.cars) scene.remove(c.m);
  for (const p of game.pickups) scene.remove(p.m);
  for (const p of game.projs) scene.remove(p.m);
  game.actors = []; game.cars = []; game.pickups = []; game.projs = [];
  for (const p of FX.parts) { p.life = 0; p.m.visible = false; }
  for (const t of FX.tracers) { t.life = 0; t.m.visible = false; }
  for (const b of FX.booms) { b.life = 0; b.m.visible = false; }
}
function startMatch() {
  initAudio();
  if (isTouch) {
    try { const de = document.documentElement; (de.requestFullscreen || de.webkitRequestFullscreen || (() => {})).call(de); } catch (e) { /* ignore */ }
    try { screen.orientation && screen.orientation.lock && screen.orientation.lock('landscape').catch(() => {}); } catch (e) { /* ignore */ }
  }
  clearMatch();
  buildWorld(S.map);
  const used = new Set();
  const nameFor = () => { let n; do n = BOT_NAMES[Math.floor(Math.random() * BOT_NAMES.length)]; while (used.has(n)); used.add(n); return n; };
  const pl = makeActor(0, true, { col: S.eq.col, hat: S.eq.hat, gl: S.eq.gl }, 'Вы', [S.eq.prim, S.eq.sec], S.armor);
  game.player = pl; game.actors.push(pl);
  const prim = ['smg', 'smg', 'rifle', 'rifle', 'shotgun', 'sniper', 'minigun', 'rocket'];
  for (let i = 0; i < 9; i++) {
    const team = i < 4 ? 0 : 1;
    const b = makeActor(team, false, randomLook(), nameFor(), [prim[Math.floor(Math.random() * prim.length)], Math.random() < .3 ? 'revolver' : 'pistol'], Math.random() < .35 ? 1 : 0);
    game.actors.push(b);
  }
  for (const a of game.actors) spawnActor(a);
  game.cars.push(makeCar(12, -44, 0, 0x2e86de), makeCar(-12, 44, Math.PI, 0xe74c3c));
  for (const [x, z] of [[-24, 0], [24, 0], [0, -31], [0, 31]]) game.pickups.push(makePickup('med', x, z));
  for (const [x, z] of [[-12, 26], [12, -26], [-30, -18], [30, 18]]) game.pickups.push(makePickup('nade', x, z));
  Object.assign(game, { scores: [0, 0], zone: { v: 0, owner: -1, n: [0, 0] }, timeLeft: MATCH_TIME, earned: 0, pKills: 0, shake: 0, time: 0, hurtFlash: 0 });
  input.fire = false; input.aim = false; input.mx = input.mz = 0;
  camDist = 3.4; camera.fov = 70; camera.updateProjectionMatrix();
  $('killfeed').innerHTML = '';
  showScreen('hud'); game.state = 'play';
  banner('Захватите точку в центре!', '#ffc928');
  lockPointer();
}
function endMatch() {
  game.state = 'end';
  const won = game.scores[0] > game.scores[1] ? 0 : game.scores[1] > game.scores[0] ? 1 : -1;
  const bonus = won === 0 ? 150 : won === -1 ? 80 : 50;
  earn(bonus);
  S.stats.games++; S.stats.kills += game.pKills; if (won === 0) S.stats.wins++;
  save();
  $('endTitle').textContent = won === 0 ? 'ПОБЕДА!' : won === 1 ? 'ПОРАЖЕНИЕ' : 'НИЧЬЯ';
  $('endTitle').style.color = won === 0 ? '#ffc928' : won === 1 ? '#ff8a8a' : '#fff';
  $('eBlue').textContent = Math.floor(game.scores[0]); $('eRed').textContent = Math.floor(game.scores[1]);
  const p = game.player;
  const best = game.actors.slice().sort((x, y) => y.kills - x.kills)[0];
  $('endStats').innerHTML = `Убийств: <b>${p.kills}</b> · Смертей: <b>${p.deaths}</b><br>Лучший игрок: <b>${best.name}</b> (${best.kills})`;
  $('endCoins').textContent = '+' + game.earned;
  unlockPointer();
  showScreen('end');
}
function quitToMenu() { save(); clearMatch(); game.state = 'menu'; unlockPointer(); showScreen('menu'); refreshMenu(); }

function update(dt) {
  game.time += dt; game.timeLeft -= dt;
  const p = game.player;
  updatePlayer(p, dt);
  for (const a of game.actors) if (a.bot) updateBot(a, dt);
  for (const a of game.actors) updateActor(a, dt);
  for (const c of game.cars) if (!c.driver || !c.driver.isPlayer) updateCar(c, dt);
  updateProjs(dt); updatePickups(dt); updateZone(dt); updateFX(dt);
  for (const b of world.blades) b.rotation.x += dt * 1.2;
  for (const a of game.actors) if (a.marker) a.marker.rotation.y += dt * 3;
  updateCamera(dt); updateHUD(dt);
  if (game.scores[0] >= WIN_SCORE || game.scores[1] >= WIN_SCORE || game.timeLeft <= 0) endMatch();
}

/* =====================================================================
   INPUT
   ===================================================================== */
function look(dx, dy, k) {
  const a = game.player; if (!a) return;
  const w = WEAPONS[a.weapons[a.cur].id];
  const z = input.aim ? (w.zoom ? 1 / w.zoom : .7) : 1;
  a.yaw -= dx * k * S.sens * z; a.pitch = clamp(a.pitch - dy * k * S.sens * z, -1.25, 1.25);
  game.lastLook = game.time;
}
function lockPointer() { if (!isTouch && canvas.requestPointerLock) try { canvas.requestPointerLock(); } catch (e) { /* ignore */ } }
function unlockPointer() { if (document.pointerLockElement) document.exitPointerLock(); }
document.addEventListener('pointerlockchange', () => { if (!document.pointerLockElement && game.state === 'play' && !isTouch) pause(); });
canvas.addEventListener('click', () => { if (game.state === 'play' && !document.pointerLockElement) lockPointer(); });
document.addEventListener('mousemove', (e) => { if (game.state === 'play' && document.pointerLockElement) look(e.movementX, e.movementY, .0023); });
canvas.addEventListener('mousedown', (e) => {
  if (game.state !== 'play' || !document.pointerLockElement) return;
  if (e.button === 0) input.fire = true; if (e.button === 2) input.aim = true;
});
document.addEventListener('mouseup', (e) => { if (e.button === 0) input.fire = false; if (e.button === 2) input.aim = false; });
document.addEventListener('contextmenu', (e) => e.preventDefault());
document.addEventListener('keydown', (e) => {
  input.keys[e.code] = true;
  if (game.state !== 'play') return;
  const p = game.player;
  switch (e.code) {
    case 'KeyR': startReload(p); break;
    case 'Digit1': switchWeapon(p, 0); break; case 'Digit2': switchWeapon(p, 1); break; case 'KeyQ': switchWeapon(p); break;
    case 'KeyG': throwNade(p, playerDir()); break;
    case 'KeyE': carAction(); break;
    case 'Space': input.jump = true; e.preventDefault(); break;
    case 'KeyP': pause(); break;
  }
});
document.addEventListener('keyup', (e) => { input.keys[e.code] = false; });
window.addEventListener('blur', () => { input.keys = {}; input.fire = false; if (game.state === 'play') pause(); });
function playerDir() { const a = game.player; return new T.Vector3(Math.sin(a.yaw) * Math.cos(a.pitch), Math.sin(a.pitch), Math.cos(a.yaw) * Math.cos(a.pitch)); }
function carAction() {
  const p = game.player; if (!p.alive) return;
  if (p.car) exitCar(p); else if (game.nearCar) enterCar(p, game.nearCar);
}

/* ---------- touch controls (pointer events, multi-touch) ---------- */
(function touchControls() {
  const joyZone = $('joyZone'), base = $('joyBase'), knob = $('joyKnob'), lookZone = $('lookZone');
  let joyId = null, jx = 0, jy = 0;
  const R = 55;
  const baseHome = () => { base.style.left = '110px'; base.style.top = ''; base.style.bottom = '75px'; };
  joyZone.addEventListener('pointerdown', (e) => {
    if (joyId !== null) return; joyId = e.pointerId; joyZone.setPointerCapture(e.pointerId);
    const r = joyZone.getBoundingClientRect(); jx = e.clientX; jy = e.clientY;
    base.style.left = (e.clientX - r.left) + 'px'; base.style.top = (e.clientY - r.top) + 'px'; base.style.bottom = 'auto';
    base.style.marginTop = '-65px';
  });
  joyZone.addEventListener('pointermove', (e) => {
    if (e.pointerId !== joyId) return;
    let dx = e.clientX - jx, dy = e.clientY - jy; const l = Math.hypot(dx, dy);
    if (l > R) { dx = dx / l * R; dy = dy / l * R; }
    knob.style.transform = `translate(${dx}px,${dy}px)`;
    input.mx = dx / R; input.mz = -dy / R;
  });
  const joyEnd = (e) => { if (e.pointerId !== joyId) return; joyId = null; input.mx = input.mz = 0; knob.style.transform = ''; baseHome(); base.style.marginTop = ''; };
  joyZone.addEventListener('pointerup', joyEnd); joyZone.addEventListener('pointercancel', joyEnd);

  const lookers = new Map();
  const startLook = (el, onDown, onUp) => {
    el.addEventListener('pointerdown', (e) => { el.setPointerCapture(e.pointerId); lookers.set(e.pointerId, { x: e.clientX, y: e.clientY }); if (onDown) onDown(); e.preventDefault(); });
    el.addEventListener('pointermove', (e) => {
      const l = lookers.get(e.pointerId); if (!l || game.state !== 'play') return;
      look(e.clientX - l.x, e.clientY - l.y, .0062); l.x = e.clientX; l.y = e.clientY;
    });
    const end = (e) => { if (!lookers.has(e.pointerId)) return; lookers.delete(e.pointerId); if (onUp) onUp(); };
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  };
  startLook(lookZone);
  startLook($('tFire'), () => { input.fire = true; $('tFire').classList.add('act'); }, () => { input.fire = false; $('tFire').classList.remove('act'); });
  const tap = (id, fn) => $(id).addEventListener('pointerdown', (e) => { e.preventDefault(); e.stopPropagation(); if (game.state === 'play') fn(); });
  tap('tJump', () => (input.jump = true));
  tap('tReload', () => startReload(game.player));
  tap('tAim', () => (input.aim = !input.aim));
  tap('tNade', () => throwNade(game.player, playerDir()));
  tap('tSwap', () => switchWeapon(game.player));
  $('btnCar').addEventListener('pointerdown', (e) => { e.preventDefault(); if (game.state === 'play') carAction(); });
})();

/* =====================================================================
   MENUS / SHOP / SETTINGS
   ===================================================================== */
const screens = ['menu', 'shop', 'settings', 'hud', 'pause', 'end'];
function showScreen(name, keep) {
  for (const s of screens) if (!(keep && keep.includes(s))) $(s).classList.toggle('hidden', s !== name);
  if (name === 'menu' || name === 'shop') { game.state = name; resize(); }
}
function pause() { if (game.state !== 'play') return; game.state = 'paused'; input.fire = false; input.keys = {}; $('pause').classList.remove('hidden'); }
function resume() { $('pause').classList.add('hidden'); game.state = 'play'; lockPointer(); }

function refreshCoins() { document.querySelectorAll('.coinVal').forEach((e) => (e.textContent = S.coins)); }
function refreshMenu() {
  refreshCoins();
  const row = $('mapRow'); row.innerHTML = '';
  for (const id in MAPS) {
    const b = document.createElement('button'); b.textContent = MAPS[id].name; b.className = S.map === id ? 'on' : '';
    b.onclick = () => { S.map = id; save(); refreshMenu(); setMenuTheme(); };
    row.appendChild(b);
  }
  $('statsLine').textContent = `Матчей: ${S.stats.games} · Побед: ${S.stats.wins} · Убийств: ${S.stats.kills}`;
  rebuildMenuChicken();
}

/* ---- menu 3D scene ---- */
let menuChicken = null, menuGround = null, menuProps = null, previewLook = null, previewGun = null;
function setMenuTheme() {
  const th = MAPS[S.map];
  menuScene.background = new T.Color(th.sky); menuScene.fog = new T.Fog(th.sky, 18, 60);
  if (menuGround) menuScene.remove(menuGround);
  const g = new T.Group();
  P(G.cyl, th.ground, 40, .1, 40, 0, -.05, 0, g);
  P(G.box, 0xb07a3c, 1.3, 1.3, 1.3, -2.6, .65, -2.2, g, 0, .4); P(G.box, 0x9c6a30, 1.1, 1.1, 1.1, -2.4, 1.85, -2.3, g, 0, .1);
  for (let i = -3; i <= 3; i++) P(G.box, 0x9c6b3e, .2, 1.3, .2, i * 1.6 + .5, .65, -6, g);
  P(G.box, 0x9c6b3e, 11, .14, .1, .5, .9, -6, g); P(G.box, 0x9c6b3e, 11, .14, .1, .5, .4, -6, g);
  if (th.tree === 'round') { P(G.cylLo, 0x7a4f2a, .3, 2.5, .3, 3.6, 1.25, -7, g); P(G.sphLo, 0x4caf50, 1.8, 1.6, 1.8, 3.6, 3.3, -7, g); }
  else if (th.tree === 'pine') { P(G.cylLo, 0x6a4428, .3, 1.6, .3, 3.6, .8, -7, g); P(G.cone8, 0x2e7d4f, 1.8, 2.4, 1.8, 3.6, 2.6, -7, g); P(G.cone8, 0xffffff, 1.2, 1, 1.2, 3.6, 3.5, -7, g); }
  else { P(G.cylLo, 0x3f9b4a, .4, 3.2, .4, 3.6, 1.6, -7, g); P(G.cylLo, 0x3f9b4a, .22, 1.2, .22, 4.4, 2.2, -7, g); }
  P(G.circle, shadowMat, 1, 1, 1, 0, .01, 0, g);
  menuScene.add(g); menuGround = g;
}
function rebuildMenuChicken() {
  if (menuChicken) menuScene.remove(menuChicken.root);
  const look = previewLook || { col: S.eq.col, hat: S.eq.hat, gl: S.eq.gl };
  menuChicken = buildChicken(Object.assign({}, look, { armor: previewLook && previewLook.armor !== undefined ? previewLook.armor : S.armor }));
  menuChicken.gun.add(buildGun(previewGun || S.eq.prim));
  menuChicken.gun.rotation.x = .25;
  menuChicken.shadow.visible = false;
  menuScene.add(menuChicken.root);
}
let menuT = 0;
function updateMenu(dt) {
  menuT += dt;
  if (!menuChicken) return;
  const r = menuChicken.root;
  r.rotation.y = .55 + Math.sin(menuT * .6) * .45;
  menuChicken.body.position.y = Math.abs(Math.sin(menuT * 2.2)) * .05;
  menuChicken.head.rotation.y = Math.sin(menuT * 1.3) * .3;
  menuChicken.head.rotation.x = Math.sin(menuT * 2.7) * .08;
  menuChicken.wingL.rotation.z = Math.sin(menuT * 3) * .15;
  menuCam.position.set(0, 1.55, 5.6); menuCam.lookAt(0, .95, 0);
}

/* ---- icons (rendered once with a tiny offscreen renderer) ---- */
const ICONS = {};
function makeIcons() {
  let r;
  try { r = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); } catch (e) { return; }
  r.setPixelRatio(1); r.setSize(180, 110); r.setClearColor(0x000000, 0);
  const sc = new T.Scene(); sc.add(new T.HemisphereLight(0xffffff, 0x777777, 1)); const dl = new T.DirectionalLight(0xffffff, .55); dl.position.set(2, 4, 5); sc.add(dl);
  const cam = new T.PerspectiveCamera(30, 180 / 110, .05, 50);
  const box = new T.Box3(), c = new T.Vector3(), s = new T.Vector3();
  const shot = (obj, elev) => {
    sc.add(obj); obj.updateMatrixWorld(true); box.setFromObject(obj); box.getCenter(c); box.getSize(s);
    const d = Math.max(s.x / .86, s.y / .54, s.z / .7) * 1.15 + .2;
    cam.position.set(c.x, c.y + d * (elev || 0), c.z + d); cam.lookAt(c);
    r.render(sc, cam); const url = r.domElement.toDataURL(); sc.remove(obj); return url;
  };
  for (const id in WEAPONS) { const g = new T.Group(); const gun = buildGun(id); gun.rotation.y = Math.PI / 2; gun.rotation.z = .12; g.add(gun); ICONS['w:' + id] = shot(g, .05); }
  for (const id in HATS) { if (id === 'none') continue; const g = new T.Group(); P(G.sph, 0xf4f1ea, .36, .36, .36, 0, 0, 0, g); g.add(buildHat(id)); g.rotation.y = .5; ICONS['hat:' + id] = shot(g, .25); }
  for (const id in GLASSES) { if (id === 'none') continue; const g = new T.Group(); P(G.sph, 0xf4f1ea, .36, .36, .36, 0, 0, 0, g); g.add(buildGlasses(id)); g.rotation.y = .3; ICONS['gl:' + id] = shot(g, .1); }
  for (let i = 1; i < ARMOR.length; i++) { const ch = buildChicken({ col: 'white', hat: i === 3 ? 'helmet' : 'none', gl: 'none', armor: i }); ch.shadow.visible = false; ch.root.rotation.y = .5; ICONS['arm:' + i] = shot(ch.root, .1); }
  r.dispose(); if (r.forceContextLoss) r.forceContextLoss();
}

/* ---- shop ---- */
const TABS = { weap: 'Оружие', hat: 'Шапки', gl: 'Очки', col: 'Перья', arm: 'Броня' };
let shopTab = 'weap', shopSel = null;
function shopItems(tab) {
  const out = [];
  if (tab === 'weap') for (const id in WEAPONS) { const w = WEAPONS[id]; out.push({ key: id, id, name: w.name, price: w.price, owned: !!S.owned[id], eq: S.eq.prim === id || S.eq.sec === id, icon: ICONS['w:' + id], w }); }
  if (tab === 'hat') for (const id in HATS) out.push({ key: 'hat:' + id, id, name: HATS[id].name, price: HATS[id].price, owned: !!S.owned['hat:' + id], eq: S.eq.hat === id, icon: ICONS['hat:' + id] });
  if (tab === 'gl') for (const id in GLASSES) out.push({ key: 'gl:' + id, id, name: GLASSES[id].name, price: GLASSES[id].price, owned: !!S.owned['gl:' + id], eq: S.eq.gl === id, icon: ICONS['gl:' + id] });
  if (tab === 'col') for (const id in FEATHERS) out.push({ key: 'col:' + id, id, name: FEATHERS[id].name, price: FEATHERS[id].price, owned: !!S.owned['col:' + id], eq: S.eq.col === id, color: FEATHERS[id].c });
  if (tab === 'arm') ARMOR.forEach((a, i) => out.push({ key: 'arm:' + i, id: i, name: a.name, price: a.price, owned: S.armor >= i, eq: S.armor === i, icon: ICONS['arm:' + i], arm: a, locked: i > S.armor + 1 }));
  return out;
}
function renderShop() {
  refreshCoins();
  const tabs = $('shopTabs'); tabs.innerHTML = '';
  for (const t in TABS) { const b = document.createElement('button'); b.textContent = TABS[t]; b.className = t === shopTab ? 'on' : ''; b.onclick = () => { shopTab = t; shopSel = null; previewLook = null; previewGun = null; rebuildMenuChicken(); renderShop(); }; tabs.appendChild(b); }
  const grid = $('shopGrid'); grid.innerHTML = '';
  const items = shopItems(shopTab);
  if (!shopSel) shopSel = (items.find((i) => i.eq) || items[0]).key;
  for (const it of items) {
    const c = document.createElement('div'); c.className = 'card' + (it.key === shopSel ? ' sel' : '');
    const vis = it.icon ? `<img src="${it.icon}" alt="">` : it.color !== undefined ? `<div class="sw" style="background:#${it.color.toString(16).padStart(6, '0')}"></div>` : '<div class="sw" style="background:rgba(255,255,255,.1)"></div>';
    c.innerHTML = vis + `<div class="nm">${it.name}</div>` + (it.owned ? '' : `<div class="pr"><i class="coin"></i>${it.price}</div>`) +
      (it.eq ? '<span class="tag eq">НАДЕТО</span>' : it.owned ? '<span class="tag">ЕСТЬ</span>' : '');
    c.onclick = () => { shopSel = it.key; previewItem(it); renderShop(); };
    grid.appendChild(c);
  }
  const it = items.find((i) => i.key === shopSel);
  const d = $('shopDetail');
  let stats = '';
  if (it.w) {
    const w = it.w, bar = (l, v) => `<span>${l}</span><i><u style="width:${Math.round(clamp(v, .04, 1) * 100)}%"></u></i>`;
    stats = `<div class="statbars">${bar('Урон', (w.dmg * (w.pellets || 1)) / 130)}${bar('Скорострельность', .045 / w.rate)}${bar('Магазин', w.mag / 60)}${bar('Точность', 1 - w.spread * 10)}</div>`;
  } else if (it.arm) stats = `<small>+${it.arm.val} брони: поглощает 60% урона</small>`;
  else stats = '<small>Только для красоты — выделяйся на поле боя!</small>';
  const slotNote = it.w ? `<small>${it.w.slot === 1 ? 'Основное оружие' : 'Пистолет (второй слот)'}</small>` : '';
  let btn;
  if (it.eq) btn = '<button class="btn gray" disabled>ВЫБРАНО</button>';
  else if (it.owned) btn = `<button class="btn blue" id="shopAct">${it.arm ? 'ЕСТЬ' : 'ВЫБРАТЬ'}</button>`;
  else if (it.locked) btn = '<button class="btn gray" disabled>СНАЧАЛА ПРЕДЫДУЩУЮ</button>';
  else btn = `<button class="btn yellow" id="shopAct" ${S.coins < it.price ? 'disabled' : ''}><i class="coin"></i>${it.price}</button>`;
  d.innerHTML = `<div class="info"><b>${it.name}</b>${slotNote}${stats}</div>${btn}`;
  const act = $('shopAct');
  if (act) act.onclick = () => shopAction(it);
}
function previewItem(it) {
  previewLook = { col: S.eq.col, hat: S.eq.hat, gl: S.eq.gl }; previewGun = null;
  if (shopTab === 'hat') previewLook.hat = it.id; else if (shopTab === 'gl') previewLook.gl = it.id; else if (shopTab === 'col') previewLook.col = it.id;
  else if (shopTab === 'arm') previewLook.armor = it.id; else if (shopTab === 'weap') previewGun = it.id;
  rebuildMenuChicken();
}
function shopAction(it) {
  if (!it.owned) {
    if (S.coins < it.price || it.locked) return;
    S.coins -= it.price;
    if (shopTab === 'arm') S.armor = it.id; else S.owned[it.key] = 1;
    sfx('buy');
  }
  if (shopTab === 'weap') { if (it.w.slot === 1) S.eq.prim = it.id; else S.eq.sec = it.id; }
  else if (shopTab === 'hat') S.eq.hat = it.id; else if (shopTab === 'gl') S.eq.gl = it.id; else if (shopTab === 'col') S.eq.col = it.id;
  save(); previewLook = null; previewGun = shopTab === 'weap' ? it.id : null; rebuildMenuChicken(); renderShop();
}

/* ---- settings ---- */
let settingsFrom = 'menu';
function renderSettings() {
  document.querySelectorAll('#qualSeg button').forEach((b) => b.classList.toggle('on', b.dataset.q === S.quality));
  $('sens').value = S.sens; $('sensVal').textContent = (+S.sens).toFixed(2);
  $('tFps').classList.toggle('on', S.fps); $('tSound').classList.toggle('on', S.sound);
  $('fps').style.display = S.fps ? '' : 'none';
}
document.querySelectorAll('#qualSeg button').forEach((b) => (b.onclick = () => { S.quality = b.dataset.q; save(); resize(); renderSettings(); }));
$('sens').oninput = (e) => { S.sens = +e.target.value; save(); renderSettings(); };
$('tFps').onclick = () => { S.fps = !S.fps; save(); renderSettings(); };
$('tSound').onclick = () => { S.sound = !S.sound; save(); renderSettings(); };
$('btnReset').onclick = () => { if (confirm('Сбросить монеты и покупки?')) { S = clone(DEFAULT); save(); renderSettings(); refreshMenu(); } };
$('setBack').onclick = () => { $('settings').classList.add('hidden'); if (settingsFrom === 'pause') $('pause').classList.remove('hidden'); };

$('btnPlay').onclick = () => { initAudio(); startMatch(); };
$('btnShop').onclick = () => { initAudio(); shopSel = null; previewLook = null; previewGun = null; showScreen('shop'); renderShop(); };
$('shopBack').onclick = () => { previewLook = null; previewGun = null; showScreen('menu'); refreshMenu(); };
$('btnSettings').onclick = () => { settingsFrom = 'menu'; renderSettings(); $('settings').classList.remove('hidden'); };
$('btnPause').addEventListener('pointerdown', (e) => { e.preventDefault(); pause(); });
$('btnResume').onclick = resume;
$('btnPauseSettings').onclick = () => { settingsFrom = 'pause'; renderSettings(); $('pause').classList.add('hidden'); $('settings').classList.remove('hidden'); };
$('btnQuit').onclick = quitToMenu;
$('btnAgain').onclick = () => startMatch();
$('btnToMenu').onclick = quitToMenu;

function checkRotate() {
  const show = isTouch && (game.state === 'play' || game.state === 'paused') && window.innerHeight > window.innerWidth;
  $('rotate').classList.toggle('hidden', !show);
}

/* =====================================================================
   MAIN LOOP — uncapped: runs at the display refresh rate (60/90/120/144 Hz)
   ===================================================================== */
let last = performance.now(), fpsFrames = 0, fpsTime = 0;
function frame(now) {
  requestAnimationFrame(frame);
  let dt = (now - last) / 1000; last = now;
  if (dt > .05) dt = .05; if (dt <= 0) dt = .001;
  fpsFrames++; fpsTime += dt;
  if (fpsTime >= .5) { if (S.fps) $('fps').textContent = Math.round(fpsFrames / fpsTime) + ' FPS'; fpsFrames = 0; fpsTime = 0; }
  if (game.state === 'play') { update(dt); renderer.render(scene, camera); }
  else if (game.state === 'paused' || game.state === 'end') { renderer.render(scene, camera); }
  else { updateMenu(dt); renderer.render(menuScene, menuCam); }
}

window.addEventListener('resize', resize);
window.addEventListener('orientationchange', () => setTimeout(resize, 200));
document.addEventListener('visibilitychange', () => { if (document.hidden && game.state === 'play') pause(); });

// boot
makeIcons();
setMenuTheme();
renderSettings();
showScreen('menu');
refreshMenu();
resize();
$('loading').remove();
requestAnimationFrame(frame);

// debug/test hook
window.__game = { game, S, WEAPONS, startMatch, endMatch, input };
})();
