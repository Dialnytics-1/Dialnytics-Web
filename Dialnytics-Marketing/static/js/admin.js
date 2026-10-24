'use strict';
document.querySelectorAll('[data-confirm-delete]').forEach(form=>form.addEventListener('submit',event=>{
  if(!window.confirm('Permanently erase this enquiry, its notes and email job? This cannot be undone.'))event.preventDefault();
}));
document.querySelectorAll('[data-confirm-chat-delete]').forEach(form=>form.addEventListener('submit',event=>{
  if(!window.confirm('Delete this chat and all its messages? A saved lead stays in the inbox.'))event.preventDefault();
}));

/* Chats badge in the admin menu */
(()=>{
  const badge=document.querySelector('[data-chat-badge]');
  if(!badge)return;
  async function refresh(){
    try{
      const r=await fetch('/admin/chats/badge.json',{credentials:'same-origin'});
      if(!r.ok)return;
      const d=await r.json();
      badge.textContent=d.unread>99?'99+':String(d.unread);
      badge.hidden=!d.unread;
    }catch(_){}
  }
  refresh(); setInterval(()=>{if(!document.hidden)refresh();},20000);
})();

/* Chat list: refresh while nobody is typing */
(()=>{
  if(!document.querySelector('[data-chat-list]'))return;
  setInterval(()=>{
    const a=document.activeElement;
    if(document.hidden||(a&&['INPUT','SELECT','TEXTAREA'].includes(a.tagName)))return;
    window.location.reload();
  },30000);
})();

/* Chat detail: live messages */
(()=>{
  const thread=document.querySelector('[data-chat-thread]');
  if(!thread)return;
  const id=thread.dataset.chatId; let last=Number(thread.dataset.lastId||0);
  const pill=document.querySelector('[data-ai-pill]');
  const names={user:document.querySelector('.admin-heading h1')?.textContent||'Customer',assistant:'AI assistant',admin:'You'};
  const fmt=new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:true,timeZone:'Asia/Karachi'});
  thread.scrollTop=thread.scrollHeight;
  function add(m){
    if(thread.querySelector('[data-id="'+m.id+'"]'))return;
    thread.querySelector('.chat-empty')?.remove();
    const row=document.createElement('div'); row.className='bubble-row '+m.role; row.dataset.id=m.id;
    const b=document.createElement('div'); b.className='bubble';
    const who=document.createElement('span'); who.className='bubble-who'; who.textContent=names[m.role]||m.role;
    const p=document.createElement('p'); p.textContent=m.text;
    const t=document.createElement('small'); t.textContent=(m.at?fmt.format(new Date(m.at))+' PKT':'')+(m.status==='failed'?' · not delivered':m.status?' · '+m.status:'');
    b.append(who,p,t); row.append(b); thread.append(row);
  }
  async function poll(){
    try{
      const r=await fetch('/admin/chats/'+encodeURIComponent(id)+'/poll?after='+last,{credentials:'same-origin'});
      if(!r.ok)return;
      const d=await r.json();
      const atBottom=thread.scrollHeight-thread.scrollTop-thread.clientHeight<80;
      d.messages.forEach(m=>{add(m); last=Math.max(last,m.id);});
      if(d.messages.length&&atBottom)thread.scrollTop=thread.scrollHeight;
      if(pill){pill.textContent='AI '+(d.ai_enabled?'ON':'OFF');pill.classList.toggle('on',d.ai_enabled);pill.classList.toggle('off',!d.ai_enabled);}
    }catch(_){}
  }
  setInterval(()=>{if(!document.hidden)poll();},4000);
  const box=document.getElementById('reply-body');
  box?.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();box.form.requestSubmit();}});
  box?.form.addEventListener('submit',()=>{const btn=box.form.querySelector('button[type="submit"]');if(btn){btn.disabled=true;btn.firstChild.textContent='Sending… ';}});
})();

// Confirm before destructive admin buttons that carry data-confirm (e.g. pricing reset).
document.addEventListener('click', event => {
  const button = event.target.closest('[data-confirm]');
  if (button && !window.confirm(button.dataset.confirm)) event.preventDefault();
});
