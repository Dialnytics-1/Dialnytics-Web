// Dialnytics free tools. Everything runs locally in the browser; nothing is sent to the server.
const root = document.querySelector('[data-tool]');
const $ = id => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
const pad = n => String(n).padStart(2, '0');
const fmtHour = h => { const hh = ((h % 24) + 24) % 24; return (hh % 12 || 12) + (hh < 12 ? ' AM' : ' PM'); };
async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); const o = btn.textContent; btn.textContent = 'Copied'; setTimeout(() => { btn.textContent = o; }, 1500); }
  catch (_) { btn.textContent = 'Select and copy the text above'; }
}
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = el('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
const today = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };

/* ---------- 1. Best time to call ---------- */
const ZONES = [['Asia/Karachi', 'Pakistan (PKT)'], ['Asia/Kolkata', 'India (IST)'], ['Asia/Dubai', 'UAE (GST)'], ['Asia/Manila', 'Philippines'],
  ['Europe/London', 'United Kingdom'], ['Europe/Paris', 'Central Europe'], ['America/New_York', 'US / Canada Eastern'], ['America/Chicago', 'US / Canada Central'],
  ['America/Denver', 'US / Canada Mountain'], ['America/Phoenix', 'Arizona'], ['America/Los_Angeles', 'US / Canada Pacific'], ['America/Anchorage', 'Alaska'],
  ['Pacific/Honolulu', 'Hawaii'], ['America/Halifax', 'Canada Atlantic'], ['Australia/Sydney', 'Australia (Sydney, Melbourne)'], ['Australia/Brisbane', 'Australia (Brisbane)'],
  ['Australia/Adelaide', 'Australia (Adelaide)'], ['Australia/Perth', 'Australia (Perth)'], ['Asia/Tokyo', 'Japan']];
function tzOffsetMin(tz, date) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    .formatToParts(date).map(x => [x.type, x.value]));
  const asUTC = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute);
  return Math.round((asUTC - date.getTime()) / 60000);
}
function inRange(h, s, e) { return s === e ? true : s < e ? h >= s && h < e : h >= s || h < e; }
function bestTime() {
  document.querySelectorAll('[data-tz]').forEach(s => ZONES.forEach(([v, l]) => s.append(new Option(l, v))));
  document.querySelectorAll('[data-hour]').forEach(s => { for (let h = 0; h < 24; h++) s.append(new Option(fmtHour(h), h)); });
  const guess = Intl.DateTimeFormat().resolvedOptions().timeZone;
  $('bt-you').value = ZONES.some(z => z[0] === guess) ? guess : 'Asia/Karachi';
  $('bt-cust').value = 'America/New_York';
  $('bt-cs').value = 9; $('bt-ce').value = 17; $('bt-ys').value = 14; $('bt-ye').value = 2; $('bt-date').value = today();
  const run = () => {
    const out = $('bt-out'); out.replaceChildren();
    const [y, m, d] = ($('bt-date').value || today()).split('-').map(Number);
    const you = $('bt-you').value, cust = $('bt-cust').value;
    const noon = new Date(Date.UTC(y, m - 1, d, 12));
    const diff = (tzOffsetMin(you, noon) - tzOffsetMin(cust, noon)) / 60;
    const cs = +$('bt-cs').value, ce = +$('bt-ce').value, ys = +$('bt-ys').value, ye = +$('bt-ye').value;
    const bar = el('div', 'bt-bar'); let good = [];
    for (let h = 0; h < 24; h++) {
      const yh = h + diff; const ok = inRange(h, cs, ce) && inRange(((Math.floor(yh) % 24) + 24) % 24, ys, ye);
      const c = el('span', ok ? 'ok' : inRange(h, cs, ce) ? 'biz' : ''); c.title = `${fmtHour(h)} customer = ${fmtHour(Math.floor(yh))}${yh % 1 ? ':30' : ''} you`; bar.append(c);
      if (ok) good.push(h);
    }
    const head = el('div', 'tl-result');
    if (good.length) {
      head.append(el('strong', '', `${good.length} hour${good.length > 1 ? 's' : ''} overlap`), el('span', '', `Customer: ${fmtHour(good[0])} to ${fmtHour(good[good.length - 1] + 1)}  ·  You: ${fmtHour(Math.floor(good[0] + diff))}${diff % 1 ? ':30' : ''} to ${fmtHour(Math.floor(good[good.length - 1] + 1 + diff))}${diff % 1 ? ':30' : ''}`));
    } else head.append(el('strong', '', 'No overlap'), el('span', '', 'Your hours and their business hours do not meet. Try a later shift or a split shift.'));
    const legend = el('div', 'bt-legend'); legend.innerHTML = '<span class="ok"></span>Best time to call <span class="biz"></span>Their business hours only <span></span>Outside hours';
    const scale = el('div', 'bt-scale'); [0, 6, 12, 18].forEach(h => scale.append(el('span', '', fmtHour(h) + ' (their time)')));
    const note = el('p', 'caption', `Time difference: you are ${Math.abs(diff)} hour${Math.abs(diff) === 1 ? '' : 's'} ${diff >= 0 ? 'ahead of' : 'behind'} your customer on this date (daylight saving included). Tip: for most B2B calls, 10-11 AM and 2-4 PM in the customer's time work best.`);
    const clocks = el('p', 'bt-clocks');
    const fmt = tz => new Intl.DateTimeFormat('en-US', { timeZone: tz, hour: 'numeric', minute: '2-digit', weekday: 'short' }).format(new Date());
    clocks.textContent = `Right now: ${fmt(you)} for you · ${fmt(cust)} for your customer`;
    out.append(head, bar, scale, legend, clocks, note);
  };
  root.querySelectorAll('select,input').forEach(i => i.addEventListener('change', run)); run(); setInterval(run, 60000);
}

/* ---------- 2. A2P 10DLC quiz ---------- */
function quiz() {
  const tips = ['Register your business first (company or sole proprietor). Carriers check the legal name.', 'Get your tax ID ready: a US EIN, or the tax number from your country.',
    'Put up a simple website that shows the same business name, what you do and how to contact you.', 'Add a privacy policy that says phone numbers are not sold or shared for marketing.',
    'Collect permission before texting: a form checkbox, a reply keyword or a signed form.', 'Add your business name and "Reply STOP to opt out" to your first message.',
    'Write one sentence about why you text customers and two example messages.'];
  $('qz-go').addEventListener('click', () => {
    const out = $('qz-out'); out.replaceChildren();
    const ans = tips.map((_, i) => root.querySelector(`[name=q${i + 1}]:checked`));
    if (ans.some(a => !a)) { out.append(el('p', 'tl-warn', 'Please answer all seven questions.')); return; }
    const yes = ans.filter(a => a.value === '1').length;
    const box = el('div', 'tl-result');
    box.append(el('strong', '', `${yes} of 7 ready`), el('span', '', yes === 7 ? 'You look ready to register. We can submit your A2P 10DLC registration for you when you add SMS texting.' : yes >= 5 ? 'Almost there. Fix the points below before you register to avoid a rejection.' : 'A few things to sort out first. Registrations missing these are usually rejected.'));
    const meter = el('div', 'qz-meter'); const fill = el('i'); fill.style.width = (yes / 7 * 100) + '%'; meter.append(fill);
    out.append(box, meter);
    const todo = ans.map((a, i) => a.value === '0' ? tips[i] : null).filter(Boolean);
    if (todo.length) { const ul = el('ul', 'tl-list'); todo.forEach(t => ul.append(el('li', '', t))); out.append(el('h3', '', 'What to fix'), ul); }
    const cta = el('p', 'caption'); cta.innerHTML = 'SMS texting is an optional add-on. <a href="/product/sms/">How texting works</a> · <a href="/pricing/#calculator">Add it to a plan</a>'; out.append(cta);
  });
}

/* ---------- 3. Follow-up cadence ---------- */
function cadence() {
  const preset = $('cd-preset'), steps = $('cd-steps');
  $('cd-start').value = today(); steps.value = preset.value;
  let rows = [];
  const run = () => {
    const out = $('cd-out'); out.replaceChildren(); rows = [];
    const [y, m, d] = ($('cd-start').value || today()).split('-').map(Number);
    const items = steps.value.split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
    let last = null;
    for (const it of items) {
      const mt = it.match(/^(\d{1,3})\s*(call|text)$/);
      if (!mt) { out.append(el('p', 'tl-warn', `Could not read "${it}". Use a day number and call or text, e.g. "3 call".`)); return; }
      const date = new Date(y, m - 1, d + Number(mt[1]));
      if ($('cd-wk').checked) while ([0, 6].includes(date.getDay())) date.setDate(date.getDate() + 1);
      if (last && date < last) date.setTime(last.getTime());
      last = new Date(date); rows.push({ date, type: mt[2] });
    }
    const list = el('ol', 'cd-list');
    rows.forEach((r, i) => { const li = el('li'); li.append(el('span', 'cd-type ' + r.type, r.type === 'call' ? 'Call' : 'Text'), el('strong', '', r.date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })), el('small', '', `Touch ${i + 1}`)); list.append(li); });
    out.append(el('div', 'tl-result', ''), list);
    out.firstChild.append(el('strong', '', `${rows.length} touches`), el('span', '', `${rows.filter(r => r.type === 'call').length} calls and ${rows.filter(r => r.type === 'text').length} texts over ${rows.length ? Math.round((rows[rows.length - 1].date - rows[0].date) / 864e5) : 0} days`));
  };
  preset.addEventListener('change', () => { if (preset.value !== 'custom') steps.value = preset.value; run(); });
  steps.addEventListener('input', () => { preset.value = 'custom'; run(); });
  ['cd-start', 'cd-wk', 'cd-name'].forEach(id => $(id).addEventListener('change', run));
  const lead = () => ($('cd-name').value.trim() || 'lead').replace(/[\r\n,;]/g, ' ');
  $('cd-copy').addEventListener('click', e => copy(rows.map((r, i) => `${i + 1}. ${r.date.toDateString()} - ${r.type} ${lead()}`).join('\n'), e.currentTarget));
  $('cd-ics').addEventListener('click', () => {
    if (!rows.length) return;
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    const ymd = dt => `${dt.getFullYear()}${pad(dt.getMonth() + 1)}${pad(dt.getDate())}`;
    const ev = rows.map((r, i) => { const n = new Date(r.date); n.setDate(n.getDate() + 1); return ['BEGIN:VEVENT', `UID:dny-${stamp}-${i}@dialnytics.com`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${ymd(r.date)}`, `DTEND;VALUE=DATE:${ymd(n)}`, `SUMMARY:${r.type === 'call' ? 'Call' : 'Text'} ${lead()} (touch ${i + 1})`, 'END:VEVENT'].join('\r\n'); });
    download('follow-up-cadence.ics', ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Dialnytics//Cadence Planner//EN', ...ev, 'END:VCALENDAR'].join('\r\n'), 'text/calendar');
  });
  run();
}

/* ---------- 4. Number cleaner ---------- */
const RULES = { 1: { len: [10], trunk: '1' }, 44: { len: [9, 10], trunk: '0' }, 61: { len: [9], trunk: '0' }, 81: { len: [9, 10], trunk: '0' }, 92: { len: [9, 10], trunk: '0' } };
const KNOWN = ['1', '44', '61', '81', '92', '91', '971', '33', '49', '34', '39', '353', '31', '27', '234', '880', '63', '64', '65', '86'];
function toE164(raw, cc) {
  let s = raw.trim(); if (!s) return null;
  s = s.replace(/(ext\.?|x|#)\s*\d+$/i, '');
  const plus = /^\s*(\+|00)/.test(s); let digits = s.replace(/\D/g, '');
  if (s.trim().startsWith('00')) digits = digits.slice(2);
  if (plus) {
    const code = KNOWN.filter(k => digits.startsWith(k)).sort((a, b) => b.length - a.length)[0];
    if (!code) return digits.length >= 8 && digits.length <= 15 ? '+' + digits : { bad: raw };
    let nat = digits.slice(code.length); const r = RULES[code];
    if (r && nat.startsWith('0') && code !== '1') nat = nat.slice(1);
    if (r && !r.len.includes(nat.length)) return { bad: raw };
    return '+' + code + nat;
  }
  const r = RULES[cc];
  if (cc === '1' && digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1);
  else if (cc !== '1' && digits.startsWith(r.trunk)) digits = digits.slice(1);
  else if (cc !== '1' && digits.startsWith(cc) && r.len.includes(digits.length - cc.length)) digits = digits.slice(cc.length);
  if (!r.len.includes(digits.length)) return { bad: raw };
  if (cc === '1' && (/^[01]/.test(digits) || /^\d{3}[01]/.test(digits))) return { bad: raw };
  return '+' + cc + digits;
}
function cleaner() {
  $('cl-go').addEventListener('click', () => {
    const out = $('cl-out'); out.replaceChildren();
    const parts = $('cl-in').value.split(/[\n,;\t]+/).map(x => x.trim()).filter(Boolean);
    const good = [], bad = []; const seen = new Set(); let dup = 0;
    parts.forEach(p => { const r = toE164(p, $('cl-cc').value); if (!r) return; if (typeof r === 'object') bad.push(r.bad); else if (seen.has(r)) dup++; else { seen.add(r); good.push(r); } });
    const box = el('div', 'tl-result'); box.append(el('strong', '', `${good.length} clean numbers`), el('span', '', `${dup} duplicates removed · ${bad.length} could not be read`)); out.append(box);
    const ta = el('textarea', 'tl-code'); ta.rows = Math.min(12, Math.max(3, good.length)); ta.readOnly = true; ta.value = good.join('\n'); out.append(ta);
    const acts = el('div', 'tl-actions'); const b1 = el('button', 'button secondary', 'Copy clean list'); b1.type = 'button'; b1.addEventListener('click', e => copy(ta.value, e.currentTarget));
    const b2 = el('button', 'button secondary', 'Download CSV'); b2.type = 'button'; b2.addEventListener('click', () => download('clean-numbers.csv', 'phone\n' + good.join('\n'), 'text/csv'));
    acts.append(b1, b2); out.append(acts);
    if (bad.length) { out.append(el('h3', '', 'Check these by hand')); const ul = el('ul', 'tl-list'); bad.slice(0, 50).forEach(b => ul.append(el('li', '', b))); out.append(ul); }
    out.append(el('p', 'caption', 'Format check only: a valid-looking number may still be disconnected. Import only numbers you have permission to call.'));
  });
}

/* ---------- 5. Erlang C ---------- */
function erlangC(A, N) { // probability a call waits
  if (N <= A) return 1;
  let sum = 1, term = 1;
  for (let k = 1; k < N; k++) { term *= A / k; sum += term; }
  const top = term * A / N * (N / (N - A));
  return top / (sum + top);
}
function staffing() {
  const run = () => {
    const out = $('er-out'); out.replaceChildren();
    const calls = +$('er-calls').value, aht = +$('er-aht').value, t = +$('er-target').value, goal = +$('er-sl').value / 100, shr = +$('er-shr').value / 100;
    if (!(calls > 0 && aht > 0 && t >= 0 && goal > 0 && goal < 1 && shr >= 0 && shr < 1)) { out.append(el('p', 'tl-warn', 'Enter positive numbers in every box.')); return; }
    const A = calls * aht / 3600; let N = Math.max(1, Math.ceil(A + 0.0001)), res;
    for (; N < 2000; N++) {
      const pw = erlangC(A, N); const sl = 1 - pw * Math.exp(-(N - A) * t / aht); const asa = pw * aht / (N - A);
      res = { N, pw, sl, asa, occ: A / N }; if (sl >= goal) break;
    }
    const sched = Math.ceil(res.N / (1 - shr));
    const box = el('div', 'tl-result'); box.append(el('strong', '', `${res.N} agents on the phones`), el('span', '', `Schedule ${sched} people to cover ${Math.round(shr * 100)}% shrinkage`));
    const grid = el('div', 'er-grid');
    [['Traffic', A.toFixed(2) + ' Erlangs'], ['Service level', (res.sl * 100).toFixed(1) + '% answered in ' + t + 's'], ['Average wait', res.asa.toFixed(1) + ' s'], ['Chance a caller waits', (res.pw * 100).toFixed(1) + '%'], ['Agent occupancy', (res.occ * 100).toFixed(0) + '%']]
      .forEach(([k, v]) => { const d = el('div'); d.append(el('small', '', k), el('strong', '', v)); grid.append(d); });
    out.append(box, grid, el('p', 'caption', 'Erlang C assumes callers wait rather than hang up, so real needs can be a little lower. Occupancy above 85% for long periods tires agents out.'));
  };
  root.querySelectorAll('input').forEach(i => i.addEventListener('input', run)); run();
}

/* ---------- 6. Area code lookup ---------- */
async function areaCodes() {
  const out = $('ac-out'); let data;
  try { data = await (await fetch('/static/tools/area-codes.json?v=1')).json(); } catch (_) { out.append(el('p', 'tl-warn', 'Could not load area codes. Refresh the page.')); return; }
  const C = { US: 'USA', CA: 'Canada', NANP: 'Caribbean / US territory' };
  const run = () => {
    out.replaceChildren(); const q = $('ac-q').value.trim().toLowerCase(); if (!q) { out.append(el('p', 'caption', `${Object.keys(data).length} area codes loaded. Start typing.`)); return; }
    let hits;
    const digits = q.replace(/\D/g, '');
    if (/^\+?1?\D*\d{3}/.test(q) && digits.length >= 3) { const code = digits.length >= 4 && digits[0] === '1' ? digits.slice(1, 4) : digits.slice(0, 3); hits = data[code] ? [[code, data[code]]] : []; }
    else hits = Object.entries(data).filter(([, v]) => v[0].toLowerCase().includes(q) || v[2].some(c => c.toLowerCase().includes(q))).slice(0, 40);
    if (!hits.length) { out.append(el('p', 'tl-warn', 'No match. Try a 3-digit code, a city or a state.')); return; }
    const list = el('div', 'ac-list');
    hits.forEach(([code, [region, country, cities]]) => {
      const card = el('div', 'ac-card'); card.append(el('strong', 'ac-code', code));
      const info = el('div'); info.append(el('b', '', region), el('small', '', C[country] || country));
      if (cities.length) info.append(el('p', '', 'Places: ' + cities.join(' · ')));
      card.append(info); list.append(card);
    });
    out.append(list);
    if (hits.some(([, v]) => v[1] === 'US' || v[1] === 'CA')) { const p = el('p', 'caption'); p.innerHTML = 'Want a local number in one of these areas? <a href="/numbers/usa-canada/">See the USA &amp; Canada plan</a>.'; out.append(p); }
  };
  $('ac-q').addEventListener('input', run); run();
}

/* ---------- 7. SMS counter ---------- */
const GSM = new Set(Array.from('@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'));
const GSM_EXT = new Set(Array.from('^{}\\[~]|€\f'));
function smsCount() {
  const run = () => {
    const out = $('sm-out'); out.replaceChildren(); const txt = $('sm-in').value; const chars = Array.from(txt);
    const bad = [...new Set(chars.filter(c => !GSM.has(c) && !GSM_EXT.has(c)))];
    const gsm = bad.length === 0; let units = gsm ? chars.reduce((n, c) => n + (GSM_EXT.has(c) ? 2 : 1), 0) : txt.length;
    const single = gsm ? 160 : 70, multi = gsm ? 153 : 67; const segs = units === 0 ? 0 : units <= single ? 1 : Math.ceil(units / multi);
    const left = units === 0 ? single : units <= single ? single - units : segs * multi - units;
    const grid = el('div', 'er-grid');
    [['Characters', String(chars.length)], ['Encoding', gsm ? 'GSM-7 (standard)' : 'Unicode (UCS-2)'], ['Segments', String(segs)], ['Left in this segment', String(left)]]
      .forEach(([k, v]) => { const d = el('div'); d.append(el('small', '', k), el('strong', '', v)); grid.append(d); });
    out.append(grid);
    if (!gsm) { const w = el('p', 'tl-warn'); w.append('These characters switch the text to Unicode, which allows only 70 characters per segment: '); bad.slice(0, 20).forEach(c => w.append(el('code', '', c === ' ' ? '␣' : c), ' ')); out.append(w); }
    out.append(el('p', 'caption', 'Each segment is billed as one text. Smart quotes, emojis and some accented letters force Unicode; replace them to save segments. Include your business name and "Reply STOP to opt out" in first messages.'));
  };
  $('sm-in').addEventListener('input', run); run();
}

/* ---------- 8. Script generator ---------- */
const PAINS = { 'Real estate': 'finding serious buyers and sellers without wasting viewings', 'Insurance': 'paying more than they need to at renewal time', 'Solar / home services': 'rising energy bills', 'Logistics & courier': 'late deliveries and unclear tracking', 'Marketing agency': 'getting steady leads from their ad spend', 'Software / SaaS': 'manual work that slows the team down', 'Recruitment': 'filling roles quickly with the right people', 'Healthcare clinic': 'no-shows and empty appointment slots', 'Education': 'choosing the right course and starting on time', 'E-commerce': 'abandoned carts and repeat orders', 'Automotive': 'finding the right car at a fair price', 'Other business': 'saving time and money' };
function script() {
  const gen = () => {
    const ind = $('sc-ind').value, type = $('sc-type').value, you = $('sc-you').value.trim() || '[Your name]', co = $('sc-co').value.trim() || '[Your company]', offer = $('sc-offer').value.trim() || '[what you offer]', pain = PAINS[ind];
    const open = { cold: `Hi, is this [Name]? This is ${you} from ${co}. I know I'm calling out of the blue. Do you have 30 seconds, and if it's not useful you can tell me to go?`, warm: `Hi [Name], it's ${you} from ${co}. You asked about ${offer} on our website, so I'm calling to help. Is now a good time?`, follow: `Hi [Name], ${you} from ${co} again. We spoke on [date] about ${offer}. I said I'd call back, is now still OK?`, appt: `Hi [Name], it's ${you} from ${co}. I'm calling to find a time for a short meeting about ${offer}. Have you got a minute?` }[type];
    const sections = [
      ['Opening', open],
      ['Reason for the call', `We help ${ind.toLowerCase()} customers with ${pain}. Most people we speak to tell us that ${pain} is a real headache. Is that true for you too?`],
      ['Questions to ask', `1. How do you handle this today?\n2. What's the biggest problem with that?\n3. If you could fix one thing, what would it be?\n4. Who else would be involved in a decision like this?`],
      ['Value', `Based on what you said, ${offer} could help by [benefit 1] and [benefit 2]. For example, a [similar customer] [result, only if true].`],
      ['Handling objections', `"Not interested": Totally fair. Is that because you already have something in place, or the timing isn't right?\n"Send me an email": Happy to. So I send the right thing, what matters most to you about this?\n"Too expensive": Understood. What would it need to save you for it to be worth it?\n"Call me later": Sure, when's best? I'll put it in my calendar now.`],
      ['Close', type === 'appt' ? `Would [day] at [time] or [day] at [time] work better for a 15-minute call?` : `Would it make sense to set up a short call on [day] so I can show you how it works? I'll send a calendar invite to your email.`],
      ['Before you hang up', `Confirm the next step and the date. If they asked not to be called again, mark them Do Not Call straight away. If the call is recorded, say so at the start where the law requires it.`],
    ];
    const out = $('sc-out'); out.replaceChildren();
    sections.forEach(([h, t]) => { const s = el('section'); s.append(el('h3', '', h)); t.split('\n').forEach(line => s.append(el('p', '', line))); out.append(s); });
    out.dataset.text = sections.map(([h, t]) => h.toUpperCase() + '\n' + t).join('\n\n');
  };
  $('sc-go').addEventListener('click', gen);
  $('sc-copy').addEventListener('click', e => { if (!$('sc-out').dataset.text) gen(); copy($('sc-out').dataset.text, e.currentTarget); });
  gen();
}

const RUN = { 'best-time-to-call': bestTime, 'a2p-10dlc-readiness-quiz': quiz, 'follow-up-cadence-planner': cadence, 'phone-number-list-cleaner': cleaner, 'call-center-staffing-calculator': staffing, 'area-code-lookup': areaCodes, 'sms-character-counter': smsCount, 'cold-call-script-generator': script };
if (root && RUN[root.dataset.tool]) RUN[root.dataset.tool]();
