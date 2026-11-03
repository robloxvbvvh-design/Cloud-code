// Клавиатура. steer > 0 = направо.
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export class Input {
  constructor() {
    this.down = new Set();
    this.steer = 0;
    this.handlers = new Map(); // code -> [fn]
    const block = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space']);
    window.addEventListener('keydown', (e) => {
      if (block.has(e.code)) e.preventDefault();
      if (e.repeat) return;
      this.down.add(e.code);
      const hs = this.handlers.get(e.code);
      if (hs) hs.forEach((fn) => fn(e));
    });
    window.addEventListener('keyup', (e) => this.down.delete(e.code));
    window.addEventListener('blur', () => this.down.clear());
  }

  // Однократное нажатие (можно несколько кодов)
  onPress(codes, fn) {
    for (const c of [].concat(codes)) {
      if (!this.handlers.has(c)) this.handlers.set(c, []);
      this.handlers.get(c).push(fn);
    }
  }

  isDown(...codes) { return codes.some((c) => this.down.has(c)); }

  getControls(dt) {
    const left = this.isDown('KeyA', 'ArrowLeft') ? 1 : 0;
    const right = this.isDown('KeyD', 'ArrowRight') ? 1 : 0;
    const target = right - left;
    const maxStep = 6 * dt;
    this.steer += clamp(target - this.steer, -maxStep, maxStep);
    return {
      throttle: this.isDown('KeyW', 'ArrowUp') ? 1 : 0,
      brake: this.isDown('KeyS', 'ArrowDown') ? 1 : 0,
      steer: this.steer,
      handbrake: this.isDown('Space'),
    };
  }

  reset() { this.down.clear(); this.steer = 0; }
}
