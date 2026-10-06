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
STATUSES=['ผ่าน','ไม่ผ่าน','ไม่ได้ประเมิน']
FACULTIES=['คณะเกษตร กำแพงแสน','คณะวิศวกรรมศาสตร์ กำแพงแสน','คณะวิทยาศาสตร์การกีฬาและสุขภาพ','คณะศิลปศาสตร์และวิทยาศาสตร์','คณะศึกษาศาสตร์และพัฒนศาสตร์','คณะอุตสาหกรรมบริการ','คณะสัตวแพทยศาสตร์','อื่น ๆ']
EXAMS=[('hearing','การได้ยิน'),('ear_canal','ช่องหู/แก้วหู'),('dental','ฟันและช่องปาก'),('pallor','ภาวะซีด'),('cervical_nodes','ต่อมน้ำเหลืองที่คอ'),('thyroid','ต่อมไทรอยด์'),('heart','หัวใจ'),('lungs','ปอด'),('liver','ตับ'),('spleen','ม้าม')]
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
 if request.path not in ('/login',) and not session.get('staff'):return redirect('/login')
 if request.method=='POST':
  if not hmac.compare_digest(request.form.get('csrf',''),session.get('csrf','!')):abort(400,'กรุณาเปิดหน้าใหม่แล้วส่งอีกครั้ง')
  if request.headers.get('sec-fetch-site')=='cross-site':abort(403)
@app.after_request
def headers(r):
 r.headers.update({'Cache-Control':'no-store, private','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','X-Robots-Tag':'noindex,nofollow','Content-Security-Policy':"default-src 'self'; img-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"})
 return r
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  password=os.getenv('PASS_EXAM','')
  if not password or not hmac.compare_digest(password,request.form.get('password','')):return render_template('login.html',error='รหัสผ่านไม่ถูกต้อง'),401
  actor=request.form.get('actor','').strip()[:100]
  if not actor:return render_template('login.html',error='กรุณาระบุชื่อเจ้าหน้าที่'),400
  session.clear();session.permanent=True;session['staff']=actor;csrf();return redirect('/')
 return render_template('login.html')
@app.post('/logout')
def logout():session.clear();return redirect('/login')
@app.get('/')
def home():return render_template('exam.html',ctx=new_context(),faculties=FACULTIES,exams=EXAMS,statuses=STATUSES,colors=list(WORDS))

def text(f,key,limit=3000):return str(f.get(key,'')).strip()[:limit]
def parse_record(f):
 student=text(f,'student_id',30)
 if not student or not student.isdigit() or len(student)>20:raise ValueError('กรุณากรอกรหัสนักศึกษาเป็นตัวเลข')
 faculty=text(f,'faculty',200)
 if faculty not in FACULTIES:raise ValueError('กรุณาเลือกคณะ')
 if faculty=='อื่น ๆ':
  faculty=text(f,'faculty_other',200)
  if not faculty:raise ValueError('กรุณาระบุชื่อคณะ')
 try:rid=str(uuid.UUID(text(f,'record_id',36)))
 except ValueError:raise ValueError('รหัสรายการไม่ถูกต้อง กรุณาเปิดหน้าใหม่') from None
 exams={}
 for key,label in EXAMS:
  status=text(f,key+'_status',20)
  if status not in STATUSES:raise ValueError('กรุณาเลือกผลตรวจ '+label)
  exams[key]={'status':status,'note':text(f,key+'_note')}
 color_status=text(f,'color_status',20)
 if color_status not in STATUSES:raise ValueError('กรุณาเลือกผลตาบอดสี')
 answers=[text(f,'plate_'+str(i+1),50) for i in range(5)]
 if color_status!='ไม่ได้ประเมิน' and any(not a for a in answers):raise ValueError('กรุณากรอกคำตอบภาพสีทั้ง 5 แผ่น รวมคำว่า ไม่เห็น ได้')
 color={'status':color_status,'note':text(f,'color_note'),'answers':answers,
  'correct':sum(a==b for a,b in zip(answers,PLATE_ANSWERS)) if color_status!='ไม่ได้ประเมิน' else None,
  'total':5,'plate_set':'legacy_generated_5','interpretation':'บันทึกคะแนนและผลที่เจ้าหน้าที่ระบุ ไม่ใช้เกณฑ์วินิจฉัยอัตโนมัติ'}
 seed=text(f,'seed',48);sig=text(f,'signature',64)
 expected=hmac.new(app.secret_key.encode(),('attempt:'+seed).encode(),hashlib.sha256).hexdigest()
 if len(seed)!=48 or not hmac.compare_digest(sig,expected):raise ValueError('ชุด Stroop ไม่ถูกต้อง กรุณาเปิดหน้าใหม่')
 try:responses=json.loads(f.get('stroop_responses','[]'))
 except (ValueError,TypeError):raise ValueError('คำตอบ Stroop ไม่ถูกต้อง') from None
 stroop={'status':'ไม่ได้ประเมิน','n_items':10,'note':text(f,'stroop_note'),'protocol':'incongruent_10_sequential_v1'}
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
 if f.get('confirm')!='yes':raise ValueError('โปรดยืนยันข้อมูลก่อนบันทึก')
 return {'record_id':rid,'student_id':student,'faculty':faculty,'created_at_bkk':datetime.now(BKK).isoformat(),'examiner':session['staff'],'color_vision':color,'stroop':stroop,'examinations':exams,'general_note':text(f,'general_note'),'schema_version':1}
@app.post('/save')
def save():
 try:record=parse_record(request.form)
 except ValueError as e:return jsonify(ok=False,error=str(e)),400
 try:db('POST',params={'on_conflict':'record_id'},payload=record)
 except Exception:return jsonify(ok=False,error='บันทึกไม่สำเร็จ โปรดลองอีกครั้ง ตรวจ Supabase Variables และ setup.sql หากยังพบปัญหา'),503
 return jsonify(ok=True,record_id=record['record_id'])
@app.get('/records')
def records():
 student=request.args.get('student_id','').strip()
 if student and (not student.isdigit() or len(student)>20):abort(400,'รหัสนักศึกษาไม่ถูกต้อง')
 params={'select':'record_id,student_id,faculty,created_at_bkk,examiner,color_vision,stroop,examinations,general_note','order':'created_at_bkk.desc','limit':100}
 if student:params['student_id']='eq.'+student
 try:rows=db('GET',params=params)
 except Exception:abort(503,'อ่านข้อมูลไม่สำเร็จ โปรดตรวจ Supabase และ setup.sql')
 return render_template('records.html',rows=rows or [],student=student,exams=EXAMS)
@app.get('/health')
def health():return {'status':'ok'}
@app.errorhandler(Exception)
def error(e):
 from werkzeug.exceptions import HTTPException
 if isinstance(e,HTTPException):return render_template('error.html',message=e.description),e.code
 return render_template('error.html',message='โปรดลองอีกครั้ง หากยังพบปัญหาโปรดตรวจการตั้งค่า'),503
