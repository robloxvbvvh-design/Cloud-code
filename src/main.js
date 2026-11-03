import * as THREE from 'three';
import { World } from './world.js';
import { Track } from './track.js';
import { Car } from './car.js';
import { Input } from './input.js';
import { ChaseCamera } from './camera.js';
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
const player = new Car({ color: CONFIG.colors.player, name: 'Вы', isPlayer: true, track });
world.scene.add(player.mesh);
const g = track.getStartGrid(2);
player.reset(g.position, g.heading);
chase.snap();
input.onPress('KeyC', () => chase.toggle());
input.onPress('KeyR', () => player.resetToTrack());

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  chase.resize(w, h);
}
window.addEventListener('resize', resize);
resize();

let last = performance.now();
function loop(now) {
  const dt = Math.min((now - last) / 1000, 0.05);
  last = now;
  player.update(dt, input.getControls(dt));
  chase.update(player, dt);
  world.update(player.position);
  renderer.render(world.scene, chase.camera);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
window.__game = { track, world, player, cars: [player] };
document.getElementById('menu').style.display = 'none';
