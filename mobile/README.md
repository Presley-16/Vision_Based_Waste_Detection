# PlanetWatch mobile app (Android + iOS)

A Capacitor app that bundles the citizen website from `../frontend`. It uses the same
pages, styles, animations and page transitions, so it behaves exactly like the website.
The only differences:

- "Install App" becomes **Share App**, a page where users send others the download link.
- The app shows no installation instructions anywhere.

`scripts/sync-web.mjs` copies `frontend/` into `www/` on every build and points the app
at the backend.

## Build the Android APK

Requirements: Node 20+, **JDK 21**, and the Android SDK.

```
cd mobile
npm install
set JAVA_HOME=C:\Users\presley.nyama\Tools\jdk-21.0.11_windows-x64_bin\jdk-21.0.11
npm run build:android                      # app talks to http://<this PC's LAN IP>:5000
npm run build:android -- https://my.server # or a specific backend address
```

The APK is copied to `mobile/dist/PlanetWatch.apk`. The backend serves it from there, so
the website's Install page (QR code and USB cable) works as soon as it exists.

The server address is fixed into the APK at build time. If the PC's IP changes, rebuild
the APK, or better, use a fixed/HTTPS address.

## Installing

From the website's **Install App** page:

- **QR code:** the phone opens `get-app.html`. Android downloads the APK. iPhone adds
  PlanetWatch to the Home Screen.
- **USB cable (Android):** enable USB debugging, connect the phone to the computer running
  the backend, choose *File transfer* and tap *Allow USB debugging*. A green check appears,
  then click *Install app*. MIDI mode doesn't work for installing apps; ADB needs USB debugging.

## iOS

> **Step-by-step guide:** [INSTALL-iOS.md](INSTALL-iOS.md) covers building, installing, renewing, and replacing the app on an iPhone.

Apple doesn't allow installing an app file directly the way Android does. There are two
ways to get PlanetWatch onto an iPhone, and **neither needs a Mac**.

### 1. Native app over USB (Sideloadly + free Apple ID)

1. **Build the .ipa on GitHub.** Push the repo, then go to GitHub → **Actions → "iOS app" →
   Run workflow**. Enter the backend address the app should use (ideally the https
   address from `run.py --tunnel`). The workflow builds on GitHub's free macOS machines
   using [.github/workflows/ios-app.yml](../.github/workflows/ios-app.yml).
2. Download the **PlanetWatch-ipa** artifact and save `PlanetWatch.ipa` into `mobile/dist/`.
   The install page's **iPhone** tab now offers it.
3. On the Windows PC, install **iTunes** (for the iPhone USB driver) and
   [Sideloadly](https://sideloadly.io). Plug in the iPhone and tap **Trust**. The install
   page shows a green check.
4. In Sideloadly, drag in `PlanetWatch.ipa`, enter an Apple ID and click **Start**.
5. On the iPhone: **Settings → General → VPN & Device Management** → trust the Apple ID.
   On iOS 16+ also turn on **Settings → Privacy & Security → Developer Mode**.

With a free Apple ID the install lasts 7 days, and up to 3 sideloaded apps at a time.
Sideloadly re-installs it. A paid Apple Developer account ($99/yr) lasts a year and allows
TestFlight.

On a Mac you can instead run `npm run open:ios` and press Run in Xcode.

### 2. Home Screen app from the QR code (no Apple ID)

Scanning the QR code in Safari and tapping **Share → Add to Home Screen** gives a
full-screen PlanetWatch with the same pages and animations. iPhones only share location
over **https**, so start the server with:

```
python backend/run.py --tunnel
```

This uses ngrok, which is already installed and configured on this PC. The QR code and
share links then use the https address. Over plain `http://` the iPhone shows a warning,
and the mandatory location popup can't be cleared.
