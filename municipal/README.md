# PlanetWatch municipal dashboard

Monitoring platform for municipal teams. It shows every pinned report on a map, filters by
All / Pending / Solved, and lets staff call the uploader, mark a report solved or reopened,
or delete it.

Static HTML/CSS/JS served by the backend at `/municipal/`. Set `window.MUNI_CONFIG = { apiBase: "https://..." }`
before `js/common.js` to host it elsewhere. `css/style.css` is a copy of the citizen design
system (`frontend/css/style.css`). Re-copy it when the shared design changes.
