import { getQuote, money, quantity } from './shared.js';
const catalog = JSON.parse(document.getElementById('pricing-data').textContent);
const root = document.querySelector('[data-calculator]');
const plan = document.getElementById('calc-plan');
const users = document.getElementById('calc-users');
const countries = document.getElementById('calc-countries');
function update() {
  const n = quantity(users); const quote = getQuote(catalog,plan.value,n,Number(countries.value));
  root.querySelector('[data-minus]').disabled = n <= 1;
  root.querySelector('[data-plus]').disabled = n >= 100;
  root.querySelector('[data-europe-count]').hidden = plan.value !== 'uk-to-europe';
  root.querySelector('[data-total]').textContent = quote.total === null ? 'Custom quote' : money(quote.total);
  root.querySelector('[data-rate]').textContent = quote.rate === null ? 'Confirm requirements with our team' : money(quote.rate) + ' per user/month';
  const link = root.querySelector('[data-calculator-link]');
  link.href='/get-started/'+plan.value+'/?users='+n;
}
root.querySelector('[data-minus]').addEventListener('click',()=>{ users.value=quantity(users)-1; update(); });
root.querySelector('[data-plus]').addEventListener('click',()=>{ users.value=quantity(users)+1; update(); });
[plan,users,countries].forEach(element=>element.addEventListener('change',update));
users.addEventListener('input',()=>{ if (users.value!=='') update(); });
update();
