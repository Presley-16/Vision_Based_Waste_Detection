// Mandatory device location for signed-in citizens.
//
// While a citizen is signed in, PlanetWatch keeps a live location fix. If
// location is switched off, blocked, or unavailable, a blocking popup insists
// it be turned on before the app can be used — it only goes away once a fix
// arrives. Pages read the fix via PW.location.current / PW.location.subscribe.
(function () {
  const PW = window.PW;
  const listeners = new Set();
  let watchId = null;
  let gate = null;

  const location_ = {
    current: null,
    subscribe(fn) {
      listeners.add(fn);
      if (location_.current) fn(location_.current);
      return () => listeners.delete(fn);
    },
  };
  PW.location = location_;

  const active = document.body.dataset.location === 'required' && Boolean(PW.getToken());
  if (!active) return;

  function messageFor(error) {
    if (!navigator.geolocation) {
      return 'This browser cannot share your location. Open PlanetWatch in an up-to-date browser or install the app.';
    }
    if (!window.isSecureContext) {
      return 'Your browser only shares location over a secure (https) connection. Ask your administrator for the https address of PlanetWatch, or install the app.';
    }
    if (error && error.code === 1) {
      return 'Location permission is blocked for PlanetWatch. Allow location access in your browser or phone settings, then tap “Turn on location”.';
    }
    if (error && error.code === 3) {
      return "We couldn't get a location fix in time. Move somewhere with a clearer view of the sky and make sure Location is on.";
    }
    return 'Your device location is switched off. Swipe down from the top of your screen, turn on Location (GPS), then tap “Turn on location”.';
  }

  function showGate(error) {
    const text = messageFor(error);
    if (gate) {
      gate.querySelector('[data-gate-text]').textContent = text;
      setRetrying(false);
      return;
    }

    gate = document.createElement('div');
    gate.className = 'location-gate';
    gate.setAttribute('role', 'alertdialog');
    gate.setAttribute('aria-modal', 'true');
    gate.setAttribute('aria-labelledby', 'locationGateTitle');
    gate.innerHTML =
      '<div class="ripple-rings"><span></span><span></span><span></span></div>' +
      '<div class="location-gate-card">' +
        '<div class="location-gate-icon">' +
          '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
            '<path d="M12 21s-7-5.1-7-11a7 7 0 0 1 14 0c0 5.9-7 11-7 11z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>' +
            '<circle cx="12" cy="10" r="2.6" stroke="currentColor" stroke-width="1.7"/>' +
          '</svg>' +
        '</div>' +
        '<h3 id="locationGateTitle">Location is required</h3>' +
        '<p class="location-gate-lead">PlanetWatch pins every report to where you are, so your device location must stay on to continue.</p>' +
        '<p class="location-gate-text" data-gate-text></p>' +
        '<button type="button" class="btn btn-primary btn-block" data-gate-retry>Turn on location</button>' +
        '<button type="button" class="location-gate-signout" data-gate-signout>Sign out instead</button>' +
      '</div>';
    gate.querySelector('[data-gate-text]').textContent = text;
    gate.querySelector('[data-gate-retry]').addEventListener('click', () => {
      setRetrying(true);
      start();
    });
    gate.querySelector('[data-gate-signout]').addEventListener('click', () => PW.logout());
    document.body.appendChild(gate);
    document.body.classList.add('location-locked');
  }

  function setRetrying(retrying) {
    if (!gate) return;
    const button = gate.querySelector('[data-gate-retry]');
    button.classList.toggle('is-loading', retrying);
    button.disabled = retrying;
    button.textContent = retrying ? 'Checking your location…' : 'Turn on location';
  }

  function hideGate() {
    if (!gate) return;
    const leaving = gate;
    gate = null;
    leaving.classList.add('is-settling');
    document.body.classList.remove('location-locked');
    setTimeout(() => leaving.remove(), 700);
  }

  function onPosition(position) {
    location_.current = {
      lat: position.coords.latitude,
      lng: position.coords.longitude,
      accuracy: position.coords.accuracy,
      timestamp: position.timestamp,
    };
    hideGate();
    listeners.forEach((fn) => fn(location_.current));
  }

  function onError(error) {
    // A slow fix after we already have one isn't worth interrupting for;
    // anything else (switched off, permission revoked) blocks again.
    if (error && error.code === 3 && location_.current) return;
    location_.current = null;
    listeners.forEach((fn) => fn(null, error));
    showGate(error);
  }

  function start() {
    if (!navigator.geolocation || !window.isSecureContext) {
      onError(null);
      return;
    }
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = navigator.geolocation.watchPosition(onPosition, onError, {
      enableHighAccuracy: true,
      maximumAge: 10000,
      timeout: 20000,
    });
  }

  // React immediately when the user flips the permission in browser settings.
  if (navigator.permissions && navigator.permissions.query) {
    navigator.permissions.query({ name: 'geolocation' }).then((status) => {
      status.addEventListener('change', () => {
        if (status.state === 'denied') onError({ code: 1 });
        else start();
      });
    }).catch(() => {});
  }

  // Coming back to the tab/app (e.g. from the phone's settings) re-checks.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && !location_.current) start();
  });

  start();
})();
