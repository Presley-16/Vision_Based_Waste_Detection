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

`ios/` is a ready Xcode project (`npm run open:ios` on a Mac). Apple only allows installing
apps through Xcode, TestFlight or the App Store, which all need a Mac and an Apple
developer account. Without those, iPhone users install the Home Screen web app from the
QR code.
