// Звук мотора через WebAudio. Любые ошибки проглатываются.
export class EngineAudio {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  start() {
    if (this.ctx) { this.ctx.resume?.(); return; }
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      const ctx = new Ctx();
      const o1 = ctx.createOscillator(); o1.type = 'sawtooth';
      const o2 = ctx.createOscillator(); o2.type = 'square';
      const filter = ctx.createBiquadFilter(); filter.type = 'lowpass'; filter.frequency.value = 600;
      const gain = ctx.createGain(); gain.gain.value = 0;
      o1.connect(filter); o2.connect(filter); filter.connect(gain); gain.connect(ctx.destination);
      o1.start(); o2.start();
      this.ctx = ctx; this.o1 = o1; this.o2 = o2; this.filter = filter; this.gain = gain;
    } catch (e) {
      this.ctx = null;
    }
  }

  update(speedRatio, throttle, active = true) {
    if (!this.ctx) return;
    try {
      const f = 60 + speedRatio * 180;
      const t = this.ctx.currentTime;
      this.o1.frequency.setTargetAtTime(f, t, 0.05);
      this.o2.frequency.setTargetAtTime(f * 0.5, t, 0.05);
      this.filter.frequency.setTargetAtTime(400 + speedRatio * 900 + throttle * 300, t, 0.1);
      const vol = this.muted || !active ? 0 : 0.05 + 0.04 * throttle;
      this.gain.gain.setTargetAtTime(vol, t, 0.08);
    } catch (e) { /* ignore */ }
  }

  toggleMute() { this.muted = !this.muted; return this.muted; }
}
