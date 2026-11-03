import * as THREE from 'three';
import { CONFIG } from './config.js';

const K = CONFIG.camera;

export class ChaseCamera {
  constructor() {
    this.camera = new THREE.PerspectiveCamera(K.fov, 1, 0.3, 2000);
    this.hood = false;
    this._pos = new THREE.Vector3();
    this._look = new THREE.Vector3();
    this._fov = K.fov;
    this.first = true;
  }

  resize(w, h) {
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  toggle() { this.hood = !this.hood; this.first = true; }
  snap() { this.first = true; }

  update(car, dt) {
    const h = car.heading;
    const fx = Math.sin(h), fz = Math.cos(h);
    const cam = this.camera;
    const speedRatio = Math.min(1, car.speedKmh / (CONFIG.car.maxSpeed * 3.6));
    const targetFov = K.fov + K.fovBoost * speedRatio;
    this._fov += (targetFov - this._fov) * (1 - Math.exp(-4 * dt));
    if (Math.abs(cam.fov - this._fov) > 0.01) { cam.fov = this._fov; cam.updateProjectionMatrix(); }

    if (this.hood) {
      cam.position.set(car.position.x + fx * 0.6, 1.25, car.position.z + fz * 0.6);
      cam.lookAt(car.position.x + fx * 20, 1.1, car.position.z + fz * 20);
      return;
    }
    const want = new THREE.Vector3(car.position.x - fx * K.distance, K.height, car.position.z - fz * K.distance);
    if (this.first) { this._pos.copy(want); this.first = false; }
    else this._pos.lerp(want, 1 - Math.exp(-K.follow * dt));
    cam.position.copy(this._pos);
    this._look.set(car.position.x + fx * 5, 1, car.position.z + fz * 5);
    cam.lookAt(this._look);
  }
}
