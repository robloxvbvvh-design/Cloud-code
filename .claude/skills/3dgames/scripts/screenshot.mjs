// Использование: node screenshot.mjs <path/to/index.html> [out.png]
// Открывает страницу в headless Chromium, кликает для старта, ждёт 2 с, сохраняет скриншот, печатает ошибки консоли.
import { createRequire } from 'module';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const file = process.argv[2];
const out = process.argv[3] || 'screenshot.png';
if (!file) { console.error('usage: node screenshot.mjs <index.html> [out.png]'); process.exit(1); }

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(String(e)));
await page.goto('file://' + path.resolve(file));
await page.waitForTimeout(1500);
await page.mouse.click(640, 360);
await page.keyboard.down('KeyW');
await page.waitForTimeout(1200);
await page.keyboard.up('KeyW');
await page.screenshot({ path: out });
await browser.close();
console.log('screenshot:', out);
console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'no console errors');
process.exit(errors.length ? 2 : 0);
