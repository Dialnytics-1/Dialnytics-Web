'use strict';
(function(){
  var root=document.documentElement;
  function isLight(){var t=root.getAttribute('data-theme');return t==='light'||(!t&&window.matchMedia('(prefers-color-scheme:light)').matches)}
  document.querySelectorAll('.nx-theme').forEach(function(b){b.addEventListener('click',function(){var n=isLight()?'dark':'light';root.setAttribute('data-theme',n);try{localStorage.setItem('dn-theme',n)}catch(e){}})});
  if(!window.matchMedia('(hover:hover) and (pointer:fine)').matches||window.matchMedia('(prefers-reduced-motion:reduce)').matches)return;
  var cur=document.createElement('div'),ring=document.createElement('div'),aura=document.createElement('div');
  cur.className='nx-cur';ring.className='nx-ring';aura.className='nx-aura';
  [aura,ring,cur].forEach(function(e){e.setAttribute('aria-hidden','true');document.body.appendChild(e)});
  var cards=document.querySelectorAll('.hm-feat,.hm-num-card,.hm-steps li,.hm-tile,.hm-stats-row>div,.hm-industries a,.hm-post,.hm-trust article,.hm-mission-grid>div,.price-teaser,.plan-card,.feature-card,.collection-card,.country-card,.calc2');
  cards.forEach(function(c){c.classList.add('nx-sp')});
  var hero=document.querySelector('.hm-hero'),shot=document.querySelector('.hm-hero .dx-frame');
  var mx=innerWidth/2,my=innerHeight/2,rx=mx,ry=my,ax=mx,ay=my,on=false;
  addEventListener('mousemove',function(e){
    mx=e.clientX;my=e.clientY;
    if(!on){on=true;rx=ax=mx;ry=ay=my;root.classList.add('nx-fx')}
    cur.style.transform='translate('+mx+'px,'+my+'px)';
    var el=e.target;
    root.classList.toggle('nx-txt',!!(el.closest&&el.closest('input,textarea,select')));
    ring.classList.toggle('big',!!(el.closest&&el.closest('a,button,summary,label,[role=button]')));
    var c=el.closest&&el.closest('.nx-sp');
    if(c){var b=c.getBoundingClientRect();c.style.setProperty('--mx',(mx-b.left)+'px');c.style.setProperty('--my',(my-b.top)+'px')}
    if(hero){hero.style.setProperty('--px',(mx/innerWidth-.5).toFixed(3));hero.style.setProperty('--py',(my/innerHeight-.5).toFixed(3))}
    if(shot){var s=shot.getBoundingClientRect();if(my>s.top-140&&my<s.bottom+140){shot.style.setProperty('--rx',Math.max(-1,Math.min(1,(mx-s.left-s.width/2)/(s.width/2))).toFixed(3));shot.style.setProperty('--ry',Math.max(-1,Math.min(1,(my-s.top-s.height/2)/(s.height/2))).toFixed(3))}else{shot.style.setProperty('--rx',0);shot.style.setProperty('--ry',0)}}
    document.querySelectorAll('.button').forEach(function(bn){var r=bn.getBoundingClientRect(),dx=mx-(r.left+r.width/2),dy=my-(r.top+r.height/2);if(Math.abs(dx)<r.width/2+36&&Math.abs(dy)<r.height/2+36){bn.style.setProperty('--bx',(dx*.2).toFixed(1)+'px');bn.style.setProperty('--by',(dy*.28).toFixed(1)+'px')}else{bn.style.setProperty('--bx','0px');bn.style.setProperty('--by','0px')}});
  });
  document.addEventListener('mouseleave',function(){root.classList.remove('nx-fx');on=false});
  (function loop(){rx+=(mx-rx)*.18;ry+=(my-ry)*.18;ax+=(mx-ax)*.07;ay+=(my-ay)*.07;ring.style.transform='translate('+rx+'px,'+ry+'px)';aura.style.transform='translate('+ax+'px,'+ay+'px)';requestAnimationFrame(loop)})();
})();
