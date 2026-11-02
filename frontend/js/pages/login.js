(function () {
  const PW = window.PW;
  const params = new URLSearchParams(location.search);
  const mode = params.get('mode') === 'signin' ? 'signin' : 'signup';
  const next = PW.safeNext(params.get('next'));

  document.title = (mode === 'signin' ? 'Sign In' : 'Sign Up') + ' — PlanetWatch';
  document.querySelector('[data-mode="' + mode + '"]').hidden = false;

  // The app is already installed — no install prompts inside it.
  if (PW.isApp) {
    document.querySelectorAll('[data-install-block]').forEach((el) => el.remove());
  }

  const form = document.querySelector('[data-auth-form="' + mode + '"]');
  const container = document.querySelector('[data-mode="' + mode + '"]');
  const errorBox = container.querySelector('[data-error]');
  const submit = form.querySelector('button[type="submit"]');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    submit.disabled = true;
    submit.classList.add('is-loading');

    try {
      const data = await PW.request('/api/auth/' + mode, { method: 'POST', body: Object.fromEntries(new FormData(form)) });
      PW.setSession(data.token, data.citizen);
      location.href = next;
    } catch (error) {
      errorBox.querySelector('[data-error-text]').textContent = error.message;
      errorBox.hidden = false;
      submit.disabled = false;
      submit.classList.remove('is-loading');
    }
  });
})();
