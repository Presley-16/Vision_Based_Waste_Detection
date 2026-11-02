# PlanetWatch citizen website

Static HTML/CSS/JS that talks to the backend API (`js/api.js`). No build step.

- `js/config.js` sets `apiBase`. Empty means same origin, when the backend serves this folder.
- `js/layout.js` adds the splash loader, nav and footer, and redirects to sign-in on protected pages.
- `js/location-guard.js` is the mandatory-location popup for signed-in citizens.
- `js/pages/*.js` holds the page logic. `vendor/leaflet/` holds the map library.

The mobile app bundles this folder as-is (see `../mobile`), so changes here appear in the
app on its next build.
