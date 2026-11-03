# Installing PlanetWatch on an iPhone

How to build the PlanetWatch iOS app, install it on an iPhone from a Windows PC, keep it
running, and replace it with a newer version. No Mac is needed.

**Contents**

1. [What you need](#1-what-you-need)
2. [Build the app on GitHub](#2-build-the-app-on-github)
3. [Download the app file](#3-download-the-app-file)
4. [Set up the PC (one-time)](#4-set-up-the-pc-one-time)
5. [Install the app on the iPhone](#5-install-the-app-on-the-iphone)
6. [Allow the app to open (one-time per iPhone)](#6-allow-the-app-to-open-one-time-per-iphone)
7. [Connect the app to the server](#7-connect-the-app-to-the-server)
8. [Every 7 days: renew the app](#8-every-7-days-renew-the-app)
9. [Replacing the app with a new version](#9-replacing-the-app-with-a-new-version)
10. [Removing the app](#10-removing-the-app)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. What you need

| Item | Notes |
| --- | --- |
| iPhone | iOS 15 or newer |
| USB cable | Lightning or USB-C, whichever fits the iPhone |
| Windows PC | The one that runs the PlanetWatch server (`backend/run.py`) |
| Apple ID | Any Apple ID works. A free one is fine. |
| GitHub account | With access to `github.com/Presley-16/Vision_Based_Waste_Detection` |
| iTunes + iCloud for Windows | Provide Apple's USB driver |
| [Sideloadly](https://sideloadly.io) | Signs and installs the app over USB |

> **Why so many steps?** Apple doesn't let an iPhone install an app file the way Android
> does. The app has to be signed with an Apple ID, and Sideloadly does that while
> installing it. A free Apple ID keeps the app working for **7 days**, after which you
> renew it (see [section 8](#8-every-7-days-renew-the-app)).

---

## 2. Build the app on GitHub

iOS apps can only be built on a Mac. GitHub provides free Mac machines that do it for us.

1. Make sure the latest code is pushed to GitHub (`git push origin main`).
2. Open **https://github.com/Presley-16/Vision_Based_Waste_Detection/actions**.
3. In the left sidebar, click **iOS app**.
4. On the right, click **Run workflow**.
5. In **server_url**, enter the address of the PlanetWatch server the app should talk to,
   for example `http://172.20.10.3:5000`.
   - To find the PC's address, run `ipconfig` in PowerShell and look for the
     **IPv4 Address** under the Wi-Fi adapter. Add `http://` in front and `:5000` at the end.
   - If you run the server with `python backend/run.py --tunnel`, use the `https://...`
     address it prints instead. This address works from any network.
6. Click the green **Run workflow** button.
7. Wait about **10 minutes**. Refresh the page; the run shows a yellow dot while it
   builds, then a **green ✓** when it's finished.
   - A **red ✗** means the build failed. Click the run, then the failed step, and copy the
     error message.

---

## 3. Download the app file

1. On the **Actions** page, click the run with the green ✓ to open the **run page**.
2. Scroll to the bottom, to the **Artifacts** section.
3. Click **PlanetWatch-ipa**. This downloads `PlanetWatch-ipa.zip` to your **Downloads**
   folder. You must be signed in to GitHub.
4. Unzip it into the project's `mobile\dist` folder. Paste this into PowerShell:

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\PlanetWatch-ipa.zip" -DestinationPath "C:\Users\presley.nyama\Desktop\Vision-Based_Illegal_Waste_Detection\mobile\dist" -Force
   ```

   Or by hand: right-click the zip → **Extract All…**, then copy **PlanetWatch.ipa** into
   `Desktop\Vision-Based_Illegal_Waste_Detection\mobile\dist\`.

You should now have `mobile\dist\PlanetWatch.ipa` (about 4–5 MB). The website's **Install
App** page, on the **iPhone** tab of the USB card, now shows a **Download PlanetWatch.ipa**
button.

---

## 4. Set up the PC (one-time)

1. **Install iTunes and iCloud for Windows.** Use the versions from Apple's website:
   - iTunes: https://www.apple.com/itunes/download/win64
   - iCloud: https://support.apple.com/en-us/103232

   If you already have the **Microsoft Store** version of iTunes and Sideloadly complains
   about iTunes or iCloud, uninstall the Store versions and install the ones from Apple's
   website.
2. **Install Sideloadly** from **https://sideloadly.io** → *Download for Windows* → run the
   installer.
3. **Allow phones to reach the server.** Open **PowerShell as Administrator**: Start menu
   → type *PowerShell* → right-click → *Run as administrator*. Then run:

   ```powershell
   New-NetFirewallRule -DisplayName "PlanetWatch (port 5000)" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Any
   ```

   On a work laptop, IT policy may block this. If so, ask IT to allow incoming
   connections on port 5000.

---

## 5. Install the app on the iPhone

1. Connect the iPhone to the PC with the USB cable and **unlock** the iPhone.
2. If the iPhone asks **"Trust This Computer?"**, tap **Trust** and enter the passcode.
   The Install App page now shows **"Apple iPhone connected"** with a green check.
3. Open **Sideloadly** and fill in:
   - **iDevice:** pick your iPhone from the list.
   - **Apple account:** type your Apple ID email.
   - **IPA:** drag `mobile\dist\PlanetWatch.ipa` onto the IPA icon, or click the icon and
     browse to it.
4. Click **Start**.
5. Enter your **Apple ID password** when asked. If your iPhone shows a **two-factor code**,
   type it into Sideloadly.
6. Wait until the status at the bottom of Sideloadly says **Done.** The **PlanetWatch**
   icon now appears on the iPhone's Home Screen.

---

## 6. Allow the app to open (one-time per iPhone)

The first time, iOS blocks apps installed this way until you trust them.

1. **Trust the Apple ID:** **Settings → General → VPN & Device Management** → under
   *Developer App* tap your Apple ID email → **Trust "…"** → **Trust**.
2. **Turn on Developer Mode (iOS 16 and newer):** **Settings → Privacy & Security →
   Developer Mode** → switch **on** → **Restart**. After the restart, tap **Turn On** and
   enter the passcode.
   - If *Developer Mode* isn't in the list, open PlanetWatch once (it will refuse), then
     look again.
3. Open **PlanetWatch** and tap **Allow While Using App** when it asks for location.
   Location is mandatory; the app won't continue without it.
4. Sign up or sign in. The app works exactly like the website.

---

## 7. Connect the app to the server

The app talks to the server address chosen in [step 2](#2-build-the-app-on-github).
Whenever you use the app:

- The server must be running on the PC: `python backend/run.py`. If the app was built
  with an https tunnel address, use `python backend/run.py --tunnel` instead.
- The iPhone and the PC must be on the **same network**, for example both on the same Wi-Fi,
  or the PC connected to the iPhone's hotspot. This doesn't apply to the tunnel address.
- The **PC's address must not have changed.** If `ipconfig` now shows a different IPv4
  address than the one you built with, the app can't connect. Rebuild with the new
  address and replace the app (see [section 9](#9-replacing-the-app-with-a-new-version)).

---

## 8. Every 7 days: renew the app

With a free Apple ID, the app stops opening 7 days after it was installed. iOS says it's
"no longer available". To renew it:

1. Connect the iPhone and unlock it.
2. In Sideloadly, select the same iPhone, the same Apple ID and the same `PlanetWatch.ipa`.
3. Click **Start** and wait for **Done.**

That's all. The app keeps its saved sign-in and settings, and you don't need to repeat
section 6.

> With a paid Apple Developer account ($99/year), installs last 1 year instead of 7 days.

---

## 9. Replacing the app with a new version

Do this whenever the app needs updating:
- the website or app code changed (the app bundles the website's pages, so any change
  to `frontend/` needs a new build), or
- the server address changed.

### Step 1: build the new version
1. Push the latest code: `git push origin main`.
2. Run the **iOS app** workflow again (see [section 2](#2-build-the-app-on-github)) with
   the correct **server_url**.

### Step 2: swap the file on the PC
1. In `mobile\dist`, **delete** the old `PlanetWatch.ipa`, plus any leftover
   `PlanetWatch-ipa.zip` or `PlanetWatch-ipa` folder.
2. In your **Downloads** folder, delete the old `PlanetWatch-ipa.zip`. Otherwise the new
   one gets saved as `PlanetWatch-ipa (1).zip`.
3. Download the new artifact and unzip it into `mobile\dist` (see
   [section 3](#3-download-the-app-file)).

### Step 3: put it on the iPhone
Pick one:

**Option A: update in place (keeps the user signed in).** This is the usual choice.
1. Connect and unlock the iPhone.
2. In Sideloadly, select the iPhone, your Apple ID and the **new** `PlanetWatch.ipa`.
3. Click **Start** and wait for **Done.**

The new version installs over the old one, because both are the same app
(`com.planetwatch.app`). Saved sign-in is kept, and you don't need to repeat section 6.

**Option B: clean replace (starts fresh).** Use this if the app misbehaves after an update,
or when giving the phone to a different person.
1. On the iPhone, press and hold the **PlanetWatch** icon → **Remove App** → **Delete App**
   → **Delete**. This also clears the saved sign-in.
2. Install the new version exactly as in [section 5](#5-install-the-app-on-the-iphone).
3. If iOS asks again, trust the Apple ID as in [section 6](#6-allow-the-app-to-open-one-time-per-iphone).

> **Use the same Apple ID** every time. Installing with a different Apple ID creates a
> separate signature, and iOS may refuse to update the existing app. If that happens, use
> Option B.

---

## 10. Removing the app

On the iPhone, press and hold the **PlanetWatch** icon → **Remove App** → **Delete App** →
**Delete**.

To also remove the trust: **Settings → General → VPN & Device Management** → your Apple ID →
**Delete App** / **Remove**.

---

## 11. Troubleshooting

| Problem | Fix |
| --- | --- |
| Install page still says *"iOS app not built yet"* | `mobile\dist\PlanetWatch.ipa` is missing or misnamed. Check the file is exactly `PlanetWatch.ipa` in `mobile\dist`. |
| Install page says the iPhone's USB driver is missing | Install iTunes from Apple's website (section 4), then reconnect the iPhone. |
| iPhone not listed in Sideloadly | Unlock the iPhone, tap **Trust**, try another cable or USB port, and restart Sideloadly. |
| Sideloadly: error about iTunes / iCloud | Install the Apple-website versions, not the Microsoft Store versions (section 4). |
| Sideloadly: *"maximum number of apps"* | A free Apple ID allows only 3 sideloaded apps at a time. Delete another sideloaded app from the iPhone and try again. |
| Sideloadly: *"maximum App ID limit"* | A free Apple ID can create 10 app IDs per week. Wait a few days, or use the same Apple ID and the same app as before. |
| *"Untrusted Developer"* when opening the app | Do section 6, step 1. |
| *"Developer Mode required"* | Do section 6, step 2. |
| App opens, but sign-in says it *"can't reach PlanetWatch"* | The server isn't running, the iPhone is on a different network, the firewall is blocking it (section 4, step 3), or the PC's address changed (section 7). |
| App keeps showing *"Location is required"* | **Settings → PlanetWatch → Location → While Using the App**, and make sure **Settings → Privacy & Security → Location Services** is on. |
| App says *"no longer available"* | The 7 days ran out. Renew it (section 8). |
| GitHub build shows a red ✗ | Open the run, click the failed step and copy the error to whoever maintains the project. |
