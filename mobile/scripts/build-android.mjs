// Builds the installable Android APK and copies it to mobile/dist/PlanetWatch.apk,
// which is where the backend serves it from for QR-code and USB installs.
//
// Needs JDK 21 (JAVA_HOME) and the Android SDK (ANDROID_HOME, or Android
// Studio's default location).
import { execSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const mobileDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const androidDir = join(mobileDir, 'android');
const run = (command, cwd = mobileDir) => execSync(command, { cwd, stdio: 'inherit' });

run(`node scripts/sync-web.mjs ${process.argv[2] || ''}`.trim());
run('npx cap sync android');

const gradlew = process.platform === 'win32' ? '.\\gradlew.bat' : './gradlew';
// Capacitor 8 needs Java 21; pin Gradle to JAVA_HOME so a global
// org.gradle.java.home (e.g. an older JDK 17) doesn't win.
const javaHome = process.env.JAVA_HOME ? ` "-Dorg.gradle.java.home=${process.env.JAVA_HOME}"` : '';
run(`${gradlew} assembleDebug${javaHome}`, androidDir);

const apk = join(androidDir, 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk');
if (!existsSync(apk)) {
  console.error(`Build finished but ${apk} is missing.`);
  process.exit(1);
}
mkdirSync(join(mobileDir, 'dist'), { recursive: true });
copyFileSync(apk, join(mobileDir, 'dist', 'PlanetWatch.apk'));
console.log('APK ready: mobile/dist/PlanetWatch.apk — the install page can now serve it.');
