/* In-page camera + EXIF tagging.
 *
 * PW.camera.open() shows a live camera, and resolves with { file, fix, takenAt } once the
 * user accepts a shot (null if they close it). The file is a JPEG whose EXIF carries
 * the pinned GPS position and the capture time, exactly like a photo from a phone
 * camera, so the backend reads it the same way as an uploaded photo.
 *
 * A live camera needs a secure context (https, localhost or the installed app). Where
 * it isn't available, PW.camera.supported() is false and the caller falls back to the
 * native camera via <input capture>.
 */
(function () {
  const PW = window.PW = window.PW || {};
  const encoder = new TextEncoder();

  // ---------- EXIF (TIFF, big-endian) ----------

  const TYPE = { BYTE: 1, ASCII: 2, LONG: 4, RATIONAL: 5 };
  const TYPE_SIZE = { 1: 1, 2: 1, 4: 4, 5: 8 };

  function ascii(text) { return encoder.encode(text + '\0'); }

  function long(value) {
    const bytes = new Uint8Array(4);
    new DataView(bytes.buffer).setUint32(0, value);
    return bytes;
  }

  function rationals(pairs) {
    const bytes = new Uint8Array(pairs.length * 8);
    const view = new DataView(bytes.buffer);
    pairs.forEach(([num, den], i) => {
      view.setUint32(i * 8, num);
      view.setUint32(i * 8 + 4, den);
    });
    return bytes;
  }

  // One IFD followed by its out-of-line values; `offset` is where it sits in the TIFF.
  function ifd(entries, offset) {
    entries.sort((a, b) => a[0] - b[0]);
    const head = 2 + entries.length * 12 + 4;
    const extra = entries.reduce((n, [, , bytes]) => n + (bytes.length > 4 ? bytes.length + (bytes.length % 2) : 0), 0);
    const out = new Uint8Array(head + extra);
    const view = new DataView(out.buffer);
    view.setUint16(0, entries.length);
    let data = head;
    entries.forEach(([tag, type, bytes], i) => {
      const p = 2 + i * 12;
      view.setUint16(p, tag);
      view.setUint16(p + 2, type);
      view.setUint32(p + 4, bytes.length / TYPE_SIZE[type]);
      if (bytes.length <= 4) {
        out.set(bytes, p + 8);
      } else {
        view.setUint32(p + 8, offset + data);
        out.set(bytes, data);
        data += bytes.length + (bytes.length % 2);
      }
    });
    return out;
  }

  const pad = (n) => String(n).padStart(2, '0');

  function exifDate(date) {
    return date.getFullYear() + ':' + pad(date.getMonth() + 1) + ':' + pad(date.getDate()) + ' ' +
      pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds());
  }

  function utcOffset(date) {
    const minutes = -date.getTimezoneOffset();
    const sign = minutes >= 0 ? '+' : '-';
    return sign + pad(Math.floor(Math.abs(minutes) / 60)) + ':' + pad(Math.abs(minutes) % 60);
  }

  function dms(value) {
    const abs = Math.abs(value);
    const degrees = Math.floor(abs);
    const minutesFull = (abs - degrees) * 60;
    const minutes = Math.floor(minutesFull);
    return [[degrees, 1], [minutes, 1], [Math.round((minutesFull - minutes) * 60 * 10000), 10000]];
  }

  function tiff(fix, date) {
    const local = exifDate(date);
    const ifd0 = (exifAt, gpsAt) => [
      [0x0131, TYPE.ASCII, ascii('PlanetWatch')],
      [0x0132, TYPE.ASCII, ascii(local)],
      [0x8769, TYPE.LONG, long(exifAt)],
      [0x8825, TYPE.LONG, long(gpsAt)],
    ];
    const exifAt = 8 + ifd(ifd0(0, 0), 8).length;
    const exifBlock = ifd([
      [0x9003, TYPE.ASCII, ascii(local)],          // DateTimeOriginal
      [0x9004, TYPE.ASCII, ascii(local)],          // DateTimeDigitized
      [0x9011, TYPE.ASCII, ascii(utcOffset(date))], // OffsetTimeOriginal
    ], exifAt);

    const gpsAt = exifAt + exifBlock.length;
    const gpsEntries = [
      [0x0000, TYPE.BYTE, new Uint8Array([2, 3, 0, 0])],
      [0x0001, TYPE.ASCII, ascii(fix.lat < 0 ? 'S' : 'N')],
      [0x0002, TYPE.RATIONAL, rationals(dms(fix.lat))],
      [0x0003, TYPE.ASCII, ascii(fix.lng < 0 ? 'W' : 'E')],
      [0x0004, TYPE.RATIONAL, rationals(dms(fix.lng))],
      [0x0007, TYPE.RATIONAL, rationals([[date.getUTCHours(), 1], [date.getUTCMinutes(), 1], [date.getUTCSeconds(), 1]])],
      [0x001D, TYPE.ASCII, ascii(date.getUTCFullYear() + ':' + pad(date.getUTCMonth() + 1) + ':' + pad(date.getUTCDate()))],
    ];
    if (fix.accuracy) gpsEntries.push([0x001F, TYPE.RATIONAL, rationals([[Math.round(fix.accuracy * 100), 100]])]);
    const gpsBlock = ifd(gpsEntries, gpsAt);

    const ifd0Block = ifd(ifd0(exifAt, gpsAt), 8);
    const out = new Uint8Array(8 + ifd0Block.length + exifBlock.length + gpsBlock.length);
    out.set([0x4D, 0x4D, 0x00, 0x2A, 0x00, 0x00, 0x00, 0x08]);
    out.set(ifd0Block, 8);
    out.set(exifBlock, exifAt);
    out.set(gpsBlock, gpsAt);
    return out;
  }

  // Insert an EXIF APP1 segment (GPS + capture time) into a JPEG blob.
  async function tagJpeg(blob, fix, date) {
    const jpeg = new Uint8Array(await blob.arrayBuffer());
    if (jpeg[0] !== 0xFF || jpeg[1] !== 0xD8) return blob;
    let at = 2;
    if (jpeg[2] === 0xFF && jpeg[3] === 0xE0) at = 4 + ((jpeg[4] << 8) | jpeg[5]); // keep JFIF first
    const body = tiff(fix, date);
    const length = 2 + 6 + body.length;
    const app1 = new Uint8Array(4 + 6 + body.length);
    app1.set([0xFF, 0xE1, length >> 8, length & 0xFF]);
    app1.set(encoder.encode('Exif\0\0'), 4);
    app1.set(body, 10);
    return new Blob([jpeg.slice(0, at), app1, jpeg.slice(at)], { type: 'image/jpeg' });
  }

  // ---------- Live camera ----------

  const icons = {
    close: '<svg viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    flip: '<svg viewBox="0 0 24 24" fill="none"><path d="M4 9a8 8 0 0 1 14-3l2 2M20 15a8 8 0 0 1-14 3l-2-2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 4v4h-4M4 20v-4h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function supported() {
    return !!(window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  function cameraError(error) {
    if (error && error.name === 'NotAllowedError') {
      return 'Camera access was blocked. Allow the camera for this site in your browser settings, then try again.';
    }
    if (error && (error.name === 'NotFoundError' || error.name === 'OverconstrainedError')) {
      return 'No camera was found on this device.';
    }
    if (error && error.name === 'NotReadableError') {
      return 'The camera is being used by another app. Close it and try again.';
    }
    return 'The camera could not be started.';
  }

  function open() {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'camera-modal';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-label', 'Take a photo');
      overlay.innerHTML =
        '<div class="camera-card">' +
          '<div class="camera-stage">' +
            '<video playsinline muted autoplay></video>' +
            '<canvas hidden></canvas>' +
            '<div class="camera-flash"></div>' +
            '<p class="camera-message" data-message>Starting camera&hellip;</p>' +
            '<span class="camera-pin" data-pin hidden></span>' +
          '</div>' +
          '<div class="camera-controls" data-live>' +
            '<button type="button" class="camera-icon-btn" data-close aria-label="Close camera">' + icons.close + '</button>' +
            '<button type="button" class="camera-shutter" data-shutter aria-label="Take photo" disabled><span></span></button>' +
            '<button type="button" class="camera-icon-btn" data-flip aria-label="Switch camera" hidden>' + icons.flip + '</button>' +
          '</div>' +
          '<div class="camera-controls" data-review hidden>' +
            '<button type="button" class="btn btn-ghost" data-retake>Retake</button>' +
            '<button type="button" class="btn btn-primary" data-use>Use photo</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(overlay);
      document.body.classList.add('camera-open');

      const video = overlay.querySelector('video');
      const canvas = overlay.querySelector('canvas');
      const message = overlay.querySelector('[data-message]');
      const pin = overlay.querySelector('[data-pin]');
      const shutter = overlay.querySelector('[data-shutter]');
      const flip = overlay.querySelector('[data-flip]');
      const live = overlay.querySelector('[data-live]');
      const review = overlay.querySelector('[data-review]');

      let stream = null;
      let facing = 'environment';
      let shot = null;

      function stop() {
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = null;
      }

      function finish(result) {
        stop();
        document.removeEventListener('keydown', onKey);
        document.body.classList.remove('camera-open');
        overlay.classList.add('is-closing');
        setTimeout(() => overlay.remove(), 250);
        resolve(result);
      }

      function onKey(event) {
        if (event.key === 'Escape') finish(null);
      }
      document.addEventListener('keydown', onKey);

      async function start() {
        stop();
        shutter.disabled = true;
        message.hidden = false;
        message.textContent = 'Starting camera…';
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } },
            audio: false,
          });
          video.srcObject = stream;
          await video.play();
          message.hidden = true;
          shutter.disabled = false;
          const devices = await navigator.mediaDevices.enumerateDevices();
          flip.hidden = devices.filter((d) => d.kind === 'videoinput').length < 2;
        } catch (error) {
          message.textContent = cameraError(error);
        }
      }

      function showLive() {
        shot = null;
        canvas.hidden = true;
        video.hidden = false;
        pin.hidden = true;
        review.hidden = true;
        live.hidden = false;
      }

      shutter.addEventListener('click', () => {
        const fix = PW.location && PW.location.current;
        if (!fix) {
          message.hidden = false;
          message.textContent = 'Waiting for your location — the photo can only be taken once you are pinned.';
          return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        shot = { fix: { lat: fix.lat, lng: fix.lng, accuracy: fix.accuracy }, takenAt: new Date() };
        overlay.classList.remove('is-flashing');
        void overlay.offsetWidth;
        overlay.classList.add('is-flashing');
        video.hidden = true;
        canvas.hidden = false;
        pin.textContent = shot.fix.lat.toFixed(5) + ', ' + shot.fix.lng.toFixed(5) + ' · ' + shot.takenAt.toLocaleTimeString();
        pin.hidden = false;
        live.hidden = true;
        review.hidden = false;
      });

      overlay.querySelector('[data-retake]').addEventListener('click', showLive);

      overlay.querySelector('[data-use]').addEventListener('click', () => {
        const { fix, takenAt } = shot;
        canvas.toBlob(async (blob) => {
          if (!blob) return finish(null);
          const tagged = await tagJpeg(blob, fix, takenAt);
          const stamp = exifDate(takenAt).replace(/:/g, '').replace(' ', '-');
          finish({ file: new File([tagged], 'camera-' + stamp + '.jpg', { type: 'image/jpeg' }), fix, takenAt });
        }, 'image/jpeg', 0.92);
      });

      flip.addEventListener('click', () => {
        facing = facing === 'environment' ? 'user' : 'environment';
        start();
      });

      overlay.querySelector('[data-close]').addEventListener('click', () => finish(null));

      start();
    });
  }

  PW.camera = { supported, open, tagJpeg, exifDate };
})();
