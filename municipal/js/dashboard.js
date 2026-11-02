(function () {
  const MUNI = window.MUNI;
  const HARARE = [-17.8252, 31.0335];
  const REFRESH_MS = 30000;
  const STATUS_LABELS = { pending: 'Pending', reviewed: 'Reviewed', resolved: 'Solved' };

  const listEl = document.getElementById('reportList');
  const toast = document.getElementById('toast');
  let filter = 'all';
  let reports = [];
  let selectedId = null;
  let fittedOnce = false;
  let lastSnapshot = '';
  const markers = new Map();

  document.getElementById('muniUser').textContent = MUNI.getUser() ? 'Signed in as ' + MUNI.getUser() : '';
  document.getElementById('logoutBtn').addEventListener('click', () => MUNI.logout());

  // ---------- Map ----------

  const map = L.map('muniMap').setView(HARARE, 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map);

  function pinIcon(report) {
    return L.divIcon({
      className: 'pw-pin-wrap',
      html: '<div class="pw-pin status-' + MUNI.escapeHtml(report.status) + (report.id === selectedId ? ' is-selected' : '') + '"></div>',
      iconSize: [28, 28],
      iconAnchor: [14, 30],
      popupAnchor: [0, -30],
    });
  }

  function wasteLabel(report) {
    return report.waste_types.length ? report.waste_types.join(', ') : 'Unclassified';
  }

  function popupHtml(report) {
    return (
      '<div class="pw-popup">' +
        '<img src="' + MUNI.escapeHtml(MUNI.apiUrl(report.image_url)) + '" alt="" onerror="this.remove();">' +
        '<strong>Report #' + report.id + '</strong>' +
        '<span>' + MUNI.escapeHtml(wasteLabel(report)) + ' &middot; ' + MUNI.escapeHtml(MUNI.formatDate(report.submitted_at)) + '</span>' +
        '<span class="status-pill status-' + MUNI.escapeHtml(report.status) + '"><span class="status-dot"></span> ' + STATUS_LABELS[report.status] + '</span>' +
      '</div>'
    );
  }

  function renderMarkers() {
    markers.forEach((marker) => marker.remove());
    markers.clear();
    reports.forEach((report) => {
      const marker = L.marker([report.latitude, report.longitude], { icon: pinIcon(report) })
        .addTo(map)
        .bindPopup(popupHtml(report));
      marker.on('click', () => select(report.id, { fromMap: true }));
      markers.set(report.id, marker);
    });
    if (!fittedOnce && reports.length) {
      map.fitBounds(L.latLngBounds(reports.map((r) => [r.latitude, r.longitude])), { padding: [40, 40], maxZoom: 15 });
      fittedOnce = true;
    }
  }

  // ---------- List ----------

  const icons = {
    phone: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M6.6 10.8c1.4 2.8 3.8 5.2 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.9 21 3 13.1 3 3.9c0-.6.4-1 1-1h3.4c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.4 0 .8-.2 1L6.6 10.8z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    undo: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    trash: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function phoneFor(report) {
    const candidates = [report.reporter.phone, report.reporter.contact];
    for (const value of candidates) {
      const digits = (value || '').replace(/[^\d+]/g, '');
      if (digits.replace(/\D/g, '').length >= 7) return { display: value, dial: digits };
    }
    return null;
  }

  function cardHtml(report) {
    const phone = phoneFor(report);
    const solved = report.status === 'resolved';
    return (
      '<div class="muni-card-top">' +
        '<img class="muni-thumb" src="' + MUNI.escapeHtml(MUNI.apiUrl(report.image_url)) + '" alt="">' +
        '<div class="muni-card-info">' +
          '<strong>Report #' + report.id + ' &middot; ' + MUNI.escapeHtml(wasteLabel(report)) + '</strong>' +
          '<span class="muni-meta">Uploader: <b>' + MUNI.escapeHtml(report.reporter.name || 'Unknown') + '</b>' +
            (phone ? ' &middot; ' + MUNI.escapeHtml(phone.display) : '') + '</span>' +
          '<span class="muni-meta">' + MUNI.escapeHtml(MUNI.formatDate(report.submitted_at)) + ' &middot; ' +
            report.latitude.toFixed(5) + ', ' + report.longitude.toFixed(5) + '</span>' +
        '</div>' +
      '</div>' +
      '<span class="status-pill status-' + MUNI.escapeHtml(report.status) + '"><span class="status-dot"></span> ' + STATUS_LABELS[report.status] + '</span>' +
      '<div class="muni-actions">' +
        (phone
          ? '<a class="btn btn-ghost btn-sm" data-action="call" href="tel:' + MUNI.escapeHtml(phone.dial) + '">' + icons.phone + ' Call uploader</a>'
          : '<button type="button" class="btn btn-ghost btn-sm" disabled>' + icons.phone + ' No phone</button>') +
        (solved
          ? '<button type="button" class="btn btn-ghost btn-sm" data-action="reopen">' + icons.undo + ' Reopen</button>'
          : '<button type="button" class="btn btn-primary btn-sm" data-action="solve">' + icons.check + ' Mark solved</button>') +
        '<button type="button" class="btn btn-danger btn-sm" data-action="delete">' + icons.trash + ' Delete</button>' +
      '</div>'
    );
  }

  function renderList() {
    if (!reports.length) {
      const empty = { all: 'No reports yet.', pending: 'Nothing pending — every flagged site is solved.', solved: 'No solved reports yet.' };
      listEl.innerHTML = '<div class="muni-empty">' + empty[filter] + '</div>';
      return;
    }
    listEl.innerHTML = '';
    reports.forEach((report) => {
      const card = document.createElement('div');
      card.className = 'muni-card' + (report.id === selectedId ? ' is-selected' : '');
      card.dataset.id = report.id;
      card.innerHTML = cardHtml(report);
      card.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]');
        if (action) {
          if (action.dataset.action !== 'call') event.stopPropagation();
          handleAction(action.dataset.action, report, card);
          return;
        }
        select(report.id);
      });
      listEl.appendChild(card);
    });
  }

  function select(id, options = {}) {
    selectedId = id;
    const report = reports.find((r) => r.id === id);
    listEl.querySelectorAll('.muni-card').forEach((card) => card.classList.toggle('is-selected', Number(card.dataset.id) === id));
    markers.forEach((marker, reportId) => marker.setIcon(pinIcon(reports.find((r) => r.id === reportId))));
    if (!report) return;
    if (options.fromMap) {
      const card = listEl.querySelector('[data-id="' + id + '"]');
      if (card) card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      map.flyTo([report.latitude, report.longitude], 17, { duration: 0.8 });
      setTimeout(() => markers.get(id) && markers.get(id).openPopup(), 850);
    }
  }

  // ---------- Data ----------

  async function load() {
    try {
      const data = await MUNI.request('/api/municipal/reports?status=' + filter);
      Object.entries(data.counts).forEach(([key, value]) => {
        document.querySelector('[data-count="' + key + '"]').textContent = value;
      });
      // Auto-refresh shouldn't replay the pin-drop animation when nothing changed.
      const snapshot = filter + JSON.stringify(data.reports);
      if (snapshot !== lastSnapshot) {
        lastSnapshot = snapshot;
        reports = data.reports;
        renderMarkers();
        renderList();
      }
      document.getElementById('lastUpdated').textContent =
        'Updated ' + new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' · refreshes every 30 seconds';
    } catch (error) {
      if (error.status === 401) {
        MUNI.logout();
        return;
      }
      document.getElementById('lastUpdated').textContent = error.message;
    }
  }

  function showToast(text) {
    toast.textContent = text;
    toast.classList.add('is-visible');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove('is-visible'), 2400);
  }

  function confirmDelete(report) {
    return new Promise((resolve) => {
      const overlay = document.createElement('div');
      overlay.className = 'ripple-popup-overlay';
      overlay.innerHTML =
        '<div class="confirm-card" role="alertdialog" aria-modal="true">' +
          '<h3>Delete report #' + report.id + '?</h3>' +
          '<p>The photo and its pin are removed permanently. The uploader won\'t be notified.</p>' +
          '<div class="confirm-actions">' +
            '<button type="button" class="btn btn-ghost" data-answer="no">Cancel</button>' +
            '<button type="button" class="btn btn-danger" data-answer="yes">Delete</button>' +
          '</div>' +
        '</div>';
      function close(answer) {
        overlay.classList.add('is-settling');
        setTimeout(() => overlay.remove(), 700);
        resolve(answer);
      }
      overlay.addEventListener('click', (event) => {
        const button = event.target.closest('[data-answer]');
        if (button) close(button.dataset.answer === 'yes');
        else if (event.target === overlay) close(false);
      });
      document.body.appendChild(overlay);
      overlay.querySelector('[data-answer="no"]').focus();
    });
  }

  async function handleAction(action, report, card) {
    if (action === 'call') return; // the tel: link opens the dialler

    if (action === 'delete') {
      if (!(await confirmDelete(report))) return;
      try {
        await MUNI.request('/api/municipal/reports/' + report.id, { method: 'DELETE' });
        card.classList.add('is-leaving');
        showToast('Report #' + report.id + ' deleted');
        setTimeout(load, 450);
      } catch (error) {
        showToast(error.message);
      }
      return;
    }

    const status = action === 'solve' ? 'solved' : 'pending';
    try {
      await MUNI.request('/api/municipal/reports/' + report.id, { method: 'PATCH', body: { status } });
      showToast('Report #' + report.id + (status === 'solved' ? ' marked solved' : ' reopened'));
      load();
    } catch (error) {
      showToast(error.message);
    }
  }

  // ---------- Filters ----------

  document.querySelectorAll('.muni-stat').forEach((tab) => {
    tab.addEventListener('click', () => {
      filter = tab.dataset.filter;
      document.querySelectorAll('.muni-stat').forEach((t) => {
        const active = t === tab;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-selected', String(active));
      });
      fittedOnce = false;
      load();
    });
  });

  document.getElementById('refreshBtn').addEventListener('click', load);
  setInterval(() => {
    if (document.visibilityState === 'visible') load();
  }, REFRESH_MS);

  load();
})();
