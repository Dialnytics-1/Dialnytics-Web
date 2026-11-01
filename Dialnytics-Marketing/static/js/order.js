import { getQuote, addonQuote, money, quantity, newKey, submitRequest, copyText } from './shared.js?v=5';
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
const teamList = document.getElementById('team-list');
const teamFields = document.getElementById('team-fields');
const quoteFields = document.getElementById('quote-fields');
const numberStatus = document.getElementById('number-status');
const holdBanner = document.getElementById('hold-banner');
let numberOptions = []; let numbersLoadedFor = ''; let holdTimer = null; let holdExpires = null; let picks = [];
const isQuotePlan = () => ['europe','custom'].includes(plan.value);
const wantsTollFree = () => selectedAddons().includes('tollfree');
const params = new URLSearchParams(window.location.search);
const requestedUsers = Number(params.get('users') || 1);
users.value = Number.isInteger(requestedUsers) ? String(requestedUsers) : '1';
const addonBoxes = Array.from(form.querySelectorAll('[name="addon"]'));
const requestedAddons = (params.get('addons') || '').split(',');
addonBoxes.forEach(box => { if (!box.disabled && requestedAddons.includes(box.value)) box.checked = true; });
const smsInput = document.getElementById('order-sms-packs');
const smsPacks = () => { if (!smsInput) return 0; const v = Math.max(0, Math.min(100, Math.floor(Number(smsInput.value) || 0))); smsInput.value = String(v); return v; };
const selectedAddons = () => addonBoxes.filter(box => box.checked && !box.disabled).map(box => box.value);
if (smsInput) {
  document.getElementById('minus-sms').addEventListener('click', () => { smsInput.value = String(smsPacks() - 1); update(); });
  document.getElementById('plus-sms').addEventListener('click', () => { smsInput.value = String(smsPacks() + 1); update(); });
  smsInput.addEventListener('input', () => update());
}
const selectedCountries = () => Array.from(form.querySelectorAll('[name="europe_country"]:checked')).map(input=>input.value);
function showError(text) { error.textContent=text; error.hidden=!text; }
function update() {
  const n = quantity(users), countryCount=Math.max(1,selectedCountries().length);
  const quote = getQuote(catalog,plan.value,n,Math.min(6,countryCount));
  minus.disabled=n<=1; plus.disabled=n>=100;
  document.getElementById('europe-picker').hidden=plan.value!=='uk-to-europe';
  document.getElementById('summary-plan').textContent=catalog.plans[plan.value].name;
  document.getElementById('summary-users').textContent=String(n);
  document.getElementById('summary-rate').textContent=quote.rate===null ? 'Quote required' : money(quote.rate);
  const tfBox = addonBoxes.find(b => b.value === 'tollfree');
  if (tfBox) { const ok = plan.value === 'usa-canada'; tfBox.disabled = !ok; if (!ok) tfBox.checked = false; tfBox.closest('label').hidden = !ok; }
  const distinct = new Set(picks.filter(Boolean)).size;
  const extras = addonQuote(catalog, selectedAddons(), n, distinct || n, smsPacks());
  document.getElementById('summary-addons').textContent=money(extras.monthly);
  document.getElementById('summary-onetime-row').hidden=!extras.oneTime;
  const smsNote=document.querySelector('[data-sms-note]'); if(smsNote) smsNote.hidden=!extras.keys.includes('sms');
  document.getElementById('summary-onetime').textContent=money(extras.oneTime);
  document.getElementById('summary-addon-names').textContent=extras.names.length ? 'Add-ons: '+extras.names.join(', ') : '';
  document.getElementById('summary-total').textContent=quote.total===null ? 'Custom quote' : money(quote.total+extras.monthly);
  const first=document.getElementById('summary-first'); if(first){first.hidden=!extras.oneTime||quote.total===null;first.querySelector('dd').textContent=quote.total===null?'':money(quote.total+extras.monthly+extras.oneTime);}
  document.getElementById('summary-countries').textContent=plan.value==='uk-to-europe' ? (selectedCountries().length ? selectedCountries().join(', ') : 'Select at least one European destination.') : '';
  document.getElementById('plan-explainer').textContent = plan.value === 'usa-canada'
    ? '1 user: '+money(Number(catalog.usa.one))+'/month. 2 users: '+money(Number(catalog.usa.two))+' total/month. 3+ users: '+money(Number(catalog.usa.per))+' per user/month.'
    : plan.value === 'uk-to-europe' ? 'The monthly rate is for your chosen destination package per user. Select 1-6 countries. For more destinations, choose Custom Plan.'
    : quote.total===null ? 'No invented price: tell us your requirements and our team will confirm a quote before you pay.'
    : money(quote.rate)+' per user/month, taxes included. Calling, your number, CRM and voicemail are included.';
  return quote;
}

function fmt(number){ const m=/^\+1(\d{3})(\d{3})(\d{4})$/.exec(number); if(m) return `+1 (${m[1]}) ${m[2]}-${m[3]}`; const u=/^\+44(\d{4})(\d{6})$/.exec(number); return u?`+44 ${u[1]} ${u[2]}`:number; }
function memberCard(i){
  const wrap=document.createElement('fieldset'); wrap.className='team-member card'; wrap.dataset.member=String(i);
  const legend=document.createElement('legend'); legend.textContent=i===0?'User 1 (account owner)':'User '+(i+1); wrap.append(legend);
  const grid=document.createElement('div'); grid.className='form-grid';
  const field=(label,name,type,attrs={})=>{ const d=document.createElement('div'); const l=document.createElement('label'); l.textContent=label+' *'; const input=document.createElement('input'); input.type=type; input.dataset.field=name; input.required=true; Object.entries(attrs).forEach(([k,v])=>input.setAttribute(k,v)); l.htmlFor='tm-'+name+'-'+i; input.id='tm-'+name+'-'+i; d.append(l,input); return d; };
  grid.append(field('Full name','name','text',{autocomplete:i===0?'name':'off',minlength:'2',maxlength:'150'}),field('Login email','email','email',{autocomplete:i===0?'email':'off',maxlength:'254'}),field('Password (min. 12 characters)','password','password',{autocomplete:'new-password',minlength:'12',maxlength:'128'}));
  const nd=document.createElement('div'); const nl=document.createElement('label'); nl.textContent=wantsTollFree()?'Toll-free number':'Phone number'; nl.htmlFor='tm-number-'+i; const sel=document.createElement('select'); sel.id='tm-number-'+i; sel.dataset.field='number'; nd.append(nl,sel); grid.append(nd);
  wrap.append(grid); return wrap;
}
function fillSelect(sel,current){
  sel.replaceChildren(new Option(numberOptions.length?'Select a number':'No numbers available right now',''));
  const list=new Set(numberOptions); if(current) list.add(current);
  [...list].sort().forEach(n=>sel.append(new Option(fmt(n),n)));
  sel.value=current&&list.has(current)?current:'';
}
function renderTeam(){
  const n=quantity(users); const existing=[...teamList.querySelectorAll('.team-member')];
  while(existing.length>n) existing.pop().remove();
  for(let i=existing.length;i<n;i++) teamList.append(memberCard(i));
  teamList.querySelectorAll('.team-member').forEach(card=>{ const sel=card.querySelector('[data-field=number]'); const cur=sel.value; fillSelect(sel,cur); card.querySelector('label[for^=tm-number]').textContent=wantsTollFree()?'Toll-free number':'Phone number'; });
  readPicks();
}
function readPicks(){ picks=[...teamList.querySelectorAll('[data-field=number]')].map(s=>s.value); }
function showNumberStatus(text,bad){ numberStatus.textContent=text; numberStatus.hidden=!text; numberStatus.classList.toggle('error-box',!!bad); }
async function loadNumbers(){
  if(isQuotePlan()) return;
  const sig=plan.value+'|'+(wantsTollFree()?1:0); showNumberStatus('Loading available numbers...');
  try{
    const r=await fetch('/api/numbers?'+new URLSearchParams({plan:plan.value,toll_free:wantsTollFree()?'1':'0',token:key}),{credentials:'same-origin'});
    const data=await r.json(); if(!r.ok) throw new Error(typeof data.detail==='string'?data.detail:'Numbers are unavailable right now.');
    numberOptions=data.numbers||[]; numbersLoadedFor=sig;
    showNumberStatus(numberOptions.length?'':'No numbers are available for this plan right now. You can still place your order: your account is created and we will contact you on WhatsApp to assign a number.',!numberOptions.length);
  }catch(err){ numberOptions=[]; numbersLoadedFor=''; showNumberStatus(err.message,true); }
  renderTeam();
}
function stopHold(){ clearInterval(holdTimer); holdTimer=null; holdExpires=null; holdBanner.hidden=true; }
function tick(){
  if(!holdExpires) return; const left=Math.max(0,Math.floor((holdExpires-Date.now())/1000));
  if(left<=0){ stopHold(); teamList.querySelectorAll('[data-field=number]').forEach(s=>{s.value='';}); readPicks(); update(); showNumberStatus('Your reservation expired and the numbers were released. Please choose your numbers again.',true); loadNumbers(); return; }
  holdBanner.hidden=false; holdBanner.textContent='Your number'+(new Set(picks.filter(Boolean)).size>1?'s are':' is')+' reserved for you. Please complete payment within '+Math.floor(left/60)+':'+String(left%60).padStart(2,'0')+' minutes, or the reservation is released.';
}
let holdBusy=false;
async function holdPicks(){
  readPicks(); const wanted=[...new Set(picks.filter(Boolean))];
  if(!wanted.length){ if(holdTimer){ try{ await fetch('/api/numbers/hold',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({token:key,plan:plan.value,numbers:[],toll_free:wantsTollFree()})}); }catch(_){} } stopHold(); update(); return; }
  if(holdBusy) return; holdBusy=true;
  try{
    const r=await fetch('/api/numbers/hold',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({token:key,plan:plan.value,numbers:wanted,toll_free:wantsTollFree()})});
    const data=await r.json(); if(!r.ok) throw new Error(typeof data.detail==='string'?data.detail:'Could not reserve the number.');
    if((data.unavailable||[]).length){ teamList.querySelectorAll('[data-field=number]').forEach(s=>{ if(data.unavailable.includes(s.value)) s.value=''; }); showNumberStatus('Someone else just reserved: '+data.unavailable.map(fmt).join(', ')+'. Please choose another number.',true); await loadNumbers(); }
    else showNumberStatus('');
    readPicks();
    if(data.expires_at && data.held.length){ holdExpires=new Date(data.expires_at).getTime(); if(!holdTimer) holdTimer=setInterval(tick,1000); tick(); } else stopHold();
  }catch(err){ showNumberStatus(err.message,true); }
  finally{ holdBusy=false; update(); }
}
function validateCurrent() {
  if (step===0 && plan.value==='uk-to-europe' && (!selectedCountries().length || selectedCountries().length>6)) { showError('Choose between 1 and 6 European destinations.'); return false; }
  if (step===2) {
    const fields=[...steps[2].querySelectorAll('#team-fields:not([hidden]) input[data-field],#team-fields:not([hidden]) select[data-field],#quote-fields:not([hidden]) input,#order-phone,#order-company,#order-message')];
    for (const field of fields) { field.required = field.dataset.field==='number' ? false : field.required; if (!field.reportValidity()) return false; }
    if (!isQuotePlan()) {
      const emails=[...teamList.querySelectorAll('[data-field=email]')].map(i=>i.value.trim().toLowerCase());
      if (new Set(emails).size!==emails.length) { showError('Each user needs a different email address.'); return false; }
      if (numberOptions.length && picks.some(p=>!p)) { showError('Choose a number for every user. Users in the same business can share one number.'); return false; }
    }
    if (!/^\+[1-9][0-9\s()-]{6,24}$/.test(form.elements.phone.value.trim())) { showError('Enter a WhatsApp number with the country code, starting with +.'); form.elements.phone.focus(); return false; }
  }
  return true;
}
function review() {
  const list = document.getElementById('review-details'); list.replaceChildren();
  const rows=[['WhatsApp',form.elements.phone.value],['Business',form.elements.company.value || '-'],['Add-ons',addonQuote(catalog,selectedAddons(),1,1,smsPacks()).names.join(', ') || 'None']];
  if (isQuotePlan()) rows.unshift(['Name',form.elements.name.value],['Email',form.elements.email.value]);
  else [...teamList.querySelectorAll('.team-member')].reverse().forEach((c,idx,arr)=>rows.unshift(['User '+(arr.length-idx)+' ('+c.querySelector('[data-field=name]').value+')',c.querySelector('[data-field=email]').value+' · '+(c.querySelector('[data-field=number]').value?fmt(c.querySelector('[data-field=number]').value):'no number')]));
  for (const [label,value] of rows) {
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
  if(step===2){ quoteFields.hidden=!isQuotePlan(); teamFields.hidden=isQuotePlan(); quoteFields.querySelectorAll('input').forEach(i=>{i.required=isQuotePlan();}); if(!isQuotePlan()){ renderTeam(); if(numbersLoadedFor!==plan.value+'|'+(wantsTollFree()?1:0)) loadNumbers(); } }
  if(step===3) review();
  if(focus){const heading=steps[step].querySelector('h2');heading.tabIndex=-1;heading.focus({preventScroll:true});root.querySelector('.order-main').scrollIntoView({behavior:'smooth',block:'start'});}
}
minus.addEventListener('click',()=>{users.value=quantity(users)-1;update();if(step===2)renderTeam();});
plus.addEventListener('click',()=>{users.value=quantity(users)+1;update();if(step===2)renderTeam();});
users.addEventListener('change',update);
users.addEventListener('input',()=>{if(users.value!=='')update();});
plan.addEventListener('change',()=>{showError('');numbersLoadedFor='';numberOptions=[];stopHold();picks=[];teamList.replaceChildren();update();});
addonBoxes.forEach(box=>box.addEventListener('change',()=>{ if(box.value==='tollfree'){ numbersLoadedFor=''; stopHold(); teamList.querySelectorAll('[data-field=number]').forEach(s=>{s.value='';}); readPicks(); } update(); }));
teamList.addEventListener('change',e=>{ if(e.target.matches('[data-field=number]')) holdPicks(); });
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
  const team=isQuotePlan()?[]:[...teamList.querySelectorAll('.team-member')].map(c=>({name:c.querySelector('[data-field=name]').value.trim(),email:c.querySelector('[data-field=email]').value.trim(),password:c.querySelector('[data-field=password]').value,number:c.querySelector('[data-field=number]').value}));
  const payload={kind:'order',name:isQuotePlan()?String(fields.get('name')).trim():team[0].name,email:isQuotePlan()?String(fields.get('email')).trim():team[0].email,phone:String(fields.get('phone')).trim(),company:String(fields.get('company')||''),message:String(fields.get('message')||''),plan:plan.value,users:quantity(users),countries:plan.value==='uk-to-europe'?selectedCountries():[],addons:selectedAddons(),sms_packs:smsPacks(),team,hold_token:key,payment:String(fields.get('payment')||''),consent:true,website:String(fields.get('website')||''),idempotency_key:key};
  busy=true;submit.disabled=true;back.disabled=true;submit.textContent='Saving your enquiry...';showError('');
  try{
    const data=await submitRequest(payload);saved=true;message=data.whatsapp_message;
    document.getElementById('order-reference').textContent=data.reference;
    document.getElementById('order-whatsapp').href=data.whatsapp_url;
    if(data.provisioned){
      stopHold();
      const box=document.getElementById('success-hold'); const mins=data.hold_minutes||60;
      const until=data.expires_at?new Date(data.expires_at).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'';
      document.getElementById('success-text').textContent='Your account'+(data.team.length>1?'s are':' is')+' created and waiting for payment. Continue on WhatsApp to get the payment details.';
      box.textContent='Please complete payment within '+(mins>=60?'1 hour':mins+' minutes')+(until?' (by '+until+')':'')+'. After that, the pending order and your reserved number'+(data.team.length>1?'s':'')+' are released automatically. Your account activates as soon as payment is confirmed.';
      box.hidden=false;
    }
    if(data.quote && data.quote.monthly_total!==null)document.getElementById('summary-total').textContent=money(Number(data.quote.monthly_total));
    if(data.checkout_url){submit.textContent='Opening secure card checkout...';window.location.assign(data.checkout_url);return;}
    if(data.checkout_error){const n=document.getElementById('order-checkout-note');n.textContent=data.checkout_error;n.hidden=false;}
    navigate(4);
  }catch(err){showError(err.message);submit.disabled=false;back.disabled=false;submit.textContent='Save enquiry & continue';}
  finally{busy=false;}
});
document.getElementById('copy-order').addEventListener('click',event=>copyText(message,event.currentTarget));
document.getElementById('print-order').addEventListener('click',()=>window.print());
update();navigate(0,false);
