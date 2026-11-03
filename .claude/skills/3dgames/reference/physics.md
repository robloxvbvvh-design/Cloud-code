# Физика на cannon-es

```js
import * as CANNON from 'cannon-es';
const world = new CANNON.World({ gravity: new CANNON.Vec3(0, -9.82, 0) });
world.broadphase = new CANNON.SAPBroadphase(world);
world.allowSleep = true;
world.defaultContactMaterial.friction = 0.3;
```

## Тела

| Тип | Как | Для чего |
|---|---|---|
| Динамическое | `mass > 0` | ящики, шары, игрок |
| Статическое | `mass: 0` / `type: CANNON.Body.STATIC` | пол, стены, платформы |
| Кинематическое | `type: CANNON.Body.KINEMATIC`, двигать через `velocity` | движущиеся платформы, лифты |
| Триггер | `isTrigger: true` (или `collisionResponse = false`) | монеты, чекпоинты, зоны смерти |

Формы: `Box(halfExtents)`, `Sphere(r)`, `Cylinder(rTop, rBot, h, seg)` (ось Y, как в three),
`Plane` (поверни `quaternion.setFromEuler(-Math.PI/2,0,0)`), `Heightfield`, `Trimesh` (только статикой),
составные: `body.addShape(shape, offset, orientation)`.

**Важно:** `Box` принимает ПОЛОВИНЫ размеров: меш `BoxGeometry(2,1,4)` ↔ `new CANNON.Box(new CANNON.Vec3(1,0.5,2))`.

## Синхронизация

```js
const objects = []; // { mesh, body }
function syncAll() { for (const o of objects) { o.mesh.position.copy(o.body.position); o.mesh.quaternion.copy(o.body.quaternion); } }
// цикл:
const dt = Math.min(clock.getDelta(), 0.1);
world.fixedStep(1 / 60, dt); // или world.step(1/60, dt, 3)
syncAll();
```

## Материалы контакта

```js
const ground = new CANNON.Material('ground'), ball = new CANNON.Material('ball'), ice = new CANNON.Material('ice');
world.addContactMaterial(new CANNON.ContactMaterial(ground, ball, { friction: 0.4, restitution: 0.7 }));
world.addContactMaterial(new CANNON.ContactMaterial(ground, ice, { friction: 0.02, restitution: 0 }));
```

## Игрок-персонаж

```js
const player = new CANNON.Body({ mass: 70, shape: new CANNON.Sphere(0.5), fixedRotation: true, linearDamping: 0.9, material: playerMat });
// на земле? луч вниз
function onGround() {
  const from = player.position, to = new CANNON.Vec3(from.x, from.y - 0.6, from.z);
  const r = new CANNON.RaycastResult(); world.raycastClosest(from, to, { skipBackfaces: true, collisionFilterMask: GROUP_WORLD }, r);
  return r.hasHit;
}
// движение — задаём горизонтальную скорость относительно камеры, вертикальную не трогаем
player.velocity.x = dir.x * speed; player.velocity.z = dir.z * speed;
if (jumpPressed && onGround()) player.velocity.y = 6;
```

## События

```js
body.addEventListener('collide', e => {
  const impact = e.contact.getImpactVelocityAlongNormal();
  if (Math.abs(impact) > 3) playHit(Math.min(Math.abs(impact) / 10, 1));
});
world.addEventListener('beginContact', e => { /* e.bodyA, e.bodyB — триггеры */ });
```

Удалять тела **не внутри** обработчика столкновения — копи в очередь и удаляй после `world.step`.

## Группы столкновений

```js
const GROUP_WORLD = 1, GROUP_PLAYER = 2, GROUP_PICKUP = 4;
body.collisionFilterGroup = GROUP_PICKUP; body.collisionFilterMask = GROUP_PLAYER;
```

## Импульсы и силы

- Удар/взрыв: `body.applyImpulse(dirTimesStrength, body.position)` (точка в мировых координатах).
- Постоянная тяга: `body.applyForce(force)` каждый кадр.
- Взрыв радиусом: для всех тел в радиусе `impulse = dir.normalize() * k * (1 - dist/R)`.
- Пробудить: `body.wakeUp()`.

## Машина (RaycastVehicle)

```js
const chassis = new CANNON.Body({ mass: 150, shape: new CANNON.Box(new CANNON.Vec3(1, 0.3, 2)) });
chassis.position.set(0, 2, 0);
const vehicle = new CANNON.RaycastVehicle({ chassisBody: chassis, indexRightAxis: 0, indexUpAxis: 1, indexForwardAxis: 2 });
const wo = { radius: 0.4, directionLocal: new CANNON.Vec3(0, -1, 0), suspensionStiffness: 30, suspensionRestLength: 0.3,
  frictionSlip: 1.5, dampingRelaxation: 2.3, dampingCompression: 4.4, maxSuspensionForce: 1e5, rollInfluence: 0.01,
  axleLocal: new CANNON.Vec3(-1, 0, 0), maxSuspensionTravel: 0.3, customSlidingRotationalSpeed: -30, useCustomSlidingRotationalSpeed: true };
for (const [x, z] of [[-1, 1.3], [1, 1.3], [-1, -1.3], [1, -1.3]]) { wo.chassisConnectionPointLocal = new CANNON.Vec3(x, 0, z); vehicle.addWheel(wo); }
vehicle.addToWorld(world);
// управление: передние колёса 0,1 — руль; задние 2,3 — привод
vehicle.setSteeringValue(steer * 0.5, 0); vehicle.setSteeringValue(steer * 0.5, 1);
vehicle.applyEngineForce(-throttle * 800, 2); vehicle.applyEngineForce(-throttle * 800, 3);
for (let i = 0; i < 4; i++) vehicle.setBrake(brake ? 20 : 0, i);
// синхронизация колёс: vehicle.updateWheelTransform(i); wheelMesh.position/quaternion ← vehicle.wheelInfos[i].worldTransform
```

## Сочленения

- `PointToPointConstraint` — маятник, цепь, верёвочный мост (цепочка маленьких тел).
- `HingeConstraint` — дверь, колесо, мельница (`enableMotor()`, `setMotorSpeed()`).
- `DistanceConstraint` — пружинка-«резинка».
- `Spring` (`applyForce` в `world.addEventListener('postStep')`) — мягкие пружины, рэгдолл-подвески.

## Отладка

Временно рисуй каркасы тел: для каждого `body.shapes` создавай `wireframe`-меш соответствующей формы.
**Проверенные грабли:**
- С `SAPBroadphase` лучи (`raycastClosest`, подвеска `RaycastVehicle`) **не попадают в `CANNON.Plane`** — машина ложится брюхом на землю. Землю делай большим тонким `Box` (`Vec3(600,1,600)` на `y=-1`).
- В `RaycastVehicle` при `indexForwardAxis: 2` **отрицательная** `applyEngineForce` везёт вперёд (+Z). Проверь в тесте, что машина едет туда, куда смотрит.
- Лента дороги из `BufferGeometry` легко оказывается гранями вниз — ставь `side: THREE.DoubleSide` или проверь порядок индексов.
- В headless (SwiftShader) кадров мало, а `dt` ограничен — таймеры и обратный отсчёт идут медленно. В тестах жди состояние (`waitForFunction`), а не фиксированные секунды.

Типовые баги: перепутаны полуразмеры Box; Plane не повёрнут; тело проваливается — слишком большой `dt`
или маленькое тело и высокая скорость (увеличь количество подшагов или толщину стен).
