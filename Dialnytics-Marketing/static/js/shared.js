export function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value);
}
export function getQuote(catalog, plan, users, count = 1) {
  if (!catalog.plans[plan] || !Number.isInteger(users) || users < 1 || users > 100) throw new Error('Choose a valid plan and 1 to 100 users.');
  let cents;
  if (['europe','custom'].includes(plan)) return { total: null, rate: null };
  if (plan === 'usa-canada') {
    // Prices come from the server catalog (admin-managed); never hardcode them here.
    const usa = catalog.usa || { one: catalog.plans[plan].price, two: catalog.plans[plan].price * 2, per: catalog.plans[plan].price };
    cents = Math.round(Number(users === 1 ? usa.one : users === 2 ? usa.two : usa.per) * 100) * (users > 2 ? users : 1);
  }
  else if (plan === 'uk-to-europe') {
    if (!catalog.europe_totals[String(count)]) throw new Error('Choose 1 to 6 European destinations.');
    cents = Math.round(Number(catalog.europe_totals[String(count)]) * 100) * users;
  } else cents = Math.round(catalog.plans[plan].price * 100) * users;
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
// Add-ons are priced per user per month; SMS also has a one-time registration fee.
export function addonQuote(catalog, keys, users) {
  const list = (catalog.addons || []).filter(a => a.live && keys.includes(a.key));
  const lines = list.map(a => ({ key: a.key, name: a.name, total: Math.round(Number(a.price) * 100) * users / 100 }));
  const monthly = lines.reduce((sum, l) => sum + Math.round(l.total * 100), 0) / 100;
  const oneTime = keys.includes('sms') ? Number(catalog.sms_setup || 0) : 0;
  return { lines, monthly, oneTime, keys: list.map(a => a.key) };
}
