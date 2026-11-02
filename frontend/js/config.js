// Where the backend API lives. Empty = same origin (the website is served by
// the backend). The mobile build overwrites this file with the server's
// address and isApp: true — see mobile/scripts/sync-web.mjs.
window.PW_CONFIG = window.PW_CONFIG || {
  apiBase: '',
  isApp: false,
};
