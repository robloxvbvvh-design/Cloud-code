import * as THREE from 'three';

const SKY = 0x0a1030;

export class World {
  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(SKY);
    this.scene.fog = new THREE.Fog(SKY, 160, 720);

    // Свет
    const hemi = new THREE.HemisphereLight(0x7a8cff, 0x1a2a14, 1.5);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xc4ceff, 1.6);
    sun.position.set(60, 120, 40);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    const sc = sun.shadow.camera;
    sc.left = -70; sc.right = 70; sc.top = 70; sc.bottom = -70; sc.near = 10; sc.far = 320;
    sun.shadow.bias = -0.0004;
    this.scene.add(sun);
    this.scene.add(sun.target);
    this.sun = sun;
    this.sunOffset = new THREE.Vector3(60, 120, 40);

    // Земля (трава)
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(2400, 2400),
      new THREE.MeshLambertMaterial({ color: 0x14301a })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    this.scene.add(ground);

    // Звёзды
    const starGeo = new THREE.BufferGeometry();
    const sp = [];
    for (let i = 0; i < 400; i++) {
      const a = Math.random() * Math.PI * 2;
      const e = 0.12 + Math.random() * 1.3;
      const r = 1500;
      sp.push(Math.cos(a) * Math.cos(e) * r, Math.sin(e) * r, Math.sin(a) * Math.cos(e) * r);
    }
    starGeo.setAttribute('position', new THREE.Float32BufferAttribute(sp, 3));
    const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 3, sizeAttenuation: false, fog: false }));
    this.scene.add(stars);
  }

  // Декор: деревья и фонари через InstancedMesh. Деревья не ближе minDist от оси трассы.
  addDecor(track, { trees = 300, minDist = 16 } = {}) {
    const dummy = new THREE.Object3D();
    const samples = track.samples;
    const minD2 = minDist * minDist;

    const trunkGeo = new THREE.CylinderGeometry(0.4, 0.55, 2.4, 6);
    trunkGeo.translate(0, 1.2, 0);
    const leafGeo = new THREE.ConeGeometry(2.4, 6.5, 7);
    leafGeo.translate(0, 2.4 + 3.25, 0);
    const trunks = new THREE.InstancedMesh(trunkGeo, new THREE.MeshLambertMaterial({ color: 0x4a2f1a }), trees);
    const leaves = new THREE.InstancedMesh(leafGeo, new THREE.MeshLambertMaterial({ color: 0x1d6b3a }), trees);
    trunks.castShadow = leaves.castShadow = true;

    let count = 0, guard = 0;
    while (count < trees && guard++ < trees * 40) {
      const x = (Math.random() * 2 - 1) * 380;
      const z = (Math.random() * 2 - 1) * 300 + 20;
      let ok = true;
      for (let i = 0; i < samples.length; i += 2) {
        const dx = x - samples[i].pos.x, dz = z - samples[i].pos.z;
        if (dx * dx + dz * dz < minD2) { ok = false; break; }
      }
      if (!ok) continue;
      const s = 0.8 + Math.random() * 0.9;
      dummy.position.set(x, 0, z);
      dummy.rotation.set(0, Math.random() * 6.28, 0);
      dummy.scale.set(s, s * (0.9 + Math.random() * 0.5), s);
      dummy.updateMatrix();
      trunks.setMatrixAt(count, dummy.matrix);
      leaves.setMatrixAt(count, dummy.matrix);
      count++;
    }
    trunks.count = leaves.count = count;
    this.scene.add(trunks, leaves);
    this.treeCount = count;

    // Неоновые фонари каждые ~40 сэмплов, по сторонам поочерёдно
    const lampIdx = [];
    for (let i = 20; i < samples.length; i += 40) lampIdx.push(i);
    const poleGeo = new THREE.CylinderGeometry(0.12, 0.16, 6, 6);
    poleGeo.translate(0, 3, 0);
    const headGeo = new THREE.BoxGeometry(0.9, 0.35, 0.9);
    headGeo.translate(0, 6.1, 0);
    const poles = new THREE.InstancedMesh(poleGeo, new THREE.MeshLambertMaterial({ color: 0x2a2f48 }), lampIdx.length);
    const heads = new THREE.InstancedMesh(headGeo, new THREE.MeshBasicMaterial({ color: 0xffffff }), lampIdx.length);
    const c1 = new THREE.Color(0x19e6ff), c2 = new THREE.Color(0xff2e97);
    lampIdx.forEach((idx, k) => {
      const s = samples[idx];
      const side = k % 2 ? 1 : -1;
      const off = track.wallOffset + 1.8;
      dummy.position.set(s.pos.x + s.normal.x * off * side, 0, s.pos.z + s.normal.z * off * side);
      dummy.rotation.set(0, 0, 0);
      dummy.scale.set(1, 1, 1);
      dummy.updateMatrix();
      poles.setMatrixAt(k, dummy.matrix);
      heads.setMatrixAt(k, dummy.matrix);
      heads.setColorAt(k, k % 2 ? c1 : c2);
    });
    poles.castShadow = true;
    this.scene.add(poles, heads);
  }

  // Подтянуть тень к игроку.
  update(targetPos) {
    this.sun.target.position.copy(targetPos);
    this.sun.position.copy(targetPos).add(this.sunOffset);
  }
}
