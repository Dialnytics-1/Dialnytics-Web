'use strict';
/* Animated hero replica of the Dialnytics dialer. Demo data only; no network calls. */
(() => {
  const root = document.querySelector('[data-hero-dialer]');
  if (!root) return;
  const W = 1120;
  const viewport = root.querySelector('.dx-viewport');
  const canvas = root.querySelector('.dx-canvas');
  const q = s => root.querySelector(s);
  const qa = s => Array.from(root.querySelectorAll(s));

  function fit() {
    const scale = viewport.clientWidth / W;
    canvas.style.transform = 'scale(' + scale + ')';
    return scale;
  }
  fit();
  window.addEventListener('resize', fit);
  if ('ResizeObserver' in window) new ResizeObserver(fit).observe(viewport);

  const RANGES = [
    { calls: 124, rate: 82, talk: 204, contacts: 18, follow: 7, out: [102, 22],
      labels: ['12 AM', '3 AM', '6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM'], bars: [8, 4, 22, 64, 88, 72, 46, 18] },
    { calls: 684, rate: 79, talk: 192, contacts: 96, follow: 31, out: [540, 144],
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', ''], bars: [62, 78, 70, 92, 84, 36, 20, 0] },
    { calls: 2918, rate: 81, talk: 198, contacts: 412, follow: 126, out: [2364, 554],
      labels: ['Wk 1', 'Wk 2', 'Wk 3', 'Wk 4', '', '', '', ''], bars: [70, 82, 76, 94, 0, 0, 0, 0] }
  ];
  const NUMBERS = ['+14155550132', '+447700900123', '+61491570006'];
  const pretty = n => n.startsWith('+44') ? n.replace(/^\+44(\d{4})(\d{6})$/, '+44 $1 $2')
    : n.startsWith('+61') ? n.replace(/^\+61(\d{3})(\d{3})(\d{3})$/, '+61 $1 $2 $3')
    : n.replace(/^\+1(\d{3})(\d{3})(\d{4})$/, '+1 $1 $2 $3');
  const mmss = s => Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  const clock = s => String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');

  const stat = k => q('[data-dx-stat="' + k + '"]');
  const status = q('[data-dx-status]');
  const input = q('[data-dx-input]');
  const cursor = q('[data-dx-cursor]');
  const toast = q('[data-dx-toast]');
  const bars = qa('.dx-bars > div');
  const pills = qa('[data-dx-range]');

  function countTo(el, from, to, fmt, ms) {
    if (!(ms > 0)) { el.textContent = fmt(to); return Promise.resolve(); }
    const start = performance.now();
    return new Promise(resolve => {
      (function step(now) {
        const t = Math.min(1, (now - start) / ms);
        const e = 1 - Math.pow(1 - t, 3);
        el.textContent = fmt(Math.round(from + (to - from) * e));
        t < 1 ? requestAnimationFrame(step) : resolve();
      })(start);
    });
  }

  let current = RANGES[0];
  function setRange(i, animate) {
    current = Object.assign({}, RANGES[i]);
    pills.forEach((p, n) => p.classList.toggle('on', n === i));
    bars.forEach((b, n) => {
      const bar = b.querySelector('b');
      b.querySelector('small').textContent = current.labels[n];
      b.style.visibility = current.labels[n] ? '' : 'hidden';
      if (animate) { bar.style.setProperty('--h', '0%'); }
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

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { root.classList.add('dx-static'); setRange(0, false); return; }

  let visible = false, run = 0;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }, { threshold: 0.15 }).observe(root);
  } else { visible = true; }

  const sleep = ms => { const r0 = run; return new Promise(resolve => {
    let left = ms, last = performance.now();
    (function wait() {
      if (run !== r0) return;
      const now = performance.now();
      if (visible && !document.hidden) left -= now - last;
      last = now;
      left <= 0 ? resolve() : setTimeout(wait, 40);
    })();
  }); };

  function point(el) {
    const scale = fit();
    const c = canvas.getBoundingClientRect(), r = el.getBoundingClientRect();
    return [(r.left - c.left + r.width * 0.55) / scale, (r.top - c.top + r.height * 0.6) / scale];
  }
  async function moveTo(el, ms = 650) {
    const [x, y] = point(el);
    cursor.style.transitionDuration = ms + 'ms';
    cursor.style.transform = 'translate(' + x + 'px,' + y + 'px)';
    await sleep(ms + 60);
  }
  async function press(el) {
    cursor.classList.add('down'); el.classList.add('press');
    await sleep(170);
    cursor.classList.remove('down'); el.classList.remove('press');
  }
  function setStatus(text, tone) { status.textContent = text; status.dataset.tone = tone || ''; }

  async function loop() {
    const my = ++run;
    let r = 0, n = 0;
    setRange(0, true);
    await sleep(1800);
    while (my === run) {
      const num = NUMBERS[n % NUMBERS.length];
      // dial the number on the keypad
      input.textContent = '+'; input.classList.add('typed');
      for (const d of num.slice(1)) {
        const key = q('[data-dx-key="' + d + '"]');
        await moveTo(key, 260); await press(key);
        input.textContent += d;
      }
      const call = q('[data-dx-call]');
      await moveTo(call, 500); await press(call);
      setStatus('Dialing…', 'warn');
      await sleep(700);
      q('[data-dx-dialed]').textContent = pretty(num);
      q('[data-dx-timer]').textContent = 'Ringing';
      root.classList.add('dx-in-call', 'dx-ringing');
      setStatus('Ringing', 'warn');
      await sleep(1900);
      root.classList.remove('dx-ringing'); root.classList.add('dx-active');
      setStatus('Active', 'ok');
      q('[data-dx-ctrl="rec"]').classList.add('on');
      let secs = 0;
      const tick = async count => { for (let i = 0; i < count; i++) { q('[data-dx-timer]').textContent = clock(++secs); await sleep(650); } };
      await tick(2);
      const mute = q('[data-dx-ctrl="mute"]');
      await moveTo(mute, 500); await press(mute); mute.classList.add('on');
      await tick(2);
      await press(mute); mute.classList.remove('on');
      await tick(2);
      const hang = q('.dx-hang');
      await moveTo(hang, 550); await press(hang);
      root.classList.remove('dx-active', 'dx-in-call');
      q('[data-dx-ctrl="rec"]').classList.remove('on');
      setStatus('Completed', 'done');
      q('[data-dx-toast-text]').textContent = pretty(num) + ' · ' + clock(secs) + ' · Recorded';
      toast.classList.add('show');
      const before = current.calls; current.calls += 1;
      countTo(stat('calls'), before, current.calls, v => v.toLocaleString(), 600);
      await sleep(2600);
      toast.classList.remove('show');
      setStatus('Ready', '');
      input.textContent = 'Enter or paste a number'; input.classList.remove('typed');
      await sleep(900);
      // switch the date range like a real user would
      r = (r + 1) % RANGES.length; n += 1;
      await moveTo(pills[r], 700); await press(pills[r]);
      setRange(r, true);
      await sleep(2200);
    }
  }
  // Start once the browser is idle and the frame has a size.
  requestAnimationFrame(() => { fit(); loop(); });
})();
