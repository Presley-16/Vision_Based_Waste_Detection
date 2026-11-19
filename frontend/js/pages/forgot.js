(function () {
  const PW = window.PW;
  const params = new URLSearchParams(location.search);
  const next = PW.safeNext(params.get('next'));
  const requestForm = document.getElementById('requestForm');
  const resetForm = document.getElementById('resetForm');
  const errorBox = document.querySelector('[data-error]');
  const resendBtn = document.getElementById('resendBtn');

  let account = null; // {name, surname} the code was sent for
  let countdown = null;

  // Arriving from Sign In with the name already typed.
  requestForm.elements.name.value = params.get('name') || '';
  requestForm.elements.surname.value = params.get('surname') || '';

  function showError(message) {
    errorBox.querySelector('[data-error-text]').textContent = message;
    errorBox.hidden = false;
  }

  function setBusy(form, busy) {
    const button = form.querySelector('button[type="submit"]');
    button.disabled = busy;
    button.classList.toggle('is-loading', busy);
  }

  function startResendTimer(seconds) {
    clearInterval(countdown);
    let left = seconds;
    resendBtn.disabled = true;
    const tick = () => {
      if (left <= 0) {
        clearInterval(countdown);
        resendBtn.disabled = false;
        resendBtn.textContent = 'Resend code';
        return;
      }
      resendBtn.textContent = 'Resend code in ' + left + 's';
      left -= 1;
    };
    tick();
    countdown = setInterval(tick, 1000);
  }

  async function sendCode() {
    const data = await PW.request('/api/auth/forgot', { method: 'POST', body: account });
    document.getElementById('sentTo').textContent =
      'We texted a code to ' + data.phone + '. It expires in ' + Math.round(data.expires_in / 60) + ' minutes.';
    document.getElementById('devNote').hidden = !data.dev_console;
    startResendTimer(data.resend_after);
  }

  requestForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    account = { name: requestForm.elements.name.value.trim(), surname: requestForm.elements.surname.value.trim() };
    setBusy(requestForm, true);
    try {
      await sendCode();
      requestForm.hidden = true;
      resetForm.hidden = false;
      resetForm.elements.code.focus();
    } catch (error) {
      showError(error.message);
    } finally {
      setBusy(requestForm, false);
    }
  });

  resendBtn.addEventListener('click', async () => {
    errorBox.hidden = true;
    resendBtn.disabled = true;
    try {
      await sendCode();
      resetForm.elements.code.value = '';
      resetForm.elements.code.focus();
    } catch (error) {
      showError(error.message);
      if (error.data && error.data.retry_after) startResendTimer(error.data.retry_after);
      else resendBtn.disabled = false;
    }
  });

  document.getElementById('changeNameBtn').addEventListener('click', () => {
    clearInterval(countdown);
    errorBox.hidden = true;
    resetForm.reset();
    resetForm.hidden = true;
    requestForm.hidden = false;
    requestForm.elements.name.focus();
  });

  // Digits only in the code box.
  resetForm.elements.code.addEventListener('input', (event) => {
    event.target.value = event.target.value.replace(/\D/g, '').slice(0, 6);
  });

  resetForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const password = resetForm.elements.password.value; // exactly as typed
    if (password !== document.getElementById('confirmPassword').value) {
      showError("The two passwords don't match.");
      document.getElementById('confirmPassword').focus();
      return;
    }
    setBusy(resetForm, true);
    try {
      const data = await PW.request('/api/auth/reset', {
        method: 'POST',
        body: { name: account.name, surname: account.surname, code: resetForm.elements.code.value, password },
      });
      PW.setSession(data.token, data.citizen);
      location.href = next;
    } catch (error) {
      showError(error.message);
      setBusy(resetForm, false);
    }
  });
})();
