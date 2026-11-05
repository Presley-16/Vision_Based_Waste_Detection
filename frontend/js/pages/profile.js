(function () {
  const PW = window.PW;
  const form = document.getElementById('profileForm');
  const savedBox = document.getElementById('savedBox');
  const errorBox = document.getElementById('errorBox');
  const editBtn = document.getElementById('editBtn');
  const avatarBtn = document.getElementById('avatarBtn');
  const avatarImg = document.getElementById('avatarImg');
  const avatarInitials = document.getElementById('avatarInitials');
  const photoInput = document.getElementById('photoInput');
  const removePhotoBtn = document.getElementById('removePhotoBtn');
  const confirmBlock = document.getElementById('confirmBlock');
  const passwordInput = document.getElementById('currentPassword');
  const submit = form.querySelector('button[type="submit"]');

  const FIELDS = ['name', 'surname', 'address', 'phone'];
  const MAX_PHOTO_BYTES = 10 * 1024 * 1024;

  let citizen = null;
  let editing = false;
  let pendingPhoto = null; // File chosen but not saved yet
  let removePhoto = false;
  let previewUrl = null;

  function showError(message) {
    errorBox.querySelector('[data-error-text]').textContent = message;
    errorBox.hidden = false;
    savedBox.hidden = true;
  }

  function hideMessages() {
    errorBox.hidden = true;
    savedBox.hidden = true;
  }

  function initials(c) {
    return ((c.name || '').charAt(0) + (c.surname || '').charAt(0)).toUpperCase() || '?';
  }

  function renderAvatar(src) {
    avatarImg.hidden = !src;
    avatarInitials.hidden = Boolean(src);
    if (src) avatarImg.src = src;
    avatarBtn.setAttribute('aria-label', src ? 'Change profile photo' : 'Add a profile photo');
    removePhotoBtn.hidden = !editing || !src;
  }

  function savedPhotoSrc() {
    return citizen && citizen.photo_url ? PW.assetUrl(citizen.photo_url) : null;
  }

  function currentPhotoSrc() {
    if (pendingPhoto) return previewUrl;
    if (removePhoto) return null;
    return savedPhotoSrc();
  }

  function fill(c) {
    citizen = c;
    FIELDS.forEach((key) => { form.elements[key].value = c[key] || ''; });
    document.getElementById('profileName').textContent = (c.name + ' ' + c.surname).trim();
    document.getElementById('memberSince').textContent = c.member_since
      ? 'Citizen since ' + new Date(c.member_since + 'Z').toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
      : '';
    avatarInitials.textContent = initials(c);

    // Accounts from before passwords existed choose one when they first save.
    document.getElementById('passwordLabel').textContent = c.has_password ? 'Current password' : 'Create a password';
    document.getElementById('passwordHint').textContent = c.has_password
      ? 'Enter your password to confirm these changes.'
      : 'Your account has no password yet. Choose one (at least 6 characters) to save these changes.';
    passwordInput.autocomplete = c.has_password ? 'current-password' : 'new-password';
    renderAvatar(currentPhotoSrc());
  }

  function clearPendingPhoto() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
    pendingPhoto = null;
    removePhoto = false;
    photoInput.value = '';
  }

  function isDirty() {
    if (!citizen) return false;
    return pendingPhoto !== null || removePhoto ||
      FIELDS.some((key) => form.elements[key].value !== (citizen[key] || ''));
  }

  // Save Changes (and the password it needs) only appear once something changed.
  function updateConfirm() {
    const dirty = isDirty();
    if (confirmBlock.hidden === dirty) {
      confirmBlock.hidden = !dirty;
      if (!dirty) passwordInput.value = '';
    }
  }

  function setEditing(on) {
    editing = on;
    form.classList.toggle('is-readonly', !on);
    FIELDS.forEach((key) => { form.elements[key].readOnly = !on; });
    editBtn.classList.toggle('is-active', on);
    editBtn.querySelector('span').textContent = on ? 'Cancel' : 'Edit profile';
    if (!on && citizen) {
      clearPendingPhoto();
      fill(citizen);
    }
    renderAvatar(currentPhotoSrc());
    updateConfirm();
  }

  PW.ready.then((c) => {
    if (c) fill(c);
  });

  editBtn.addEventListener('click', () => {
    hideMessages();
    setEditing(!editing);
    if (editing) form.elements.name.focus();
  });

  form.addEventListener('input', (event) => {
    if (event.target !== passwordInput) updateConfirm();
  });

  avatarBtn.addEventListener('click', () => {
    hideMessages();
    if (!editing) setEditing(true);
    photoInput.click();
  });

  photoInput.addEventListener('change', () => {
    const file = photoInput.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      showError('Please choose a photo (JPG or PNG).');
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      showError('That photo is too large. Please choose one under 10 MB.');
      return;
    }
    clearPendingPhoto();
    pendingPhoto = file;
    previewUrl = URL.createObjectURL(file);
    renderAvatar(previewUrl);
    updateConfirm();
  });

  removePhotoBtn.addEventListener('click', () => {
    clearPendingPhoto();
    removePhoto = Boolean(citizen && citizen.photo_url);
    renderAvatar(null);
    updateConfirm();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!isDirty()) return;
    hideMessages();
    if (!passwordInput.value) {
      showError(citizen.has_password ? 'Enter your current password to save these changes.' : 'Choose a password to save these changes.');
      passwordInput.focus();
      return;
    }

    const body = new FormData();
    FIELDS.forEach((key) => body.append(key, form.elements[key].value));
    // Sent exactly as typed: spaces and symbols are part of the password.
    body.append(citizen.has_password ? 'current_password' : 'new_password', passwordInput.value);
    if (pendingPhoto) body.append('photo', pendingPhoto, pendingPhoto.name);
    if (removePhoto) body.append('remove_photo', '1');

    submit.disabled = true;
    submit.classList.add('is-loading');
    try {
      const data = await PW.request('/api/me', { method: 'PUT', body });
      PW.setCitizen(data.citizen);
      clearPendingPhoto();
      citizen = data.citizen;
      setEditing(false);
      savedBox.hidden = false;
    } catch (error) {
      showError(error.message);
      if (error.status === 403) {
        passwordInput.select();
        passwordInput.focus();
      }
    } finally {
      submit.disabled = false;
      submit.classList.remove('is-loading');
    }
  });

  document.getElementById('logoutBtn').addEventListener('click', () => PW.logout());
})();
