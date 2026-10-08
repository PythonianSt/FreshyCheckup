(() => {
 'use strict';
 const $=id=>document.getElementById(id), items=JSON.parse($('stroop-items').textContent);
 let answers=[],index=0,started=0,running=false,locked=false,submitting=false,saved=false,pendingTimer=null,attemptVersion=0,scoring=false;
 function show(){ $('stroop-progress').textContent=`ข้อ ${index+1}/10`; $('stroop-word').textContent=items[index].word;$('stroop-word').style.color=items[index].hex;$('stroop-box').hidden=false;locked=false;started=performance.now(); }
 function setDone(key,value){const radio=document.querySelector(`input[name="${key}_done"][value="${value}"]`);if(radio)radio.checked=true;}
 async function calculateScore(){
  const version=attemptVersion;scoring=true;$('retry-score').hidden=true;$('stroop-result').textContent='กำลังคำนวณเวลาและคะแนน…';
  try{
   const response=await fetch('/stroop/score',{method:'POST',body:new FormData($('exam-form')),credentials:'same-origin'});
   const data=await response.json();if(!response.ok||!data.ok)throw Error(data.error||'คำนวณไม่สำเร็จ');
   if(version!==attemptVersion)return;
   const r=data.result;$('stroop-result').textContent=`เวลา ${r.duration_sec.toFixed(3)} วินาที · ถูก ${r.correct}/10 · ผิด ${r.errors} · ความถูกต้อง ${r.accuracy_percent}%`;
  }catch(error){if(version===attemptVersion){$('stroop-result').textContent=error.message;$('retry-score').hidden=false;}}
  finally{if(version===attemptVersion)scoring=false;}
 }
 $('retry-score').onclick=calculateScore;
 $('hide-words').onclick=()=>{$('memory-words').hidden=true;};
 document.querySelectorAll('input[name="memory_immediate_done"],input[name="memory_delayed_done"]').forEach(el=>el.addEventListener('change',()=>{$('memory-words').hidden=true;}));
 function screeningSummary(){
  const totals=['phq','gad'].map(prefix=>{const a=[1,2].map(i=>document.querySelector(`[name="${prefix}_${i}"]`).value);return `${prefix.toUpperCase()}-2: ${a.every(x=>x!=='')?a.reduce((sum,x)=>sum+Number(x),0)+'/6':'ยังตอบไม่ครบ'}`;});
  $('screening-summary').textContent=totals.join(' · ');
 }
 document.querySelectorAll('.screening-answer').forEach(el=>el.addEventListener('change',()=>{
  for(const prefix of ['phq','gad']){const values=[1,2].map(i=>document.querySelector(`[name="${prefix}_${i}"]`).value);if(values.every(x=>x!==''))setDone(prefix+'2','ได้ทำ');}
  screeningSummary();
 }));
 $('next-student').onclick=()=>{if(submitting)return;if(!saved&&$('student-id').value&&!confirm('ข้อมูลยังไม่ได้บันทึก เริ่มตรวจคนต่อไปและล้างข้อมูลหน้านี้?'))return;saved=true;window.location.assign('/');};
 $('faculty').addEventListener('change',()=>{const other=$('faculty').value==='อื่น ๆ';$('other-faculty').hidden=!other;$('faculty-other').required=other;});
 $('start-stroop').onclick=()=>{
  if(!$('student-id').value.trim()||!$('faculty').value){$('stroop-progress').textContent='กรอกรหัสนักศึกษาและคณะก่อนเริ่ม';return;}
  if(answers.length&&!confirm('เริ่มใหม่และล้างคำตอบ Stroop เดิม?'))return;
  attemptVersion++;clearTimeout(pendingTimer);document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);setDone('stroop','ไม่ได้ทำ');answers=[];index=0;running=true;$('stroop-responses').value='[]';$('stroop-result').textContent='';$('start-stroop').disabled=true;show();
 };
 document.querySelectorAll('[data-color]').forEach(button=>button.onclick=()=>{
  if(!running||locked)return;locked=true;
  answers.push({answer:button.dataset.color,elapsed_ms:Math.max(.01,performance.now()-started)});
  $('stroop-responses').value=JSON.stringify(answers);index++;
  if(index===10){running=false;$('stroop-box').hidden=true;$('stroop-progress').textContent='ทำครบ 10 ข้อแล้ว';setDone('stroop','ได้ทำ');calculateScore();$('start-stroop').disabled=false;}
  else {document.querySelectorAll('[data-color]').forEach(b=>b.disabled=true);pendingTimer=setTimeout(()=>{if(!running||index>=10)return;document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);show();},200);}
 });
 $('reset-stroop').onclick=()=>{
  if((running||answers.length)&&!confirm('ล้างผล Stroop และระบุไม่ได้ทำ?'))return;
  attemptVersion++;$('retry-score').hidden=true;clearTimeout(pendingTimer);document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);setDone('stroop','ไม่ได้ทำ');running=false;answers=[];index=0;locked=false;$('stroop-responses').value='[]';$('stroop-box').hidden=true;$('stroop-progress').textContent='ยังไม่ได้ประเมิน';$('stroop-result').textContent='';$('start-stroop').disabled=false;
 };
 $('exam-form').addEventListener('submit',async event=>{
  event.preventDefault();if(saved||submitting)return;
  if(running){$('save-status').textContent='Stroop ยังไม่ครบ 10 ข้อ กรุณาทำให้ครบหรือกดล้างผล';return;}
  submitting=true;$('next-student').disabled=true;$('save-button').disabled=true;$('save-status').textContent='กำลังบันทึก…';
  try{
   const response=await fetch('/save',{method:'POST',body:new FormData($('exam-form')),credentials:'same-origin'});
   
   const data=await response.json();
   if(!response.ok||!data.ok)throw Error(data.error||'บันทึกไม่สำเร็จ');
   saved=true;$('next-student').disabled=false;$('save-status').textContent='บันทึกผลตรวจสำเร็จ · รหัสรายการ '+data.record_id;
   $('exam-form').querySelectorAll('input,select,textarea,button').forEach(e=>e.disabled=true);
  }catch(error){$('save-status').textContent=error.message+' · ข้อมูลในหน้านี้ยังอยู่ โปรดลองบันทึกใหม่';$('save-button').disabled=false;}
  finally{submitting=false;$('next-student').disabled=false;}
 });
 window.addEventListener('beforeunload',event=>{if(!saved&&($('student-id').value||answers.length)){event.preventDefault();event.returnValue='';}});
})();
