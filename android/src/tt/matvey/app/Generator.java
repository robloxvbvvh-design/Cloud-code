package tt.matvey.app;

import android.graphics.*;
import android.media.*;
import android.text.Layout;
import android.text.StaticLayout;
import android.text.TextPaint;
import java.io.File;
import java.nio.ByteBuffer;
import java.util.*;

/** Генератор видео на телефоне: рисует кадры сцен, звук и кодирует в mp4 (MediaCodec). */
class Generator {
    interface Progress { void on(float p, String stage); }

    static final int AR = 44100;
    final String prompt; final int durSec, heightQ; final boolean vertical, audio; final Bitmap character;
    final Progress cb;
    int W, H, fps;

    // сцены
    int nScenes; float sceneLen;
    int[][] cols; float[][] freq; float[][] spd; float[][][] parts; int[] motion; String[] caps;
    Random rng;
    // звук
    double[] tones; double[] lfo;

    // кодирование
    MediaCodec venc, aenc; MediaMuxer mux;
    int vTrack = -1, aTrack = -1; boolean started = false;
    final List<Object[]> pending = new ArrayList<>();

    Generator(String prompt, int durSec, int heightQ, boolean vertical, boolean audio, Bitmap character, Progress cb) {
        this.prompt = prompt; this.durSec = durSec; this.heightQ = heightQ; this.vertical = vertical;
        this.audio = audio; this.character = character; this.cb = cb;
    }

    /** Возвращает итоговую высоту (может быть меньше запрошенной, если телефон не тянет). */
    int run(File out) throws Exception {
        pickSize();
        initScenes();
        cb.on(0f, "Запускаю кодер…");
        MediaFormat vf = MediaFormat.createVideoFormat("video/avc", W, H);
        vf.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible);
        vf.setInteger(MediaFormat.KEY_BIT_RATE, Math.max(1500000, (int) ((long) W * H * fps / 9)));
        vf.setInteger(MediaFormat.KEY_FRAME_RATE, fps);
        vf.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1);
        venc = MediaCodec.createEncoderByType("video/avc");
        venc.configure(vf, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
        venc.start();
        if (audio) {
            MediaFormat af = MediaFormat.createAudioFormat("audio/mp4a-latm", AR, 1);
            af.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC);
            af.setInteger(MediaFormat.KEY_BIT_RATE, 128000);
            af.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384);
            aenc = MediaCodec.createEncoderByType("audio/mp4a-latm");
            aenc.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE);
            aenc.start();
        }
        mux = new MediaMuxer(out.getAbsolutePath(), MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4);
        try {
            Bitmap bmp = Bitmap.createBitmap(W, H, Bitmap.Config.ARGB_8888);
            Canvas cv = new Canvas(bmp);
            int[] px = new int[W * H];
            byte[] yb = new byte[W * H], ub = new byte[(W / 2) * (H / 2)], vb = new byte[(W / 2) * (H / 2)];
            int total = durSec * fps;
            long audioFed = 0; long audioTotal = (long) durSec * AR;
            for (int f = 0; f < total; f++) {
                float T = (float) f / fps;
                renderFrame(cv, T);
                bmp.getPixels(px, 0, W, 0, 0, W, H);
                toYuv(px, yb, ub, vb);
                queueVideo(yb, ub, vb, (long) f * 1000000L / fps, false);
                if (audio) audioFed = feedAudio(audioFed, Math.min(audioTotal, (long) ((T + 0.6f) * AR)), false);
                if (f % 3 == 0) cb.on(0.95f * f / total, "Рисую кадры и склеиваю…");
            }
            cb.on(0.96f, "Финальное кодирование…");
            queueVideo(null, null, null, (long) total * 1000000L / fps, true);
            if (audio) feedAudio(audioFed, audioTotal, true);
            drainAll();
            bmp.recycle();
        } finally {
            try { venc.stop(); } catch (Exception e) { }
            venc.release();
            if (aenc != null) { try { aenc.stop(); } catch (Exception e) { } aenc.release(); }
            try { if (started) mux.stop(); } catch (Exception e) { }
            mux.release();
        }
        cb.on(1f, "Готово");
        return H;
    }

    // ---------- размеры ----------
    void pickSize() {
        int h = heightQ;
        int[] ladder = {2160, 1440, 1080, 720, 480};
        MediaCodecInfo.VideoCapabilities caps = null;
        try {
            MediaCodec tmp = MediaCodec.createEncoderByType("video/avc");
            caps = tmp.getCodecInfo().getCapabilitiesForType("video/avc").getVideoCapabilities();
            tmp.release();
        } catch (Exception e) { }
        for (int cand : ladder) {
            if (cand > h) continue;
            int w = ((int) Math.round(cand * 16.0 / 9)) & ~1;
            int hh = cand & ~1;
            int a = vertical ? hh : w, b = vertical ? w : hh;
            if (caps == null || caps.isSizeSupported(a, b)) { W = a; H = b; h = cand; break; }
        }
        if (W == 0) { W = vertical ? 480 : 854; H = vertical ? 854 : 480; }
        fps = h >= 1440 ? 15 : 24;
    }

    // ---------- сцены ----------
    void initScenes() {
        long seed = prompt.hashCode() * 2654435761L;
        rng = new Random(seed);
        nScenes = Math.max(1, Math.round(durSec / 5f));
        sceneLen = (float) durSec / nScenes;
        caps = splitCaptions(prompt, nScenes);
        cols = new int[nScenes][3]; freq = new float[nScenes][4]; spd = new float[nScenes][3];
        parts = new float[nScenes][][]; motion = new int[nScenes];
        for (int s = 0; s < nScenes; s++) {
            float base = rng.nextFloat() * 360f;
            for (int k = 0; k < 3; k++)
                cols[s][k] = Color.HSVToColor(new float[]{(base + k * 65f) % 360f, 0.75f, 0.95f - 0.2f * k});
            for (int k = 0; k < 4; k++) freq[s][k] = 1.5f + rng.nextFloat() * 2.5f;
            for (int k = 0; k < 3; k++) spd[s][k] = 0.2f + rng.nextFloat() * 0.5f;
            int n = 18 + rng.nextInt(16);
            parts[s] = new float[n][7];
            for (int i = 0; i < n; i++) {
                parts[s][i] = new float[]{rng.nextFloat(), rng.nextFloat(), 0.01f + rng.nextFloat() * 0.04f,
                    (rng.nextFloat() - 0.5f) * 0.1f, -0.02f - rng.nextFloat() * 0.1f, rng.nextFloat() * 6.28f, 60 + rng.nextInt(90)};
            }
            motion[s] = rng.nextInt(3);
        }
        tones = new double[4]; lfo = new double[4];
        double[] roots = {110.0, 123.47, 130.81, 146.83, 164.81};
        double[][] rat = {{1, 1.2, 1.5, 2}, {1, 1.25, 1.5, 1.875}, {1, 1.125, 1.5, 2.25}};
        double root = roots[rng.nextInt(roots.length)];
        double[] r = rat[rng.nextInt(rat.length)];
        for (int i = 0; i < 4; i++) { tones[i] = root * r[i] * (i > 1 ? 2 : 1); lfo[i] = 0.1 + rng.nextDouble() * 0.3; }
    }

    static String[] splitCaptions(String prompt, int n) {
        List<String> parts = new ArrayList<>();
        for (String p : prompt.split("[.!?;\\n]+")) if (!p.trim().isEmpty()) parts.add(p.trim());
        if (parts.isEmpty()) parts.add(prompt.trim());
        while (parts.size() < n) {
            int bi = 0;
            for (int i = 1; i < parts.size(); i++) if (parts.get(i).length() > parts.get(bi).length()) bi = i;
            String[] w = parts.get(bi).split("\\s+");
            if (w.length < 4) break;
            int mid = w.length / 2;
            parts.remove(bi);
            parts.add(bi, join(w, mid, w.length));
            parts.add(bi, join(w, 0, mid));
        }
        String[] out = new String[n];
        if (parts.size() > n) {
            float k = (float) parts.size() / n;
            for (int i = 0; i < n; i++) {
                StringBuilder sb = new StringBuilder();
                for (int j = (int) (i * k); j < (int) ((i + 1) * k); j++) sb.append(sb.length() > 0 ? " " : "").append(parts.get(j));
                out[i] = sb.toString();
            }
        } else for (int i = 0; i < n; i++) out[i] = parts.get(i % parts.size());
        return out;
    }

    static String join(String[] w, int a, int b) {
        StringBuilder sb = new StringBuilder();
        for (int i = a; i < b; i++) sb.append(i > a ? " " : "").append(w[i]);
        return sb.toString();
    }

    // ---------- кадры ----------
    final Paint pFill = new Paint(Paint.ANTI_ALIAS_FLAG), pBmp = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG);
    Bitmap small; int[] spx; int sw, sh;

    void renderFrame(Canvas cv, float T) {
        int si = Math.min((int) (T / sceneLen), nScenes - 1);
        float t = T - si * sceneLen;
        drawScene(cv, si, t);
        float x = 0.7f;
        if (si + 1 < nScenes && t > sceneLen - x) {
            float k = (t - (sceneLen - x)) / x;
            int sc = cv.saveLayerAlpha(0, 0, W, H, (int) (k * 255));
            drawScene(cv, si + 1, 0f);
            cv.restoreToCount(sc);
        }
    }

    void drawScene(Canvas cv, int s, float t) {
        // фон-плазма в малом разрешении, растягивается с фильтрацией
        if (small == null) {
            sw = vertical ? 54 : 96; sh = vertical ? 96 : 54;
            small = Bitmap.createBitmap(sw, sh, Bitmap.Config.ARGB_8888); spx = new int[sw * sh];
        }
        float[] f = freq[s], sp = spd[s];
        int c0 = cols[s][0], c1 = cols[s][1], c2 = cols[s][2];
        for (int y = 0; y < sh; y++) {
            float gy = (float) y / sh;
            for (int x = 0; x < sw; x++) {
                float gx = (float) x / sw;
                float a = (float) (Math.sin(gx * f[0] * 3 + t * sp[0] * 3) + Math.sin(gy * f[1] * 3 - t * sp[1] * 3));
                float b = (float) Math.sin((gx + gy) * f[2] * 2 + t * sp[2] * 2);
                float c = (float) Math.sin(Math.hypot(gx - 0.5, gy - 0.5) * f[3] * 6 - t * 1.4);
                float m = Math.max(0, Math.min(1, (a + b + c) / 6f + 0.5f));
                float k = (float) (Math.sin(gx * 3 + t * 0.3) * 0.5 + 0.5) * 0.4f;
                spx[y * sw + x] = mix(mix(c0, c1, m), c2, k);
            }
        }
        small.setPixels(spx, 0, sw, 0, 0, sw, sh);
        cv.drawBitmap(small, null, new Rect(0, 0, W, H), pBmp);

        int mn = Math.min(W, H);
        for (float[] p : parts[s]) {
            float px = (((p[0] + p[3] * t) % 1f) + 1f) % 1f * W;
            float py = (((p[1] + p[4] * t) % 1f) + 1f) % 1f * H;
            float r = p[2] * mn * (1 + 0.25f * (float) Math.sin(t * 2 + p[5]));
            pFill.setColor(Color.argb((int) p[6], 255, 255, 255));
            cv.drawCircle(px, py, r, pFill);
        }

        float prog = t / sceneLen;
        if (character != null) {
            float ch = H * (0.55f + 0.05f * (float) Math.sin(t * 2));
            if (motion[s] == 1) ch *= 0.8f + 0.4f * prog;
            float sc = ch / character.getHeight();
            float cx, cy;
            if (motion[s] == 0) { cx = W * (0.5f + 0.18f * (float) Math.cos(t * 0.9)); cy = H * (0.5f + 0.06f * (float) Math.sin(t * 1.8)); }
            else if (motion[s] == 2) { cx = W * (0.2f + 0.6f * prog); cy = H * (0.5f + 0.05f * (float) Math.sin(t * 3)); }
            else { cx = W * 0.5f; cy = H * 0.5f + H * 0.03f * (float) Math.sin(t * 2); }
            Matrix m = new Matrix();
            m.postTranslate(-character.getWidth() / 2f, -character.getHeight() / 2f);
            m.postScale(sc, sc);
            m.postRotate(4 * (float) Math.sin(t * 1.3));
            m.postTranslate(cx + 8, cy + 12);
            Paint sh2 = new Paint(Paint.FILTER_BITMAP_FLAG);
            sh2.setColorFilter(new PorterDuffColorFilter(0x59000000, PorterDuff.Mode.SRC_IN));
            cv.drawBitmap(character, m, sh2);
            m.postTranslate(-8, -12);
            cv.drawBitmap(character, m, pBmp);
        }

        String cap = caps[s];
        if (cap != null && !cap.isEmpty()) {
            float alpha = Math.max(0, Math.min(1, Math.min(t / 0.6f, (sceneLen - t) / 0.6f)));
            TextPaint tp = new TextPaint(Paint.ANTI_ALIAS_FLAG);
            tp.setTypeface(Typeface.DEFAULT_BOLD);
            tp.setTextSize(Math.max(18, W / (vertical ? 14f : 24f)));
            tp.setColor(Color.argb((int) (255 * alpha), 255, 255, 255));
            tp.setShadowLayer(tp.getTextSize() / 12f, 2, 3, Color.argb((int) (170 * alpha), 0, 0, 0));
            StaticLayout lay = StaticLayout.Builder.obtain(cap, 0, cap.length(), tp, (int) (W * 0.86f))
                .setAlignment(Layout.Alignment.ALIGN_CENTER).setMaxLines(3).build();
            cv.save();
            cv.translate(W * 0.07f, H - lay.getHeight() - H * 0.07f - (1 - alpha) * 20);
            lay.draw(cv);
            cv.restore();
        }
    }

    static int mix(int a, int b, float k) {
        int r = (int) (Color.red(a) * (1 - k) + Color.red(b) * k);
        int g = (int) (Color.green(a) * (1 - k) + Color.green(b) * k);
        int bl = (int) (Color.blue(a) * (1 - k) + Color.blue(b) * k);
        return 0xFF000000 | (r << 16) | (g << 8) | bl;
    }

    // ---------- RGB -> YUV ----------
    void toYuv(int[] px, byte[] y, byte[] u, byte[] v) {
        int cw = W / 2;
        for (int j = 0; j < H; j++) {
            int row = j * W;
            for (int i = 0; i < W; i++) {
                int p = px[row + i];
                int r = (p >> 16) & 255, g = (p >> 8) & 255, b = p & 255;
                y[row + i] = (byte) (((66 * r + 129 * g + 25 * b + 128) >> 8) + 16);
                if ((j & 1) == 0 && (i & 1) == 0) {
                    int ci = (j / 2) * cw + i / 2;
                    u[ci] = (byte) (((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128);
                    v[ci] = (byte) (((112 * r - 94 * g - 18 * b + 128) >> 8) + 128);
                }
            }
        }
    }

    // ---------- кодирование ----------
    final MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();

    void queueVideo(byte[] y, byte[] u, byte[] v, long pts, boolean eos) {
        int idx;
        while ((idx = venc.dequeueInputBuffer(10000)) < 0) drain(venc, true, false);
        if (eos) { venc.queueInputBuffer(idx, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM); return; }
        Image img = venc.getInputImage(idx);
        Image.Plane[] pl = img.getPlanes();
        put(pl[0], y, W, H);
        put(pl[1], u, W / 2, H / 2);
        put(pl[2], v, W / 2, H / 2);
        venc.queueInputBuffer(idx, 0, W * H * 3 / 2, pts, 0);
        drain(venc, true, false);
    }

    static void put(Image.Plane pl, byte[] src, int w, int h) {
        ByteBuffer buf = pl.getBuffer();
        int rs = pl.getRowStride(), ps = pl.getPixelStride();
        if (ps == 1) {
            for (int r = 0; r < h; r++) { buf.position(r * rs); buf.put(src, r * w, w); }
        } else {
            int cap = buf.capacity();
            for (int r = 0; r < h; r++) {
                int base = r * rs;
                for (int c = 0; c < w; c++) { int i = base + c * ps; if (i < cap) buf.put(i, src[r * w + c]); }
            }
        }
    }

    long feedAudio(long fed, long upTo, boolean eos) {
        while (fed < upTo) {
            int idx = aenc.dequeueInputBuffer(eos ? 10000 : 0);
            if (idx < 0) { drain(aenc, false, false); if (eos) continue; else break; }
            ByteBuffer ib = aenc.getInputBuffer(idx);
            ib.clear();
            int n = (int) Math.min(ib.capacity() / 2, Math.min(4096, upTo - fed));
            for (int i = 0; i < n; i++) ib.putShort(sample(fed + i));
            aenc.queueInputBuffer(idx, 0, n * 2, fed * 1000000L / AR, 0);
            fed += n;
            drain(aenc, false, false);
        }
        if (eos) {
            int idx;
            while ((idx = aenc.dequeueInputBuffer(10000)) < 0) drain(aenc, false, false);
            aenc.queueInputBuffer(idx, 0, 0, fed * 1000000L / AR, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
        }
        return fed;
    }

    short sample(long i) {
        double t = (double) i / AR, s = 0;
        for (int k = 0; k < 4; k++) s += 0.11 * Math.sin(2 * Math.PI * tones[k] * t) * (0.65 + 0.35 * Math.sin(2 * Math.PI * lfo[k] * t + k));
        double fade = Math.min(1.5, durSec / 4.0), total = durSec;
        double env = Math.min(1, Math.min(t / fade, (total - t) / fade));
        return (short) (Math.max(-1, Math.min(1, s * env)) * 32000);
    }

    void drainAll() {
        boolean vDone = false, aDone = !audio;
        long end = System.currentTimeMillis() + 60000;
        while ((!vDone || !aDone) && System.currentTimeMillis() < end) {
            if (!vDone) vDone = drain(venc, true, true);
            if (!aDone) aDone = drain(aenc, false, true);
        }
    }

    /** true — достигнут конец потока. */
    boolean drain(MediaCodec c, boolean video, boolean wait) {
        for (;;) {
            int o = c.dequeueOutputBuffer(info, wait ? 10000 : 0);
            if (o == MediaCodec.INFO_TRY_AGAIN_LATER) return false;
            if (o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                int t = mux.addTrack(c.getOutputFormat());
                if (video) vTrack = t; else aTrack = t;
                if (vTrack >= 0 && (!audio || aTrack >= 0)) {
                    mux.start(); started = true;
                    for (Object[] p : pending)
                        mux.writeSampleData(((Integer) p[0]) == -1 ? vTrack : aTrack, (ByteBuffer) p[1], (MediaCodec.BufferInfo) p[2]);
                    pending.clear();
                }
                continue;
            }
            if (o < 0) continue;
            ByteBuffer ob = c.getOutputBuffer(o);
            boolean eos = (info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0;
            if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) != 0) info.size = 0;
            if (info.size > 0) {
                ob.position(info.offset); ob.limit(info.offset + info.size);
                int track = video ? vTrack : aTrack;
                if (started) mux.writeSampleData(track, ob, info);
                else {
                    ByteBuffer copy = ByteBuffer.allocate(info.size); copy.put(ob); copy.flip();
                    MediaCodec.BufferInfo bi = new MediaCodec.BufferInfo();
                    bi.set(0, info.size, info.presentationTimeUs, info.flags);
                    pending.add(new Object[]{video ? -1 : -2, copy, bi}); // -1 видео, -2 звук
                }
            }
            c.releaseOutputBuffer(o, false);
            if (eos) return true;
        }
    }
}
