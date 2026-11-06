#!/bin/bash
# Сборка APK без Gradle. Нужны ANDROID_HOME (platforms;android-34, build-tools;34.0.0) и JDK 17+.
set -e
cd "$(dirname "$0")"
BT=$(ls -d "$ANDROID_HOME"/build-tools/* | tail -1); JAR="$ANDROID_HOME/platforms/android-34/android.jar"
rm -rf out && mkdir -p out/classes out/res
"$BT/aapt2" compile --dir res -o out/res
"$BT/aapt2" link -o out/base.apk -I "$JAR" --manifest AndroidManifest.xml --min-sdk-version 24 --target-sdk-version 34 --version-code 1 --version-name 1.0 out/res/*.flat
javac -nowarn --release 8 -cp "$JAR" -d out/classes $(find src -name '*.java') 2>&1 | grep -v warning || true
"$BT/d8" --lib "$JAR" --min-api 24 --output out $(find out/classes -name '*.class')
(cd out && zip -q base.apk classes.dex)
"$BT/zipalign" -f 4 out/base.apk out/aligned.apk
[ -f debug.keystore ] || keytool -genkey -v -keystore debug.keystore -storepass android -keypass android -alias key -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=MatveyTT" >/dev/null 2>&1
"$BT/apksigner" sign --v1-signing-enabled true --v2-signing-enabled true --ks debug.keystore --ks-pass pass:android --key-pass pass:android --out ii-matvey-tt.apk out/aligned.apk
echo built: $(pwd)/ii-matvey-tt.apk
