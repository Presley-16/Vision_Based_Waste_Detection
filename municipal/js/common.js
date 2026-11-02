// Municipal dashboard: config, API client, and shared page chrome.
(function () {
  // Where the backend API lives. Empty = same origin (served by the backend at /municipal/).
  const config = window.MUNI_CONFIG || { apiBase: '' };
  const TOKEN_KEY = 'pw_municipal_token';
  const USER_KEY = 'pw_municipal_user';

  function apiUrl(path) {
    return (config.apiBase || '').replace(/\/$/, '') + path;
  }

  async function request(path, options = {}) {
    const headers = {};
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = 'Bearer ' + token;
    let body;
    if (options.body) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(options.body);
    }

    let response;
    try {
      response = await fetch(apiUrl(path), { method: options.method || 'GET', headers, body });
    } catch (e) {
      const error = new Error("Can't reach the PlanetWatch server.");
      error.status = 0;
      throw error;
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error((data && data.error) || 'Request failed (' + response.status + ').');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    const date = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
    return date.toLocaleString(undefined, { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function hideLoaderOnLoad() {
    window.addEventListener('load', () => {
      const loader = document.getElementById('pageLoader');
      if (!loader) return;
      setTimeout(() => {
        loader.classList.add('loader-hide');
        setTimeout(() => loader.remove(), 700);
      }, 500);
    });
  }

  window.MUNI = {
    apiUrl,
    request,
    escapeHtml,
    formatDate,
    hideLoaderOnLoad,
    getToken: () => localStorage.getItem(TOKEN_KEY),
    getUser: () => localStorage.getItem(USER_KEY),
    setSession(token, user) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, user);
    },
    logout() {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      location.href = 'index.html';
    },
  };

  hideLoaderOnLoad();
})();
