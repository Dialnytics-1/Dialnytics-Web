import assert from 'node:assert/strict';
import { getQuote } from '../static/js/shared.js';
const catalog={plans:{'usa-canada':{},uk:{price:29},australia:{price:44},japan:{price:64},global:{price:179},'uk-to-europe':{},europe:{},custom:{}},europe_totals:{1:'44',2:'79',3:'110.60',4:'137.40',5:'159.85',6:'178.52'}};
let cases=0;
for (const [plan,users,expected] of [['usa-canada',1,22],['usa-canada',2,38],['usa-canada',3,45],['usa-canada',10,150],['uk',3,87],['australia',2,88],['japan',2,128],['global',2,358],['custom',5,null],['europe',5,null]]){assert.equal(getQuote(catalog,plan,users).total,expected);cases++;}
for (const [count,value] of Object.entries(catalog.europe_totals)){assert.equal(getQuote(catalog,'uk-to-europe',2,Number(count)).total,Math.round(Number(value)*100)*2/100);cases++;}
for(const n of [0,-1,101,true,2.5]){assert.throws(()=>getQuote(catalog,'uk',n));cases++;}
console.log(`${cases} JavaScript pricing assertions passed.`);
