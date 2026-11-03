# Процедурные 3D-модели в Three.js

## Принципы «крутой» модели

1. **Силуэт важнее деталей.** Сначала крупные формы (2–5 примитивов), потом детали.
2. **Пропорции и иерархия.** Модель — `THREE.Group`; части — дети с локальными позициями.
   Подвижные части (колёса, руки, башня) — отдельные группы с точкой вращения в шарнире.
3. **Скругления.** `RoundedBoxGeometry` (`three/addons/geometries/RoundedBoxGeometry.js`),
   `CapsuleGeometry`, `LatheGeometry` (вазы, бутылки, колонны), `ExtrudeGeometry` с `bevelEnabled`
   (логотипы, лезвия, крылья) — резкие кубы выглядят дёшево.
4. **Материалы.** `MeshStandardMaterial` / `MeshPhysicalMaterial`:
   - металл: `metalness: 1, roughness: 0.25–0.4`
   - пластик: `metalness: 0, roughness: 0.5`
   - стекло: `MeshPhysicalMaterial({ transmission: 1, roughness: 0.05, thickness: 0.5 })`
   - автокраска: `clearcoat: 1, clearcoatRoughness: 0.1`
   - светящиеся детали: `emissive` + `emissiveIntensity: 2`
   Для отражений обязательно окружение: `scene.environment = pmrem.fromScene(new RoomEnvironment()).texture`.
5. **Палитра.** 3–5 цветов, один акцентный. Не чистые `0xff0000` — используй насыщенные, но мягкие.
6. **Детали вторичного уровня:** фары, швы, болты, окна, кант (тонкий тор/цилиндр) — дают «дорогой» вид.
7. **Flat shading** (`flatShading: true`) — для стиля low-poly; смешивать стили нельзя.

## Процедурные текстуры (без файлов)

```js
function canvasTexture(size, draw) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8; return t;
}
// шахматка / плитка пола
const grid = canvasTexture(512, (g, s) => {
  g.fillStyle = '#3b4252'; g.fillRect(0, 0, s, s);
  g.strokeStyle = '#4c566a'; g.lineWidth = 4;
  for (let i = 0; i <= 8; i++) { const p = i * s / 8;
    g.beginPath(); g.moveTo(p, 0); g.lineTo(p, s); g.moveTo(0, p); g.lineTo(s, p); g.stroke(); }
});
grid.repeat.set(20, 20);
```

Шум для рельефа: сумма синусов или простой value-noise; смещай вершины `PlaneGeometry`
(`geometry.attributes.position`), затем `computeVertexNormals()`. Для физики — `CANNON.Heightfield`
из тех же высот.

## Примеры фабрик

```js
// Машина (стилизованная)
function createCar(color = 0xe63946) {
  const g = new THREE.Group();
  const paint = new THREE.MeshPhysicalMaterial({ color, metalness: 0.6, roughness: 0.3, clearcoat: 1 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x1d1d1d, roughness: 0.8 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x88aacc, roughness: 0.05, metalness: 0.2, transmission: 0.6 });
  const body = new THREE.Mesh(new RoundedBoxGeometry(2, 0.5, 4, 4, 0.15), paint); body.position.y = 0.55;
  const cabin = new THREE.Mesh(new RoundedBoxGeometry(1.7, 0.5, 2, 4, 0.2), glass); cabin.position.set(0, 1.0, -0.2);
  g.add(body, cabin);
  const wheelGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.3, 24).rotateZ(Math.PI / 2);
  g.userData.wheels = [[-1, 1.3], [1, 1.3], [-1, -1.3], [1, -1.3]].map(([x, z]) => {
    const w = new THREE.Mesh(wheelGeo, dark); w.position.set(x, 0.4, z); g.add(w); return w; });
  const lightMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff2cc, emissiveIntensity: 2 });
  for (const x of [-0.6, 0.6]) { const l = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), lightMat); l.position.set(x, 0.6, 2.0); g.add(l); }
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}

// Дерево low-poly
function createTree(h = 3) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.25, h * 0.4, 6),
    new THREE.MeshStandardMaterial({ color: 0x6b4226, flatShading: true }));
  trunk.position.y = h * 0.2; g.add(trunk);
  const leaf = new THREE.MeshStandardMaterial({ color: 0x3a7d44, flatShading: true });
  for (let i = 0; i < 3; i++) {
    const c = new THREE.Mesh(new THREE.ConeGeometry(h * 0.35 - i * 0.2, h * 0.4, 7), leaf);
    c.position.y = h * 0.45 + i * h * 0.2; g.add(c);
  }
  g.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } });
  return g;
}

// Персонаж (робот) с подвижными конечностями
function createRobot(color = 0x4cc9f0) {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color, metalness: 0.5, roughness: 0.35 });
  const j = new THREE.MeshStandardMaterial({ color: 0x222831, metalness: 0.8, roughness: 0.3 });
  const torso = new THREE.Mesh(new RoundedBoxGeometry(0.9, 1.0, 0.5, 4, 0.12), m); torso.position.y = 1.4;
  const head = new THREE.Mesh(new RoundedBoxGeometry(0.6, 0.5, 0.5, 4, 0.12), m); head.position.y = 2.2;
  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.12, 0.05),
    new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0xff4d6d, emissiveIntensity: 3 }));
  visor.position.set(0, 2.22, 0.26);
  g.add(torso, head, visor);
  const limb = (x, y, len) => { const pivot = new THREE.Group(); pivot.position.set(x, y, 0);
    const seg = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, len, 4, 8), j); seg.position.y = -len / 2 - 0.1;
    pivot.add(seg); g.add(pivot); return pivot; };
  g.userData.limbs = { armL: limb(-0.6, 1.8, 0.7), armR: limb(0.6, 1.8, 0.7), legL: limb(-0.22, 0.9, 0.7), legR: limb(0.22, 0.9, 0.7) };
  g.traverse(o => { if (o.isMesh) o.castShadow = true; });
  return g;
}
// Анимация ходьбы: const s = Math.sin(t*8)*0.6*speed; limbs.armL.rotation.x = s; limbs.armR.rotation.x = -s; limbs.legL.rotation.x = -s; limbs.legR.rotation.x = s;
```

## Массовые объекты

```js
const mesh = new THREE.InstancedMesh(geo, mat, count);
const d = new THREE.Object3D();
for (let i = 0; i < count; i++) { d.position.set(...); d.rotation.y = Math.random()*6.28; d.scale.setScalar(0.8+Math.random()*0.5);
  d.updateMatrix(); mesh.setMatrixAt(i, d.matrix); }
mesh.instanceMatrix.needsUpdate = true;
```

## Экспорт в GLB

```js
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
new GLTFExporter().parse(model, glb => {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([glb], { type: 'model/gltf-binary' }));
  a.download = 'model.glb'; a.click();
}, console.error, { binary: true });
```
