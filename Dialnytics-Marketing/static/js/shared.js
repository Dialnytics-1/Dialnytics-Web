export function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value);
}
export function getQuote(catalog, plan, users, count = 1) {
  if (!catalog.plans[plan] || !Number.isInteger(users) || users < 1 || users > 100) throw new Error('Choose a valid plan and 1 to 100 users.');
  let cents;
  if (['europe','custom'].includes(plan)) return { total: null, rate: null };
  if (plan === 'usa-canada') cents = users === 1 ? 2200 : users === 2 ? 3800 : users * 1500;
  else if (plan === 'uk-to-europe') {
    if (!catalog.europe_totals[String(count)]) throw new Error('Choose 1 to 6 European destinations.');
    cents = Math.round(Number(catalog.europe_totals[String(count)]) * 100) * users;
  } else cents = catalog.plans[plan].price * users * 100;
  return { total: cents / 100, rate: cents / 100 / users };
}
export function quantity(input) {
  const value = Number(input.value);
  const valid = Number.isFinite(value) ? Math.max(1,Math.min(100,Math.floor(value))) : 1;
  input.value = String(valid);
  return valid;
}
export function newKey() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = Array.from(bytes,byte => byte.toString(16).padStart(2,'0')).join('');
  return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
export async function submitRequest(payload) {
  let response;
  try {
    response = await fetch('/api/requests', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type':'application/json', 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content },
      body: JSON.stringify(payload)
    });
  } catch (_) { throw new Error('Connection interrupted. Your request may not have been saved. Retry without changing the form, or contact us directly.'); }
  let data;
  try { data = await response.json(); }
  catch (_) { throw new Error('The server returned an unexpected response. Please retry or contact us on WhatsApp.'); }
  if (!response.ok) {
    let message = data.detail;
    if (Array.isArray(message)) message = message.map(item => item.loc.slice(1).join(' ') + ': ' + item.msg).join('. ');
    throw new Error(typeof message === 'string' ? message : 'Could not save your request. Please try again.');
  }
  if (data.saved !== true || !data.reference) throw new Error('The server did not confirm that your request was saved. Please contact us.');
  return data;
}
export async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    const old = button.textContent; button.textContent = 'Copied';
    setTimeout(() => { button.textContent = old; },1800);
  } catch (_) {
    const area = document.createElement('textarea'); area.value=text; area.setAttribute('readonly','');
    area.style.position='fixed'; area.style.top='10px'; area.style.left='10px'; area.style.zIndex='9999';
    document.body.append(area); area.focus(); area.select();
    const copied = document.execCommand('copy');
    if (copied) { area.remove(); button.textContent='Copied'; }
    else { button.textContent='Select and copy the message above'; area.addEventListener('blur',()=>area.remove(),{once:true}); }
  }
}
