// Shared page chrome: splash loader, nav, footer, and auth gating.
// Loaded synchronously as the first thing in <body> so the loader covers the
// page before anything paints — the same splash + "melt" transition runs on
// the website and inside the mobile app.
(function () {
  const body = document.body;
  const page = body.dataset.page || '';
  const authMode = body.dataset.auth || 'optional'; // required | optional | none
  const PW = window.PW;

  const navigatingAway = new Promise(() => {});

  if (PW.isApp && (page === 'install' || page === 'get-app')) {
    // The app never shows install instructions — it offers sharing instead.
    PW.ready = navigatingAway;
    location.replace('share.html');
    return;
  }

  if (authMode === 'required' && !PW.getToken()) {
    PW.ready = navigatingAway;
    PW.redirectToLogin();
    return;
  }

  const icons = {
    phone: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="6.5" y="2.5" width="11" height="19" rx="2.6" stroke="currentColor" stroke-width="1.7"/><path d="M10.5 18.2h3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    share: '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="18" cy="5.5" r="2.5" stroke="currentColor" stroke-width="1.7"/><circle cx="6" cy="12" r="2.5" stroke="currentColor" stroke-width="1.7"/><circle cx="18" cy="18.5" r="2.5" stroke="currentColor" stroke-width="1.7"/><path d="M8.2 10.8l7.6-4.1M8.2 13.2l7.6 4.1" stroke="currentColor" stroke-width="1.7"/></svg>',
  };

  function link(href, label, key, extraClass) {
    const classes = [extraClass, page === key ? 'active' : ''].filter(Boolean).join(' ');
    return '<a href="' + href + '" class="' + classes + '">' + label + '</a>';
  }

  function navLinks() {
    if (page === 'login') {
      const params = new URLSearchParams(location.search);
      const hint = params.get('mode') === 'signin'
        ? ''
        : '<span class="nav-auth-hint">Already have an account? <a href="login.html?mode=signin&next=' +
          encodeURIComponent(params.get('next') || 'index.html') + '">Sign In</a></span>';
      return link('map.html', 'Live Map', 'map') + link('about.html', 'About Us', 'about') + hint;
    }

    const extra = PW.isApp
      ? link('share.html', icons.share + '<span>Share App</span>', 'share', 'nav-install')
      : link('install.html', icons.phone + '<span>Install App</span>', 'install', 'nav-install');

    return (
      link('index.html', 'Home', 'home') +
      link('report.html', 'Report Dumping', 'report') +
      link('map.html', 'Live Map', 'map') +
      link('about.html', 'About Us', 'about') +
      link('profile.html', 'Profile', 'profile', 'nav-profile') +
      extra
    );
  }

  body.insertAdjacentHTML('afterbegin',
    '<div class="page-loader" id="pageLoader">' +
      '<img src="img/clean-africa-3.jpg" alt="PlanetWatch" onerror="this.remove();">' +
    '</div>' +
    '<nav class="site-nav">' +
      '<div class="container">' +
        '<a class="brand" href="index.html">' +
          '<span class="brand-mark">' +
            '<svg class="brand-fallback" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
              '<path d="M12 3C7 3 4 6.5 4 11c0 5.5 4.5 10 8 10s8-4.5 8-10c0-4.5-3-8-8-8z" stroke="white" stroke-width="1.6" stroke-linejoin="round"/>' +
              '<path d="M12 7v9M12 7c-2 1.5-3 3.5-3 5.5" stroke="white" stroke-width="1.6" stroke-linecap="round"/>' +
            '</svg>' +
            '<img class="brand-logo" src="img/clean-africa-2.jpg" alt="PlanetWatch logo" onerror="this.remove();">' +
          '</span>' +
          'PlanetWatch' +
        '</a>' +
        '<button type="button" class="nav-toggle" aria-label="Open menu" aria-expanded="false">' +
          '<span></span><span></span><span></span>' +
        '</button>' +
        '<div class="nav-links">' + navLinks() + '</div>' +
      '</div>' +
    '</nav>'
  );

  const toggle = body.querySelector('.nav-toggle');
  const nav = body.querySelector('.site-nav');
  toggle.addEventListener('click', () => {
    const open = nav.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', String(open));
  });

  document.addEventListener('DOMContentLoaded', () => {
    body.insertAdjacentHTML('beforeend',
      '<footer class="site-footer">' +
        '<div class="container">' +
          '<span>&copy; 2026 PlanetWatch &mdash; Vision-based illegal dumping detection</span>' +
          '<span>Powered by YOLOv11</span>' +
        '</div>' +
      '</footer>'
    );
  });

  window.addEventListener('load', () => {
    const loader = document.getElementById('pageLoader');
    if (!loader) return;
    setTimeout(() => {
      loader.classList.add('loader-hide');
      setTimeout(() => loader.remove(), 700);
    }, 500);
  });

  // Verify the stored token with the server; a restart (new secret key)
  // invalidates it and sends protected pages back to sign-in.
  PW.ready = PW.loadCitizen().then((citizen) => {
    if (authMode === 'required' && !citizen) {
      PW.redirectToLogin();
      return navigatingAway;
    }
    return citizen;
  });
})();
