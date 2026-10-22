'use strict';
document.querySelectorAll('[data-confirm-delete]').forEach(form=>form.addEventListener('submit',event=>{
  if(!window.confirm('Permanently erase this enquiry, its notes and email job? This cannot be undone.'))event.preventDefault();
}));
