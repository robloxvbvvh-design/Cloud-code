import * as THREE from 'three';
import { World } from './world.js';
import { Track } from './track.js';

const canvas = document.getElementById('game');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const world = new World();
const track = new Track();
world.scene.add(track.group);
world.addDecor(track);

const camera = new THREE.PerspectiveCamera(65, 1, 0.3, 2000);
const g = track.getStartGrid(0);
camera.position.set(g.position.x - 30, 14, g.position.z - 40);
camera.lookAt(g.position.x + 40, 0, g.position.z);

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

function loop() {
  renderer.render(world.scene, camera);
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
window.__game = { track, world, scene: world.scene, camera };
