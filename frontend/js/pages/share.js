(function () {
  const PW = window.PW;
  const linkInput = document.getElementById('shareLink');
  const toast = document.getElementById('toast');
  const message = 'Help keep our community clean — report illegal dumping with PlanetWatch: ';
  let shareUrl = '';

  function showToast(text) {
    toast.textContent = text;
    toast.classList.add('is-visible');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove('is-visible'), 2200);
  }

  PW.request('/api/install/info').then((info) => {
    shareUrl = info.share_url;
    linkInput.value = shareUrl;
    const text = encodeURIComponent(message + shareUrl);
    document.getElementById('whatsappLink').href = 'https://wa.me/?text=' + text;
    document.getElementById('smsLink').href = 'sms:?&body=' + text;
    document.getElementById('emailLink').href = 'mailto:?subject=' + encodeURIComponent('Join me on PlanetWatch') + '&body=' + text;
    document.getElementById('facebookLink').href = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(shareUrl);
  }).catch((error) => {
    linkInput.value = error.message;
  });

  async function copyLink() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
    } catch (e) {
      linkInput.select();
      document.execCommand('copy');
    }
    showToast('Link copied');
  }

  document.getElementById('copyBtn').addEventListener('click', copyLink);

  document.getElementById('shareBtn').addEventListener('click', async () => {
    if (!shareUrl) return;
    const payload = { title: 'PlanetWatch', text: message, url: shareUrl };
    // Native share sheet: Capacitor's Share plugin in the app, Web Share in browsers.
    const nativeShare = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Share;
    try {
      if (nativeShare) {
        await nativeShare.share(Object.assign({ dialogTitle: 'Share PlanetWatch' }, payload));
      } else if (navigator.share) {
        await navigator.share(payload);
      } else {
        await copyLink();
      }
    } catch (e) {
      // Closing the share sheet rejects — nothing to do.
    }
  });
})();
