(function () {
  const PW = window.PW;
  const statusEl = document.getElementById('location-status');
  const coordsEl = document.getElementById('pinCoords');
  const form = document.getElementById('reportForm');
  const submitBtn = document.getElementById('submitBtn');
  const errorBox = document.getElementById('errorBox');
  const successBox = document.getElementById('successBox');
  const grid = document.getElementById('photoGrid');
  const dropzone = document.getElementById('dropzone');
  const contactInput = document.getElementById('contact');

  const pinSvg = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 21s-7-5.1-7-11a7 7 0 0 1 14 0c0 5.9-7 11-7 11z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="10" r="2.4" stroke="currentColor" stroke-width="2"/></svg>';

  // Each photo carries the location that was pinned at the moment it was added.
  let photos = [];
  let submitting = false;

  PW.ready.then((citizen) => {
    if (!citizen) return;
    const pill = document.getElementById('reportingAs');
    pill.querySelector('[data-name]').textContent = citizen.name + ' ' + citizen.surname;
    pill.querySelector('[data-logout]').addEventListener('click', (event) => {
      event.preventDefault();
      PW.logout();
    });
    pill.hidden = false;
    if (!contactInput.value) contactInput.value = citizen.phone || '';
    loadMyPins();
  });

  // ---------- Pinned-location map ----------

  const map = PW.maps.createMap(document.getElementById('pinMap'), { zoom: 13 });
  let youMarker = null;
  let accuracyCircle = null;
  let centred = false;

  function setLocationStatus(state, text) {
    statusEl.className = 'location-pill' + (state ? ' ' + state : '');
    statusEl.innerHTML = '<span class="dot"></span> ' + text;
  }

  function formatCoords(lat, lng) {
    return lat.toFixed(5) + ', ' + lng.toFixed(5);
  }

  PW.location.subscribe((fix) => {
    if (!fix) {
      setLocationStatus('warn', 'Location is off — switch it on to pin your report.');
      coordsEl.textContent = 'No location fix';
      updateSubmit();
      return;
    }
    const latLng = [fix.lat, fix.lng];
    if (!youMarker) {
      youMarker = L.marker(latLng, { icon: PW.maps.youIcon, zIndexOffset: 1000 }).addTo(map).bindTooltip('You are here');
      accuracyCircle = L.circle(latLng, { radius: fix.accuracy, color: '#2563eb', weight: 1, fillOpacity: 0.08 }).addTo(map);
    } else {
      youMarker.setLatLng(latLng);
      accuracyCircle.setLatLng(latLng).setRadius(fix.accuracy);
    }
    if (!centred) {
      map.setView(latLng, 17);
      centred = true;
    }
    setLocationStatus('ok', 'Location pinned — photos will be tagged here.');
    coordsEl.innerHTML = 'Pinned at <strong>' + formatCoords(fix.lat, fix.lng) + '</strong> &middot; &plusmn;' + Math.round(fix.accuracy) + ' m';
    updateSubmit();
  });

  function addReportPin(report) {
    return L.marker([report.latitude, report.longitude], { icon: PW.maps.statusIcon(report.status) })
      .addTo(map)
      .bindPopup(PW.maps.popupHtml(report));
  }

  function loadMyPins() {
    PW.request('/api/me/reports').then((data) => {
      data.reports.filter((r) => r.latitude != null).forEach((r) => addReportPin(r));
    }).catch(() => {});
  }

  // ---------- Photos ----------

  function renderPhotos() {
    grid.innerHTML = '';
    photos.forEach((photo, index) => {
      const thumb = document.createElement('div');
      thumb.className = 'photo-thumb';
      thumb.innerHTML =
        '<img alt="">' +
        '<button type="button" class="photo-remove" aria-label="Remove photo">&times;</button>' +
        '<span class="photo-pin">' + pinSvg + formatCoords(photo.lat, photo.lng) + '</span>';
      thumb.querySelector('img').src = photo.url;
      thumb.querySelector('.photo-remove').addEventListener('click', () => {
        URL.revokeObjectURL(photo.url);
        photos.splice(index, 1);
        renderPhotos();
      });
      grid.appendChild(thumb);
    });
    updateSubmit();
  }

  // `takenAt` is only known for camera shots; uploads keep the time in their own EXIF.
  function addFiles(fileList, takenAt) {
    const fix = PW.location.current;
    if (!fix) {
      showError('Waiting for your location — photos can only be added once your position is pinned.');
      return;
    }
    hideMessages();
    Array.from(fileList).filter((file) => file.type.startsWith('image/') || /\.(jpe?g|png|heic)$/i.test(file.name)).forEach((file) => {
      photos.push({ file, url: URL.createObjectURL(file), lat: fix.lat, lng: fix.lng, takenAt: takenAt || null });
    });
    renderPhotos();
  }

  const photoInput = document.getElementById('photo');
  photoInput.addEventListener('change', () => {
    addFiles(photoInput.files);
    photoInput.value = '';
  });

  // Native camera fallback (phones on plain http, where a live camera isn't allowed).
  const cameraInput = document.getElementById('cameraInput');
  cameraInput.addEventListener('change', () => {
    addFiles(cameraInput.files, new Date());
    cameraInput.value = '';
  });

  document.getElementById('cameraBtn').addEventListener('click', async () => {
    if (!PW.location.current) {
      showError('Waiting for your location — photos can only be taken once your position is pinned.');
      return;
    }
    if (!PW.camera.supported()) {
      cameraInput.click();
      return;
    }
    const shot = await PW.camera.open();
    if (!shot) return;
    hideMessages();
    photos.push({ file: shot.file, url: URL.createObjectURL(shot.file), lat: shot.fix.lat, lng: shot.fix.lng, takenAt: shot.takenAt });
    renderPhotos();
  });

  ['dragenter', 'dragover'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-active');
    });
  });

  ['dragleave', 'drop'].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-active');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  });

  function updateSubmit() {
    submitBtn.disabled = submitting || !photos.length || !PW.location.current;
    if (!submitting) {
      submitBtn.textContent = photos.length > 1 ? 'Submit ' + photos.length + ' Photos' : 'Submit Report';
    }
  }

  // ---------- Submit ----------

  function hideMessages() {
    errorBox.hidden = true;
    successBox.hidden = true;
  }

  function showError(message) {
    errorBox.querySelector('[data-error-text]').textContent = message;
    errorBox.hidden = false;
    successBox.hidden = true;
  }

  function showSuccess(reports) {
    const detections = [];
    reports.forEach((r) => r.detections.forEach((d) => detections.push(d)));
    const body = successBox.querySelector('[data-success-body]');
    successBox.querySelector('[data-success-title]').textContent = reports.length > 1
      ? 'Thanks — ' + reports.length + ' photos were submitted and pinned.'
      : 'Thanks — your report was submitted.';
    if (detections.length) {
      body.innerHTML = '<p>Detected waste types:</p><ul class="detection-list">' +
        detections.map((d) => '<li>' + PW.escapeHtml(d.waste_type) + ' &middot; ' + (d.confidence * 100).toFixed(1) + '%</li>').join('') +
        '</ul>';
    } else {
      body.innerHTML = '<p>No waste detected automatically — it will still be reviewed manually.</p>';
    }
    successBox.hidden = false;
    errorBox.hidden = true;
  }

  function showRipplePopup() {
    const popup = document.createElement('div');
    popup.className = 'ripple-popup-overlay';
    popup.innerHTML =
      '<div class="ripple-rings"><span></span><span></span><span></span></div>' +
      '<div class="ripple-popup-card">' +
        '<img class="popup-cheer-img" src="img/cheer2.jpg" alt="" onerror="this.remove();">' +
        '<div class="popup-check"><img src="img/icons/success.png" alt=""></div>' +
        '<p>Thanks &mdash; your report was submitted</p>' +
      '</div>';
    document.body.appendChild(popup);
    setTimeout(() => {
      popup.classList.add('is-settling');
      setTimeout(() => popup.remove(), 700);
    }, 4000);
  }

  // Shown when the model finds no waste: the photo isn't submitted. Stays until closed.
  function showRejectPopup(rejectedCount, submittedCount) {
    const title = submittedCount
      ? rejectedCount + (rejectedCount === 1 ? ' photo was' : ' photos were') + ' not submitted'
      : (rejectedCount === 1 ? 'Photo not submitted' : 'Photos not submitted');
    const text = submittedCount
      ? 'No waste was detected in ' + (rejectedCount === 1 ? 'it' : 'them') + '. The other ' +
        (submittedCount === 1 ? 'photo was' : submittedCount + ' photos were') + ' submitted.'
      : 'No waste, litter or garbage was detected. Take a clearer photo that shows the dumped waste and try again.';
    const popup = document.createElement('div');
    popup.className = 'ripple-popup-overlay reject-popup';
    popup.setAttribute('role', 'alertdialog');
    popup.innerHTML =
      '<div class="ripple-rings"><span></span><span></span><span></span></div>' +
      '<div class="ripple-popup-card">' +
        '<button type="button" class="popup-close" aria-label="Close">&times;</button>' +
        '<img class="popup-reject-img" src="img/icons/decline.png" alt="">' +
        '<p>' + title + '</p>' +
        '<span class="popup-reject-text">' + text + '</span>' +
      '</div>';
    document.body.appendChild(popup);

    function close() {
      document.removeEventListener('keydown', onKey);
      popup.classList.add('is-settling');
      setTimeout(() => popup.remove(), 700);
    }
    function onKey(event) {
      if (event.key === 'Escape') close();
    }
    document.addEventListener('keydown', onKey);
    popup.querySelector('.popup-close').addEventListener('click', close);
    popup.addEventListener('click', (event) => {
      if (event.target === popup) close();
    });
    popup.querySelector('.popup-close').focus();
  }

  function clearPhotos() {
    photos.forEach((photo) => URL.revokeObjectURL(photo.url));
    photos = [];
    renderPhotos();
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!photos.length || !PW.location.current) return;

    const body = new FormData();
    photos.forEach((photo) => {
      body.append('photos', photo.file, photo.file.name);
      body.append('latitude', photo.lat);
      body.append('longitude', photo.lng);
      body.append('captured_at', photo.takenAt ? PW.camera.exifDate(photo.takenAt) : '');
    });
    body.append('contact', contactInput.value);

    submitting = true;
    hideMessages();
    submitBtn.disabled = true;
    submitBtn.classList.add('is-loading');
    submitBtn.textContent = 'Analysing photos…';

    try {
      const data = await PW.request('/api/reports', { method: 'POST', body });
      data.reports.forEach((report) => addReportPin(report));
      clearPhotos();
      showSuccess(data.reports);
      const rejected = (data.rejected || []).length;
      if (rejected) showRejectPopup(rejected, data.reports.length);
      else showRipplePopup();
    } catch (error) {
      if (error.status === 401) {
        PW.redirectToLogin();
        return;
      }
      if (error.status === 422 && error.data && error.data.rejected) {
        clearPhotos();
        showRejectPopup(error.data.rejected.length, 0);
        return;
      }
      showError(error.message);
    } finally {
      submitting = false;
      submitBtn.classList.remove('is-loading');
      updateSubmit();
    }
  });
})();
