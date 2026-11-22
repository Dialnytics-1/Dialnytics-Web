'use strict';
/* Interactive replica of the Dialnytics dialer. Example data only; no network calls.
   Plays a short self-running demo until the visitor clicks anything, then hands over control. */
(() => {
  const root = document.querySelector('[data-hero-dialer]');
  if (!root) return;
  const W = 1120;
  const viewport = root.querySelector('.dx-viewport');
  const canvas = root.querySelector('.dx-canvas');
  const q = s => root.querySelector(s);
  const qa = s => Array.from(root.querySelectorAll(s));

  function fit() { const scale = viewport.clientWidth / W; canvas.style.transform = 'scale(' + scale + ')'; return scale; }
  fit();
  window.addEventListener('resize', fit);
  if ('ResizeObserver' in window) new ResizeObserver(fit).observe(viewport);

  const RANGES = [
    { calls: 124, rate: 82, talk: 204, contacts: 18, follow: 7, out: [102, 22], labels: ['12 AM', '3 AM', '6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM'], bars: [8, 4, 22, 64, 88, 72, 46, 18] },
    { calls: 684, rate: 79, talk: 192, contacts: 96, follow: 31, out: [540, 144], labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', ''], bars: [62, 78, 70, 92, 84, 36, 20, 0] },
    { calls: 2918, rate: 81, talk: 198, contacts: 412, follow: 126, out: [2364, 554], labels: ['Wk 1', 'Wk 2', 'Wk 3', 'Wk 4', '', '', '', ''], bars: [70, 82, 76, 94, 0, 0, 0, 0] }
  ];
  const NUMBERS = ['+14155550132', '+447700900123', '+61491570006'];
  const pretty = n => { n = n.replace(/[^\d+]/g, ''); return n.startsWith('+44') ? n.replace(/^\+44(\d{4})(\d{6})$/, '+44 $1 $2') : n.startsWith('+61') ? n.replace(/^\+61(\d{3})(\d{3})(\d{3})$/, '+61 $1 $2 $3') : n.replace(/^\+1(\d{3})(\d{3})(\d{4})$/, '+1 $1 $2 $3'); };
  const mmss = s => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  const clock = s => String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  const stat = k => q('[data-dx-stat="' + k + '"]');
  const status = q('[data-dx-status]');
  const input = q('[data-dx-input]');
  const cursor = q('[data-dx-cursor]');
  const toast = q('[data-dx-toast]');
  const bars = qa('.dx-bars > div');
  const pills = qa('[data-dx-range]');
  const hint = q('[data-dx-hint]');
  const PLACEHOLDER = 'Enter or paste a number';

  function countTo(el, from, to, fmt, ms) {
    if (!(ms > 0)) { el.textContent = fmt(to); return Promise.resolve(); }
    const start = performance.now();
    return new Promise(resolve => { (function step(now) { const t = Math.min(1, (now - start) / ms); const e = 1 - Math.pow(1 - t, 3); el.textContent = fmt(Math.round(from + (to - from) * e)); t < 1 ? requestAnimationFrame(step) : resolve(); })(start); });
  }

  let current = Object.assign({}, RANGES[0]), rangeIdx = 0;
  function setRange(i, animate) {
    rangeIdx = i; current = Object.assign({}, RANGES[i]);
    pills.forEach((p, n) => p.classList.toggle('on', n === i));
    bars.forEach((b, n) => {
      const bar = b.querySelector('b');
      b.querySelector('small').textContent = current.labels[n];
      b.style.visibility = current.labels[n] ? '' : 'hidden';
      if (animate) bar.style.setProperty('--h', '0%');
      requestAnimationFrame(() => requestAnimationFrame(() => bar.style.setProperty('--h', current.bars[n] + '%')));
    });
    const o = current.out, total = o[0] + o[1];
    q('[data-dx-out="o"]').textContent = o[0].toLocaleString() + ' · ' + Math.round(o[0] / total * 100) + '%';
    q('[data-dx-out="f"]').textContent = o[1].toLocaleString() + ' · ' + Math.round(o[1] / total * 100) + '%';
    q('.dx-track b.g').style.setProperty('--w', Math.round(o[0] / total * 100) + '%');
    q('.dx-track b.r').style.setProperty('--w', Math.round(o[1] / total * 100) + '%');
    const ms = animate ? 1100 : 0;
    countTo(stat('calls'), 0, current.calls, v => v.toLocaleString(), ms);
    countTo(stat('rate'), 0, current.rate, v => v + '%', ms);
    countTo(stat('talk'), 0, current.talk, mmss, ms);
    countTo(stat('contacts'), 0, current.contacts, v => v.toLocaleString(), ms);
    countTo(stat('follow'), 0, current.follow, v => v.toLocaleString(), ms);
  }

  /* ---------- example data and views ---------- */
  const LOGS = [
    ['Michael Turner', '+1 415 555 0132', 'Outgoing', '3:12', 'Today 10:42'], ['Olivia Bennett', '+44 7700 900123', 'Outgoing', '1:48', 'Today 10:15'],
    ['Robert Hayes', '+1 713 555 0124', 'Incoming', '0:56', 'Today 09:51'], ['Grace Collins', '+61 491 570 006', 'Missed', '-', 'Today 09:20'],
    ['Liam Foster', '+1 212 555 0147', 'Outgoing', '5:03', 'Yesterday 17:44'], ['Sofia Alvarez', '+44 20 7946 0321', 'Incoming', '2:21', 'Yesterday 16:02']];
  const CONTACTS = [['Michael Turner', '+14155550132', 'Callback'], ['Olivia Bennett', '+447700900123', 'Interested'], ['Robert Hayes', '+17135550124', 'New'], ['Grace Collins', '+61491570006', 'Interested'], ['Liam Foster', '+12125550147', 'Callback'], ['Sofia Alvarez', '+442079460321', 'New']];
  const CRM = { New: ['Robert Hayes', 'Sofia Alvarez'], Interested: ['Olivia Bennett', 'Grace Collins'], Callback: ['Michael Turner', 'Liam Foster'], Won: ['Hannah Price'] };
  const CRM_ORDER = ['New', 'Interested', 'Callback', 'Won'];
  const QUEUE = ['Michael Turner', 'Olivia Bennett', 'Robert Hayes', 'Grace Collins', 'Liam Foster'];
  const CAMPS = [['Spring follow-ups', 64, true], ['UK enquiries', 38, true], ['Win-back list', 81, false]];
  const FOLLOW = [['Send quote to Olivia Bennett', 'Today 14:00', false], ['Call Michael Turner back', 'Today 16:30', false], ['Confirm viewing with Robert Hayes', 'Tomorrow 10:00', false], ['Check in with Grace Collins', 'Fri 11:15', true]];
  const SCRIPTS = { Opening: 'Hi, this is Sam from Dialnytics. Is now a good time for a two-minute call about your calling setup?', Objections: 'If price comes up: every plan includes taxes, there is no setup fee, and you can add or remove add-ons later.', Closing: 'Great. I will send the plan details on WhatsApp now. Can we agree a start date for your first users?' };
  const SETTINGS = [['Call recording', 'Record calls when you have permission', true], ['Voicemail', 'Let missed callers leave a message', true], ['Do Not Call check', 'Skip leads marked Do Not Call', true], ['Desktop alerts', 'Show a notification for incoming calls', false]];
  const state = { follow: FOLLOW.map(f => f.slice()), camps: CAMPS.map(c => c.slice()), settings: SETTINGS.map(s => s.slice()), crm: JSON.parse(JSON.stringify(CRM)), users: 3, script: 'Opening', logFilter: 'All', queue: { i: -1, running: false, timer: 0 }, recPlay: -1 };
  const other = q('[data-dx-view="other"]'), dash = q('[data-dx-view="dash"]');
  const TITLES = { dash: 'Dashboard', logs: 'Call Logs', rec: 'Recordings', contacts: 'Contacts', crm: 'CRM', power: 'Power Dialer', camp: 'Campaigns', follow: 'Follow-ups', script: 'Script', billing: 'Billing', settings: 'Settings' };
  let view = 'dash', searchTerm = '';
  const head = (k, extra) => '<div class="dx-head"><h4>' + TITLES[k] + '</h4>' + (extra || '') + '</div>';
  const chip = (s) => '<em class="dx-chip ' + s.toLowerCase() + '">' + s + '</em>';

  function pricePlan(n) { return n === 1 ? 22 : n === 2 ? 40 : 18 * n; }
  const R = {
    logs() {
      const rows = LOGS.filter(r => state.logFilter === 'All' || r[2] === state.logFilter);
      return head('logs', '<div class="dx-pills">' + ['All', 'Outgoing', 'Incoming', 'Missed'].map(f => '<span role="button" tabindex="0" data-dx-filter="' + f + '" class="' + (state.logFilter === f ? 'on' : '') + '">' + f + '</span>').join('') + '</div>') +
        '<div class="dx-card dx-tbl"><div class="dx-tr dx-th"><span>Contact</span><span>Number</span><span>Type</span><span>Talk</span><span>When</span></div>' +
        rows.map(r => '<div class="dx-tr"><span><b>' + esc(r[0]) + '</b></span><span>' + esc(r[1]) + '</span><span>' + chip(r[2]) + '</span><span>' + r[3] + '</span><span>' + r[4] + '</span></div>').join('') + '</div>';
    },
    rec() {
      const rows = LOGS.filter(r => r[2] !== 'Missed');
      return head('rec') + '<div class="dx-card dx-tbl">' + rows.map((r, i) => '<div class="dx-tr dx-rec"><span role="button" tabindex="0" class="dx-play' + (state.recPlay === i ? ' on' : '') + '" data-dx-play="' + i + '" aria-label="Play recording">' + (state.recPlay === i ? '&#10074;&#10074;' : '&#9654;') + '</span><span><b>' + esc(r[0]) + '</b><small>' + r[4] + '</small></span><span class="dx-prog"><b style="width:' + (state.recPlay === i ? '100%' : '0%') + '"></b></span><span>' + r[3] + '</span></div>').join('') + '</div>';
    },
    contacts() {
      const t = searchTerm.toLowerCase();
      const rows = CONTACTS.filter(c => !t || c[0].toLowerCase().includes(t) || c[1].includes(t));
      return head('contacts') + '<div class="dx-card dx-tbl">' + (rows.length ? rows.map(c => '<div class="dx-tr dx-ct"><span><b>' + esc(c[0]) + '</b></span><span>' + pretty(c[1]) + '</span><span>' + chip(c[2]) + '</span><span role="button" tabindex="0" class="dx-btn" data-dx-callnum="' + c[1] + '">Call</span></div>').join('') : '<p class="dx-tip">No contacts match "' + esc(searchTerm) + '".</p>') + '</div>';
    },
    crm() {
      return head('crm') + '<p class="dx-tip dx-tipline">Click a lead to move it to the next stage.</p><div class="dx-cols">' + CRM_ORDER.map(k => '<div class="dx-col"><h5>' + k + ' <small>' + state.crm[k].length + '</small></h5>' + state.crm[k].map(n => '<div class="dx-lead" role="button" tabindex="0" data-dx-lead="' + k + '|' + esc(n) + '">' + esc(n) + '</div>').join('') + '</div>').join('') + '</div>';
    },
    power() {
      const qs = state.queue;
      return head('power', '<span role="button" tabindex="0" class="dx-btn ' + (qs.running ? 'warn' : 'go') + '" data-dx-queue>' + (qs.running ? 'Pause queue' : qs.i >= QUEUE.length - 1 ? 'Restart queue' : 'Start queue') + '</span>') +
        '<div class="dx-card dx-tbl">' + QUEUE.map((n, i) => { const st = i < qs.i ? 'Done' : i === qs.i ? (qs.running ? 'Calling' : 'Paused') : 'Queued'; return '<div class="dx-tr dx-q' + (i === qs.i ? ' now' : '') + '"><span><b>' + esc(n) + '</b></span><span>' + chip(st) + '</span></div>'; }).join('') + '</div>' +
        '<div class="dx-card"><h5>Call notes</h5><p class="dx-tip">Confirm the requirements. Agree a clear next step.</p></div>';
    },
    camp() {
      return head('camp') + '<div class="dx-camps">' + state.camps.map((c, i) => '<div class="dx-card"><h5>' + c[0] + '</h5><div class="dx-line"><span>Progress</span><span>' + c[1] + '%</span></div><div class="dx-track"><b class="g" style="--w:' + c[1] + '%"></b></div><span role="button" tabindex="0" class="dx-btn ' + (c[2] ? 'go' : '') + '" data-dx-camp="' + i + '">' + (c[2] ? 'Active, click to pause' : 'Paused, click to resume') + '</span></div>').join('') + '</div>';
    },
    follow() {
      return head('follow') + '<div class="dx-card dx-tbl">' + state.follow.map((f, i) => '<div class="dx-tr dx-fu' + (f[2] ? ' done' : '') + '"><span role="button" tabindex="0" class="dx-check' + (f[2] ? ' on' : '') + '" data-dx-follow="' + i + '" aria-label="Mark done">' + (f[2] ? '&#10003;' : '') + '</span><span><b>' + f[0] + '</b></span><span>' + f[1] + '</span></div>').join('') + '</div>';
    },
    script() {
      return head('script', '<div class="dx-pills">' + Object.keys(SCRIPTS).map(k => '<span role="button" tabindex="0" data-dx-script="' + k + '" class="' + (state.script === k ? 'on' : '') + '">' + k + '</span>').join('') + '</div>') + '<div class="dx-card dx-script"><h5>' + state.script + '</h5><p>' + SCRIPTS[state.script] + '</p></div>';
    },
    billing() {
      const n = state.users;
      return head('billing') + '<div class="dx-card"><h5>USA &amp; Canada plan</h5><div class="dx-line"><span>Users</span><span class="dx-step"><span role="button" tabindex="0" class="dx-btn" data-dx-users="-1" aria-label="Fewer users">&minus;</span><b>' + n + '</b><span role="button" tabindex="0" class="dx-btn" data-dx-users="1" aria-label="More users">+</span></span></div><div class="dx-bill"><strong>$' + pricePlan(n) + '<small>/month</small></strong><small>' + (n >= 3 ? '$18 per user, taxes included' : n === 2 ? '2 users, taxes included' : '1 user, taxes included') + '</small></div></div><p class="dx-tip dx-tipline">Example pricing. Your real total is shown in the calculator below.</p>';
    },
    settings() {
      return head('settings') + '<div class="dx-card dx-tbl">' + state.settings.map((s, i) => '<div class="dx-tr dx-set"><span><b>' + s[0] + '</b><small>' + s[1] + '</small></span><span role="button" tabindex="0" class="dx-switch' + (s[2] ? ' on' : '') + '" data-dx-set="' + i + '" aria-label="Toggle ' + s[0] + '"><i></i></span></div>').join('') + '</div>';
    }
  };

  function show(k) {
    view = k;
    qa('[data-dx-nav]').forEach(n => n.classList.toggle('on', n.dataset.dxNav === k));
    const isDash = k === 'dash';
    dash.hidden = !isDash; other.hidden = isDash;
    dash.classList.toggle('on', isDash);
    if (!isDash) other.innerHTML = R[k]();
    if (isDash) setRange(rangeIdx, true);
  }
  const rerender = () => { if (view !== 'dash') other.innerHTML = R[view](); };

  /* ---------- calling ---------- */
  let digits = '', inCall = false, callTimers = [], secs = 0;
  function showInput() { if (digits) { input.textContent = digits; input.classList.add('typed'); } else { input.textContent = PLACEHOLDER; input.classList.remove('typed'); } }
  function setStatus(text, tone) { status.textContent = text; status.dataset.tone = tone || ''; }
  let toastT = 0;
  function note(title, text) { q('[data-dx-toast] strong').textContent = title; q('[data-dx-toast-text]').textContent = text; toast.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => toast.classList.remove('show'), 2600); }

  function startCall(num) {
    if (inCall) return;
    inCall = true; secs = 0;
    digits = num; showInput();
    setStatus('Dialing…', 'warn');
    q('[data-dx-dialed]').textContent = pretty(num);
    q('[data-dx-timer]').textContent = 'Ringing';
    root.classList.add('dx-in-call', 'dx-ringing');
    callTimers.push(setTimeout(() => {
      root.classList.remove('dx-ringing'); root.classList.add('dx-active'); setStatus('Active', 'ok');
      q('[data-dx-ctrl="rec"]').classList.add('on');
      q('[data-dx-timer]').textContent = clock(0);
      callTimers.push(setInterval(() => { q('[data-dx-timer]').textContent = clock(++secs); }, 1000));
    }, 1700));
    setStatus('Ringing', 'warn');
  }
  function endCall(save) {
    if (!inCall) return;
    callTimers.forEach(t => { clearTimeout(t); clearInterval(t); }); callTimers = [];
    const num = digits, dur = secs;
    inCall = false;
    root.classList.remove('dx-active', 'dx-in-call', 'dx-ringing');
    qa('[data-dx-ctrl]').forEach(c => c.classList.remove('on'));
    digits = ''; showInput();
    if (save && dur > 0) {
      LOGS.unshift([(CONTACTS.find(c => c[1] === num) || ['New contact'])[0], pretty(num), 'Outgoing', mmss(dur), 'Just now']);
      const before = current.calls; current.calls += 1;
      countTo(stat('calls'), before, current.calls, v => v.toLocaleString(), 500);
      note('Call saved to Call Logs', pretty(num) + ' · ' + clock(dur) + ' · Recorded');
      setStatus('Completed', 'done');
      setTimeout(() => { if (!inCall) setStatus('Ready', ''); }, 2200);
    } else { setStatus('Ready', ''); }
    rerender();
  }
  function normalise(d) { const n = d.replace(/[^\d+]/g, ''); if (n.startsWith('+')) return n; return n.length === 10 ? '+1' + n : '+' + n; }
  function press(k) { if (inCall) return; if (digits.length < 16) { digits += k; showInput(); } }

  /* ---------- hand over from autoplay ---------- */
  let run = 0, manual = false;
  function takeover() {
    if (manual) return; manual = true; run++;
    callTimers.forEach(t => { clearTimeout(t); clearInterval(t); }); callTimers = [];
    cursor.style.display = 'none'; if (hint) hint.classList.add('off');
    root.classList.remove('dx-in-call', 'dx-ringing', 'dx-active');
    qa('[data-dx-ctrl]').forEach(c => c.classList.remove('on', 'press'));
    qa('.press').forEach(c => c.classList.remove('press'));
    toast.classList.remove('show'); setStatus('Ready', ''); digits = ''; inCall = false; showInput();
  }

  function act(t) {
    const d = t.closest('[data-dx-nav],[data-dx-range],[data-dx-key],[data-dx-call],[data-dx-back],[data-dx-clear],[data-dx-hang],[data-dx-ctrl],[data-dx-filter],[data-dx-play],[data-dx-callnum],[data-dx-lead],[data-dx-queue],[data-dx-camp],[data-dx-follow],[data-dx-script],[data-dx-users],[data-dx-set],.dx-ico,.dx-avatar');
    if (!d) return false;
    takeover();
    const ds = d.dataset;
    if (ds.dxNav) show(ds.dxNav);
    else if (ds.dxRange !== undefined) { if (view !== 'dash') show('dash'); setRange(+ds.dxRange, true); }
    else if (ds.dxKey !== undefined) press(ds.dxKey);
    else if (ds.dxBack !== undefined) { if (!inCall) { digits = digits.slice(0, -1); showInput(); } }
    else if (ds.dxClear !== undefined) { if (!inCall) { digits = ''; showInput(); } }
    else if (ds.dxCall !== undefined) { if (inCall) return true; if (digits.replace(/\D/g, '').length >= 6) startCall(normalise(digits)); else { setStatus('Enter a number first', 'warn'); setTimeout(() => { if (!inCall) setStatus('Ready', ''); }, 1600); } }
    else if (ds.dxHang !== undefined) endCall(true);
    else if (ds.dxCtrl) {
      if (!inCall) return true;
      if (ds.dxCtrl === 'mute' || ds.dxCtrl === 'hold' || ds.dxCtrl === 'rec') d.classList.toggle('on');
      else note(ds.dxCtrl === 'add' ? 'Add Call' : ds.dxCtrl === 'transfer' ? 'Transfer' : 'Keypad', 'Available in the real dialer');
    }
    else if (ds.dxFilter) { state.logFilter = ds.dxFilter; rerender(); }
    else if (ds.dxPlay !== undefined) { state.recPlay = state.recPlay === +ds.dxPlay ? -1 : +ds.dxPlay; rerender(); if (state.recPlay >= 0) { const i = state.recPlay; setTimeout(() => { if (state.recPlay === i && view === 'rec') { state.recPlay = -1; rerender(); } }, 6000); } }
    else if (ds.dxCallnum) { if (!inCall) startCall(ds.dxCallnum); }
    else if (ds.dxLead) { const [k, n] = ds.dxLead.split('|'); const idx = CRM_ORDER.indexOf(k); const to = CRM_ORDER[(idx + 1) % CRM_ORDER.length]; state.crm[k] = state.crm[k].filter(x => x !== n); state.crm[to].push(n); rerender(); }
    else if (ds.dxQueue !== undefined) toggleQueue();
    else if (ds.dxCamp !== undefined) { const c = state.camps[+ds.dxCamp]; c[2] = !c[2]; rerender(); }
    else if (ds.dxFollow !== undefined) { const f = state.follow[+ds.dxFollow]; f[2] = !f[2]; rerender(); }
    else if (ds.dxScript) { state.script = ds.dxScript; rerender(); }
    else if (ds.dxUsers) { state.users = Math.max(1, Math.min(25, state.users + (+ds.dxUsers))); rerender(); }
    else if (ds.dxSet !== undefined) { const s = state.settings[+ds.dxSet]; s[2] = !s[2]; rerender(); }
    else if (d.classList.contains('dx-ico') || d.classList.contains('dx-avatar')) note('Demo only', 'Settings and help are in the real dialer');
    return true;
  }
  function toggleQueue() {
    const qs = state.queue;
    if (qs.running) { qs.running = false; clearTimeout(qs.timer); rerender(); return; }
    if (qs.i >= QUEUE.length - 1 && qs.i !== -1 && !qs.running) { qs.i = -1; }
    qs.running = true;
    (function next() {
      if (!qs.running) return;
      qs.i += 1;
      if (qs.i >= QUEUE.length) { qs.i = QUEUE.length - 1; qs.running = false; note('Queue finished', QUEUE.length + ' calls completed'); if (view === 'power') rerender(); return; }
      if (view === 'power') rerender();
      qs.timer = setTimeout(next, 1700);
    })();
  }

  root.addEventListener('click', e => { if (act(e.target)) e.preventDefault(); });
  root.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[role=button]')) { e.preventDefault(); act(e.target); } });
  const searchEl = q('[data-dx-search]');
  searchEl.addEventListener('focus', takeover);
  searchEl.addEventListener('input', () => { takeover(); searchTerm = searchEl.value.trim(); if (view !== 'contacts') show('contacts'); else rerender(); });

  // make the interactive pieces reachable from the keyboard
  qa('[data-dx-nav],[data-dx-range],[data-dx-key],[data-dx-call],[data-dx-back],[data-dx-clear],[data-dx-hang],[data-dx-ctrl],.dx-ico,.dx-avatar').forEach(el => { el.setAttribute('role', 'button'); el.tabIndex = 0; });
  qa('[data-dx-nav]').forEach(el => el.setAttribute('aria-label', 'Open ' + el.textContent.trim()));
  q('[data-dx-call]').setAttribute('aria-label', 'Start call'); q('[data-dx-hang]').setAttribute('aria-label', 'End call'); q('[data-dx-back]').setAttribute('aria-label', 'Delete last digit'); q('[data-dx-clear]').setAttribute('aria-label', 'Clear number');

  /* ---------- autoplay demo (stops on first interaction) ---------- */
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { root.classList.add('dx-static'); setRange(0, false); if (hint) hint.classList.add('off'); return; }

  let visible = false;
  if ('IntersectionObserver' in window) new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }, { threshold: 0.15 }).observe(root); else visible = true;
  const sleep = ms => { const r0 = run; return new Promise(resolve => { let left = ms, last = performance.now(); (function wait() { if (run !== r0) return; const now = performance.now(); if (visible && !document.hidden) left -= now - last; last = now; left <= 0 ? resolve() : setTimeout(wait, 40); })(); }); };
  function point(el) { const scale = fit(); const c = canvas.getBoundingClientRect(), r = el.getBoundingClientRect(); return [(r.left - c.left + r.width * 0.55) / scale, (r.top - c.top + r.height * 0.6) / scale]; }
  async function moveTo(el, ms = 650) { const [x, y] = point(el); cursor.style.transitionDuration = ms + 'ms'; cursor.style.transform = 'translate(' + x + 'px,' + y + 'px)'; await sleep(ms + 60); }
  async function tap(el) { cursor.classList.add('down'); el.classList.add('press'); await sleep(170); cursor.classList.remove('down'); el.classList.remove('press'); }

  async function loop() {
    const my = ++run;
    let r = 0, n = 0;
    setRange(0, true);
    await sleep(1800);
    while (my === run) {
      const num = NUMBERS[n % NUMBERS.length];
      digits = '+'; showInput();
      for (const d of num.slice(1)) { const key = q('[data-dx-key="' + d + '"]'); await moveTo(key, 260); await tap(key); digits += d; showInput(); }
      const call = q('[data-dx-call]');
      await moveTo(call, 500); await tap(call);
      if (my !== run) return;
      startCall(num);
      await sleep(1700 + 1900);
      const mute = q('[data-dx-ctrl="mute"]');
      await moveTo(mute, 500); await tap(mute); mute.classList.add('on');
      await sleep(1500); await tap(mute); mute.classList.remove('on');
      await sleep(1300);
      const hang = q('.dx-hang');
      await moveTo(hang, 550); await tap(hang);
      if (my !== run) return;
      endCall(true);
      await sleep(3200);
      if (my !== run) return;
      r = (r + 1) % RANGES.length; n += 1;
      await moveTo(pills[r], 700); await tap(pills[r]);
      setRange(r, true);
      await sleep(2200);
    }
  }
  requestAnimationFrame(() => { fit(); loop(); });
})();
