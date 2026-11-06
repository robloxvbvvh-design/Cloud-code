package tt.matvey.app;
import android.net.Uri;
import android.webkit.*;
class Chrome extends WebChromeClient {
    final MainActivity a;
    Chrome(MainActivity a) { this.a = a; }
    @Override public boolean onShowFileChooser(WebView w, ValueCallback<Uri[]> cb, FileChooserParams p) {
        if (a.fileCb2 != null) a.fileCb2.onReceiveValue(null);
        a.fileCb2 = cb;
        try { a.startActivityForResult(p.createIntent(), 1); } catch (Exception e) { a.fileCb2 = null; return false; }
        return true;
    }
}
