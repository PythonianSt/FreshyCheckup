"""First-year exam station. Patient data is sent only to Supabase."""
import os, json, secrets, hmac, hashlib, uuid, math, random, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from flask import Flask, request, session, render_template, redirect, abort, jsonify

app=Flask(__name__)
app.secret_key=os.getenv('APP_SECRET','')
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',
 SESSION_COOKIE_SECURE=os.getenv('COOKIE_SECURE','true').lower()=='true',
 PERMANENT_SESSION_LIFETIME=timedelta(hours=8),MAX_CONTENT_LENGTH=100000)
BKK=ZoneInfo('Asia/Bangkok')
STATUSES=['ผ่าน','ไม่ผ่าน']
EXAMINER='กำธร'
DONE=['ได้ทำ','ไม่ได้ทำ']
QUESTIONS=[('phq_1','PHQ-2 ข้อ 1: เบื่อ หรือไม่สนใจทำสิ่งต่าง ๆ'),('phq_2','PHQ-2 ข้อ 2: รู้สึกเศร้า หดหู่ หรือสิ้นหวัง'),('gad_1','GAD-2 ข้อ 1: รู้สึกกระวนกระวาย วิตกกังวล หรือเครียด'),('gad_2','GAD-2 ข้อ 2: ไม่สามารถหยุดหรือควบคุมความกังวลได้')]
FREQUENCIES=[('0','ไม่มีเลย'),('1','เป็นบางวัน'),('2','มากกว่าครึ่งหนึ่งของวัน'),('3','เกือบทุกวัน')]
FACULTIES=['คณะเกษตร กำแพงแสน','คณะวิศวกรรมศาสตร์ กำแพงแสน','คณะวิทยาศาสตร์การกีฬาและสุขภาพ','คณะศิลปศาสตร์และวิทยาศาสตร์','คณะศึกษาศาสตร์และพัฒนศาสตร์','คณะอุตสาหกรรมบริการ','คณะสัตวแพทยศาสตร์','อื่น ๆ']
EXAMS=[('hearing','การได้ยิน'),('ear_canal','แก้วหู'),('dental','ฟันและช่องปาก'),('pallor','ภาวะซีด'),('cervical_nodes','ต่อมน้ำเหลืองที่คอ'),('thyroid','ต่อมไทรอยด์'),('heart','หัวใจ'),('lungs','ปอด'),('liver','ตับ'),('spleen','ม้าม')]
CHECKS=[('phq2','PHQ-2'),('gad2','GAD-2'),('color_vision','ตาบอดสี'),('stroop','สมาธิ Stroop'),('memory_immediate','ความจำ 3 คำ'),('serial_sevens','คิดเลข 100−7'),('thai_months','ชื่อเดือนภาษาไทย'),('memory_delayed','ทวนคำ 3 คำ'),('balance','การทรงตัว'),('multitask','Multitask ของสมอง')]+EXAMS
WORDS={'แดง':'#E53935','น้ำเงิน':'#1E88E5','เขียว':'#43A047','เหลือง':'#FDD835','ม่วง':'#8E24AA','ส้ม':'#FB8C00'}
PLATE_ANSWERS=['12','8','6','29','57']

def db(method,params=None,payload=None):
 root=os.getenv('SUPABASE_URL','').strip().rstrip('/')
 key=os.getenv('SUPABASE_SECRET_KEY','').strip() or os.getenv('SUPABASE_SERVICE_ROLE_KEY','').strip()
 if not root.startswith('https://') or not key:raise RuntimeError('Supabase configuration missing')
 headers={'apikey':key,'Content-Type':'application/json','Prefer':'return=representation,resolution=ignore-duplicates'}
 if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
 r=requests.request(method,root+'/rest/v1/student_physical_exam_records',headers=headers,params=params,json=payload,timeout=(5,20))
 r.raise_for_status();return r.json() if r.content else []

def make_items(seed):
 digest=hmac.new(app.secret_key.encode(),('stroop:'+seed).encode(),hashlib.sha256).hexdigest()
 rng=random.Random(int(digest,16));names=list(WORDS);items=[]
 for _ in range(10):
  word=rng.choice(names);ink=rng.choice([c for c in names if c!=word]);items.append({'word':word,'ink':ink,'hex':WORDS[ink]})
 return items

def new_context():
 seed=secrets.token_hex(24)
 signature=hmac.new(app.secret_key.encode(),('attempt:'+seed).encode(),hashlib.sha256).hexdigest()
 return {'record_id':str(uuid.uuid4()),'seed':seed,'signature':signature,'items':[{'word':x['word'],'hex':x['hex']} for x in make_items(seed)]}

def csrf():
 if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
 return session['csrf']
app.jinja_env.globals.update(csrf=csrf)
@app.before_request
def check():
 if request.path=='/health':return
 if len(app.secret_key)<32:abort(503,'ตั้ง APP_SECRET ให้ยาวอย่างน้อย 32 ตัวอักษร')
 if request.path.startswith('/static/'):return
 if request.method=='POST':
  if not hmac.compare_digest(request.form.get('csrf',''),session.get('csrf','!')):abort(400,'กรุณาเปิดหน้าใหม่แล้วส่งอีกครั้ง')
  if request.headers.get('sec-fetch-site')=='cross-site':abort(403)
@app.after_request
def headers(r):
 r.headers.update({'Cache-Control':'no-store, private','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','X-Robots-Tag':'noindex,nofollow','Content-Security-Policy':"default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})
 return r
@app.get('/login')
def login():return redirect('/')
@app.get('/')
def home():return render_template('exam.html',ctx=new_context(),faculties=FACULTIES,exams=EXAMS,statuses=STATUSES,colors=list(WORDS),checks=CHECKS,questions=QUESTIONS,frequencies=FREQUENCIES,examiner=EXAMINER)

def text(f,key,limit=3000):return str(f.get(key,'')).strip()[:limit]
def score_stroop(f):
 seed=text(f,'seed',48);sig=text(f,'signature',64)
 expected=hmac.new(app.secret_key.encode(),('attempt:'+seed).encode(),hashlib.sha256).hexdigest()
 if len(seed)!=48 or not hmac.compare_digest(sig,expected):raise ValueError('ชุด Stroop ไม่ถูกต้อง กรุณาเปิดหน้าใหม่')
 try:responses=json.loads(f.get('stroop_responses','[]'))
 except (ValueError,TypeError):raise ValueError('คำตอบ Stroop ไม่ถูกต้อง') from None
 stroop={'status':'ไม่ได้ประเมิน','n_items':10,'protocol':'incongruent_10_sequential_v1'}
 if not isinstance(responses,list):raise ValueError('คำตอบ Stroop ไม่ถูกต้อง')
 if responses:
  if len(responses)!=10:raise ValueError('Stroop ต้องตอบครบ 10 ข้อ หรือกดล้างเพื่อไม่ได้ประเมิน')
  scored=[]
  for i,(answer,item) in enumerate(zip(responses,make_items(seed))):
   if not isinstance(answer,dict) or answer.get('answer') not in WORDS:raise ValueError('สีคำตอบ Stroop ไม่ถูกต้อง')
   elapsed=answer.get('elapsed_ms')
   if isinstance(elapsed,bool) or not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or elapsed<=0 or elapsed>3600000:raise ValueError('เวลา Stroop ไม่ถูกต้อง')
   scored.append({'no':i+1,'word':item['word'],'ink':item['ink'],'answer':answer['answer'],'correct':answer['answer']==item['ink'],'elapsed_ms':round(elapsed,2)})
  correct=sum(r['correct'] for r in scored);duration=sum(r['elapsed_ms'] for r in scored)/1000
  stroop.update(status='ทำครบแล้ว',correct=correct,errors=10-correct,accuracy_percent=correct*10,duration_sec=round(duration,3),correct_per_min=round(correct*60/duration,2),trials=scored)
 return stroop

def parse_record(f):
 student=text(f,'student_id',30)
 if not student.isascii() or not student.isdigit() or len(student)>20:raise ValueError('กรุณากรอกรหัสนักศึกษาเป็นตัวเลข')
 faculty=text(f,'faculty',200)
 if faculty not in FACULTIES:raise ValueError('กรุณาเลือกคณะ')
 if faculty=='อื่น ๆ':
  faculty=text(f,'faculty_other',200)
  if not faculty:raise ValueError('กรุณาระบุชื่อคณะ')
 try:rid=str(uuid.UUID(text(f,'record_id',36)))
 except ValueError:raise ValueError('รหัสรายการไม่ถูกต้อง กรุณาเปิดหน้าใหม่') from None
 exams={}
 for key,label in CHECKS:
  done=f.get(key+'_done','')
  if done not in DONE:raise ValueError('กรุณาระบุได้ทำ / ไม่ได้ทำ: '+label)
  exams[key]={'done':done=='ได้ทำ'}
 screening={}
 for prefix in ('phq','gad'):
  values=[f.get(prefix+'_'+str(i),'') for i in (1,2)]
  performed=exams[prefix+'2']['done']
  if performed and any(x not in ('0','1','2','3') for x in values):raise ValueError('กรุณาตอบ '+prefix.upper()+'-2 ทั้งสองข้อ')
  if not performed and any(values):raise ValueError('มีคำตอบ '+prefix.upper()+'-2 กรุณาเลือกได้ทำ หรือเลือกยังไม่ได้ตอบทั้งสองข้อ')
  screening[prefix+'2']={'done':performed,'answers':[int(x) for x in values] if performed else [],'score':sum(int(x) for x in values) if performed else None,'timeframe_days':14}
 stroop=score_stroop(f)
 if exams['stroop']['done'] != (stroop['status']=='ทำครบแล้ว'):raise ValueError('สถานะได้ทำของ Stroop ต้องตรงกับการทำครบ 10 ข้อ')
 final=text(f,'final_status',20)
 if final not in STATUSES:raise ValueError('กรุณาเลือกผลรวมผ่าน / ไม่ผ่าน')
 if f.get('confirm')!='yes':raise ValueError('โปรดยืนยันข้อมูลก่อนบันทึก')
 exams['screening']=screening
 exams['summary']={'status':final,'note':text(f,'general_note')}
 exams['memory_word_set']=['มะนาว','กุญแจ','ลูกบอล']
 return {'record_id':rid,'student_id':student,'faculty':faculty,'created_at_bkk':datetime.now(BKK).isoformat(),'examiner':EXAMINER,'color_vision':{'done':exams['color_vision']['done'],'plate_set':'legacy_generated_5'},'stroop':stroop,'examinations':exams,'general_note':text(f,'general_note'),'schema_version':2}

@app.post('/stroop/score')
def stroop_score():
 try:result=score_stroop(request.form)
 except ValueError as e:return jsonify(ok=False,error=str(e)),400
 return jsonify(ok=True,result=result)
@app.post('/save')
def save():
 try:record=parse_record(request.form)
 except ValueError as e:return jsonify(ok=False,error=str(e)),400
 try:db('POST',params={'on_conflict':'record_id'},payload=record)
 except Exception:return jsonify(ok=False,error='บันทึกไม่สำเร็จ โปรดลองอีกครั้ง ตรวจ Supabase Variables และ setup.sql หากยังพบปัญหา'),503
 return jsonify(ok=True,record_id=record['record_id'])
@app.get('/records')
def records():abort(404)
@app.get('/health')
def health():return {'status':'ok'}
@app.errorhandler(Exception)
def error(e):
 from werkzeug.exceptions import HTTPException
 if isinstance(e,HTTPException):return render_template('error.html',message=e.description),e.code
 return render_template('error.html',message='โปรดลองอีกครั้ง หากยังพบปัญหาโปรดตรวจการตั้งค่า'),503
