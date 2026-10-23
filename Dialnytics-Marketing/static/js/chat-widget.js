'use strict';
/* Dialnytics AI assistant: website chat widget */
(() => {
  const root = document.getElementById('dn-chat');
  if (!root) return;
  const WA = root.dataset.wa || '';
  const T = {
    en: { title: 'Dialnytics Assistant', status: 'Online · replies in seconds', placeholder: 'Type your message…',
          send: 'Send', typing: 'Assistant is typing', waiting: 'Our team will reply here shortly.',
          error: 'Message not sent. Please check your connection and try again.', foot: 'AI assistant · our team can join anytime',
          chips: ['See prices', 'How does it work?', 'Product tour', 'Talk to a person'], lang: 'اردو / UR' },
    ur: { title: 'Dialnytics Assistant', status: 'Online · foran jawab', placeholder: 'Apna message likhein…',
          send: 'Bhejein', typing: 'Assistant likh raha hai', waiting: 'Hamari team jald yahin jawab degi.',
          error: 'Message nahi gaya. Internet check karke dobara koshish karein.', foot: 'AI assistant · team kisi bhi waqt shamil ho sakti hai',
          chips: ['Prices batayein', 'Kaise kaam karta hai?', 'Product tour', 'Team se baat karein'], lang: 'English / EN' },
  };
  let csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  let loaded = false, lang = '', last = 0, open = false, busy = false, started = false, unread = 0, pollTimer = null;
  const store = { get(k) { try { return sessionStorage.getItem(k); } catch (_) { return null; } },
                  set(k, v) { try { sessionStorage.setItem(k, v); } catch (_) {} } };

  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const svg = (path, size = 22) => `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
  const ICON_CHAT = '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" stroke-width="2.6"/>';
  const ICON_X = '<path d="M6 6l12 12M18 6 6 18"/>';
  const ICON_SEND = '<path d="M4 12 20 4l-6 16-3-7z"/><path d="m11 13 9-9"/>';
  const ICON_WA = '<path d="M20 11.6a8.3 8.3 0 0 1-12.3 7.3L3.5 20l1.2-4A8.3 8.3 0 1 1 20 11.6z"/><path d="M9 8.6c.2-.4.4-.4.7-.4h.5c.2 0 .4 0 .5.4l.7 1.7c.1.2 0 .4-.1.6l-.5.6c-.1.1-.1.3 0 .5a6 6 0 0 0 2.8 2.5c.2.1.4 0 .5-.1l.6-.7c.2-.2.4-.2.6-.1l1.6.8c.2.1.3.3.3.5 0 .9-.7 1.8-1.7 1.9-1 .1-2.6-.3-4.4-2S8.6 10.8 8.7 9.8c0-.5.1-.9.3-1.2z" fill="currentColor" stroke="none"/>';

  // ------------------------------------------------------------ DOM
  const launcher = el('button', 'dnc-launcher');
  launcher.type = 'button'; launcher.setAttribute('aria-label', 'Chat with Dialnytics'); launcher.setAttribute('aria-expanded', 'false');
  launcher.innerHTML = `<span class="dnc-l-icon dnc-l-chat">${svg(ICON_CHAT, 26)}</span><span class="dnc-l-icon dnc-l-close">${svg(ICON_X, 24)}</span><span class="dnc-online" aria-hidden="true"></span>`;
  const badge = el('span', 'dnc-badge'); badge.hidden = true; launcher.append(badge);
  const teaser = el('div', 'dnc-teaser'); teaser.hidden = true;
  const teaserText = el('button', 'dnc-teaser-text'); teaserText.type = 'button';
  teaserText.innerHTML = '<strong>Hi! 👋 Questions about plans?</strong><span>Ask our assistant — English or Roman Urdu.</span>';
  const teaserClose = el('button', 'dnc-teaser-x'); teaserClose.type = 'button'; teaserClose.setAttribute('aria-label', 'Dismiss'); teaserClose.innerHTML = svg(ICON_X, 14);
  teaser.append(teaserText, teaserClose);

  const panel = el('section', 'dnc-panel'); panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Dialnytics chat'); panel.hidden = true;
  const head = el('header', 'dnc-head');
  const avatar = el('span', 'dnc-avatar'); const avImg = el('img'); avImg.src = '/static/img/dialnytics-favlogo.png?v=2'; avImg.alt = ''; avatar.append(avImg);
  const headText = el('div', 'dnc-head-text'); const hTitle = el('strong', null, T.en.title); const hStatus = el('small', null, T.en.status); headText.append(hTitle, hStatus);
  const langBtn = el('button', 'dnc-hbtn dnc-lang'); langBtn.type = 'button'; langBtn.hidden = true; langBtn.setAttribute('aria-label', 'Change language');
  const waBtn = el('a', 'dnc-hbtn'); waBtn.href = 'https://wa.me/' + WA; waBtn.target = '_blank'; waBtn.rel = 'noopener'; waBtn.setAttribute('aria-label', 'Continue on WhatsApp'); waBtn.title = 'Continue on WhatsApp'; waBtn.innerHTML = svg(ICON_WA, 20);
  const closeBtn = el('button', 'dnc-hbtn'); closeBtn.type = 'button'; closeBtn.setAttribute('aria-label', 'Close chat'); closeBtn.innerHTML = svg(ICON_X, 20);
  head.append(avatar, headText, langBtn, waBtn, closeBtn);

  const body = el('div', 'dnc-body'); body.setAttribute('aria-live', 'polite');
  const welcome = el('div', 'dnc-welcome');
  welcome.innerHTML = '<div class="dnc-hello"><span class="dnc-wave">👋</span><h3>Welcome to Dialnytics</h3><p>Business calling with a dedicated caller ID, CRM, Power Dialer and recording. Ask us anything.</p></div><p class="dnc-choose">Please choose your language<br><span>Apni zubaan muntakhib karein</span></p>';
  const langs = el('div', 'dnc-langs');
  [['en', 'English', 'Continue in English'], ['ur', 'Roman Urdu', 'Roman Urdu mein baat karein']].forEach(([code, name, sub]) => {
    const b = el('button', 'dnc-langbtn'); b.type = 'button'; b.dataset.lang = code;
    b.innerHTML = `<span class="dnc-flag">${code === 'en' ? 'EN' : 'UR'}</span><span><strong>${name}</strong><small>${sub}</small></span>`;
    b.addEventListener('click', () => start(code)); langs.append(b);
  });
  welcome.append(langs);
  const list = el('div', 'dnc-list');
  const typing = el('div', 'dnc-msg bot dnc-typing'); typing.hidden = true;
  typing.innerHTML = '<div class="dnc-bubble"><span></span><span></span><span></span></div>';
  const chips = el('div', 'dnc-chips'); chips.hidden = true;
  body.append(welcome, list, typing, chips);

  const form = el('form', 'dnc-form');
  const input = el('textarea', 'dnc-input'); input.rows = 1; input.maxLength = 1000; input.placeholder = T.en.placeholder; input.setAttribute('aria-label', 'Message'); input.disabled = true;
  const sendBtn = el('button', 'dnc-send'); sendBtn.type = 'submit'; sendBtn.setAttribute('aria-label', 'Send'); sendBtn.innerHTML = svg(ICON_SEND, 20); sendBtn.disabled = true;
  form.append(input, sendBtn);
  const foot = el('div', 'dnc-foot'); const footText = el('span', null, T.en.foot); const privacy = el('a', null, 'Privacy'); privacy.href = '/legal/privacy/'; foot.append(footText, privacy);
  const errorBox = el('div', 'dnc-error'); errorBox.hidden = true;
  panel.append(head, body, errorBox, form, foot);
  root.append(teaser, panel, launcher); root.hidden = false;

  // ------------------------------------------------------------ rendering
  function linkify(node, text) {
    const re = /(https?:\/\/[^\s<>"')]+[^\s<>"').,!?])/g; let pos = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > pos) node.append(document.createTextNode(text.slice(pos, m.index)));
      const a = el('a', null, m[0].replace(/^https?:\/\/(www\.)?/, '')); a.href = m[0];
      if (!m[0].startsWith(location.origin)) { a.target = '_blank'; a.rel = 'noopener'; }
      node.append(a); pos = m.index + m[0].length;
    }
    if (pos < text.length) node.append(document.createTextNode(text.slice(pos)));
  }
  function bold(node, text) { // WhatsApp-style *bold* only
    text.split(/(\*[^*\n]{1,80}\*)/g).forEach(part => {
      if (/^\*[^*\n]{1,80}\*$/.test(part)) { const b = el('strong'); linkify(b, part.slice(1, -1)); node.append(b); }
      else linkify(node, part);
    });
  }
  function addMessage(m) {
    if (list.querySelector(`[data-id="${m.id}"]`)) return;
    const row = el('div', 'dnc-msg ' + (m.from === 'me' ? 'me' : m.from === 'team' ? 'team' : 'bot')); row.dataset.id = m.id;
    if (m.from === 'team') row.append(el('span', 'dnc-who', 'Dialnytics team'));
    const bubble = el('div', 'dnc-bubble'); bold(bubble, m.text || ''); row.append(bubble);
    if (m.at) { const t = el('time', 'dnc-time', new Date(m.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })); row.append(t); }
    list.append(row); last = Math.max(last, Number(m.id) || 0);
    if (loaded && m.from !== 'me' && !open) { unread += 1; badge.textContent = String(unread); badge.hidden = false; }
  }
  function note(text) { const n = el('div', 'dnc-note', text); list.append(n); scroll(); }
  function scroll() { requestAnimationFrame(() => { body.scrollTop = body.scrollHeight; }); }
  function applyLang(code) {
    lang = code; const t = T[code] || T.en;
    hTitle.textContent = t.title; hStatus.textContent = t.status; input.placeholder = t.placeholder; footText.textContent = t.foot;
    sendBtn.setAttribute('aria-label', t.send); langBtn.textContent = code === 'ur' ? 'EN' : 'UR'; langBtn.title = t.lang; langBtn.hidden = !code;
    welcome.hidden = !!code; input.disabled = !code; sendBtn.disabled = !code;
    chips.replaceChildren(...t.chips.map(label => { const c = el('button', 'dnc-chip', label); c.type = 'button'; c.addEventListener('click', () => send(label)); return c; }));
    chips.hidden = !code || list.querySelectorAll('.dnc-msg.me').length > 0;
  }
  function showError(text) { errorBox.textContent = text; errorBox.hidden = !text; }

  // ------------------------------------------------------------ network
  async function api(url, data) {
    const res = await fetch(url, data === undefined ? { credentials: 'same-origin' } : {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify(data) });
    let json = {}; try { json = await res.json(); } catch (_) {}
    if (res.status === 403 && data !== undefined) { await history(); throw new Error('retry'); }
    if (!res.ok) throw new Error(typeof json.detail === 'string' ? json.detail : (T[lang] || T.en).error);
    return json;
  }
  async function history() {
    try {
      const d = await api('/api/chat/history?after=' + last);
      if (d.csrf) csrf = d.csrf;
      if (d.enabled === false) { root.hidden = true; return; }
      (d.messages || []).forEach(addMessage);
      if (d.language && d.language !== lang) applyLang(d.language);
      if (d.messages && d.messages.length) { started = true; scroll(); }
    } catch (_) {}
  }
  async function start(code) {
    if (busy) return; busy = true; showError('');
    try {
      let d;
      try { d = await api('/api/chat/start', { language: code }); }
      catch (e) { if (e.message !== 'retry') throw e; d = await api('/api/chat/start', { language: code }); }
      started = true; applyLang(d.language || code);
      (d.messages || []).forEach(addMessage); chips.hidden = list.querySelectorAll('.dnc-msg.me').length > 0;
      scroll(); input.focus();
    } catch (e) { showError(e.message); }
    finally { busy = false; }
  }
  async function send(text) {
    text = (text || '').trim(); if (!text || busy || !lang) return;
    busy = true; showError(''); chips.hidden = true; sendBtn.disabled = true;
    const temp = el('div', 'dnc-msg me pending'); const tb = el('div', 'dnc-bubble'); linkify(tb, text); temp.append(tb); list.append(temp);
    input.value = ''; autosize(); typing.hidden = false; scroll();
    try {
      let d;
      try { d = await api('/api/chat/message', { text }); }
      catch (e) { if (e.message !== 'retry') throw e; d = await api('/api/chat/message', { text }); }
      temp.remove(); (d.messages || []).forEach(addMessage);
      if (d.waiting) note((T[lang] || T.en).waiting);
    } catch (e) { temp.classList.add('failed'); input.value = text; showError(e.message); }
    finally { typing.hidden = true; busy = false; sendBtn.disabled = false; scroll(); }
  }

  // ------------------------------------------------------------ open / close
  function setOpen(v) {
    open = v; panel.hidden = !v; root.classList.toggle('is-open', v); launcher.setAttribute('aria-expanded', String(v));
    document.documentElement.classList.toggle('dnc-lock', v && window.matchMedia('(max-width: 600px)').matches);
    store.set('dnc-open', v ? '1' : '0');
    if (v) { teaser.hidden = true; store.set('dnc-teased', '1'); unread = 0; badge.hidden = true; history().then(scroll); if (lang) setTimeout(() => input.focus(), 50); }
    clearInterval(pollTimer);
    pollTimer = setInterval(() => { if (!document.hidden && (open || started)) history(); }, v ? 5000 : 30000);
  }
  launcher.addEventListener('click', () => setOpen(!open));
  closeBtn.addEventListener('click', () => { setOpen(false); launcher.focus(); });
  teaserText.addEventListener('click', () => setOpen(true));
  teaserClose.addEventListener('click', () => { teaser.hidden = true; store.set('dnc-teased', '1'); });
  langBtn.addEventListener('click', () => start(lang === 'ur' ? 'en' : 'ur'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && open) { setOpen(false); launcher.focus(); } });
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 120) + 'px'; }
  input.addEventListener('input', autosize);
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(input.value); } });
  form.addEventListener('submit', e => { e.preventDefault(); send(input.value); });

  history().then(() => {
    loaded = true;
    if (store.get('dnc-open') === '1') setOpen(true);
    else if (!started && store.get('dnc-teased') !== '1') setTimeout(() => { if (!open) teaser.hidden = false; }, 7000);
    if (!open) { clearInterval(pollTimer); pollTimer = setInterval(() => { if (!document.hidden && started) history(); }, 30000); }
  });
})();
