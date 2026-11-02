(function () {
  const PW = window.PW;
  const map = PW.maps.createMap(document.getElementById('liveMap'));
  const markers = new Map(); // report id -> Leaflet marker
  const myReportsEl = document.getElementById('myReports');

  PW.request('/api/reports').then((data) => {
    const reports = data.features.map(PW.maps.fromFeature);
    const count = reports.length;
    document.getElementById('reportCount').textContent = count + ' report' + (count === 1 ? '' : 's') + ' tracked';

    reports.forEach((report) => {
      const marker = L.marker([report.latitude, report.longitude], { icon: PW.maps.statusIcon(report.status) })
        .addTo(map)
        .bindPopup(PW.maps.popupHtml(report));
      markers.set(report.id, marker);
    });

    if (reports.length) {
      map.fitBounds(L.latLngBounds(reports.map((r) => [r.latitude, r.longitude])), { padding: [40, 40], maxZoom: 15 });
    }
  }).catch((error) => {
    document.getElementById('reportCount').textContent = error.message;
  });

  // Show the citizen's own position alongside the reports.
  let youMarker = null;
  PW.location.subscribe((fix) => {
    if (!fix) return;
    if (!youMarker) {
      youMarker = L.marker([fix.lat, fix.lng], { icon: PW.maps.youIcon, zIndexOffset: 1000 }).addTo(map).bindTooltip('You are here');
    } else {
      youMarker.setLatLng([fix.lat, fix.lng]);
    }
  });

  function focusReport(report) {
    const marker = markers.get(report.id);
    map.flyTo([report.latitude, report.longitude], 17, { duration: 0.8 });
    if (marker) setTimeout(() => marker.openPopup(), 850);
    document.getElementById('liveMap').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  PW.ready.then((citizen) => {
    if (!citizen) {
      myReportsEl.innerHTML =
        '<div class="login-prompt-card">' +
          "<p>Log in to see the reports you've submitted and follow their status.</p>" +
          '<a class="btn btn-primary" href="login.html?mode=signin&next=map.html">Log In</a>' +
        '</div>';
      return;
    }

    document.getElementById('myReportsTitle').textContent = 'Reports from ' + citizen.name + ' ' + citizen.surname;

    PW.request('/api/me/reports').then((data) => {
      if (!data.reports.length) {
        myReportsEl.innerHTML =
          '<div class="login-prompt-card">' +
            "<p>You haven't submitted any reports yet.</p>" +
            '<a class="btn btn-primary" href="report.html">Report Illegal Dumping</a>' +
          '</div>';
        return;
      }

      const list = document.createElement('div');
      list.className = 'my-reports-list';
      data.reports.forEach((report) => {
        const waste = report.waste_types.length ? report.waste_types.join(', ') : 'Unclassified';
        const card = document.createElement('div');
        card.className = 'my-report-card' + (report.latitude != null ? ' is-clickable' : '');
        card.innerHTML =
          '<div class="my-report-main">' +
            '<img class="my-report-thumb" src="' + PW.escapeHtml(PW.assetUrl(report.image_url)) + '" alt="">' +
            '<div class="my-report-info">' +
              '<strong>Report #' + report.id + ' &middot; ' + PW.escapeHtml(waste) + '</strong>' +
              '<span>Submitted ' + PW.escapeHtml(PW.formatDate(report.submitted_at)) + '</span>' +
            '</div>' +
          '</div>' +
          '<span class="status-pill status-' + PW.escapeHtml(report.status) + '">' +
            '<span class="status-dot"></span> ' + PW.maps.statusLabel(report.status) +
          '</span>';
        if (report.latitude != null) card.addEventListener('click', () => focusReport(report));
        list.appendChild(card);
      });
      myReportsEl.innerHTML = '';
      myReportsEl.appendChild(list);
    }).catch((error) => {
      myReportsEl.innerHTML = '<div class="login-prompt-card"><p>' + PW.escapeHtml(error.message) + '</p></div>';
    });
  });
})();
