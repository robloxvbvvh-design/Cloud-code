// Все числовые константы игры в одном месте.
export const CONFIG = {
  laps: 3,

  track: {
    samples: 1000,
    halfWidth: 7,
    wallOffset: 11,
    wallHeight: 1.2,
    searchWindow: 40,
    // Контрольные точки [x, z]: длинная прямая со стартом, быстрая дуга,
    // S-связка, шпилька.
    points: [
      [-60, -100], // 0: старт (прямая вдоль +X)
      [40, -100],
      [120, -100],
      [190, -85],
      [230, -30], // быстрая дуга
      [205, 30],
      [140, 55],
      [80, 100], // S-повороты
      [20, 75],
      [-35, 115],
      [-100, 135],
      [-175, 140],
      [-235, 105], // шпилька
      [-240, 45],
      [-205, 0],
      [-190, -55],
      [-150, -95],
    ],
  },

  car: {
    accel: 22,
    brakeForce: 40,
    maxReverse: 10,
    drag: 0.25,
    rolling: 0.8,
    maxSpeed: 58,
    maxSteer: 2.2,
    grip: 9,
    handbrakeGrip: 1.8,
    offroadFactor: 0.45,
    offroadDrag: 1.5,
    radius: 1.6,
    wallRestitutionSpeed: 0.6,
  },

  ai: {
    skillMin: 0.85,
    skillMax: 1.0,
    laneMax: 2,
    lookaheadMin: 12,
    lookaheadMax: 18,
    stuckSpeed: 2,
    stuckTime: 2,
    rubberFar: 0.15, // доля круга
    rubberSlow: 0.95,
    rubberFast: 1.05,
  },

  race: {
    checkpoints: [250, 500, 750],
    checkpointWindow: 30,
    startGridSlotPlayer: 2,
  },

  camera: {
    fov: 65,
    fovBoost: 10,
    distance: 9,
    height: 4,
    follow: 6,
  },

  colors: {
    player: 0xff3355,
    bots: [0x22ddff, 0xffcc22, 0xaa66ff],
  },
};
