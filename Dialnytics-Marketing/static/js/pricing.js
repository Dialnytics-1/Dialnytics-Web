import { getQuote, addonQuote, money, quantity } from './shared.js?v=3';
const catalog = JSON.parse(document.getElementById('pricing-data').textContent);
const root = document.querySelector('[data-calculator]');
if (root) {
  const plan = root.querySelector('#calc-plan');
  const users = root.querySelector('#calc-users');
  const countries = root.querySelector('#calc-countries');
  const boxes = Array.from(root.querySelectorAll('[data-addon]'));
  const $ = sel => root.querySelector(sel);
  function update() {
    const n = quantity(users);
    const quote = getQuote(catalog, plan.value, n, Number(countries.value));
    const extras = addonQuote(catalog, boxes.filter(b => b.checked).map(b => b.value), n);
    $('[data-minus]').disabled = n <= 1;
    $('[data-plus]').disabled = n >= 100;
    $('[data-europe-count]').hidden = plan.value !== 'uk-to-europe';
    $('[data-plan-line]').textContent = quote.total === null ? 'Custom quote' : money(quote.total);
    $('[data-addon-line]').textContent = money(extras.monthly);
    $('[data-total]').textContent = quote.total === null ? 'Custom quote' : money(quote.total + extras.monthly);
    $('[data-onetime-row]').hidden = !extras.oneTime;
    $('[data-onetime]').textContent = money(extras.oneTime);
    $('[data-rate]').textContent = quote.rate === null
      ? 'We confirm a tailored price with you before payment.'
      : money(quote.rate) + ' per user for the plan' + (extras.monthly ? ' + ' + money(extras.monthly / n) + ' per user in add-ons' : '') + '.';
    const q = new URLSearchParams({ users: String(n) });
    if (extras.keys.length) q.set('addons', extras.keys.join(','));
    $('[data-calculator-link]').href = '/get-started/' + plan.value + '/?' + q.toString();
  }
  $('[data-minus]').addEventListener('click', () => { users.value = quantity(users) - 1; update(); });
  $('[data-plus]').addEventListener('click', () => { users.value = quantity(users) + 1; update(); });
  [plan, users, countries, ...boxes].forEach(el => el.addEventListener('change', update));
  users.addEventListener('input', () => { if (users.value !== '') update(); });
  update();
}
