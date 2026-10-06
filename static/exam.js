(() => {
 'use strict';
 const $=id=>document.getElementById(id), items=JSON.parse($('stroop-items').textContent);
 let answers=[],index=0,started=0,running=false,locked=false,submitting=false,saved=false,pendingTimer=null;
 function show(){ $('stroop-progress').textContent=`ข้อ ${index+1}/10`; $('stroop-word').textContent=items[index].word;$('stroop-word').style.color=items[index].hex;$('stroop-box').hidden=false;locked=false;started=performance.now(); }
 $('faculty').addEventListener('change',()=>{const other=$('faculty').value==='อื่น ๆ';$('other-faculty').hidden=!other;$('faculty-other').required=other;});
 $('start-stroop').onclick=()=>{
  if(!$('student-id').value.trim()||!$('faculty').value){$('stroop-progress').textContent='กรอกรหัสนักศึกษาและคณะก่อนเริ่ม';return;}
  if(answers.length&&!confirm('เริ่มใหม่และล้างคำตอบ Stroop เดิม?'))return;
  clearTimeout(pendingTimer);document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);answers=[];index=0;running=true;$('stroop-responses').value='[]';$('stroop-result').textContent='';$('start-stroop').disabled=true;show();
 };
 document.querySelectorAll('[data-color]').forEach(button=>button.onclick=()=>{
  if(!running||locked)return;locked=true;
  answers.push({answer:button.dataset.color,elapsed_ms:Math.max(.01,performance.now()-started)});
  $('stroop-responses').value=JSON.stringify(answers);index++;
  if(index===10){running=false;$('stroop-box').hidden=true;$('stroop-progress').textContent='ทำครบ 10 ข้อแล้ว';$('stroop-result').textContent='บันทึกผลพร้อมรายการตรวจอื่นได้ โดยระบบคำนวณคะแนนเมื่อส่งข้อมูล';$('start-stroop').disabled=false;}
  else {document.querySelectorAll('[data-color]').forEach(b=>b.disabled=true);pendingTimer=setTimeout(()=>{if(!running||index>=10)return;document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);show();},200);}
 });
 $('reset-stroop').onclick=()=>{
  if((running||answers.length)&&!confirm('ล้างผล Stroop และบันทึกเป็นไม่ได้ประเมิน?'))return;
  clearTimeout(pendingTimer);document.querySelectorAll('[data-color]').forEach(b=>b.disabled=false);running=false;answers=[];index=0;locked=false;$('stroop-responses').value='[]';$('stroop-box').hidden=true;$('stroop-progress').textContent='ยังไม่ได้ประเมิน';$('stroop-result').textContent='';$('start-stroop').disabled=false;
 };
 $('exam-form').addEventListener('submit',async event=>{
  event.preventDefault();if(saved||submitting)return;
  if(running){$('save-status').textContent='Stroop ยังไม่ครบ 10 ข้อ กรุณาทำให้ครบหรือกดล้างผล';return;}
  submitting=true;$('save-button').disabled=true;$('save-status').textContent='กำลังบันทึก…';
  try{
   const response=await fetch('/save',{method:'POST',body:new FormData($('exam-form')),credentials:'same-origin'});
   if(response.redirected)throw Error('หมดเวลาเข้าสู่ระบบ กรุณาเข้าสู่ระบบอีกครั้งในแท็บใหม่');
   const data=await response.json();
   if(!response.ok||!data.ok)throw Error(data.error||'บันทึกไม่สำเร็จ');
   saved=true;$('save-status').textContent='บันทึกผลตรวจสำเร็จ · รหัสรายการ '+data.record_id;$('next-student').hidden=false;
   $('exam-form').querySelectorAll('input,select,textarea,button').forEach(e=>e.disabled=true);
  }catch(error){$('save-status').textContent=error.message+' · ข้อมูลในหน้านี้ยังอยู่ โปรดลองบันทึกใหม่';$('save-button').disabled=false;}
  finally{submitting=false;}
 });
 window.addEventListener('beforeunload',event=>{if(!saved&&($('student-id').value||answers.length)){event.preventDefault();event.returnValue='';}});
})();
