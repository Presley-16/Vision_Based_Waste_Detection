// Leaflet helpers shared by the Report page and the Live Map.
(function () {
  const PW = window.PW;
  const HARARE = [-17.8252, 31.0335];

  function createMap(element, options = {}) {
    const map = L.map(element, Object.assign({ zoomControl: true, attributionControl: true }, options))
      .setView(options.center || HARARE, options.zoom || 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);
    return map;
  }

  function statusIcon(status, extraClass) {
    return L.divIcon({
      className: 'pw-pin-wrap',
      html: '<div class="pw-pin status-' + PW.escapeHtml(status) + ' ' + (extraClass || '') + '"></div>',
      iconSize: [28, 28],
      iconAnchor: [14, 30],
      popupAnchor: [0, -30],
    });
  }

  const youIcon = L.divIcon({ className: '', html: '<div class="pw-you"></div>', iconSize: [18, 18], iconAnchor: [9, 9] });

  function statusLabel(status) {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  function popupHtml(report) {
    const waste = (report.waste_types && report.waste_types.length) ? report.waste_types.join(', ') : 'Unclassified';
    return (
      '<div class="pw-popup">' +
        '<img src="' + PW.escapeHtml(PW.assetUrl(report.image_url)) + '" alt="" onerror="this.remove();">' +
        '<strong>Report #' + report.id + '</strong>' +
        '<span>' + PW.escapeHtml(waste) + ' &middot; ' + PW.escapeHtml(PW.formatDate(report.submitted_at)) + '</span>' +
        '<span class="status-pill status-' + PW.escapeHtml(report.status) + '"><span class="status-dot"></span> ' + statusLabel(report.status) + '</span>' +
      '</div>'
    );
  }

  // GeoJSON feature (from /api/reports) -> flat report object.
  function fromFeature(feature) {
    return Object.assign({}, feature.properties, {
      latitude: feature.geometry.coordinates[1],
      longitude: feature.geometry.coordinates[0],
    });
  }

  PW.maps = { HARARE, createMap, statusIcon, youIcon, popupHtml, statusLabel, fromFeature };
})();
