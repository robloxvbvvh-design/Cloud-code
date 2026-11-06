package tt.matvey.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.provider.MediaStore;
import android.text.InputFilter;
import android.text.InputType;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.security.SecureRandom;

public class MainActivity extends Activity {
    static final int BG = 0xFF0D0B1A, CARD = 0xFF17142B, MUT = 0xFF9B96C4, A = 0xFF8B5CF6;
    SharedPreferences prefs;
    FrameLayout root;
    String email, code; long codeTime;
    Bitmap character; String charName;
    TextView charLabel;
    boolean audioOn = true;
    File lastVideo;
    final Handler ui = new Handler(Looper.getMainLooper());

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("mtt", MODE_PRIVATE);
        root = new FrameLayout(this);
        root.setBackgroundColor(BG);
        setContentView(root);
        String e = prefs.getString("email", "");
        if (!e.isEmpty()) { email = e; showApp(); } else showWelcome();
    }

    // ---------- вспомогательное ----------
    int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density); }

    LinearLayout page() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setPadding(dp(20), dp(24), dp(20), dp(24));
        root.removeAllViews();
        ScrollView sv = new ScrollView(this);
        sv.setFillViewport(true);
        sv.addView(l, new ViewGroup.LayoutParams(-1, -2));
        root.addView(sv);
        return l;
    }

    TextView text(String s, int size, int color) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(size); t.setTextColor(color);
        return t;
    }

    Button button(String s, boolean primary, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(s); b.setAllCaps(false); b.setTextColor(primary ? Color.WHITE : MUT);
        b.setTextSize(16); b.setOnClickListener(l);
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable(
            android.graphics.drawable.GradientDrawable.Orientation.LEFT_RIGHT,
            primary ? new int[]{A, 0xFFEC4899} : new int[]{CARD, CARD});
        g.setCornerRadius(dp(14));
        if (!primary) g.setStroke(dp(1), 0xFF2D2850);
        b.setBackground(g);
        return b;
    }

    EditText input(String hint, int type) {
        EditText e = new EditText(this);
        e.setHint(hint); e.setHintTextColor(0xFF6A6592); e.setTextColor(Color.WHITE);
        e.setInputType(type); e.setBackgroundColor(CARD); e.setPadding(dp(14), dp(14), dp(14), dp(14));
        return e;
    }

    LinearLayout.LayoutParams lp(int top) {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.topMargin = dp(top);
        return p;
    }

    void toast(String s) { Toast.makeText(this, s, Toast.LENGTH_LONG).show(); }

    // ---------- 1. Приветствие ----------
    void showWelcome() {
        LinearLayout l = page();
        l.setGravity(Gravity.CENTER_HORIZONTAL);
        TextView logo = text("Ии Матвей ТТ", 22, A); logo.setTypeface(null, Typeface.BOLD);
        l.addView(logo);
        View sp = new View(this); l.addView(sp, new LinearLayout.LayoutParams(-1, 0, 1));
        TextView hi = text("Привет! 👋", 44, Color.WHITE); hi.setTypeface(null, Typeface.BOLD); hi.setGravity(Gravity.CENTER);
        l.addView(hi);
        TextView d = text("Зарегистрируйтесь и создавайте видео по описанию — до 30 секунд, до 4K, со звуком.", 16, MUT);
        d.setGravity(Gravity.CENTER); l.addView(d, lp(12));
        View sp2 = new View(this); l.addView(sp2, new LinearLayout.LayoutParams(-1, 0, 1));
        l.addView(button("Начать", true, v -> showEmail()), lp(0));
    }

    // ---------- 2. E-mail ----------
    void showEmail() {
        LinearLayout l = page();
        l.addView(text("Введите e-mail", 24, Color.WHITE));
        l.addView(text("Мы отправим на него код подтверждения.", 14, MUT), lp(4));
        EditText e = input("you@example.com", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        l.addView(e, lp(20));
        TextView err = text("", 14, 0xFFFF7B9C); l.addView(err, lp(6));
        Button send = button("Получить код", true, null);
        l.addView(send, lp(8));
        send.setOnClickListener(v -> {
            String m = e.getText().toString().trim().toLowerCase();
            if (!m.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]{2,}$")) { err.setText("Неверный e-mail"); return; }
            send.setEnabled(false); err.setText("Отправляю код…");
            email = m;
            code = String.format("%06d", new SecureRandom().nextInt(1000000));
            codeTime = System.currentTimeMillis();
            new Thread(() -> {
                String sent = null;
                String host = prefs.getString("smtp_host", ""), user = prefs.getString("smtp_user", ""), pass = prefs.getString("smtp_pass", "");
                if (!host.isEmpty() && !user.isEmpty()) {
                    try {
                        Mailer.send(host, 465, user, pass, m, "Код входа: " + code,
                            "Ваш код для входа в «Ии Матвей ТТ»: " + code + "\nКод действует 10 минут.");
                        sent = "ok";
                    } catch (Exception ex) { sent = "Ошибка почты: " + ex.getMessage(); }
                }
                final String res = sent;
                ui.post(() -> {
                    send.setEnabled(true);
                    if ("ok".equals(res)) showCode("Код отправлен на " + email + ". Проверьте почту (и «Спам»).");
                    else showCode((res != null ? res + "\n" : "") + "Почта не настроена или недоступна — режим проверки.\nВаш код: " + code);
                });
            }).start();
        });
        l.addView(button("Настроить почту отправки", false, v -> showSmtp()), lp(14));
    }

    void showSmtp() {
        LinearLayout l = page();
        l.addView(text("Почта для отправки кодов", 22, Color.WHITE));
        l.addView(text("Укажите ящик, с которого приложение будет отправлять коды. Для Gmail: smtp.gmail.com и «пароль приложения» (Аккаунт Google → Безопасность → Пароли приложений). Данные хранятся только на этом телефоне.", 14, MUT), lp(6));
        EditText h = input("SMTP сервер (smtp.gmail.com)", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        EditText u = input("Ваша почта (you@gmail.com)", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText p = input("Пароль приложения", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        h.setText(prefs.getString("smtp_host", "smtp.gmail.com")); u.setText(prefs.getString("smtp_user", ""));
        l.addView(h, lp(16)); l.addView(u, lp(8)); l.addView(p, lp(8));
        l.addView(button("Сохранить", true, v -> {
            prefs.edit().putString("smtp_host", h.getText().toString().trim())
                .putString("smtp_user", u.getText().toString().trim())
                .putString("smtp_pass", p.getText().toString().trim()).apply();
            showEmail();
        }), lp(16));
        l.addView(button("Назад", false, v -> showEmail()), lp(8));
    }

    // ---------- 3. Код ----------
    void showCode(String note) {
        LinearLayout l = page();
        l.addView(text("Введите код", 24, Color.WHITE));
        l.addView(text(note, 14, MUT), lp(4));
        EditText c = input("••••••", InputType.TYPE_CLASS_NUMBER);
        c.setGravity(Gravity.CENTER); c.setTextSize(26);
        c.setFilters(new InputFilter[]{new InputFilter.LengthFilter(6)});
        l.addView(c, lp(20));
        TextView err = text("", 14, 0xFFFF7B9C); l.addView(err, lp(6));
        l.addView(button("Войти", true, v -> {
            if (System.currentTimeMillis() - codeTime > 600000) { err.setText("Код истёк, запросите новый"); return; }
            if (!c.getText().toString().trim().equals(code)) { err.setText("Неверный код"); return; }
            prefs.edit().putString("email", email).apply();
            showApp();
        }), lp(8));
        l.addView(button("Другой e-mail", false, v -> showEmail()), lp(8));
    }

    // ---------- 4. Генерация ----------
    int[] heights = {480, 720, 1080, 1440, 2160};
    void showApp() {
        LinearLayout l = page();
        LinearLayout top = new LinearLayout(this);
        TextView logo = text("Ии Матвей ТТ", 20, A); logo.setTypeface(null, Typeface.BOLD);
        top.addView(logo, new LinearLayout.LayoutParams(0, -2, 1));
        top.addView(text(email, 12, MUT));
        l.addView(top);

        // результат
        LinearLayout res = new LinearLayout(this); res.setOrientation(LinearLayout.VERTICAL);
        l.addView(res, lp(10));
        TextView stage = text("", 15, Color.WHITE);
        ProgressBar bar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        bar.setMax(100);
        VideoView vv = new VideoView(this);
        Button save = button("Сохранить в галерею", true, null);
        res.setVisibility(View.GONE);

        l.addView(text("Запрос", 13, MUT), lp(14));
        EditText prompt = input("Опишите видео. Каждое предложение — новая сцена. Например: Космонавт летит над океаном. Закат окрашивает небо.",
            InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        prompt.setMinLines(4); prompt.setGravity(Gravity.TOP);
        l.addView(prompt, lp(4));

        l.addView(text("Персонаж (необязательно)", 13, MUT), lp(14));
        LinearLayout cr = new LinearLayout(this); cr.setGravity(Gravity.CENTER_VERTICAL);
        charLabel = text(character == null ? "Не выбран" : charName, 14, MUT);
        cr.addView(charLabel, new LinearLayout.LayoutParams(0, -2, 1));
        cr.addView(button("Загрузить", false, v -> {
            Intent i = new Intent(Intent.ACTION_GET_CONTENT); i.setType("image/*");
            startActivityForResult(i, 1);
        }));
        cr.addView(button("✕", false, v -> { character = null; charLabel.setText("Не выбран"); }));
        l.addView(cr, lp(4));

        TextView dl = text("Длительность: 10 сек", 13, MUT); l.addView(dl, lp(14));
        SeekBar sb = new SeekBar(this); sb.setMax(27); sb.setProgress(7);
        sb.setOnSeekBarChangeListener(new Seek(dl));
        l.addView(sb);

        l.addView(text("Качество", 13, MUT), lp(10));
        Spinner q = new Spinner(this);
        q.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new String[]{"480p", "720p", "1080p", "1440p", "4K"}));
        q.setSelection(2);
        l.addView(q);
        l.addView(text("Формат", 13, MUT), lp(10));
        Spinner ar = new Spinner(this);
        ar.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new String[]{"16:9 (горизонт)", "9:16 (вертикаль)"}));
        l.addView(ar);

        l.addView(text("Звук", 13, MUT), lp(10));
        LinearLayout ar2 = new LinearLayout(this);
        Button on = button("Со звуком", true, null), off = button("Без звука", false, null);
        ar2.addView(on, new LinearLayout.LayoutParams(0, -2, 1)); ar2.addView(off, new LinearLayout.LayoutParams(0, -2, 1));
        l.addView(ar2);
        on.setOnClickListener(v -> { audioOn = true; on.setTextColor(Color.WHITE); off.setTextColor(MUT); });
        off.setOnClickListener(v -> { audioOn = false; off.setTextColor(Color.WHITE); on.setTextColor(MUT); });

        TextView err = text("", 14, 0xFFFF7B9C); l.addView(err, lp(6));
        Button gen = button("Создать видео", true, null);
        l.addView(gen, lp(4));
        l.addView(button("Выйти", false, v -> { prefs.edit().remove("email").apply(); showWelcome(); }), lp(10));

        gen.setOnClickListener(v -> {
            String pr = prompt.getText().toString().trim();
            if (pr.length() < 3) { err.setText("Напишите запрос"); return; }
            err.setText("");
            gen.setEnabled(false);
            res.removeAllViews(); res.setVisibility(View.VISIBLE);
            res.addView(stage); res.addView(bar);
            stage.setText("Готовлю…"); bar.setProgress(0);
            int dur = sb.getProgress() + 3, hq = heights[q.getSelectedItemPosition()];
            boolean vert = ar.getSelectedItemPosition() == 1;
            File out = new File(getCacheDir(), "video_" + System.currentTimeMillis() + ".mp4");
            Bitmap ch = character;
            new Thread(() -> {
                String error = null; int h = 0;
                try {
                    Generator g = new Generator(pr, dur, hq, vert, audioOn, ch, (p, s) -> ui.post(() -> {
                        stage.setText(s); bar.setProgress((int) (p * 100));
                    }));
                    h = g.run(out);
                } catch (Throwable ex) { error = "Не удалось создать видео: " + ex; }
                final String fe = error; final int fh = h;
                ui.post(() -> {
                    gen.setEnabled(true);
                    if (fe != null) { res.setVisibility(View.GONE); err.setText(fe); return; }
                    lastVideo = out;
                    res.removeAllViews();
                    if (fh < hq) res.addView(text("Телефон не поддерживает это качество, видео создано в " + fh + "p", 13, MUT));
                    res.addView(vv, new LinearLayout.LayoutParams(-1, dp(vert ? 420 : 220)));
                    vv.setVideoPath(out.getAbsolutePath());
                    vv.setMediaController(new MediaController(this));
                    vv.setOnPreparedListener(mp -> { mp.setLooping(true); vv.start(); });
                    res.addView(save, lp(8));
                });
            }).start();
        });
        save.setOnClickListener(v -> {
            try {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.Video.Media.DISPLAY_NAME, "matvey-tt-" + System.currentTimeMillis() + ".mp4");
                cv.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
                cv.put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/Матвей ТТ");
                Uri u = getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, cv);
                try (InputStream in = new FileInputStream(lastVideo); OutputStream o = getContentResolver().openOutputStream(u)) {
                    byte[] buf = new byte[65536]; int n;
                    while ((n = in.read(buf)) > 0) o.write(buf, 0, n);
                }
                toast("Сохранено в галерею (Movies/Матвей ТТ)");
            } catch (Exception ex) { toast("Не удалось сохранить: " + ex.getMessage()); }
        });
    }

    @Override protected void onActivityResult(int req, int res, Intent data) {
        if (req == 1 && res == RESULT_OK && data != null) {
            try {
                Uri u = data.getData();
                BitmapFactory.Options o = new BitmapFactory.Options(); o.inJustDecodeBounds = true;
                try (InputStream in = getContentResolver().openInputStream(u)) { BitmapFactory.decodeStream(in, null, o); }
                int s = 1; while (o.outHeight / s > 1200 || o.outWidth / s > 1200) s *= 2;
                o = new BitmapFactory.Options(); o.inSampleSize = s;
                try (InputStream in = getContentResolver().openInputStream(u)) { character = BitmapFactory.decodeStream(in, null, o); }
                charName = "Картинка выбрана";
                if (charLabel != null) charLabel.setText(charName);
            } catch (Exception e) { toast("Не удалось открыть картинку"); }
        }
    }
}
