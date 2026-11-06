// Встроенный движок Коли: сам рендерит видео (ffmpeg) — без ключей, моделей и видеокарты.
// Это процедурная кинематографичная сцена по описанию (цвет, свет, погода, камера, зерно, чёрные полосы, звук),
// а не фотореалистичная нейросетевая съёмка людей. Фото персонажа вставляется в кадр как есть.
const { spawn } = require('child_process');
const fs = require('fs');

const SIZES = { '720p': [1280, 720], '1080p': [1920, 1080], '1440p': [2560, 1440], '4K': [3840, 2160] };
// c0..c2 — палитра, fx — погода, snd — тип звука, hz — аккорд
const THEMES = [
  { k: /дожд|ливн|rain|storm|гроз/i, c: ['0b1d2e', '1c4a63', '07090f'], fx: 'rain', snd: 'rain' },
  { k: /снег|зим|мороз|snow|winter/i, c: ['9fb6cc', '3b5873', '0e1a2a'], fx: 'snow', snd: 'wind' },
  { k: /мор[еяю]|океан|волн|пляж|sea|ocean|beach|wave/i, c: ['0a3d5c', '2a8fa8', '061726'], fx: 'none', snd: 'sea' },
  { k: /огон|огн|костёр|костер|пожар|fire|flame/i, c: ['2b0a02', 'e2561a', '120400'], fx: 'embers', snd: 'fire' },
  { k: /космос|звёзд|звезд|планет|space|galaxy|star/i, c: ['03030f', '2b1b5e', '000000'], fx: 'stars', snd: 'space' },
  { k: /неон|киберпанк|город|ночн|токио|улиц|city|neon|cyber|night/i, c: ['12031f', 'e0258f', '03121f'], fx: 'rain', snd: 'city' },
  { k: /закат|рассвет|солнц|sunset|sunrise|sun/i, c: ['ff7b2e', '7a1f5c', '1b0a2a'], fx: 'none', snd: 'wind' },
  { k: /лес|дерев|forest|jungle|tree/i, c: ['0b2a14', '3f7a3a', '020a05'], fx: 'none', snd: 'forest' },
  { k: /пустын|песок|desert|sand/i, c: ['e9b66a', 'a8541f', '2a1206'], fx: 'none', snd: 'wind' },
];
const DEFAULT = { c: ['101826', '3a4a7a', '05070c'], fx: 'none', snd: 'pad' };

function pick(prompt) {
  const t = THEMES.find(t => t.k.test(prompt)) || DEFAULT;
  let h = 0; for (const ch of prompt) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return { ...t, seed: h };
}
function findFont() {
  for (const f of ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/Library/Fonts/Arial Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf']) if (fs.existsSync(f)) return f;
  return null;
}
const esc = s => s.replace(/[\\':%]/g, ' ').replace(/[\r\n]+/g, ' ').trim();

function audioGraph(th, T) {
  const pad = `aevalsrc='0.16*sin(2*PI*110*t)+0.11*sin(2*PI*164.81*t)+0.08*sin(2*PI*220*t)+0.06*sin(2*PI*261.63*t)*(0.6+0.4*sin(2*PI*0.2*t))':s=44100:d=${T},lowpass=f=900,aecho=0.8:0.7:400|700:0.3|0.2`;
  const noise = (col, lo, hi, vol, trem) => `anoisesrc=c=${col}:r=44100:d=${T}:a=${vol},highpass=f=${lo},lowpass=f=${hi}` + (trem ? `,tremolo=f=${trem}:d=0.7` : '');
  const m = {
    rain: noise('pink', 400, 9000, 0.5) + '[n];' + pad + ',volume=0.5[p];[n][p]amix=2:duration=longest:normalize=0',
    city: noise('pink', 300, 5000, 0.2) + '[n];' + pad + '[p];[n][p]amix=2:duration=longest:normalize=0',
    sea: noise('brown', 40, 1800, 0.9, 0.13) + '[n];' + pad + ',volume=0.4[p];[n][p]amix=2:duration=longest:normalize=0',
    wind: noise('brown', 60, 1200, 0.8, 0.3) + '[n];' + pad + ',volume=0.5[p];[n][p]amix=2:duration=longest:normalize=0',
    fire: noise('white', 1500, 9000, 0.12, 9) + '[n];' + noise('brown', 40, 400, 0.6) + '[b];' + pad + ',volume=0.4[p];[n][b][p]amix=3:duration=longest:normalize=0',
    forest: noise('pink', 2000, 8000, 0.06, 0.4) + '[n];' + pad + ',volume=0.6[p];[n][p]amix=2:duration=longest:normalize=0',
    space: pad + ',volume=1.2,lowpass=f=500',
    pad: pad,
  }[th.snd];
  return m;
}

function fxGraph(th, w, h, T, fps) {
  const sparse = (a, b) => `lut=y='clip((val-${a})*${b},0,255)'`;
  if (th.fx === 'rain') return `color=c=black:s=${Math.round(w / 3)}x${Math.round(h / 14)}:r=${fps}:d=${T},format=gray,noise=alls=100:allf=t,${sparse(238, 30)},scale=${w}:${h}:flags=neighbor,scroll=vertical=0.9,format=yuv420p[fx]`;
  if (th.fx === 'snow') return `color=c=black:s=${w / 6}x${h / 6}:r=${fps}:d=${T},format=gray,noise=alls=100:allf=t,${sparse(200, 10)},scale=${w}:${h}:flags=bilinear,avgblur=sizeX=3:sizeY=3,scroll=vertical=0.08:horizontal=0.01,format=yuv420p[fx]`;
  if (th.fx === 'embers') return `color=c=black:s=${w / 8}x${h / 8}:r=${fps}:d=${T},format=gray,noise=alls=100:allf=t,${sparse(215, 10)},scale=${w}:${h}:flags=bilinear,avgblur=sizeX=2:sizeY=6,scroll=vertical=-0.12,format=gbrp,colorchannelmixer=rr=1:gg=0.4:bb=0.1[fx]`;
  if (th.fx === 'stars') return `color=c=black:s=${w / 2}x${h / 2}:r=${fps}:d=${T},format=gray,noise=alls=100:allf=t,${sparse(235, 20)},scale=${w}:${h}:flags=neighbor,scroll=horizontal=0.004,format=yuv420p[fx]`;
  return null;
}

// Возвращает Promise; onProgress(0..100)
function render({ prompt, seconds, quality, audio, imagePath, out, onProgress }) {
  return new Promise((resolve, reject) => {
    const [W, H] = SIZES[quality] || SIZES['1080p'];
    const T = Math.max(1, Math.min(10, seconds)), fps = 24, n = T * fps;
    const th = pick(prompt);
    const iw = 1280, ih = 720; // внутреннее разрешение рендера; дальше — Lanczos до выбранного качества
    const bar = Math.round(ih * (1 - (iw / 2.39) / ih) / 2); // анаморфные полосы 2.39:1
    const font = findFont();
    const args = ['-y', '-loglevel', 'error', '-progress', 'pipe:1'];
    const g = [];
    const [c0, c1, c2] = th.c;
    const spd = (0.012 + (th.seed % 10) / 1000).toFixed(3);
    if (imagePath) {
      args.push('-loop', '1', '-framerate', String(fps), '-t', String(T), '-i', imagePath);
      const dir = th.seed % 2 ? 'x+(iw-iw/zoom)*on/' + n : '(iw-iw/zoom)-(iw-iw/zoom)*on/' + n;
      g.push(`[0:v]scale=2400:-2:force_original_aspect_ratio=increase,crop=2400:1350,zoompan=z='1.0+0.22*on/${n}':x='${dir}':y='ih/2-(ih/zoom/2)':d=1:s=${iw}x${ih}:fps=${fps},` +
        `eq=contrast=1.12:saturation=1.1,colorbalance=rs=0.05:bs=-0.06:rh=0.06:bh=-0.04[bg]`);
    } else {
      args.push('-f', 'lavfi', '-i', `gradients=s=${iw}x${ih}:c0=${c0}:c1=${c1}:c2=${c2}:nb_colors=3:speed=${spd}:duration=${T}:rate=${fps}:type=linear:seed=${th.seed % 9999}`);
      g.push('[0:v]gblur=sigma=12,eq=contrast=1.2:saturation=1.15[bg]');
    }
    let last = 'bg';
    const fx = fxGraph(th, iw, ih, T, fps);
    if (fx) {
      g.push(fx.replace('[fx]', '[fx0]'));
      g.push(`[${last}]format=yuv420p[b0];[b0][fx0]blend=c0_mode=screen:c0_opacity=${th.fx === "stars" ? 0.9 : 0.35}:c1_expr=A:c2_expr=A[bl]`); last = 'bl';
    }
    const title = esc(prompt).slice(0, 70);
    const text = font && title
      ? `,drawtext=fontfile='${font}':text='${title}':fontcolor=white:fontsize=${Math.round(ih / 24)}:x=(w-text_w)/2:y=h-${bar}-${Math.round(ih / 9)}:alpha='if(lt(t,0.8),0,if(lt(t,1.6),(t-0.8)/0.8,if(lt(t,${Math.max(2.4, T - 1)}),1,max(0,(${T}-t)/1))))':shadowcolor=black:shadowx=2:shadowy=2` : '';
    g.push(`[${last}]format=yuv420p,vignette=angle=PI/4:mode=backward:eval=init,noise=alls=9:allf=t,` +
      `drawbox=x=0:y=0:w=iw:h=${bar}:color=black:t=fill,drawbox=x=0:y=ih-${bar}:w=iw:h=${bar}:color=black:t=fill${text},` +
      `fade=t=in:st=0:d=0.8,fade=t=out:st=${Math.max(0, T - 0.8)}:d=0.8,scale=${W}:${H}:flags=lanczos,format=yuv420p[v]`);
    const aIdx = imagePath ? 1 : 1; // аудио-источники идут после видео-входа
    let filter = g.join(';');
    if (audio) {
      const ag = audioGraph(th, T);
      // источники аудио встраиваются прямо в граф
      filter += ';' + ag.replace(/(^|;)(?=anoisesrc|aevalsrc)/g, '$1') + `[araw];[araw]afade=t=in:d=1,afade=t=out:st=${Math.max(0, T - 1.2)}:d=1.2,alimiter=limit=0.9[a]`;
    }
    args.push('-filter_complex', filter, '-map', '[v]');
    if (audio) args.push('-map', '[a]', '-c:a', 'aac', '-b:a', '192k');
    args.push('-t', String(T), '-r', String(fps), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', quality === '4K' ? '20' : '18', '-movflags', '+faststart', out);
    const p = spawn('ffmpeg', args);
    let err = '';
    p.stderr.on('data', d => err += d);
    p.stdout.on('data', d => { const m = /out_time_us=(\d+)/.exec(String(d)); if (m && onProgress) onProgress(Math.min(99, Math.round(+m[1] / 1e4 / T))); });
    p.on('error', e => reject(new Error('ffmpeg не найден: установите ffmpeg (' + e.message + ')')));
    p.on('close', c => c === 0 ? resolve() : reject(new Error('Рендер не удался: ' + err.slice(-300))));
  });
}
module.exports = { render, SIZES };
