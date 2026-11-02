(function () {
  const PW = window.PW;
  if (PW.isApp) return; // layout.js already redirected to the Share page

  const qrOption = document.getElementById('qrOption');
  const usbOption = document.getElementById('usbOption');
  const qrStatus = document.getElementById('qrStatus');
  const usbStatus = document.getElementById('usbStatus');
  const installBtn = document.getElementById('usbInstallBtn');

  // Ties the QR on this screen to the phone that scans it, so the green check
  // only appears for *this* visitor's phone.
  const sessionId = Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, '0')).join('');

  function setPill(el, state, html) {
    el.className = 'location-pill install-status' + (state ? ' ' + state : '');
    el.innerHTML = '<span class="dot"></span> ' + html;
  }

  // ---------- QR ----------

  PW.request('/api/install/info?session=' + sessionId).then((info) => {
    document.getElementById('qrBox').innerHTML = info.qr_svg;
    const link = document.getElementById('qrLink');
    link.href = info.page_url;
    link.textContent = info.page_url;
    document.getElementById('apkMissing').hidden = info.apk_available;
    pollQr();
  }).catch((error) => {
    setPill(qrStatus, 'warn', PW.escapeHtml(error.message));
  });

  function pollQr() {
    PW.request('/api/install/status?session=' + sessionId).then((status) => {
      if (status.qr.scanned) {
        qrOption.classList.add('is-connected');
        const device = { android: 'Android phone', ios: 'iPhone' }[status.qr.platform] || 'Phone';
        setPill(qrStatus, 'ok', status.qr.downloaded
          ? device + ' connected — download started'
          : device + ' connected — follow the steps on your phone');
      }
      if (!status.qr.downloaded) setTimeout(pollQr, 2000);
    }).catch(() => setTimeout(pollQr, 4000));
  }

  // ---------- USB ----------

  let readyDevice = null;
  let installing = false;
  let installed = false;

  // Returns whether polling should continue.
  function renderUsb(data) {
    if (installed) return false;
    readyDevice = null;
    usbOption.classList.remove('is-connected');

    if (!data.supported) {
      const reasons = {
        remote: 'Cable install works on the computer running PlanetWatch — open this page there, or use the QR code.',
        'no-adb': 'Android platform-tools (adb) isn\'t installed on this computer — use the QR code instead.',
        'adb-error': 'Couldn\'t talk to adb on this computer — reconnect the cable and try again.',
      };
      setPill(usbStatus, 'warn', reasons[data.reason] || 'Cable install isn\'t available here.');
      installBtn.disabled = true;
      return data.reason === 'adb-error';
    }

    const devices = data.devices || [];
    const ready = devices.find((d) => d.state === 'device');
    const unauthorised = devices.find((d) => d.state === 'unauthorized');

    if (ready) {
      readyDevice = ready;
      usbOption.classList.add('is-connected');
      setPill(usbStatus, 'ok', PW.escapeHtml(ready.model || 'Android phone') + ' connected');
    } else if (unauthorised) {
      setPill(usbStatus, 'waiting', 'Phone found — tap <strong>Allow</strong> on your phone');
    } else {
      setPill(usbStatus, 'waiting', 'Waiting for your phone&hellip; connect the cable');
    }
    installBtn.disabled = installing || !readyDevice || !data.apk_available;
    return true;
  }

  function pollUsb() {
    PW.request('/api/install/usb').then(renderUsb).catch((error) => {
      if (error.status === 403) return renderUsb(error.data || { supported: false, reason: 'remote' });
      return true;
    }).then((keepPolling) => {
      if (keepPolling !== false && !installed) setTimeout(pollUsb, 2000);
    });
  }

  installBtn.addEventListener('click', async () => {
    if (!readyDevice) return;
    installing = true;
    installBtn.disabled = true;
    installBtn.classList.add('is-loading');
    installBtn.textContent = 'Installing on your phone…';
    try {
      await PW.request('/api/install/usb/install', { method: 'POST', body: { serial: readyDevice.serial } });
      setPill(usbStatus, 'ok', 'Installed! Open <strong>PlanetWatch</strong> on your phone.');
      installBtn.textContent = 'Installed';
      installed = true;
    } catch (error) {
      setPill(usbStatus, 'warn', PW.escapeHtml(error.message));
      installBtn.textContent = 'Try again';
      installBtn.disabled = false;
      installing = false;
    } finally {
      installBtn.classList.remove('is-loading');
    }
  });

  pollUsb();
})();
