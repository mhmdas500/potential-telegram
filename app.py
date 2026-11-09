import os, sqlite3, uuid, secrets
from functools import wraps
from flask import (Flask, request, session, redirect, url_for,
                   render_template, send_file, abort, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from jinja2 import DictLoader

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'data.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'private_uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024

DOC_TYPES = [
    ('personal_photo', 'عکس شخصی'), ('full_body', 'عکس تمام‌قد ایستاده'),
    ('face', 'عکس چهره روبه‌رو'), ('id_front', 'تذکره – جلو'),
    ('id_back', 'تذکره – پشت'), ('id_with_person', 'شخص با تذکره در دست'),
]
SKILL_FA = {'beginner':'🟢 تازه‌کار', 'semi':'🔵 نیمه‌حرفه‌ای', 'pro':'🟣 حرفه‌ای'}

BASE_HTML = """
<!DOCTYPE html><html lang="fa" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>جوانه دیجیتال</title><style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800&display=swap');
:root{ --emerald:#10b981; --emerald-d:#059669; --black:#0a0a0a; --dark:#0f1419; --dark-2:#161c22; --border:#242b33; --white:#fff; --muted:#8b95a1; --danger:#ef4444; }
body{ font-family:'Vazirmatn',Tahoma,sans-serif; direction:rtl; background:radial-gradient(1200px 600px at 90% -10%, rgba(16,185,129,.12), transparent 60%), var(--dark); color:var(--white); min-height:100vh; margin:0; line-height:1.7; }
a{color:var(--emerald);text-decoration:none} h1,h2,h3{font-weight:800} .muted{color:var(--muted)}
.nav{display:flex;justify-content:space-between;align-items:center; padding:14px 24px;border-bottom:1px solid var(--border); background:rgba(10,10,10,.7); position:sticky;top:0;z-index:50}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:#fff}
.brand .dot{width:10px;height:10px;border-radius:50%;background:var(--emerald); box-shadow:0 0 12px var(--emerald)}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 16px;border-radius:8px; border:1px solid var(--border);background:var(--dark-2);color:#fff;font:inherit; font-weight:600;cursor:pointer;}
.btn-primary{background:linear-gradient(135deg,var(--emerald),var(--emerald-d)); border:none;color:#04140d}
.btn-danger{background:rgba(239,68,68,.15);border-color:rgba(239,68,68,.4);color:#fca5a5}
.btn-sm{padding:6px 12px;font-size:13px}
.card{background:linear-gradient(180deg,var(--dark-2),rgba(15,20,25,.7)); border:1px solid var(--border);border-radius:14px;padding:24px;}
.container{max-width:1100px;margin:28px auto;padding:0 20px} .auth-wrap{max-width:520px;margin:40px auto;padding:0 20px}
.field{margin-bottom:14px} .field label{display:block;margin-bottom:6px;font-size:14px;color:#cfd8e3}
.field input,.field textarea{ width:100%;padding:10px 12px;border-radius:8px;border:1px solid var(--border); background:var(--black);color:#fff;font:inherit}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.levels{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:8px}
.level{position:relative;border:1px solid var(--border);border-radius:10px;padding:12px; text-align:center;cursor:pointer;background:var(--black);}
.level input{position:absolute;opacity:0} .level:has(input:checked){border-color:var(--emerald);background:rgba(16,185,129,.1);}
.uploads{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
.up-item{border:1px dashed var(--border);border-radius:10px;padding:12px;text-align:center; cursor:pointer;background:var(--black);display:block}
.up-item .title{font-size:13px;font-weight:600;} .up-item input{display:none}
.badge{padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600;border:1px solid var(--border)}
.b-pending{background:rgba(245,158,11,.12);color:#fcd34d} .b-approved{background:rgba(16,185,129,.12);color:#6ee7b7} .b-rejected{background:rgba(239,68,68,.12);color:#fca5a5}
table{width:100%;border-collapse:collapse;font-size:14px} th,td{padding:10px 8px;text-align:right;border-bottom:1px solid var(--border)}
.flash{padding:10px 14px;border-radius:8px;margin-bottom:8px;} .flash-error{background:rgba(239,68,68,.12);color:#fca5a5} .flash-success{background:rgba(16,185,129,.12);color:#6ee7b7}
.uploads-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;}
.upload-card{background:var(--black);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center}
.upload-card img{width:100%;height:150px;object-fit:cover;border-radius:8px;margin:8px 0}
</style></head><body>
<nav class="nav"><a href="/" class="brand"><span class="dot"></span> جوانه دیجیتال</a>
<div>{% if session.get('user_id') %}<a href="/logout" class="btn btn-sm">خروج</a>{% else %}<a href="/login" class="btn btn-sm">ورود</a>{% endif %}</div></nav>
<div class="container">{% with msgs = get_flashed_messages(with_categories=true) %}{% for cat, msg in msgs %}<div class="flash flash-{{ cat }}">{{ msg }}</div>{% endfor %}{% endwith %}</div>
{% block body %}{% endblock %}</body></html>
"""

REGISTER_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="container"><form method="post" enctype="multipart/form-data" class="card">
<h1>ثبت‌نام برنامه‌نویس</h1>
<div style="text-align: center; margin-bottom: 25px;">
    <span class="badge b-approved" style="font-size: 16px; padding: 10px 20px;">
        👥 {{ total_members }} برنامه‌نویس حرفه‌ای به تیم جوانه دیجیتال پیوسته‌اند
    </span>
</div>
<div class="grid-2">
<div class="field"><label>نام و نام خانوادگی *</label><input name="full_name" required></div>
<div class="field"><label>ایمیل *</label><input name="email" type="email" required></div>
<div class="field"><label>شماره تماس *</label><input name="phone" required></div>
<div class="field"><label>کشور</label><input name="country"></div></div>
<div class="field"><label>مهارت‌ها</label><input name="skills"></div>
<div class="field"><label>سطح مهارت *</label><div class="levels">
<label class="level"><input type="radio" name="skill_level" value="beginner">🟢 تازه‌کار</label>
<label class="level"><input type="radio" name="skill_level" value="semi">🔵 نیمه‌حرفه‌ای</label>
<label class="level"><input type="radio" name="skill_level" value="pro">🟣 حرفه‌ای</label>
</div></div><div class="field"><label>رمز عبور *</label><input name="password" type="password" minlength="8" required></div>
<h2>بارگذاری مدارک</h2><div class="uploads">
{% for key, label in docs %}<label class="up-item"><div class="title">{{ label }}</div><input type="file" name="{{ key }}" accept="image/*"></label>{% endfor %}
</div><button class="btn btn-primary" style="width:100%;margin-top:20px">ثبت‌نام</button></form></div>
{% endblock %}
"""

LOGIN_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="auth-wrap"><form method="post" class="card"><h1>ورود به جوانه دیجیتال</h1>
<div class="field"><label>ایمیل</label><input name="email" type="email" required></div>
<div class="field"><label>رمز عبور</label><input name="password" type="password" required></div>
<button class="btn btn-primary" style="width:100%">ورود</button>
</form></div>
{% endblock %}
"""

SUCCESS_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="auth-wrap"><div class="card" style="text-align:center; padding: 40px 20px;">
<div style="font-size: 60px; margin-bottom: 10px;">🛡️</div><h1>ثبت‌نام انجام شد</h1>
<p class="muted" style="line-height: 1.8;">{{ name }} عزیز، اطلاعات شما با موفقیت ثبت شد.<br>درخواست شما هم‌اکنون <strong>در حال بررسی سیستم ایمنی</strong> قرار دارد.</p>
<a href="/login" class="btn btn-primary" style="margin-top: 15px; padding: 10px 30px;">ورود به پنل</a>
</div></div>
{% endblock %}
"""

PENDING_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="auth-wrap"><div class="card" style="text-align:center; padding: 40px 20px;">
<h1>پنل کاربری جوانه دیجیتال</h1><p class="muted">خوش آمدید، {{ user.full_name }}</p><hr style="border-color: #242b33; margin: 20px 0;">
{% if user.status == 'pending' %}
    <div style="font-size: 60px; margin-bottom: 10px;">🛡️</div><h2 style="color: #fcd34d;">در حال بررسی سیستم ایمنی</h2>
    <p class="muted">درخواست شما در صف بررسی قرار دارد. لطفاً شکیبا باشید.</p>
{% elif user.status == 'approved' %}
    <div style="font-size: 60px; margin-bottom: 10px;">🎉</div><h2 style="color: #6ee7b7;">تبریک! درخواست شما تایید شد</h2>
    {% if user.approval_message %}<div class="flash flash-success" style="margin-top: 10px; font-weight: bold; font-size: 15px; text-align: right;">پیام مدیر: {{ user.approval_message }}</div>{% endif %}
    <p class="muted" style="margin-top: 15px;">حساب شما فعال است. به زودی پروژه‌ها برای شما ارسال می‌شود.</p>
{% elif user.status == 'rejected' %}
    <div style="font-size: 60px; margin-bottom: 10px;">❌</div><h2 style="color: #fca5a5;">درخواست شما رد شد</h2>
    <div class="flash flash-error" style="margin-top: 10px; font-weight: bold; font-size: 15px; text-align: right;">دلیل رد شدن: {{ user.rejection_reason or 'مدارک ناقص است' }}</div>
    <div class="card" style="margin-top: 20px; background: #0a0a0a; border-color: #242b33;"><h3 style="margin-top:0;">ارسال مجدد مدرک</h3>
        <form method="post" action="/user/reupload" enctype="multipart/form-data">
            <select name="doc_type" required style="width: 100%; padding: 10px; margin-bottom: 10px; background: #161c22; color: #fff; border: 1px solid #242b33; border-radius: 8px;">
                <option value="">کدام مدرک را می‌خواهید اصلاح کنید؟</option>{% for key, label in docs %}<option value="{{ key }}">{{ label }}</option>{% endfor %}
            </select><input type="file" name="file" accept="image/*" required style="width: 100%; margin-bottom: 15px; color: #fff;">
            <button class="btn btn-primary" style="width: 100%;">آپلود و ارسال مجدد</button>
        </form>
    </div>
{% elif user.status == 'blocked' %}
    <div style="font-size: 60px; margin-bottom: 10px;">🚫</div><h2 style="color: #fca5a5;">حساب شما مسدود است</h2>
{% endif %}
</div></div>
{% endblock %}
"""

ADMIN_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="container"><h1>پنل مدیریت جوانه دیجیتال</h1>
<h2>⏳ در انتظار تأیید ({{ pending|length }})</h2>
<div class="card" style="margin-bottom: 25px; border-right: 4px solid #fcd34d;"><table>
<thead><tr><th>نام</th><th>ایمیل</th><th>عکس‌ها</th><th>عملیات</th></tr></thead><tbody>
{% for u in pending %}<tr><td>{{ u.full_name }}</td><td>{{ u.email }}</td><td>{{ u.doc_count }}/6</td><td><a href="/admin/review/{{ u.id }}" class="btn btn-primary btn-sm">بررسی درخواست</a></td></tr>{% endfor %}
{% if not pending %}<tr><td colspan="4" class="muted">موردی وجود ندارد.</td></tr>{% endif %}</tbody></table></div>

<h2>✅ تایید شده‌ها ({{ approved|length }})</h2>
<div class="card" style="margin-bottom: 25px; border-right: 4px solid #6ee7b7;"><table>
<thead><tr><th>نام</th><th>ایمیل</th><th>سطح</th><th>عملیات</th></tr></thead><tbody>
{% for u in approved %}<tr><td>{{ u.full_name }}</td><td>{{ u.email }}</td><td>{{ levels[u.skill_level] }}</td><td><a href="/admin/review/{{ u.id }}" class="btn btn-sm">مشاهده مدارک</a></td></tr>{% endfor %}
{% if not approved %}<tr><td colspan="4" class="muted">موردی وجود ندارد.</td></tr>{% endif %}</tbody></table></div>

<h2>❌ رد شده‌ها ({{ rejected|length }})</h2>
<div class="card" style="margin-bottom: 25px; border-right: 4px solid #fca5a5;"><table>
<thead><tr><th>نام</th><th>ایمیل</th><th>دلیل رد</th><th>عملیات</th></tr></thead><tbody>
{% for u in rejected %}<tr><td>{{ u.full_name }}</td><td>{{ u.email }}</td><td style="color: #fca5a5; font-size: 13px;">{{ u.rejection_reason or 'نامشخص' }}</td><td><a href="/admin/review/{{ u.id }}" class="btn btn-sm">مشاهده و بررسی</a></td></tr>{% endfor %}
{% if not rejected %}<tr><td colspan="4" class="muted">موردی وجود ندارد.</td></tr>{% endif %}</tbody></table></div>

<h2>🚫 مسدود شده‌ها ({{ blocked|length }})</h2>
<div class="card" style="border-right: 4px solid #8b95a1;"><table>
<thead><tr><th>نام</th><th>ایمیل</th><th>عملیات</th></tr></thead><tbody>
{% for u in blocked %}<tr><td>{{ u.full_name }}</td><td>{{ u.email }}</td><td><a href="/admin/review/{{ u.id }}" class="btn btn-sm">بررسی</a></td></tr>{% endfor %}
{% if not blocked %}<tr><td colspan="3" class="muted">موردی وجود ندارد.</td></tr>{% endif %}</tbody></table></div>
</div>
{% endblock %}
"""

REVIEW_HTML = """
{% extends 'base.html' %}{% block body %}
<div class="container"><a href="/admin" class="btn btn-sm">← بازگشت به پنل</a><h1>بررسی درخواست: {{ user.full_name }}</h1>
<div class="card" style="margin-bottom:20px"><p>ایمیل: {{ user.email }} | تلفن: {{ user.phone }}</p></div>
<h2>عکس‌های مدارک</h2><div class="uploads-grid">
{% for key, label in doc_types %}<div class="upload-card"><div>{{ label }}</div>
{% if key in docs_by_type %}<a href="/admin/doc/{{ docs_by_type[key]['id'] }}" target="_blank"><img src="/admin/doc/{{ docs_by_type[key]['id'] }}"></a><div class="sub">✔ تایید</div>
{% else %}<div class="empty">✗ بارگذاری نشده</div>{% endif %}</div>{% endfor %}
</div>
{% if user.status == 'pending' %}
<div style="display:flex; flex-direction:column; gap:20px; margin-top:30px;">
    <div class="card" style="border-color: #10b981; background: #0a1a14;"><h3 style="margin-top:0; color: #6ee7b7;">✅ تایید درخواست</h3>
        <form method="post" action="/admin/action/{{ user.id }}/approve">
            <div class="field"><textarea name="reason" placeholder="پیام خوش‌آمدگویی برای کاربر (اختیاری)..." style="width: 100%; min-height: 60px; padding: 10px; background: #000; color: #fff; border: 1px solid #242b33; border-radius: 8px; resize: vertical;"></textarea></div>
            <button class="btn btn-primary" style="width: 100%;">تایید و فعال‌سازی حساب</button>
        </form>
    </div>
    <div class="card" style="border-color: #ef4444; background: #1a1111;"><h3 style="margin-top:0; color: #fca5a5;">❌ رد درخواست</h3>
        <form method="post" action="/admin/action/{{ user.id }}/reject">
            <div class="field"><textarea name="reason" required placeholder="دلیل رد شدن را بنویسید (مثلاً: عکس تذکره ناخوانا است)..." style="width: 100%; min-height: 60px; padding: 10px; background: #000; color: #fff; border: 1px solid #242b33; border-radius: 8px; resize: vertical;"></textarea></div>
            <button class="btn btn-danger" style="width: 100%;">ثبت دلیل و رد درخواست</button>
        </form>
    </div>
</div>
{% endif %}
</div>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base.html': BASE_HTML, 'register.html': REGISTER_HTML, 'login.html': LOGIN_HTML,
    'success.html': SUCCESS_HTML, 'pending.html': PENDING_HTML, 'admin.html': ADMIN_HTML, 'review.html': REVIEW_HTML
})

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
            whatsapp TEXT, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, country TEXT, city TEXT,
            skills TEXT, languages TEXT, experience TEXT, portfolio TEXT,
            skill_level TEXT NOT NULL CHECK(skill_level IN ('beginner','semi','pro')),
            status TEXT NOT NULL DEFAULT 'pending', role TEXT NOT NULL DEFAULT 'developer',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type TEXT NOT NULL, filename TEXT NOT NULL, original_name TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, type)
        );''')
        try: conn.execute('SELECT rejection_reason FROM users LIMIT 1')
        except sqlite3.OperationalError: conn.execute('ALTER TABLE users ADD COLUMN rejection_reason TEXT'); conn.commit()
        try: conn.execute('SELECT approval_message FROM users LIMIT 1')
        except sqlite3.OperationalError: conn.execute('ALTER TABLE users ADD COLUMN approval_message TEXT'); conn.commit()
            
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@moradi.digital')
        admin_pass  = os.environ.get('ADMIN_PASSWORD', 'Admin@12345')
        if not conn.execute("SELECT id FROM users WHERE role='admin'").fetchone():
            conn.execute('''INSERT INTO users (full_name,phone,whatsapp,email,password_hash,skill_level,status,role)
                VALUES (?,?,?,?,?,?,?,?)''', ('مدیر جوانه دیجیتال','00000000000','00000000000',admin_email, generate_password_hash(admin_pass),'pro','approved','admin'))

def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*a, **kw)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if session.get('role') != 'admin': abort(403)
        return f(*a, **kw)
    return wrap

@app.route('/')
def index(): return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    with get_db() as conn:
        total_members = conn.execute("SELECT COUNT(*) FROM users WHERE role='developer' AND status='approved'").fetchone()[0]

    if request.method == 'POST':
        f = request.form
        full_name, phone, email = f.get('full_name','').strip(), f.get('phone','').strip(), f.get('email','').strip().lower()
        password, skill_level = f.get('password',''), f.get('skill_level','')
        errors = []
        if not full_name: errors.append('نام الزامی است')
        if not phone: errors.append('شماره تماس الزامی است')
        if not email or '@' not in email: errors.append('ایمیل نامعتبر است')
        if len(password) < 8: errors.append('رمز عبور حداقل ۸ کاراکتر باشد')
        if skill_level not in ('beginner','semi','pro'): errors.append('سطح مهارت را انتخاب کنید')

        with get_db() as conn:
            existing_user = conn.execute('SELECT * FROM users WHERE email=? OR phone=?', (email, phone)).fetchone()

        if existing_user:
            if existing_user['status'] == 'rejected' and existing_user['email'] == email:
                user_id = existing_user['id']
                with get_db() as conn:
                    conn.execute('''UPDATE users SET full_name=?, whatsapp=?, country=?, city=?, skills=?, languages=?, experience=?, portfolio=?,
                                    skill_level=?, password_hash=?, status='pending', rejection_reason=NULL, approval_message=NULL WHERE id=?''',
                        (full_name, f.get('whatsapp',''), f.get('country',''), f.get('city',''), f.get('skills',''), f.get('languages',''),
                         f.get('experience',''), f.get('portfolio',''), skill_level, generate_password_hash(password), user_id))
                    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
                    os.makedirs(user_dir, exist_ok=True)
                    for key, _label in DOC_TYPES:
                        file = request.files.get(key)
                        if file and file.filename:
                            ext = os.path.splitext(secure_filename(file.filename))[1].lower() or '.jpg'
                            if ext not in ('.jpg','.jpeg','.png','.webp'): continue
                            fname = uuid.uuid4().hex + ext
                            file.save(os.path.join(user_dir, fname))
                            conn.execute('DELETE FROM documents WHERE user_id=? AND type=?', (user_id, key))
                            conn.execute('INSERT INTO documents (user_id,type,filename,original_name) VALUES (?,?,?,?)', (user_id, key, fname, file.filename))
             
