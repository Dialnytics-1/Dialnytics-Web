
(() => {
  'use strict';

  const PIXEL_ID = '1171289765222256';
  const KEY = 'dialnytics_marketing_consent_v1';

  const banner = document.getElementById('cookie-banner');
  const accept = document.getElementById('cookie-accept');
  const reject = document.getElementById('cookie-reject');
  const settings = document.getElementById('cookie-settings');

  if (!banner || !accept || !reject || !settings) return;

  let pixelLoaded = false;

  function loadPixel() {
    if (pixelLoaded) return;
    pixelLoaded = true;

    window.fbq = window.fbq || function () {
      (window.fbq.queue = window.fbq.queue || []).push(arguments);
    };

    window.fbq('init', PIXEL_ID);
    window.fbq('track', 'PageView');

    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://connect.facebook.net/en_US/fbevents.js';
    document.head.appendChild(script);
  }

  function readConsent() {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  }

  function saveConsent(value) {
    try {
      localStorage.setItem(KEY, value);
    } catch {
      // Consent remains effective for this page.
    }
  }

  function setConsent(value) {
    saveConsent(value);
    banner.hidden = true;

    if (value === 'accepted') {
      loadPixel();
    } else {
      // Stop future tracking calls on this page.
      window.fbq = function () {};
      // Reload to discard an already loaded Pixel.
      if (pixelLoaded) location.reload();
    }
  }

  accept.addEventListener('click', () => setConsent('accepted'));
  reject.addEventListener('click', () => setConsent('rejected'));

  settings.addEventListener('click', () => {
    banner.hidden = false;
  });

  const saved = readConsent();

  if (saved === 'accepted') {
    loadPixel();
  } else if (saved !== 'rejected') {
    banner.hidden = false;
  }
})();
