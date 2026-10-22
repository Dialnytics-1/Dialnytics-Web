
(() => {
  'use strict';

  const META_PIXEL_ID = '1171289765222256';
  const GA4_ID = 'G-74DV3HV81W';
  const KEY = 'dialnytics_marketing_consent_v2';

  const banner = document.getElementById('cookie-banner');
  const accept = document.getElementById('cookie-accept');
  const reject = document.getElementById('cookie-reject');
  const settings = document.getElementById('cookie-settings');

  if (!banner || !accept || !reject || !settings) return;

  let trackingLoaded = false;

  function addScript(src) {
    const script = document.createElement('script');
    script.async = true;
    script.src = src;
    document.head.appendChild(script);
  }

  function loadTracking() {
    if (trackingLoaded) return;
    trackingLoaded = true;

    // Meta Pixel
    window.fbq = window.fbq || function () {
      (window.fbq.queue = window.fbq.queue || []).push(arguments);
    };

    window.fbq('init', META_PIXEL_ID);
    window.fbq('track', 'PageView');

    addScript(
      'https://connect.facebook.net/en_US/fbevents.js'
    );

    // Google Analytics 4
    window.dataLayer = window.dataLayer || [];

    window.gtag = function () {
      window.dataLayer.push(arguments);
    };

    window.gtag('js', new Date());
    window.gtag('config', GA4_ID, {
      send_page_view: true
    });

    addScript(
      'https://www.googletagmanager.com/gtag/js?id=' +
      encodeURIComponent(GA4_ID)
    );
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
      // Storage may be unavailable.
    }
  }

  function setConsent(value) {
    const previouslyLoaded = trackingLoaded;

    saveConsent(value);
    banner.hidden = true;

    if (value === 'accepted') {
      loadTracking();
    } else if (previouslyLoaded) {
      // Remove active tracking by reloading the page.
      location.reload();
    }
  }

  accept.addEventListener('click', () => {
    setConsent('accepted');
  });

  reject.addEventListener('click', () => {
    setConsent('rejected');
  });

  settings.addEventListener('click', () => {
    banner.hidden = false;
  });

  const saved = readConsent();

  if (saved === 'accepted') {
    loadTracking();
  } else if (saved !== 'rejected') {
    banner.hidden = false;
  }
})();
