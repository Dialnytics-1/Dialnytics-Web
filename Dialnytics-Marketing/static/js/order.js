import { getQuote, addonQuote, money, quantity, newKey, submitRequest, copyText } from './shared.js?v=28';
const catalog = JSON.parse(document.getElementById('pricing-data').textContent);
const root = document.getElementById('order-app');
const form = document.getElementById('order-form');
const plan = document.getElementById('order-plan');
const users = document.getElementById('order-users');
const minus = document.getElementById('minus-users');
const plus = document.getElementById('plus-users');
const next = document.getElementById('order-next');
const back = document.getElementById('order-back');
const submit = document.getElementById('order-submit');
const error = document.getElementById('order-error');
const steps = Array.from(document.querySelectorAll('[data-step]'));
let step = 0; let busy = false; let saved = false; let message = '';
const key = newKey();
const params = new URLSearchParams(window.location.search);
const requestedUsers = Number(params.get('users') || 1);
users.value = Number.isInteger(requestedUsers) ? String(requestedUsers) : '1';
const addonBoxes = Array.from(form.querySelectorAll('[name="addon"]'));
const requestedAddons = (params.get('addons') || '').split(',');
addonBoxes.forEach(box => { if (!box.disabled && requestedAddons.includes(box.value)) box.checked = true; });
const selectedAddons = () => addonBoxes.filter(box => box.checked && !box.disabled).map(box => box.value);
const selectedCountries = () => Array.from(form.querySelectorAll('[name="europe_country"]:checked')).map(input=>input.value);
// Inventory is the provider-owned pool, not numbers offered for purchase.
const picker=document.getElementById('owned-number-picker');
const countrySelect=document.getElementById('number-country');
const numberOptions=document.getElementById('number-options');
const availability=document.getElementById('number-availability-status');
let inventoryEnabled=false, inventoryRequest=0;
const selectedNumberIds=()=>Array.from(numberOptions.querySelectorAll('input:checked')).map(el=>el.value);
async function refreshInventory(){
  if(!inventoryEnabled)return;
  const seq=++inventoryRequest;
  availability.textContent='Loading available numbers...';
  numberOptions.replaceChildren();
  try{
    const response=await fetch('/api/numbers/available?country='+encodeURIComponent(countrySelect.value),{credentials:'same-origin'});
    if(!response.ok)throw new Error('Unable to load numbers');
    const result=await response.json();if(seq!==inventoryRequest)return;
    for(const number of result.numbers||[]){
      const label=document.createElement('label');const input=document.createElement('input');
      input.type='checkbox';input.value=number.id;input.name='selected_owned_number';
      input.addEventListener('change',()=>{
        if(selectedNumberIds().length>quantity(users)){input.checked=false;showError('Select one number per user.');}
        else showError('');
      });
      label.append(input,document.createTextNode(' '+number.number));numberOptions.append(label);
    }
    availability.textContent=(result.numbers||[]).length+' numbers available. Select '+quantity(users)+' unique number(s).';
  }catch(e){if(seq===inventoryRequest)availability.textContent='Number inventory unavailable. Please retry or contact support.';}
}
fetch('/api/checkout/inventory-mode',{credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{
  inventoryEnabled=Boolean(data&&(data.enabled===true));
  picker.hidden=!inventoryEnabled;if(inventoryEnabled)refreshInventory();
}).catch(()=>{});
countrySelect.addEventListener('change',refreshInventory);

function showError(text) { error.textContent=text; error.hidden=!text; }
function update() {
  const n = quantity(users), countryCount=Math.max(1,selectedCountries().length);
  const quote = getQuote(catalog,plan.value,n,Math.min(6,countryCount));
  minus.disabled=n<=1; plus.disabled=n>=100;
  if(inventoryEnabled)availability.textContent='Select '+n+' unique number(s).';
  document.getElementById('europe-picker').hidden=plan.value!=='uk-to-europe';
  document.getElementById('summary-plan').textContent=catalog.plans[plan.value].name;
  document.getElementById('summary-users').textContent=String(n);
  document.getElementById('summary-rate').textContent=quote.rate===null ? 'Quote required' : money(quote.rate);
  const extras = addonQuote(catalog, selectedAddons(), n);
  document.getElementById('summary-addons').textContent=money(extras.monthly);
  document.getElementById('summary-onetime-row').hidden=!extras.oneTime;
  const smsNote=document.querySelector('[data-sms-note]'); if(smsNote) smsNote.hidden=!extras.keys.includes('sms');
  document.getElementById('summary-onetime').textContent=money(extras.oneTime);
  document.getElementById('summary-addon-names').textContent=extras.lines.length ? 'Add-ons: '+extras.lines.map(l=>l.name).join(', ') : '';
  document.getElementById('summary-total').textContent=quote.total===null ? 'Custom quote' : money(quote.total+extras.monthly);
  document.getElementById('summary-countries').textContent=plan.value==='uk-to-europe' ? (selectedCountries().length ? selectedCountries().join(', ') : 'Select at least one European destination.') : '';
  document.getElementById('plan-explainer').textContent = plan.value === 'usa-canada'
    ? '1 user: '+money(Number(catalog.usa.one))+'/month. 2 users: '+money(Number(catalog.usa.two))+' total/month. 3+ users: '+money(Number(catalog.usa.per))+' per user/month.'
    : plan.value === 'uk-to-europe' ? 'The monthly rate is for your chosen destination package per user. Select 1-6 countries. For more destinations, choose Custom Plan.'
    : quote.total===null ? 'No invented price: tell us your requirements and our team will confirm a quote before you pay.'
    : money(quote.rate)+' per user/month, taxes included. Calling, your number and voicemail are included. CRM + Power Dialer is optional.';
  return quote;
}
function validateCurrent() {
  if(step===0 && inventoryEnabled && selectedNumberIds().length!==quantity(users)){showError('Select exactly one available number per user.');return false;}
  if (step===0 && plan.value==='uk-to-europe' && (!selectedCountries().length || selectedCountries().length>6)) { showError('Choose between 1 and 6 European destinations.'); return false; }
  if (step===2) {
    for (const field of steps[2].querySelectorAll('input,textarea')) if (!field.reportValidity()) return false;
    if (!/^\+[1-9][0-9\s()-]{6,24}$/.test(form.elements.phone.value.trim())) { showError('Enter a WhatsApp number with the country code, starting with +.'); form.elements.phone.focus(); return false; }
  }
  return true;
}
function review() {
  const list = document.getElementById('review-details'); list.replaceChildren();
  for (const [label,value] of [['Name',form.elements.name.value],['Email',form.elements.email.value],['WhatsApp',form.elements.phone.value],['Business',form.elements.company.value || '-'],['Add-ons',addonQuote(catalog,selectedAddons(),quantity(users)).lines.map(l=>l.name).join(', ') || 'None']]) {
    const row=document.createElement('div'), left=document.createElement('span'), right=document.createElement('strong');
    left.textContent=label;right.textContent=value;row.append(left,right);list.append(row);
  }
}
function navigate(n,focus=true) {
  step=n; showError('');
  steps.forEach((panel,i)=>{ panel.hidden=i!==step; });
  document.querySelectorAll('[data-progress]').forEach((item,i)=>{item.classList.toggle('active',i===step);item.classList.toggle('complete',i<step);if(i===step)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');});
  back.hidden=step===0 || step===4;next.hidden=step>=3;submit.hidden=step!==3;
  document.querySelector('.wizard-actions').hidden=step===4;
  if(step===3) review();
  if(focus){const heading=steps[step].querySelector('h2');heading.tabIndex=-1;heading.focus({preventScroll:true});root.querySelector('.order-main').scrollIntoView({behavior:'smooth',block:'start'});}
}
minus.addEventListener('click',()=>{users.value=quantity(users)-1;update();});
plus.addEventListener('click',()=>{users.value=quantity(users)+1;update();});
users.addEventListener('change',update);
users.addEventListener('input',()=>{if(users.value!=='')update();});
plan.addEventListener('change',()=>{showError('');update();});
addonBoxes.forEach(box=>box.addEventListener('change',update));
form.querySelectorAll('[name="europe_country"]').forEach(input=>input.addEventListener('change',()=>{
  if(selectedCountries().length>6){input.checked=false;showError('Select up to 6 destinations. Use Custom Plan for a larger destination mix.');}else showError('');
  update();
}));
next.addEventListener('click',()=>{showError('');if(validateCurrent())navigate(step+1);});
back.addEventListener('click',()=>{if(!busy)navigate(Math.max(0,step-1));});
form.addEventListener('keydown',event=>{if(event.key==='Enter' && event.target.tagName!=='TEXTAREA' && step<3 && !['BUTTON','SELECT'].includes(event.target.tagName)){event.preventDefault();next.click();}});
form.addEventListener('submit',async event=>{
  event.preventDefault(); if(busy||saved)return;
  if(step!==3){if(validateCurrent())navigate(Math.min(3,step+1));return;}
  if(!document.getElementById('order-consent').reportValidity())return;
  const fields=new FormData(form);
  const payload={kind:'order',name:String(fields.get('name')).trim(),email:String(fields.get('email')).trim(),phone:String(fields.get('phone')).trim(),company:String(fields.get('company')||''),message:String(fields.get('message')||''),plan:plan.value,users:quantity(users),countries:plan.value==='uk-to-europe'?selectedCountries():[],addons:selectedAddons(),payment:String(fields.get('payment')),number_preference:String(fields.get('number_preference')||''),consent:true,website:String(fields.get('website')||''),idempotency_key:key,number_country:inventoryEnabled?countrySelect.value:'',number_ids:inventoryEnabled?selectedNumberIds():[],dialer_password:String(fields.get('dialer_password')||'')};
  busy=true;submit.disabled=true;back.disabled=true;submit.textContent='Saving your enquiry...';showError('');
  try{
    const data=await submitRequest(payload);saved=true;message=data.whatsapp_message;
    document.getElementById('order-reference').textContent=data.reference;
    document.getElementById('order-whatsapp').href=data.whatsapp_url;
    if(data.quote && data.quote.monthly_total!==null)document.getElementById('summary-total').textContent=money(Number(data.quote.monthly_total));
    if(data.checkout_url){submit.textContent='Opening secure card checkout...';window.location.assign(data.checkout_url);return;}
    if(data.payment_deadline){startPendingCountdown(data.payment_deadline);}
    if(data.checkout_error){const n=document.getElementById('order-checkout-note');n.textContent=data.checkout_error;n.hidden=false;}
    navigate(4);
  }catch(err){showError(err.message);submit.disabled=false;back.disabled=false;submit.textContent='Save enquiry & continue';}
  finally{busy=false;}
});
function startPendingCountdown(iso){
  const target=Date.parse(iso);if(!Number.isFinite(target))return;
  const el=document.getElementById('pending-payment-timer');if(!el)return;
  el.hidden=false;
  const updateTimer=()=>{
    const remaining=Math.max(0,Math.ceil((target-Date.now())/1000));
    el.textContent=remaining ? 'Payment window: '+String(Math.floor(remaining/60)).padStart(2,'0')+':'+String(remaining%60).padStart(2,'0')+' remaining. Contact support on WhatsApp to confirm payment.' : 'Payment window expired. Contact support to place a new order.';
    if(remaining===0)clearInterval(timer);
  };
  const timer=setInterval(updateTimer,1000);updateTimer();
}
document.getElementById('copy-order').addEventListener('click',event=>copyText(message,event.currentTarget));
document.getElementById('print-order').addEventListener('click',()=>window.print());
update();navigate(0,false);
