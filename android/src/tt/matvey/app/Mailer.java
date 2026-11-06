package tt.matvey.app;

import java.io.*;
import java.net.Socket;
import javax.net.ssl.SSLSocketFactory;
import android.util.Base64;

/** Минимальный SMTP-клиент (SSL, порт 465, AUTH LOGIN): отправляет код прямо с телефона. */
class Mailer {
    static void send(String host, int port, String user, String pass, String to, String subject, String body) throws Exception {
        Socket s = SSLSocketFactory.getDefault().createSocket(host, port);
        s.setSoTimeout(20000);
        try {
            BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream(), "UTF-8"));
            Writer out = new OutputStreamWriter(s.getOutputStream(), "UTF-8");
            expect(in, "220");
            cmd(in, out, "EHLO matvey.tt", "250");
            cmd(in, out, "AUTH LOGIN", "334");
            cmd(in, out, b64(user), "334");
            cmd(in, out, b64(pass), "235");
            cmd(in, out, "MAIL FROM:<" + user + ">", "250");
            cmd(in, out, "RCPT TO:<" + to + ">", "250");
            cmd(in, out, "DATA", "354");
            String msg = "From: =?UTF-8?B?" + b64("Ии Матвей ТТ") + "?= <" + user + ">\r\n"
                + "To: <" + to + ">\r\n"
                + "Subject: =?UTF-8?B?" + b64(subject) + "?=\r\n"
                + "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n"
                + "Content-Transfer-Encoding: base64\r\n\r\n"
                + Base64.encodeToString(body.getBytes("UTF-8"), Base64.CRLF) + "\r\n.\r\n";
            out.write(msg); out.flush();
            expect(in, "250");
            cmd(in, out, "QUIT", "221");
        } finally { s.close(); }
    }

    private static String b64(String x) throws Exception {
        return Base64.encodeToString(x.getBytes("UTF-8"), Base64.NO_WRAP);
    }

    private static void cmd(BufferedReader in, Writer out, String c, String code) throws Exception {
        out.write(c + "\r\n"); out.flush();
        expect(in, code);
    }

    private static void expect(BufferedReader in, String code) throws Exception {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.length() >= 4 && line.charAt(3) == '-') continue; // продолжение ответа
            if (line.startsWith(code)) return;
            throw new Exception("SMTP: " + line);
        }
        throw new Exception("SMTP: соединение закрыто");
    }
}
