import { newKey, submitRequest } from './shared.js';
const form = document.getElementById('enquiry-form');
const error = document.getElementById('form-error');
const kind = form.dataset.kind; const key = newKey();
let busy=false;
const preferredDate=document.getElementById('preferred-date');
if(preferredDate){const today=new Date();preferredDate.min=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');}
form.addEventListener('submit',async event=>{
  event.preventDefault(); if(busy||!form.reportValidity())return;
  const fields=new FormData(form);
  const value=name=>String(fields.get(name)||'').trim();
  const payload={kind,name:value('name'),email:value('email'),phone:value('phone'),company:value('company'),message:value('message'),subject:value('subject'),website:value('website'),consent:fields.get('consent')==='on',idempotency_key:key};
  if(kind==='demo')Object.assign(payload,{preferred_date:value('preferred_date'),preferred_time:value('preferred_time'),timezone:value('timezone')});
  if(kind==='quote')Object.assign(payload,{plan:value('plan'),users:Number(fields.get('users')||1)});
  const submit=form.querySelector('button[type="submit"]'); const label=submit.textContent;
  busy=true; submit.disabled=true;submit.textContent='Saving your request...';error.hidden=true;
  try{
    const data=await submitRequest(payload);
    document.getElementById('form-reference').textContent=data.reference;
    document.getElementById('form-whatsapp').href=data.whatsapp_url;
    form.hidden=true; const success=document.getElementById('form-success');success.hidden=false;success.tabIndex=-1;success.focus();success.scrollIntoView({behavior:'smooth',block:'center'});
  }catch(err){error.textContent=err.message;error.hidden=false;submit.disabled=false;submit.textContent=label;}
  finally{busy=false;}
});
