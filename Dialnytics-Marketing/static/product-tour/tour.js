const $=s=>document.querySelector(s),TOT=9;
const imgs=[...document.querySelectorAll('#zoom img')];
const wrap=$('#wrap'),stage=$('#stage'),lap=$('#lap'),zoomEl=$('#zoom'),spotEl=$('#spot'),cur=$('#cur'),cap=$('#cap'),chap=$('#chap'),inp=$('#inp'),ls=$('#logoscr');
function fit(){stage.style.transform='scale('+wrap.clientWidth/1280+')'}fit();addEventListener('resize',fit);
let paused=false,run=0;
const sleep=ms=>new Promise(r=>{const t=Date.now()+ms;(function w(){Date.now()>=t&&!paused?r():setTimeout(w,40)})()});
// 1 login,2 dash,3 week,4 menu,5 recordings,6 crm,7 power,8 popup,9 billing,10 active call
const show=n=>imgs.forEach((im,i)=>im.classList.toggle('on',i==n-1));
const zoom=(o,s)=>{zoomEl.style.transformOrigin=o;zoomEl.style.transform='scale('+s+')'};
const spot=(x,y,w,h)=>Object.assign(spotEl.style,{left:x+'%',top:y+'%',width:w+'%',height:h+'%',opacity:1});
const off=()=>spotEl.style.opacity=0;
const at=async(x,y,ms=1000)=>{cur.style.left=x+'%';cur.style.top=y+'%';await sleep(ms)};
const cam=(s,ms)=>{lap.style.transitionDuration=ms+'ms';lap.style.transform='scale('+s+')'};
function say(n,ch,html){$('#chap em').textContent=n;$('#chap span').textContent=ch;cap.innerHTML=html;$('#stp').textContent=n+' / '+TOT;$('#pg i').style.width=n/TOT*100+'%'}
const K={1:[88.1,29.2],2:[91.7,29.2],3:[95.2,29.2],4:[88.1,35.5],5:[91.7,35.5],6:[95.2,35.5],7:[88.1,41.8],8:[91.7,41.8],9:[95.2,41.8],0:[91.7,48.1]};
async function play(){
const my=++run,ok=()=>my==run;
off();zoom('50% 50%',1);inp.style.display='none';show(1);cur.style.left='50%';cur.style.top='85%';
cap.style.opacity=0;chap.style.opacity=0;lap.classList.remove('on');
ls.style.transition='none';ls.className='';ls.offsetWidth;ls.style.transition='';
cam(.45,0);$('#pg i').style.width=0;$('#stp').textContent='0 / '+TOT;
await sleep(1500);if(!ok())return;
lap.classList.add('on');ls.classList.add('on');await sleep(900);ls.classList.add('show');await sleep(3400);if(!ok())return;
cam(1,2900);await sleep(3400);if(!ok())return;
ls.classList.add('gone');await sleep(900);cap.style.opacity=1;chap.style.opacity=1;
// 1 sign in
say(1,'Sign in','Open Dialnytics in <b>any browser</b> and sign in');await sleep(900);if(!ok())return;
await at(78,49.7);spot(65.9,23.8,24.2,52.3);await sleep(1300);await at(78,65.7);await sleep(700);off();if(!ok())return;
// 2 dashboard
show(2);say(2,'Your dashboard','Your dashboard shows how the day is going, <b>live</b>');await sleep(600);
zoom('40% 15%',1.3);spot(12.8,12.4,69.2,12.2);await at(60,18,1100);await sleep(1700);if(!ok())return;
zoom('40% 40%',1.2);say(2,'Your dashboard','Calls, outcomes and <b>ways to improve</b>');spot(12.8,25.8,69.2,41.5);await at(40,45,1000);await sleep(2400);off();if(!ok())return;
// 3 dial
say(3,'Dial and call','Dial any number — or <b>click to call</b>');zoom('100% 35%',1.7);spot(84.4,17,14.5,45);await sleep(1400);
inp.style.display='flex';let n='';for(const d of '12522514083'){const[x,y]=K[d];await at(x,y,380);n+=d;inp.textContent='+'+n}
if(!ok())return;off();await at(91.7,55.9,800);inp.style.display='none';
// 4 in-call
show(10);zoom('100% 55%',1.5);say(4,'In-call controls','Mute, hold, record — <b>all in one place</b>');spot(83,39.5,15.7,42);await at(90.5,62,900);await sleep(3000);if(!ok())return;
// 5 insights
off();zoom('50% 50%',1);show(2);say(5,'Insights','Switch to <b>this week</b> or this month in one click');await at(74.8,9.4,1100);show(3);spot(12.8,12.4,69.2,54.6);await sleep(2600);off();if(!ok())return;
// 6 recordings
show(5);say(6,'Recordings','Listen to <b>every recorded call</b>');await sleep(500);spot(12.8,14.2,69.2,8);await at(75,18.2);await sleep(2800);off();if(!ok())return;
// 7 CRM
show(6);say(7,'CRM','Manage <b>leads, consent and follow-ups</b>');await sleep(500);spot(12.8,18,69.2,38);await at(45,40);await sleep(3000);off();if(!ok())return;
// 8 power dialer
show(7);say(8,'Power Dialer','Build a <b>call queue</b> in seconds');await sleep(500);spot(12.8,30.7,69.2,16.6);await at(40.6,39.4);await sleep(1500);off();
show(8);say(8,'Power Dialer','Pick your leads and <b>add them to the queue</b>');spot(31.3,30.8,37.5,38.4);await at(62.2,65.3,1200);await sleep(2300);off();if(!ok())return;
// 9 account
show(4);say(9,'Your account','Profile, billing and preferences — <b>one menu</b>');await at(98.3,2.9,900);spot(81.5,6.5,17.6,53.3);await sleep(2600);off();
show(9);say(9,'Billing','See your <b>plan and renewal date</b> anytime');await sleep(500);spot(12.8,11,34.2,22.5);await at(30,22);await sleep(2600);off();if(!ok())return;
// outro
cap.style.opacity=0;chap.style.opacity=0;ls.className='on';ls.offsetWidth;ls.classList.add('show');await sleep(3200);if(!ok())return;
cam(.45,2800);await sleep(3600);lap.classList.remove('on');
}
$('#pp').onclick=()=>{paused=!paused;$('#pp').textContent=paused?'▶ Play':'⏸ Pause'};
$('#rs').onclick=()=>{paused=false;$('#pp').textContent='⏸ Pause';play()};
play();
