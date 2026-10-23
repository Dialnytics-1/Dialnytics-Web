'use strict';
/* Dialnytics product tour v6 - real dialer screens (demo data) with optional voice-over via the browser's speech engine. */
(() => {
const $ = s => document.querySelector(s);
const wrap = $('#wrap'), stage = $('#stage'), cam = $('#cam'), shots = $('#shots'), spot = $('#spot'), cur = $('#cur'),
  typed = $('#typed'), cap = $('#cap'), chap = $('#chap'), title = $('#title'), ui = $('#ui'), bar = $('#bar'), menu = $('#menu'),
  big = $('#big'), voBtn = $('#vo'), voPill = $('#vpill');
const SW = 1280, SH = 720, BASE = '/static/product-tour/screens/';

/* Each step: s screen, c caption, v narration, k spotlight, z/zk zoom, m cursor target, clk click, after screen shown after the click, t minimum ms. */
const nav = (key, screen, c, v) => ({k: 'dash.' + key, m: 'dash.' + key, clk: 1, after: screen, c, v});
const CH = [
 {n: 'Welcome', steps: [{title: 'intro', t: 4200, v: 'Welcome to Dialnytics, the smart cloud dialer for business calling.'}]},
 {n: 'Sign in', steps: [
  {s: 'login', z: 1, k: 'hero', c: 'Open <b>dialnytics.co.uk</b> in any modern browser — nothing to install', v: 'Dialnytics runs in your browser, so there is nothing to install.'},
  {z: 1.5, zk: 'card', k: 'email', m: 'email', clk: 1, c: 'Sign in with the email and password from your activation', v: 'Sign in with the email and password from your activation.'},
  {k: 'btn', m: 'btn', clk: 1, after: 'dash', c: '<b>Show</b> checks your password — then press <b>Sign in</b>', v: 'Use show to check your password, then press sign in.'}]},
 {n: 'Dashboard', steps: [
  {s: 'dash', z: 1, k: 'nav', c: 'Every page is one click away in the <b>sidebar</b>', v: 'Your dashboard opens first. Every page is one click away in the sidebar.'},
  {k: 'stats', z: 1.45, zk: 'stats', c: 'Total calls, answer rate, average talk time, contacts and follow-ups', v: 'See total calls, answer rate, talk time, contacts and follow-ups.'},
  {k: 'chart', z: 1.35, zk: 'chart', c: '<b>Calls Over Time</b> and <b>Call Outcomes</b>', v: 'The charts show when you call, and how many calls connect.'},
  {k: 'seg', z: 1.9, zk: 'seg', m: 'week', clk: 1, after: 'dash_week', c: 'Switch between <b>Today</b>, <b>This Week</b> and <b>This Month</b>', v: 'Switch between today, this week and this month.'}]},
 {n: 'Make a call', steps: [
  {s: 'dash_week', z: 1.7, zk: 'dash.rail', k: 'dash.rail', c: 'The <b>dialer</b> sits on the right of every page', v: 'The dialer is always on the right.'},
  {s: 'dash', k: 'dial.pad', typ: '+14155550132', c: 'Type or <b>paste</b> a number in international format', v: 'Type a number in international format, or paste it from your clipboard.'},
  {s: 'dial', k: 'call', m: 'call', clk: 1, after: 'calling', c: 'Press the green button to call', v: 'Press the green button.'},
  {s: 'calling', k: 'state', c: '<b>Calling…</b> → <b>Ringing</b> → <b>Active</b>', v: 'The status moves from calling, to ringing,', t: 1800},
  {s: 'active', k: 'state', c: '<b>Active</b> — connected with your dedicated caller ID', v: 'to active, using your dedicated caller ID.'}]},
 {n: 'In-call controls', steps: [
  {s: 'active', z: 1.75, zk: 'grid', k: 'mute', m: 'mute', clk: 1, after: 'muted', c: '<b>Mute</b> your microphone', v: 'During a call, mute your microphone,'},
  {s: 'muted', k: 'active.hold', m: 'active.hold', clk: 1, after: 'hold', c: '<b>Hold</b> the caller — <b>Resume</b> when ready', v: 'put the caller on hold,'},
  {s: 'hold', k: 'active.keypad', m: 'active.keypad', clk: 1, after: 'dtmf', c: 'The <b>Keypad</b> sends digits to phone menus', v: 'or open the keypad for phone menus.'},
  {s: 'active', k: 'rec', m: 'rec', c: '<b>REC</b> records the call — <b>STOP</b> saves it', v: 'Rec records the call, and stop saves it to recordings.'},
  {k: 'transfer', m: 'transfer', clk: 1, after: 'transfer', c: '<b>Transfer</b> the caller to another number', v: 'Transfer sends the caller to another number.'},
  {s: 'active', z: 1.75, zk: 'active.grid', k: 'add', m: 'add', clk: 1, after: 'calllist', c: '<b>Add Call</b> holds the first caller and dials a second', v: 'Add call holds the first caller and dials a second,'},
  {s: 'calllist', k: 'calls', c: '<b>Call List</b> shows every call — hang up either one', v: 'and the call list shows both.'},
  {s: 'active', k: 'hang', m: 'hang', clk: 1, c: 'Hang up — every call is saved to <b>Call Logs</b>', v: 'Hang up when you are done. Every call is saved.'}]},
 {n: 'Incoming calls', steps: [
  {s: 'incoming', z: 1.7, zk: 'incoming', k: 'answer', m: 'answer', clk: 1, c: '<b>Incoming calls</b> ring in your browser — <b>Answer</b> or <b>Decline</b>', v: 'Incoming calls ring in your browser. Answer or decline with one click.'}]},
 {n: 'Call Logs', steps: [
  nav('nav_logs', 'logs', '<b>Call Logs</b> — direction, status and duration of every call', 'Call logs lists every call, with status and duration.'),
  {s: 'logs', k: 'chips', z: 1.6, zk: 'chips', m: 'incoming', clk: 1, c: 'Filter by <b>All</b>, <b>Incoming</b>, <b>Outgoing</b> or <b>Missed</b>', v: 'Filter incoming, outgoing or missed calls,'},
  {k: 'callbtn', z: 1.5, zk: 'row', m: 'callbtn', clk: 1, c: 'Call anyone back with one click', v: 'and call anyone back with one click.'}]},
 {n: 'Recordings', steps: [
  nav('nav_recs', 'recs', '<b>Recordings</b> — every recorded call in one place', 'Recordings keeps every recorded call in one place,'),
  {s: 'recs', k: 'row', z: 1.6, zk: 'row', m: 'audio', clk: 1, c: 'Number, date, length — and play it right in the browser', v: 'with the number, date and length. Press play to listen in the browser.'}]},
 {n: 'Contacts', steps: [
  nav('nav_contacts', 'contacts', 'Save and call your <b>Contacts</b>', 'In contacts, save the people you call,'),
  {s: 'contacts', k: 'new', m: 'new', clk: 1, c: 'Add a contact with <b>+ New</b> — call from the list', v: 'add new ones, and call them from the list.'}]},
 {n: 'CRM', steps: [
  nav('nav_crm', 'crm', 'The <b>CRM</b> — manage your leads', 'The CRM is where you manage your leads.'),
  {s: 'crm', z: 1.45, zk: 'stats', k: 'stats', c: 'Total leads, consented, callbacks and Do Not Call', v: 'It tracks consent, callbacks and do not call numbers.'},
  {z: 1.2, zk: 'table', k: 'table', c: 'Status, consent and next follow-up for every lead', v: 'Every lead shows its status, consent and next follow-up.'},
  {k: 'dnc_row', c: 'Leads marked <b>Do Not Call</b> are clearly flagged', v: 'Do not call leads are clearly flagged.'},
  {z: 1.5, zk: 'toolbar', k: 'toolbar', m: 'search', c: 'Search by name, phone or email — filter by status', v: 'Search, or filter by status.'},
  {z: 1, k: 'add', m: 'add', clk: 1, after: 'crm_add', c: '<b>Add Lead</b> with status, follow-up time and notes', v: 'Add lead saves details, a follow-up time and notes,'},
  {s: 'crm_add', z: 1.45, zk: 'dialog', k: 'consent', m: 'consent', c: 'Record <b>explicit calling consent</b> first', v: 'with explicit calling consent.'},
  {s: 'crm', z: 1.2, zk: 'help', k: 'help', m: 'csv', c: '<b>Import CSV</b> — up to 500 consented leads', v: 'You can also import up to five hundred leads from a CSV file.'}]},
 {n: 'Power Dialer', steps: [
  nav('nav_power', 'power', 'The <b>Power Dialer</b> calls your CRM leads one after another', 'The power dialer calls your leads one after another.'),
  {s: 'power', z: 1.3, zk: 'setup', k: 'mode', m: 'mode', c: '<b>Manual</b> or <b>Auto</b> mode, with a 3–30 second delay', v: 'Choose manual or auto mode, and a delay between calls.'},
  {k: 'create', m: 'create', clk: 1, after: 'power_pick', c: 'Create a queue from eligible leads', v: 'Create a queue,'},
  {s: 'power_pick', z: 1.4, zk: 'dialog', k: 'opts', m: 'confirm', clk: 1, after: 'power_run', c: 'Only consented leads not on Do Not Call can be picked', v: 'and pick leads. Only consented leads can be selected.'},
  {s: 'power_run', z: 1.4, zk: 'stats', k: 'stats', c: 'Track <b>Queued</b>, <b>Completed</b> and <b>Remaining</b>', v: 'Track queued, completed and remaining calls.'},
  {z: 1.6, zk: 'controls', k: 'controls', c: '<b>Start</b>, <b>Pause</b>, <b>Stop</b> or <b>Skip</b> at any time', v: 'Start, pause, stop or skip at any time.'},
  {s: 'power_out', z: 1.3, zk: 'notes', k: 'notes', c: 'Type <b>call notes</b> while you talk', v: 'Type notes while you talk,'},
  {k: 'outcomes', z: 1.5, zk: 'outcomes', m: 'interested', clk: 1, c: 'Save the outcome — then on to the next lead', v: 'save the outcome, and move to the next lead.'}]},
 {n: 'Campaigns', steps: [
  nav('nav_campaigns', 'campaigns', '<b>Campaigns</b> keep lists of numbers to work through', 'Campaigns keep lists of numbers to work through.')]},
 {n: 'Scripts', steps: [
  nav('nav_script', 'scripts', 'Write <b>call scripts</b> with formatting', 'Scripts help you write call scripts with formatting,'),
  {s: 'scripts', k: 'toolbar', m: 'toolbar', z: 1.3, zk: 'editor', c: 'Format with bold, italic, lists and links', v: 'Format them with bold, lists and links,'},
  {k: 'default', m: 'default', c: 'Set your most-used script as the <b>default</b>', v: 'and set a default script.'}]},
 {n: 'Billing', steps: [
  nav('nav_billing', 'billing', '<b>Billing</b> — plan, renewal date and days remaining', 'Billing shows your plan, renewal date and days left.'),
  {s: 'billing', z: 1.35, zk: 'plan', k: 'pay', c: 'Payment options open 3 days before your renewal', v: 'Payment options open three days before renewal.'}]},
 {n: 'Workspace tools', steps: [
  {s: 'billing', k: 'dash.collapse', m: 'dash.collapse', clk: 1, after: 'collapsed', c: 'Collapse the sidebar for more room', v: 'Collapse the sidebar for more room,'},
  {s: 'collapsed', k: 'dash.help', m: 'dash.help', c: '<b>?</b> opens WhatsApp support from any page', v: 'use the question mark for WhatsApp support,'},
  {s: 'collapsed', k: 'dash.theme', m: 'dash.theme', clk: 1, after: 'light', c: 'Switch between <b>dark</b> and <b>light</b> themes', v: 'or switch to the light theme.'}]},
 {n: 'Profile menu', steps: [
  {s: 'light', m: 'theme', clk: 1, after: 'dash', t: 1300},
  {s: 'dash', k: 'avatar', m: 'avatar', clk: 1, after: 'profile_open', c: 'Your <b>profile icon</b> opens account options', v: 'Your profile icon opens account options.'},
  {s: 'profile_open', z: 1.3, zk: 'menu', k: 'head', c: 'Your name, account type and <b>Online</b> status', v: 'You see your name and online status.'},
  {k: 'dnd', m: 'dnd', clk: 1, after: 'profile', c: '<b>Do Not Disturb</b> silences incoming calls', v: 'Do not disturb silences incoming calls.'},
  {s: 'profile', k: 'e_dash', m: 'e_dash', c: '<b>Dashboard</b>', v: 'Open the dashboard,', t: 1500},
  {k: 'e_pref', m: 'e_pref', c: '<b>My Profile</b> and <b>Calling Preferences</b>', v: 'your profile and calling preferences,'},
  {k: 'e_bill', m: 'e_bill', c: '<b>Billing</b>', v: 'billing,', t: 1400},
  {k: 'e_help', m: 'e_help', c: '<b>Help &amp; Support</b> on WhatsApp', v: 'help and support,'},
  {k: 'e_tour', m: 'e_tour', c: '<b>Keyboard Shortcuts</b> and <b>Take the Tour</b>', v: 'keyboard shortcuts, and the quick tour.'},
  {k: 'e_out', m: 'e_out', c: '<b>Sign Out</b> ends your session securely', v: 'Sign out ends your session.'},
  {k: 'e_me', m: 'e_me', clk: 1, after: 'settings', t: 1500},
  {s: 'settings', z: 1.45, zk: 'panel', k: 'panel', c: 'Your name, email, <b>caller ID</b> and plan renewal', v: 'My profile shows your caller ID and renewal date.'}]},
 {n: 'Get started', steps: [{title: 'outro', t: 5200, v: 'Ready to see it live? Book a fifteen minute demo at dialnytics dot com.'}]}
];

let R = {};
let VO = null;            // recorded voice-over manifest (voice/voice.json), optional
const steps = [];
const imgs = {};
let totalMs = 0;
const MS_PER_WORD = 335;            // estimate at speech rate 1.1
const speechMs = v => v ? v.split(/\s+/).length * MS_PER_WORD + 450 : 0;

function rect(screen, key) {
  if (!key) return null;
  const [s, k] = key.includes('.') ? key.split('.') : [screen, key];
  return (R[s] && R[s][k]) || null;
}
const centre = r => [r[0] + r[2] * 0.5, r[1] + r[3] * 0.55];

function build() {
  CH.forEach(ch => {
    ch.start = totalMs; ch.first = steps.length;
    let screen = null, zoom = {z: 1, r: null}, curPos = [62, 80], caption = '', li = 0;
    const vo = VO && VO[CH.indexOf(ch)];
    if (steps.length) { const p = steps[steps.length - 1]; screen = p.endScreen; curPos = p.endCur; }
    ch.steps.forEach((st, si) => {
      const step = Object.assign({}, st, {ci: CH.indexOf(ch), first: si === 0});
      if (st.s) screen = st.s;
      step.screen = screen;
      if (st.z !== undefined) zoom = {z: st.z, r: st.z > 1 ? rect(screen, st.zk || st.k) : null};
      else if (si === 0) zoom = {z: 1, r: null};
      step.cam = zoom;
      step.spot = rect(screen, st.k);
      step.startCur = curPos;
      step.move = st.m ? rect(screen, st.m) : null;
      if (step.move) curPos = centre(step.move);
      ['k', 'm', 'zk'].forEach(f => { if (st[f] && !rect(screen, st[f])) console.warn('tour: missing target', ch.n, screen, st[f]); });
      // Visual time needed for the actions, then stretch to fit the narration.
      let need = 650 + (st.m ? 880 : 0) + (st.clk ? 330 : 0) + (st.after ? 250 : 0);
      if (st.typ) need = 700 + st.typ.length * 330 + 500;
      if (st.v && vo && vo.lines[li]) { step.seg = vo.lines[li]; step.file = vo.file; }
      if (st.v) li++;
      const talk = step.seg ? (step.seg[1] - step.seg[0]) * 1000 : speechMs(st.v);
      step.t = Math.max(st.t || 0, need, talk + 150);
      if (st.c !== undefined) caption = st.c; else if (si === 0) caption = '';
      step.caption = caption;
      step.endCur = curPos;
      step.endScreen = st.after || screen;
      if (st.after) screen = st.after;
      step.start = totalMs; totalMs += step.t;
      steps.push(step);
    });
    ch.ms = totalMs - ch.start;
  });
}

/* ---------- voice-over (browser speech engine) ---------- */
const synth = window.speechSynthesis;
let voiceOn = false, voice = null, speakToken = 0, speaking = false;
const PREFER = [/(Aria|Jenny|Ava|Emma|Michelle|Sonia|Libby|Natasha).*(Natural|Online)/i, /Google US English/i, /Samantha/i, /Google UK English Female/i,
  /Microsoft (Aria|Jenny|Zira|Hazel|Susan)/i, /(Karen|Moira|Tessa|Serena|Victoria|Allison|Ava|Susan|Fiona|Kate|Nicky)/i, /female|woman/i];
function pickVoice() {
  if (!synth) return null;
  const vs = synth.getVoices().filter(v => /^en(-|_|$)/i.test(v.lang));
  for (const re of PREFER) { const v = vs.find(x => re.test(x.name)); if (v) return v; }
  return vs.find(v => /en-US/i.test(v.lang)) || vs[0] || null;
}
/* Recorded voice-over: decoded with the Web Audio API so each line plays exactly (no media-src/blob CSP needed). */
let actx = null, curSrc = null;
const buffers = {};
function audioCtx() {
  if (!actx) { const C = window.AudioContext || window.webkitAudioContext; if (C) actx = new C(); }
  return actx;
}
function loadBuf(file) {
  const c = audioCtx();
  if (!c) return Promise.resolve(null);
  if (!buffers[file]) {
    buffers[file] = fetch('/static/product-tour/voice/' + file)
      .then(r => { if (!r.ok) throw Error(r.status); return r.arrayBuffer(); })
      .then(ab => new Promise((res, rej) => c.decodeAudioData(ab, res, rej)))
      .catch(() => null);
  }
  return buffers[file];
}
function speakTTS(text, token) {
  if (!synth || !text) { speaking = false; return; }
  const u = new SpeechSynthesisUtterance(text);
  if (!voice) voice = pickVoice();
  if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = 'en-US';
  u.rate = 1.1; u.pitch = 1.05;
  const done = () => { if (token === speakToken) speaking = false; };
  u.onend = done; u.onerror = done;
  setTimeout(done, speechMs(text) * 2 + 2500);
  synth.speak(u);
}
function stopSrc() { if (curSrc) { try { curSrc.onended = null; curSrc.stop(); } catch (e) {} curSrc = null; } }
// Plays this step's line: the recorded segment when available, otherwise the browser voice.
function speakStep(st) {
  const token = ++speakToken;
  if (synth) synth.cancel();
  stopSrc(); speaking = false;
  if (!voiceOn || !st || !st.v) return;
  speaking = true;
  const c = st.seg ? audioCtx() : null;
  if (!c) { speakTTS(st.v, token); return; }
  if (!paused && c.state === 'suspended') c.resume().catch(() => {});
  let started = false;
  loadBuf(st.file).then(buf => {
    if (token !== speakToken) return;
    if (!buf) { speakTTS(st.v, token); return; }
    const src = c.createBufferSource(); src.buffer = buf; src.connect(c.destination);
    src.onended = () => { if (token === speakToken) { speaking = false; curSrc = null; } };
    const from = Math.max(0, st.seg[0]), len = Math.max(0.05, Math.min(buf.duration, st.seg[1]) - from);
    src.start(0, from, len); curSrc = src; started = true;
  });
  setTimeout(() => { if (token === speakToken && !started) speakTTS(st.v, token); }, 6000);   // file never arrived
}
function stopVoice() { speakToken++; speaking = false; if (synth) synth.cancel(); stopSrc(); }
function pauseVoice() { if (curSrc && actx) actx.suspend().catch(() => {}); else stopVoice(); }
function resumeVoice() {
  if (!voiceOn) return;
  if (curSrc && speaking && actx) actx.resume().catch(() => {});
  else if (steps[idx] && !ended) speakStep(steps[idx]);
}
function setVoice(on) {
  voiceOn = on && (!!synth || !!VO);
  voBtn.setAttribute('aria-pressed', String(voiceOn));
  voBtn.setAttribute('aria-label', voiceOn ? 'Turn voice-over off' : 'Turn voice-over on');
  voBtn.classList.toggle('on', voiceOn);
  voPill.hidden = voiceOn || !(synth || VO);
  if (voiceOn && VO) { const c = audioCtx(); if (c && c.state === 'suspended') c.resume().catch(() => {}); Object.values(VO).forEach(v => loadBuf(v.file)); }
  if (voiceOn) { const st = steps[idx]; if (st && !paused) speakStep(st); } else stopVoice();
}
if (synth) synth.onvoiceschanged = () => { voice = pickVoice(); };


/* ---------- rendering helpers ---------- */
function fit() { stage.style.transform = 'scale(' + wrap.clientWidth / SW + ')'; }
addEventListener('resize', fit);
let shown = null;
function showScreen(name) {
  if (!name || name === shown) return;
  if (!imgs[name]) loadImg(name);
  Object.entries(imgs).forEach(([n, im]) => im.classList.toggle('on', n === name));
  shown = name;
}
function loadImg(name) {
  const im = new Image(); im.className = 'scr'; im.alt = ''; im.decoding = 'async';
  im.src = BASE + name + '.jpg'; shots.appendChild(im); imgs[name] = im; return im;
}
let camScale = 1;
function setCam(c) {
  let s = c && c.r ? c.z : 1, tx = 0, ty = 0;
  if (s > 1) {
    const cx = (c.r[0] + c.r[2] / 2) / 100 * SW, cy = (c.r[1] + c.r[3] / 2) / 100 * SH;
    tx = Math.min(0, Math.max(SW - SW * s, SW / 2 - cx * s));
    ty = Math.min(0, Math.max(SH - SH * s, SH / 2 - cy * s));
  }
  camScale = s;
  cam.style.transform = 'translate(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px) scale(' + s + ')';
  cur.style.setProperty('--inv', (1 / s).toFixed(3));
}
function setSpot(r) {
  if (!r) { spot.classList.remove('on'); return; }
  Object.assign(spot.style, {left: (r[0] - 0.45) + '%', top: (r[1] - 0.8) + '%', width: (r[2] + 0.9) + '%', height: (r[3] + 1.6) + '%'});
  spot.style.borderRadius = Math.max(6, 12 / camScale) + 'px';
  spot.classList.add('on');
}
function setCur(p) { cur.style.left = p[0] + '%'; cur.style.top = p[1] + '%'; }
function setCaption(html, animate) {
  if (!html) { cap.classList.remove('on'); return; }
  if (cap.innerHTML !== html) {
    cap.innerHTML = html;
    if (animate) { cap.classList.remove('swap'); void cap.offsetWidth; cap.classList.add('swap'); }
  }
  cap.classList.add('on');
}
function setChapter(ci, flash) {
  const ch = CH[ci], show = !steps[ch.first].title;
  chap.querySelector('em').textContent = ci;
  chap.querySelector('span').textContent = ch.n;
  chap.classList.toggle('on', show);
  if (flash && show) { chap.classList.remove('flash'); void chap.offsetWidth; chap.classList.add('flash'); }
  $('#cname').textContent = ch.n;
  $('#stp').textContent = ci + ' / ' + (CH.length - 2);
  menu.querySelectorAll('button').forEach((b, i) => b.classList.toggle('on', i === ci));
}
function ripple(p) {
  const r = document.createElement('span'); r.className = 'ripple';
  r.style.left = p[0] + '%'; r.style.top = p[1] + '%'; r.style.transform = 'scale(' + (1 / camScale) + ')';
  cam.appendChild(r); setTimeout(() => r.remove(), 650);
}
function showTitle(kind) {
  $('#tsub').textContent = kind === 'outro' ? 'See it live — book a 15-minute demo at dialnytics.com' : 'A complete walkthrough of the Dialnytics dialer';
  title.classList.remove('gone', 'show'); void title.offsetWidth; title.classList.add('show');
}
function snap(on) { [cam, spot, cur].forEach(el => el.style.transition = on ? 'none' : ''); }

/* ---------- timing ---------- */
let run = 0, paused = false, idx = 0, stepElapsed = 0, ended = false;
const sleep = ms => { const r0 = run; return new Promise(res => {
  let left = ms, last = performance.now();
  (function w() {
    if (run !== r0) return;
    const now = performance.now(), d = now - last; last = now;
    if (!paused && !document.hidden) { left -= d; stepElapsed += d; }
    left <= 0 ? res() : setTimeout(w, 30);
  })();
}); };

async function doStep(st, my) {
  const ok = () => my === run;
  stepElapsed = 0;
  speakStep(st);
  if (VO && voiceOn) { const nx = steps[steps.indexOf(st) + 1]; if (nx && nx.file) loadBuf(nx.file); }
  if (st.title) {
    setCaption(''); setSpot(null); chap.classList.remove('on'); typed.classList.remove('on');
    showTitle(st.title); setChapter(st.ci, false);
    await sleep(st.t - 900); if (!ok()) return;
    while (voiceOn && speaking) { await sleep(80); if (!ok()) return; }
    if (st.title === 'intro') title.classList.add('gone');
    await sleep(900); return;
  }
  title.classList.add('gone');
  if (st.first) setChapter(st.ci, true);
  showScreen(st.screen);
  setCam(st.cam);
  setCaption(st.caption, true);
  await sleep(160); if (!ok()) return;
  setSpot(st.spot);
  let used = 160;
  if (st.typ) {
    const ir = rect('dial', 'input');
    Object.assign(typed.style, {left: (ir[0] + 0.15) + '%', top: (ir[1] + 0.3) + '%', width: (ir[2] - 0.3) + '%', height: (ir[3] - 0.6) + '%'});
    typed.textContent = ''; typed.classList.add('on');
    await sleep(240); used += 240; if (!ok()) return;
    for (const ch of st.typ) {
      const key = rect('dial', 'k' + (ch === '+' ? '0' : ch));
      if (key) { cur.style.transitionDuration = '.26s'; setCur(centre(key)); }
      await sleep(300); used += 300; if (!ok()) return;
      if (key) { cur.classList.add('down'); ripple(centre(key)); setTimeout(() => cur.classList.remove('down'), 120); }
      typed.textContent += ch;
      await sleep(30); used += 30; if (!ok()) return;
    }
    cur.style.transitionDuration = '';
  }
  if (st.move) {
    await sleep(180); used += 180; if (!ok()) return;
    setCur(centre(st.move));
    await sleep(660); used += 660; if (!ok()) return;
    if (st.clk) {
      cur.classList.add('down'); ripple(centre(st.move));
      await sleep(170); used += 170; if (!ok()) return;
      cur.classList.remove('down');
      if (st.after) { await sleep(180); used += 180; if (!ok()) return; setSpot(null); showScreen(st.after); }
    }
  }
  await sleep(Math.max(150, st.t - used)); if (!ok()) return;
  while (voiceOn && speaking) { await sleep(80); if (!ok()) return; }   // let the sentence finish
  if (st.typ) typed.classList.remove('on');
}

function applyInstant(i) {
  const st = steps[i];
  snap(true);
  typed.classList.remove('on'); setSpot(null);
  if (st.title) showTitle(st.title);
  else { title.classList.add('gone'); showScreen(st.screen); setCam(st.cam); setCur(st.startCur); setCaption(st.caption, false); }
  void cam.offsetWidth; snap(false);
}
async function runFrom(i) {
  const my = ++run; ended = false; big.classList.remove('on'); stopVoice();
  applyInstant(i); setChapter(steps[i].ci, false);
  for (idx = i; idx < steps.length; idx++) {
    await doStep(steps[idx], my);
    if (my !== run) return;
  }
  ended = true; idx = steps.length - 1; stepElapsed = steps[idx].t;
  setPaused(true); big.classList.add('on');
}
function seekStep(i) { setPaused(false); runFrom(Math.max(0, Math.min(steps.length - 1, i))); }
function seekChapter(ci) { seekStep(CH[Math.max(0, Math.min(CH.length - 1, ci))].first); }
function elapsed() { const st = steps[idx]; return st ? st.start + Math.min(stepElapsed, st.t) : 0; }

/* ---------- controls ---------- */
const PAUSE = '<svg viewBox="0 0 24 24"><rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/></svg>';
const PLAY = '<svg viewBox="0 0 24 24"><path d="M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5z"/></svg>';
function setPaused(p) {
  const was = paused; paused = p;
  const b = $('#pp'); b.innerHTML = p ? PLAY : PAUSE; b.setAttribute('aria-label', p ? 'Play' : 'Pause');
  if (p) pauseVoice();
  else if (was && voiceOn && !ended) resumeVoice();
  poke();
}
function togglePlay() { if (ended) { seekStep(0); return; } setPaused(!paused); }
const fmt = ms => { const s = Math.round(ms / 1000); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); };
function buildUi() {
  CH.forEach((ch, i) => {
    const seg = document.createElement('span'); seg.style.flex = ch.ms + ' 1 0'; seg.title = ch.n; seg.appendChild(document.createElement('i')); bar.appendChild(seg);
    const b = document.createElement('button'); b.type = 'button';
    b.innerHTML = '<em>' + i + '</em>' + ch.n + '<small>' + fmt(ch.ms) + '</small>';
    b.onclick = () => { closeMenu(); seekChapter(i); };
    menu.appendChild(b);
  });
}
function tick() {
  const e = elapsed();
  bar.querySelectorAll('i').forEach((el, i) => { const ch = CH[i]; el.style.width = Math.max(0, Math.min(1, (e - ch.start) / ch.ms)) * 100 + '%'; });
  $('#time').textContent = fmt(e) + ' / ' + fmt(totalMs);
  bar.setAttribute('aria-valuenow', Math.round(e / 1000)); bar.setAttribute('aria-valuemax', Math.round(totalMs / 1000));
}
bar.addEventListener('click', ev => {
  const segs = [...bar.children];
  const hit = segs.findIndex(s => { const b = s.getBoundingClientRect(); return ev.clientX >= b.left - 2 && ev.clientX <= b.right + 2; });
  if (hit < 0) return;
  const b = segs[hit].getBoundingClientRect(), frac = Math.max(0, Math.min(1, (ev.clientX - b.left) / b.width));
  const target = CH[hit].start + frac * CH[hit].ms;
  let i = steps.findIndex(s => s.start + s.t > target); if (i < 0) i = steps.length - 1;
  seekStep(i);
});
bar.addEventListener('keydown', e => { if (e.key === 'ArrowRight') seekChapter(steps[idx].ci + 1); if (e.key === 'ArrowLeft') seekChapter(steps[idx].ci - 1); });
$('#pp').onclick = togglePlay;
big.onclick = () => seekStep(0);
$('#rs').onclick = () => seekStep(0);
$('#next').onclick = () => seekChapter(steps[idx].ci + 1);
$('#prev').onclick = () => { const ci = steps[idx].ci; seekChapter(elapsed() - CH[ci].start > 2500 ? ci : ci - 1); };
voBtn.onclick = e => { e.stopPropagation(); setVoice(!voiceOn); };
voPill.onclick = e => { e.stopPropagation(); setVoice(true); if (paused && !ended) setPaused(false); };
function closeMenu() { menu.hidden = true; $('#ch').setAttribute('aria-expanded', 'false'); }
$('#ch').onclick = e => { e.stopPropagation(); menu.hidden = !menu.hidden; $('#ch').setAttribute('aria-expanded', String(!menu.hidden)); poke(); };
document.addEventListener('click', e => { if (!menu.hidden && !menu.contains(e.target)) closeMenu(); });
$('#fs').onclick = () => {
  const el = document.documentElement;
  if (document.fullscreenElement) document.exitFullscreen?.();
  else (el.requestFullscreen || el.webkitRequestFullscreen)?.call(el);
};
stage.addEventListener('click', () => { if (!ended) togglePlay(); });
document.addEventListener('keydown', e => {
  if (e.key === ' ' || e.key === 'k') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'm') setVoice(!voiceOn);
  else if (e.key === 'ArrowRight' && e.target !== bar) seekChapter(steps[idx].ci + 1);
  else if (e.key === 'ArrowLeft' && e.target !== bar) seekChapter(steps[idx].ci - 1);
});
document.addEventListener('visibilitychange', () => { if (document.hidden) stopVoice(); });
addEventListener('pagehide', stopVoice);
let idleT;
function poke() {
  ui.classList.remove('idle'); clearTimeout(idleT);
  idleT = setTimeout(() => { if (!paused && menu.hidden && !ui.matches(':hover')) ui.classList.add('idle'); }, 2600);
}
['mousemove', 'touchstart', 'keydown'].forEach(ev => document.addEventListener(ev, poke, {passive: true}));

/* ---------- start ---------- */
async function start() {
  fit();
  try { R = await (await fetch(BASE + 'rects.json', {cache: 'no-cache'})).json(); }
  catch (e) { cap.textContent = 'The tour could not load. Please refresh the page.'; cap.classList.add('on'); return; }
  try { const r = await fetch('/static/product-tour/voice/voice.json', {cache: 'no-cache'}); if (r.ok) VO = await r.json(); } catch (e) { VO = null; }
  if (!synth && !VO) { voBtn.hidden = true; voPill.hidden = true; }
  build(); buildUi();
  [...new Set(steps.map(s => s.screen).filter(Boolean))].forEach((n, i) => setTimeout(() => imgs[n] || loadImg(n), i < 4 ? 0 : 1500 + i * 120));
  setInterval(tick, 200);
  setVoice(false);
  runFrom(0); poke();
}
start();
})();
