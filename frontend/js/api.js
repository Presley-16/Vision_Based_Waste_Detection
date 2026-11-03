// API client + auth state shared by every page (website and mobile app alike).
(function () {
  const config = window.PW_CONFIG || { apiBase: '', isApp: false };
  const TOKEN_KEY = 'pw_token';
  const CITIZEN_KEY = 'pw_citizen';

  const isApp = Boolean(config.isApp || (window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform()));

  function apiUrl(path) {
    return (config.apiBase || '').replace(/\/$/, '') + path;
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getCitizen() {
    try {
      return JSON.parse(localStorage.getItem(CITIZEN_KEY));
    } catch (e) {
      return null;
    }
  }

  function setSession(token, citizen) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(CITIZEN_KEY, JSON.stringify(citizen));
  }

  function setCitizen(citizen) {
    localStorage.setItem(CITIZEN_KEY, JSON.stringify(citizen));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(CITIZEN_KEY);
  }

  async function request(path, options = {}) {
    const headers = Object.assign({}, options.headers);
    // ngrok (`run.py --tunnel`) shows a browser warning page unless asked not to.
    headers['ngrok-skip-browser-warning'] = '1';
    const token = getToken();
    if (token) headers.Authorization = 'Bearer ' + token;

    let body = options.body;
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(apiUrl(path), { method: options.method || 'GET', headers, body });
    } catch (e) {
      const error = new Error("Can't reach PlanetWatch right now — check your connection and try again.");
      error.status = 0;
      throw error;
    }

    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      data = null;
    }

    if (!response.ok) {
      const error = new Error((data && data.error) || 'Something went wrong (' + response.status + ').');
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  // Only ever redirect to a page of this site after sign-in (no open redirects).
  function safeNext(next) {
    if (!next || !/^[a-z0-9-]+\.html(\?[^#]*)?(#.*)?$/i.test(next)) return 'index.html';
    return next;
  }

  function currentPage() {
    const file = location.pathname.split('/').pop() || 'index.html';
    return file + location.search;
  }

  function redirectToLogin() {
    location.replace('login.html?next=' + encodeURIComponent(currentPage()));
  }

  function logout() {
    clearSession();
    location.href = 'login.html?mode=signin';
  }

  // Resolves with the signed-in citizen (fresh from the server), or null.
  // A 401 means the token is stale — e.g. the server restarted — so drop it.
  let citizenPromise = null;
  function loadCitizen() {
    if (!citizenPromise) {
      citizenPromise = getToken()
        ? request('/api/me').then((data) => {
            setCitizen(data.citizen);
            return data.citizen;
          }).catch((error) => {
            if (error.status === 401) {
              clearSession();
              return null;
            }
            return getCitizen();
          })
        : Promise.resolve(null);
    }
    return citizenPromise;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    const date = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    return date.toLocaleString(undefined, { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  window.PW = Object.assign(window.PW || {}, {
    config,
    isApp,
    apiUrl,
    assetUrl: apiUrl,
    request,
    getToken,
    getCitizen,
    setSession,
    setCitizen,
    clearSession,
    loadCitizen,
    redirectToLogin,
    logout,
    safeNext,
    escapeHtml,
    formatDate,
  });
})();
