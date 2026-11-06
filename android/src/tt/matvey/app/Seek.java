package tt.matvey.app;
import android.widget.SeekBar;
import android.widget.TextView;
class Seek implements SeekBar.OnSeekBarChangeListener {
    final TextView t;
    Seek(TextView t) { this.t = t; }
    public void onProgressChanged(SeekBar s, int p, boolean u) { t.setText("Длительность: " + (p + 3) + " сек"); }
    public void onStartTrackingTouch(SeekBar s) { }
    public void onStopTrackingTouch(SeekBar s) { }
}
