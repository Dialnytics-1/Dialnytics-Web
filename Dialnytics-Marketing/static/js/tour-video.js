'use strict';
/* Dialnytics product tour video player: chapters, playback speed, keyboard shortcuts. No inline script (CSP-safe). */
(() => {
  const CHAPTERS = [
    {t: 0,    title: 'Getting started', desc: 'Sign in, read your dashboard, switch Today / Week / Month, theme, Do Not Disturb and your caller ID.'},
    {t: 98,   title: 'Making calls', desc: 'The dialer lives on the right side of every page — dial, talk, record and keep working while you call.'},
    {t: 217,  title: 'Talk to two people at once', desc: 'Put one caller on hold, call another, switch between them — or merge everyone into one conference call.'},
    {t: 343,  title: 'Transfer calls to your team', desc: 'Pass a customer to the right teammate in two clicks — even if they are busy on another call.'},
    {t: 488,  title: 'Incoming calls', desc: 'When a customer calls your number, the dialer rings on any page you have open.'},
    {t: 522,  title: 'Call logs, recordings & voicemail', desc: 'Every call is saved automatically — who, when, how long, and the recording if you made one.'},
    {t: 622,  title: 'Text messages & contacts', desc: 'Send and receive SMS from your business number, and keep your contacts one click away.'},
    {t: 728,  title: 'CRM & Power Dialer', desc: 'Keep every lead in one place, then call through your list automatically — one lead after another.'},
    {t: 899,  title: 'Scripts & campaigns', desc: 'Keep your best call scripts ready, and group the numbers you want to call into campaigns.'},
    {t: 988,  title: 'Your team, live', desc: 'For company owners: see who is online, who is on a call right now, and how each agent is doing today.'},
    {t: 1057, title: 'Billing, profile & preferences', desc: 'Your plan, your login details, and how the dialer rings and records.'}
  ];
  const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
  const root = document.querySelector('[data-tour-video]');
  if (!root) return;
  const video = root.querySelector('video');
  const fmt = s => { s = Math.max(0, Math.floor(s || 0)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = String(s % 60).padStart(2, '0'); return h ? h + ':' + String(m).padStart(2, '0') + ':' + x : m + ':' + x; };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; };
  const I = {
    play: '<svg viewBox="0 0 24 24"><path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z"/></svg>',
    pause: '<svg viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>',
    back: '<svg viewBox="0 0 24 24"><path d="M12 5V2L7 6l5 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7z"/><text x="12" y="15.5" font-size="6.5" text-anchor="middle" font-weight="700">10</text></svg>',
    fwd: '<svg viewBox="0 0 24 24"><path d="M12 5V2l5 4-5 4V7a5 5 0 1 0 5 5h2a7 7 0 1 1-7-7z"/><text x="12" y="15.5" font-size="6.5" text-anchor="middle" font-weight="700">10</text></svg>',
    vol: '<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 8.5a4.5 4.5 0 0 1 0 7M18.5 6a8 8 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    mute: '<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16 9l5 6m0-6l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    list: '<svg viewBox="0 0 24 24"><path d="M4 6h2v2H4zm4 0h12v2H8zM4 11h2v2H4zm4 0h12v2H8zM4 16h2v2H4zm4 0h12v2H8z"/></svg>',
    full: '<svg viewBox="0 0 24 24"><path d="M4 4h6v2H6v4H4zm10 0h6v6h-2V6h-4zM4 14h2v4h4v2H4zm14 0h2v6h-6v-2h4z"/></svg>'
  };

  /* ---------- build the controls ---------- */
  video.controls = false;
  const big = el('button', 'tv-big', I.play); big.type = 'button'; big.setAttribute('aria-label', 'Play product tour');
  const chapPill = el('div', 'tv-chap'); chapPill.setAttribute('aria-live', 'polite');
  const bar = el('div', 'tv-bar');
  const seek = el('div', 'tv-seek'); seek.tabIndex = 0; seek.setAttribute('role', 'slider'); seek.setAttribute('aria-label', 'Seek');
  const buffered = el('div', 'tv-buf'), played = el('div', 'tv-played'), knob = el('div', 'tv-knob'), tip = el('div', 'tv-tip');
  seek.append(buffered, played, knob, tip);
  const row = el('div', 'tv-row');
  const btn = (cls, label, icon) => { const b = el('button', 'tv-btn ' + cls, icon); b.type = 'button'; b.setAttribute('aria-label', label); b.title = label; return b; };
  const bPlay = btn('tv-play', 'Play (Space)', I.play), bBack = btn('', 'Back 10 seconds (J)', I.back), bFwd = btn('', 'Forward 10 seconds (L)', I.fwd);
  const bVol = btn('tv-vol', 'Mute (M)', I.vol);
  const vol = el('input', 'tv-volume'); vol.type = 'range'; vol.min = 0; vol.max = 1; vol.step = 0.05; vol.value = 1; vol.setAttribute('aria-label', 'Volume');
  const time = el('span', 'tv-time', '0:00 / 0:00');
  const now = el('button', 'tv-now'); now.type = 'button'; now.title = 'Chapters';
  const bSpeed = btn('tv-speed', 'Playback speed', '1x'); bSpeed.setAttribute('aria-haspopup', 'true');
  const bList = btn('', 'Chapters', I.list); bList.setAttribute('aria-haspopup', 'true');
  const bFull = btn('', 'Full screen (F)', I.full);
  row.append(bPlay, bBack, bFwd, bVol, vol, time, now, bSpeed, bList, bFull);
  bar.append(seek, row);
  const speedMenu = el('div', 'tv-menu tv-speed-menu'); speedMenu.hidden = true; speedMenu.setAttribute('role', 'menu');
  SPEEDS.forEach(s => { const b = el('button', '', s === 1 ? 'Normal' : s + 'x'); b.type = 'button'; b.dataset.speed = s; b.setAttribute('role', 'menuitemradio'); speedMenu.append(b); });
  const listMenu = el('div', 'tv-menu tv-list-menu'); listMenu.hidden = true; listMenu.setAttribute('role', 'menu');
  root.append(big, chapPill, bar, speedMenu, listMenu);
  CHAPTERS.forEach((c, i) => {
    const b = el('button', '', '<em>' + (i + 1) + '</em><span>' + c.title + '</span><small>' + fmt(c.t) + '</small>');
    b.type = 'button'; b.dataset.chapter = i; listMenu.append(b);
  });

  /* chapter cards under the video (tour page only) */
  const cards = document.querySelector('[data-tour-chapters]');
  if (cards) {
    CHAPTERS.forEach((c, i) => {
      const a = el('button', 'tv-card');
      a.type = 'button'; a.dataset.chapter = i;
      a.innerHTML = '<span class="tv-card-n">Chapter ' + (i + 1) + '<b>' + fmt(c.t) + '</b></span><strong>' + c.title + '</strong><p>' + c.desc + '</p><span class="tv-card-go">Watch this part</span>';
      cards.append(a);
    });
  }

  /* ---------- helpers ---------- */
  const dur = () => (isFinite(video.duration) && video.duration > 0 ? video.duration : 1154);
  const chapterAt = t => { let i = 0; CHAPTERS.forEach((c, n) => { if (t >= c.t - 0.25) i = n; }); return i; };
  function drawMarks() {
    seek.querySelectorAll('.tv-mark').forEach(m => m.remove());
    CHAPTERS.forEach((c, i) => { if (!i) return; const m = el('i', 'tv-mark'); m.style.left = (c.t / dur() * 100) + '%'; seek.append(m); });
  }
  let lastChap = -1;
  function update() {
    const t = video.currentTime, d = dur(), p = t / d * 100;
    played.style.width = p + '%'; knob.style.left = p + '%';
    if (video.buffered.length) buffered.style.width = (video.buffered.end(video.buffered.length - 1) / d * 100) + '%';
    time.textContent = fmt(t) + ' / ' + fmt(d);
    seek.setAttribute('aria-valuenow', Math.round(t)); seek.setAttribute('aria-valuemax', Math.round(d)); seek.setAttribute('aria-valuetext', fmt(t) + ' of ' + fmt(d));
    const ci = chapterAt(t);
    if (ci !== lastChap) {
      lastChap = ci;
      now.textContent = (ci + 1) + '. ' + CHAPTERS[ci].title;
      chapPill.textContent = 'Chapter ' + (ci + 1) + ' · ' + CHAPTERS[ci].title;
      const live = root.classList.contains('started');
      document.querySelectorAll('[data-chapter]').forEach(b => b.classList.toggle('on', Number(b.dataset.chapter) === ci && (live || root.contains(b))));
      if (video.currentTime > 1 && !video.paused) { chapPill.classList.remove('flash'); void chapPill.offsetWidth; chapPill.classList.add('flash'); }
    }
  }
  function setPlayIcon() {
    const p = video.paused;
    bPlay.innerHTML = p ? I.play : I.pause; bPlay.setAttribute('aria-label', p ? 'Play (Space)' : 'Pause (Space)');
    root.classList.toggle('is-paused', p); big.hidden = !p || root.classList.contains('started');
    if (p) showUi();
  }
  const play = () => { if (!root.classList.contains('started')) { root.classList.add('started'); lastChap = -1; update(); } big.hidden = true; const r = video.play(); if (r && r.catch) r.catch(() => {}); };
  const toggle = () => (video.paused ? play() : video.pause());
  const jump = s => { video.currentTime = Math.max(0, Math.min(dur() - 0.2, video.currentTime + s)); showUi(); };
  function goChapter(i, scroll) {
    i = Math.max(0, Math.min(CHAPTERS.length - 1, i));
    video.currentTime = CHAPTERS[i].t + (i ? 0.05 : 0);
    closeMenus(); play(); update();
    if (scroll) root.scrollIntoView({behavior: 'smooth', block: 'center'});
    try { history.replaceState(null, '', '#chapter-' + (i + 1)); } catch (e) {}
  }
  function setSpeed(s) {
    video.playbackRate = s; video.defaultPlaybackRate = s; bSpeed.textContent = (s === 1 ? '1' : String(s)) + 'x';
    speedMenu.querySelectorAll('button').forEach(b => { const on = Number(b.dataset.speed) === s; b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); });
    store.set('dn-tour-speed', String(s));
  }
  function closeMenus() { speedMenu.hidden = true; listMenu.hidden = true; }
  function openMenu(m) { const was = !m.hidden; closeMenus(); m.hidden = was; showUi(); }
  let hideT;
  function showUi() {
    root.classList.remove('ui-hidden'); clearTimeout(hideT);
    hideT = setTimeout(() => { if (!video.paused && speedMenu.hidden && listMenu.hidden) root.classList.add('ui-hidden'); }, 2800);
  }
  const seekTo = clientX => { const r = seek.getBoundingClientRect(); const f = Math.max(0, Math.min(1, (clientX - r.left) / r.width)); video.currentTime = f * dur(); update(); };

  /* ---------- events ---------- */
  ['timeupdate', 'progress', 'loadedmetadata', 'durationchange', 'seeked'].forEach(e => video.addEventListener(e, update));
  video.addEventListener('loadedmetadata', drawMarks);
  ['play', 'pause', 'ended'].forEach(e => video.addEventListener(e, setPlayIcon));
  video.addEventListener('click', toggle);
  big.addEventListener('click', play);
  bPlay.addEventListener('click', toggle);
  bBack.addEventListener('click', () => jump(-10));
  bFwd.addEventListener('click', () => jump(10));
  bVol.addEventListener('click', () => { video.muted = !video.muted; });
  vol.addEventListener('input', () => { video.volume = Number(vol.value); video.muted = video.volume === 0; });
  video.addEventListener('volumechange', () => { const m = video.muted || video.volume === 0; bVol.innerHTML = m ? I.mute : I.vol; bVol.setAttribute('aria-label', m ? 'Unmute (M)' : 'Mute (M)'); vol.value = video.muted ? 0 : video.volume; });
  bSpeed.addEventListener('click', e => { e.stopPropagation(); openMenu(speedMenu); });
  bList.addEventListener('click', e => { e.stopPropagation(); openMenu(listMenu); });
  now.addEventListener('click', e => { e.stopPropagation(); openMenu(listMenu); });
  speedMenu.addEventListener('click', e => { const b = e.target.closest('[data-speed]'); if (b) { setSpeed(Number(b.dataset.speed)); closeMenus(); } });
  document.addEventListener('click', e => {
    const c = e.target.closest('[data-chapter]');
    if (c) { goChapter(Number(c.dataset.chapter), !root.contains(c)); return; }
    if (!speedMenu.contains(e.target) && !listMenu.contains(e.target)) closeMenus();
  });
  let dragging = false;
  seek.addEventListener('pointerdown', e => { dragging = true; seek.setPointerCapture(e.pointerId); seekTo(e.clientX); });
  seek.addEventListener('pointermove', e => {
    const r = seek.getBoundingClientRect(), f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)), t = f * dur();
    tip.textContent = fmt(t) + ' · ' + CHAPTERS[chapterAt(t)].title; tip.style.left = (f * 100) + '%'; tip.classList.add('on');
    if (dragging) seekTo(e.clientX);
  });
  seek.addEventListener('pointerup', () => { dragging = false; });
  seek.addEventListener('pointerleave', () => tip.classList.remove('on'));
  seek.addEventListener('keydown', e => { if (e.key === 'ArrowRight') { jump(5); e.preventDefault(); } if (e.key === 'ArrowLeft') { jump(-5); e.preventDefault(); } });
  bFull.addEventListener('click', () => {
    if (document.fullscreenElement || document.webkitFullscreenElement) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    else if (root.requestFullscreen) root.requestFullscreen().catch(() => {});
    else if (root.webkitRequestFullscreen) root.webkitRequestFullscreen();
    else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();   // iPhone
  });
  ['mousemove', 'touchstart', 'focusin'].forEach(e => root.addEventListener(e, showUi, {passive: true}));
  root.tabIndex = -1;
  root.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    const k = e.key;
    if (k === ' ' || k === 'k') { e.preventDefault(); toggle(); }
    else if (k === 'j') jump(-10); else if (k === 'l') jump(10);
    else if (k === 'ArrowLeft' && e.target === root) jump(-5); else if (k === 'ArrowRight' && e.target === root) jump(5);
    else if (k === 'm') video.muted = !video.muted;
    else if (k === 'f') bFull.click();
    else if (k === '>' || k === '.') setSpeed(SPEEDS[Math.min(SPEEDS.length - 1, SPEEDS.indexOf(video.playbackRate) + 1)] || 1);
    else if (k === '<' || k === ',') setSpeed(SPEEDS[Math.max(0, SPEEDS.indexOf(video.playbackRate) - 1)] || 1);
    else if (k === 'Escape') closeMenus();
    else return;
    showUi();
  });

  /* ---------- start ---------- */
  const saved = Number(store.get('dn-tour-speed'));
  setSpeed(SPEEDS.includes(saved) ? saved : 1);
  video.addEventListener('ratechange', () => { if (SPEEDS.includes(video.playbackRate)) setSpeed(video.playbackRate); });
  drawMarks(); update(); setPlayIcon();
  const m = /#chapter-(\d+)/.exec(location.hash);
  if (m) { const i = Number(m[1]) - 1; video.addEventListener('loadedmetadata', () => { video.currentTime = CHAPTERS[Math.max(0, Math.min(CHAPTERS.length - 1, i))].t; update(); }, {once: true}); root.scrollIntoView({block: 'center'}); }
})();
