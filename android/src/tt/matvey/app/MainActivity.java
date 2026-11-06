package tt.matvey.app;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.*;
import android.widget.*;

public class MainActivity extends Activity implements View.OnClickListener {
    EditText input;
    ValueCallback<Uri[]> fileCb2;
    private WebView web;
    private LinearLayout setup;
        private SharedPreferences prefs;

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("mtt", MODE_PRIVATE);
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#0d0b1a"));

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setBackgroundColor(Color.parseColor("#0d0b1a"));
        web.setWebViewClient(new Client(this));
        web.setWebChromeClient(new Chrome(this));
        root.addView(web);

        setup = new LinearLayout(this);
        setup.setOrientation(LinearLayout.VERTICAL);
        setup.setGravity(Gravity.CENTER);
        setup.setPadding(48, 48, 48, 48);
        setup.setBackgroundColor(Color.parseColor("#0d0b1a"));
        TextView t = new TextView(this);
        t.setText("Ии Матвей ТТ");
        t.setTextSize(28); t.setTextColor(Color.WHITE);
        TextView h = new TextView(this);
        h.setText("Адрес сервера (например http://192.168.1.5:3000 или https://ваш-сайт.ру)");
        h.setTextColor(Color.parseColor("#9b96c4")); h.setPadding(0, 24, 0, 24);
        EditText in = new EditText(this);
        in.setHint("http://...");
        in.setTextColor(Color.WHITE); in.setHintTextColor(Color.GRAY);
        in.setSingleLine(true);
        in.setText(prefs.getString("url", ""));
        Button go = new Button(this);
        go.setText("Подключиться");
        go.setOnClickListener(this);
input = in;
        setup.addView(t); setup.addView(h); setup.addView(in); setup.addView(go);
        root.addView(setup);
        setContentView(root);

        String u = prefs.getString("url", "");
        if (u.isEmpty()) showSetup(); else open(u);
    }

    void open(String u) { setup.setVisibility(View.GONE); web.setVisibility(View.VISIBLE); web.loadUrl(u); }
    void showSetup() { web.setVisibility(View.GONE); setup.setVisibility(View.VISIBLE); }

    @Override protected void onActivityResult(int req, int res, Intent data) {
        if (req == 1 && fileCb2 != null) {
            fileCb2.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(res, data));
            fileCb2 = null;
        }
    }

    @Override public void onClick(View v) {
        String u = input.getText().toString().trim();
        if (u.isEmpty()) return;
        if (!u.startsWith("http")) u = "http://" + u;
        prefs.edit().putString("url", u).apply();
        open(u);
    }

    @Override public void onBackPressed() {
        if (web.getVisibility() == View.VISIBLE && web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
