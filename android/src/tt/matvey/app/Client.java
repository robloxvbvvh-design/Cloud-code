package tt.matvey.app;
import android.webkit.*;
import android.widget.Toast;
class Client extends WebViewClient {
    final MainActivity a;
    Client(MainActivity a) { this.a = a; }
    @Override public void onReceivedError(WebView v, int code, String desc, String url) {
        Toast.makeText(a, "Не удалось подключиться к серверу", Toast.LENGTH_LONG).show();
        a.showSetup();
    }
}
