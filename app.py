from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import razorpay
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from itsdangerous import URLSafeTimedSerializer
from functools import wraps
from datetime import datetime
import re
import io
from flask import request, render_template, session, flash, redirect, url_for
import PyPDF2
import mysql.connector
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session
from flask_wtf.csrf import CSRFProtect
from functools import wraps
from flask import abort, session, redirect, url_for
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from functools import wraps
from flask_mail import Message

app = Flask(__name__)
app.secret_key = 'secret123'

# ✅ database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/skillnexa_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ ONLY ONE db instance (IMPORTANT)
db = SQLAlchemy(app)

# --- App Initialization ---
RAZORPAY_KEY_ID = "rzp_test_SSqFjmH1mZG1is"
RAZORPAY_KEY_SECRET = "b3xLH3du05sWGuW6dp5fTn0o"
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

MASTER_SKILLS = [
    'Python', 'Java', 'JavaScript', 'React', 'Node.js', 'HTML', 'CSS', 
    'SQL', 'MongoDB', 'AWS', 'Docker', 'Git', 'Flask', 'Django', 'C++',
    'Machine Learning', 'Data Analysis', 'PHP', 'Laravel', 'UI/UX'
]

# --- Configurations ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, 'database', 'users.db')
PROFILE_PICS_FOLDER = os.path.join(BASE_DIR, 'static', 'profile_pics')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['PROFILE_PICS_FOLDER'] = PROFILE_PICS_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['WTF_CSRF_ENABLED'] = False

os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
os.makedirs(PROFILE_PICS_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

s = URLSafeTimedSerializer(app.secret_key)

# ----------------- DATABASE FUNCTIONS -----------------
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="skillnexa_db"
    )
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            username VARCHAR(255) UNIQUE,
            password VARCHAR(255) NOT NULL,
            profile_image VARCHAR(255) DEFAULT 'default.png',
            dob VARCHAR(100),
            location VARCHAR(255),
            is_pro INT DEFAULT 0
        )
    """)

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_pro INT DEFAULT 0")
    except:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_title VARCHAR(255) NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            job_type VARCHAR(100) NOT NULL,
            salary VARCHAR(100),
            description TEXT NOT NULL,
            application_link VARCHAR(500) NOT NULL,
            posted_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            employer_id INT,
            FOREIGN KEY (employer_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

init_db()

# ----------------- DECORATORS & HELPERS -----------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def create_default_profile_pic(name, user_id):
    initials = "".join([n[0] for n in name.split()[:2]]).upper()
    img = Image.new('RGB', (200, 200), color='#00FFFF')
    try:
        font = ImageFont.truetype("arialbd.ttf", 90)
    except IOError:
        font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)
    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    position = ((200 - text_width) / 2, (200 - text_height) / 2 - 10)
    draw.text(position, initials, fill='#111439', font=font)
    filename = f"default_{user_id}.png"
    filepath = os.path.join(app.config['PROFILE_PICS_FOLDER'], filename)
    img.save(filepath)
    return filename

# ----------------- EMAIL FUNCTIONS -----------------
def send_welcome_email(to_email, name):
    sender_email = 'goskillnexa@gmail.com'
    app_password = 'wjpr fnkq fiog seud'
    
    linkedin_url = "https://www.linkedin.com/in/goskillnexa" 
    twitter_url = "https://twitter.com/goskillnexa"
    instagram_url = "https://www.instagram.com/goskillnexa"

    msg = EmailMessage()
    msg['Subject'] = 'Welcome to the Future of Hiring! 🚀 | GoSkillNexa'
    msg['From'] = formataddr(('GoSkillNexa', sender_email))
    msg['To'] = to_email

    # ✅ Premium & Clean Design (No Black Box)
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: 'Segoe UI', Arial, sans-serif;">
        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 24px; overflow: hidden; box-shadow: 0 15px 45px rgba(0,0,0,0.07); border: 1px solid #e2e8f0;">
            
            <div style="background: #ffffff; padding: 50px 20px; text-align: center; border-bottom: 1px solid #f1f5f9;">
                <div style="font-size: 32px; font-weight: 800; color: #2563eb; letter-spacing: -1px;">
                    GoSkill<span style="color: #0f172a;">Nexa</span>
                </div>
                <p style="margin: 10px 0 0 0; color: #64748b; font-size: 14px; text-transform: uppercase; letter-spacing: 2px;">Elite Talent Platform</p>
            </div>

            <div style="padding: 40px; color: #1e293b;">
                <h2 style="font-size: 26px; color: #0f172a; margin-top: 0; font-weight: 700;">Welcome to the Community, <span style="color: #2563eb;">{name}</span>!</h2>
                <p style="font-size: 16px; line-height: 1.8; color: #475569;">
                    We're thrilled to have you! <b>GoSkillNexa</b> is designed to make your professional journey smoother and smarter. You're now ready to explore a world of opportunities.
                </p>

                <div style="background: linear-gradient(to right, #f0f9ff, #e0f2fe); border-radius: 16px; padding: 25px; margin: 30px 0; border: 1px solid #bae6fd;">
                    <p style="margin: 0 0 12px 0; font-weight: bold; color: #0369a1; font-size: 16px;">🚀 Quick Start Guide:</p>
                    <div style="color: #0c4a6e; font-size: 15px; line-height: 2;">
                        • Set up your AI-driven profile<br>
                        • Upload your resume for instant matching<br>
                        • Apply to premium job listings
                    </div>
                </div>

                <div style="text-align: center; margin: 40px 0;">
                    <a href="http://127.0.0.1:5000/login" 
                       style="background: #2563eb; 
                              color: #ffffff; 
                              padding: 18px 40px; 
                              text-decoration: none; 
                              border-radius: 14px; 
                              font-weight: 700; 
                              font-size: 16px;
                              display: inline-block;
                              box-shadow: 0 10px 25px rgba(37, 99, 235, 0.25);">
                        Go to My Dashboard
                    </a>
                </div>

                <p style="font-size: 14px; color: #94a3b8; text-align: center; font-style: italic;">
                    Need help? Just hit reply, our team is always here for you.
                </p>
            </div>

            <div style="background: #f8fafc; padding: 30px; text-align: center; border-top: 1px solid #f1f5f9;">
                <p style="margin: 0 0 15px 0; color: #475569; font-weight: 600; font-size: 14px;">Connect with us</p>
                
                <div style="margin-bottom: 20px;">
                    <a href="{linkedin_url}" style="display: inline-block; margin: 0 12px; color: #2563eb; text-decoration: none; font-weight: 700; font-size: 13px;">LinkedIn</a>
                    <a href="{twitter_url}" style="display: inline-block; margin: 0 12px; color: #2563eb; text-decoration: none; font-weight: 700; font-size: 13px;">Twitter</a>
                    <a href="{instagram_url}" style="display: inline-block; margin: 0 12px; color: #2563eb; text-decoration: none; font-weight: 700; font-size: 13px;">Instagram</a>
                </div>

                <p style="margin: 5px 0; color: #94a3b8; font-size: 12px;">&copy; 2026 Resume Analyzer by GoSkillNexa</p>
                <p style="margin: 5px 0; color: #cbd5e1; font-size: 11px;">Mumbai, Maharashtra, India</p>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    msg.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
            print(f"✅ Clean Premium Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error: {e}")


def send_payment_alert_to_admin(user_name, user_email, payment_id):
    sender_email = 'goskillnexa@gmail.com'
    app_password = 'wjpr fnkq fiog seud'
    
    msg = EmailMessage()
    msg['Subject'] = 'New Pro Payment Received! 💰'
    msg['From'] = formataddr(('GoSkillNexa Sales', sender_email))
    msg['To'] = sender_email

    # Simple & Clear HTML Body for Admin (Arun)
    html_body = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 2px solid #10b981; border-radius: 15px; background-color: #f0fdf4;">
        <h2 style="color: #166534; margin-top: 0;">Payment Alert! 💸</h2>
        <p>Hi Arun, a new user has just upgraded to <b>Pro Match</b>.</p>
        <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #dcfce7;">
            <p style="margin: 5px 0;"><b>User:</b> {user_name}</p>
            <p style="margin: 5px 0;"><b>Email:</b> {user_email}</p>
            <p style="margin: 5px 0;"><b>Amount:</b> ₹299.00</p>
            <p style="margin: 5px 0;"><b>Payment ID:</b> <span style="color: #2563eb;">{payment_id}</span></p>
        </div>
        <p style="margin-top: 20px; font-size: 13px;">Time to scale! Check your Razorpay dashboard for settlement details.</p>
    </div>
    """
    msg.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
    except Exception as e:
        print(f"Admin Alert Mail Error: {e}")

# ----------------- AUTH ROUTES -----------------
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def home():
    return render_template('index.html')

# --- JOB DETAILS ROUTE ---
@app.route('/job/<int:job_id>')
def job_details(job_id):
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = '''
        SELECT jobs.*, users.profile_image 
        FROM jobs 
        LEFT JOIN users ON jobs.employer_id = users.id 
        WHERE jobs.id = %s
    '''
    cursor.execute(query, (job_id,))
    job_data = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if job_data:
        if isinstance(job_data.get('posted_on'), str):
            try:
                job_data['posted_on'] = datetime.strptime(job_data['posted_on'], '%Y-%m-%d %H:%M:%S')
            except:
                pass
        return render_template('job_details.html', job=job_data)
    
    return render_template('404.html'), 404

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('fullName')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirmPassword')

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')

        username = generate_unique_username(full_name)
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (full_name, email, password, username) VALUES (%s, %s, %s, %s)", 
                (full_name, email, hashed_password, username)
            )
            user_id = cursor.lastrowid
            default_pic = create_default_profile_pic(full_name, user_id)
            cursor.execute("UPDATE users SET profile_image = %s WHERE id = %s", (default_pic, user_id))
            conn.commit()
            
            session['username'] = username
            session['user_name'] = full_name
            session['user_id'] = user_id

            send_welcome_email(email, full_name)
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error:
            flash('Email already registered.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            user_status = user.get('status', 'active').lower()
            
            if user_status == 'suspended':
                flash('Your account is suspended. Please contact admin.', 'warning')
                return redirect(url_for('login'))
                
            if user_status == 'blocked':
                flash('Your account has been blocked permanently.', 'error')
                return redirect(url_for('login'))

            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['profile_image'] = user['profile_image']
            session['is_pro'] = user['is_pro']
            return redirect(url_for('home'))
            
        flash('Invalid login credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>')
def reset_password(token):
    return render_template('reset_password.html', token=token)

# ----------------- DASHBOARD & PROFILE -----------------
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        full_name = request.form.get('fullName')
        username = request.form.get('username', '').lower()
        dob = request.form.get('dob')
        location = request.form.get('location')

        cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash('Username already taken! Please choose another one.', 'error')
            return redirect(url_for('dashboard'))

        try:
            cursor.execute('''
                UPDATE users 
                SET full_name = %s, dob = %s, location = %s, username = %s 
                WHERE id = %s
            ''', (full_name, dob, location, username, user_id))
            
            conn.commit()
            session['user_name'] = full_name
            session['username'] = username
            flash('Profile updated successfully!', 'success')
        except mysql.connector.Error:
            flash('An error occurred during update.', 'error')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('dashboard'))

    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', user=user)

# ----------------- SCAN & UPLOAD (LOCKED) -----------------
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        print(f"PDF Extraction Error: {e}")
        return ""
    
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
            
        file = request.files['resume']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file:
            resume_text = extract_text_from_pdf(file)
            
            if not resume_text:
                flash('Could not read the PDF file. Please try another one.', 'error')
                return redirect(request.url)

            # --- STRICT SKILL DETECTION ---
            detected_skills = []
            for skill in MASTER_SKILLS:
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, resume_text, re.IGNORECASE):
                    detected_skills.append(skill)

            # --- STRICT JOB MATCHING ---
            conn = get_db_connection()
            all_jobs = conn.execute('SELECT * FROM jobs').fetchall()
            conn.close()

            matched_jobs = []
            for job in all_jobs:
                job_desc = (job['description'] + " " + job['job_title']).lower()
                
                score = 0
                for skill in detected_skills:
                    if skill.lower() in job_desc:
                        score += 1
                
                if score > 0:
                    matched_jobs.append({
                        'job': job,
                        'score': score
                    })

            matched_jobs.sort(key=lambda x: x['score'], reverse=True)
            final_jobs = [j['job'] for j in matched_jobs]

            return render_template('upload.html', 
                                   skills=detected_skills, 
                                   jobs=final_jobs, 
                                   total_matches=len(final_jobs))

    return render_template('upload.html')
# ----------------- JOB ROUTES (CRUD) -----------------
@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT is_pro, posts_consumed FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        session.clear()
        flash('User session expired or user not found. Please login again.', 'error')
        return redirect(url_for('login'))

    consumed = user['posts_consumed']
    plan_limit = 2
    if user['is_pro'] == 1:
        plan_limit = 10
    elif user['is_pro'] == 2:
        plan_limit = 999999
        
    if request.method == 'POST':
        if consumed >= plan_limit:
            flash(f'Limit Reached! Your plan allows only {plan_limit} lifetime posts.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('hire'))

        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        location = request.form.get('location')
        job_type = request.form.get('job_type')
        salary = request.form.get('salary')
        description = request.form.get('description')
        app_link = request.form.get('application_link').strip()

        if app_link and not app_link.startswith(('http://', 'https://')):
            app_link = 'https://' + app_link

        cursor.execute('''
            INSERT INTO jobs (job_title, company_name, location, job_type, salary, description, application_link, employer_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (job_title, company_name, location, job_type, salary, description, app_link, user_id))
        
        cursor.execute('UPDATE users SET posts_consumed = posts_consumed + 1 WHERE id = %s', (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Job posted successfully!', 'success')
        return redirect(url_for('employer_dashboard'))

    cursor.close()
    conn.close()
    return render_template('post_job.html', current_count=consumed, limit=plan_limit)

@app.route('/employer-dashboard')
@login_required
def employer_dashboard():
    from datetime import timedelta
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT is_pro, posts_consumed, last_reset_date FROM users WHERE id = %s', (user_id,))
    user_info = cursor.fetchone()
    
    if user_info:
        reset_happened = check_and_reset_quota(user_id, user_info, conn)
        if reset_happened:
            cursor.execute('SELECT is_pro, posts_consumed, last_reset_date FROM users WHERE id = %s', (user_id,))
            user_info = cursor.fetchone()

    next_reset_val = "N/A"
    if user_info and user_info['last_reset_date']:
        next_date = user_info['last_reset_date'] + timedelta(days=30)
        next_reset_val = next_date.strftime('%d %b, %Y')

    cursor.execute('''
        SELECT jobs.*, users.profile_image 
        FROM jobs 
        LEFT JOIN users ON jobs.employer_id = users.id 
        WHERE jobs.employer_id = %s 
        ORDER BY jobs.posted_on DESC
    ''', (user_id,))
    jobs = cursor.fetchall()
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM applications 
        WHERE job_id IN (SELECT id FROM jobs WHERE employer_id = %s)
    ''', (user_id,))
    applicants_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count FROM profile_views WHERE employer_id = %s', (user_id,))
    hits_count = cursor.fetchone()['count']
    
    cursor.close()
    conn.close()
    
    return render_template('employer_dashboard.html', 
                           jobs=jobs, 
                           applicants_count=applicants_count, 
                           hits_count=hits_count,
                           posts_consumed=user_info['posts_consumed'] if user_info else 0,
                           next_reset_date=next_reset_val)

@app.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        job_title = request.form.get('job_title')
        company_name = request.form.get('company_name')
        location = request.form.get('location')
        job_type = request.form.get('job_type')
        salary = request.form.get('salary')
        description = request.form.get('description')
        app_link = request.form.get('application_link')

        cursor.execute('''
            UPDATE jobs 
            SET job_title = %s, company_name = %s, location = %s, job_type = %s, 
                salary = %s, description = %s, application_link = %s 
            WHERE id = %s AND employer_id = %s
        ''', (job_title, company_name, location, job_type, salary, description, app_link, job_id, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Job updated successfully!', 'success')
        return redirect(url_for('employer_dashboard'))

    cursor.execute('SELECT * FROM jobs WHERE id = %s AND employer_id = %s', (job_id, user_id))
    job = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if job:
        return render_template('edit_job.html', job=job)
    
    return render_template('404.html'), 404

@app.route('/delete-job/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM jobs WHERE id = %s AND employer_id = %s', (job_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('employer_dashboard'))

@app.route('/search')
@login_required
def search():
    kw = request.args.get('keyword', '')
    loc = request.args.get('location', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT jobs.*, users.profile_image 
        FROM jobs 
        LEFT JOIN users ON jobs.employer_id = users.id 
        WHERE jobs.job_title LIKE %s AND jobs.location LIKE %s
        ORDER BY jobs.posted_on DESC
    """
    params = (f'%{kw}%', f'%{loc}%')
    
    cursor.execute(query, params)
    jobs = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('search.html', jobs=jobs, search_keyword=kw, search_location=loc)

# ----------------- PAYMENT ROUTES -----------------

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        print("Creating order for test...")
        order = client.order.create({
            "amount": 29900, 
            "currency": "INR", 
            "receipt": "test_order_101"
        })
        print(f"✅ Success! Order ID: {order['id']}")
        return jsonify(order)
    except Exception as e:
        print(f"❌ Razorpay Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/payment_success')
@login_required
def payment_success():
    user_id = session['user_id']
    payment_id = request.args.get('id', 'N/A')
    plan_type = request.args.get('plan', 'pro')
    
    is_pro_val = 1 if plan_type == 'pro' else 2
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        UPDATE users 
        SET is_pro = %s, posts_consumed = 0, last_reset_date = CURRENT_DATE 
        WHERE id = %s
    ''', (is_pro_val, user_id))
    
    cursor.execute('SELECT full_name, email FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    
    conn.commit()
    cursor.close()
    conn.close()
    
    session['is_pro'] = is_pro_val
    
    if user:
        send_payment_alert_to_admin(user['full_name'], user['email'], payment_id)
    
    return render_template('payment_success.html')

@app.route('/post-job-check')
@login_required
def post_job_check():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT is_pro FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not user or user['is_pro'] == 0:
        flash('Please choose a plan to start posting jobs!', 'info')
        return redirect(url_for('hire'))
    
    return redirect(url_for('post_job'))

@app.route('/view-applicants')
@login_required
def view_applicants():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    query = '''
        SELECT a.applied_on, j.job_title, u.full_name, u.email 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN users u ON a.user_id = u.id
        WHERE j.employer_id = %s
        ORDER BY a.applied_on DESC
    '''
    
    cursor.execute(query, (user_id,))
    applicants = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    job = {'job_title': 'All Postings'}
    
    return render_template('view_applicants.html', applicants=applicants, job=job)

@app.route('/employer-profile/<int:employer_id>')
def employer_profile(employer_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO profile_views (employer_id, viewer_ip) VALUES (%s, %s)", 
                   (employer_id, request.remote_addr))
    conn.commit()

    cursor.execute("SELECT * FROM users WHERE id = %s", (employer_id,))
    employer = cursor.fetchone()
    
    cursor.close()
    conn.close()
    return render_template('employer_public_profile.html', employer=employer)

@app.route('/profile-analytics')
@login_required
def profile_analytics():
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('''
        SELECT DATE(viewed_at) as date, COUNT(*) as count 
        FROM profile_views 
        WHERE employer_id = %s 
        GROUP BY DATE(viewed_at) 
        ORDER BY date DESC LIMIT 7
    ''', (user_id,))
    graph_data = cursor.fetchall()
    
    dates = [row['date'].strftime('%d %b') for row in reversed(graph_data)]
    counts = [row['count'] for row in reversed(graph_data)]

    cursor.execute('''
        SELECT viewer_ip, viewed_at 
        FROM profile_views 
        WHERE employer_id = %s 
        ORDER BY viewed_at DESC LIMIT 15
    ''', (user_id,))
    recent_views = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('profile_analytics.html', dates=dates, counts=counts, recent_views=recent_views)

def generate_unique_username(name):
    base = "".join(name.split()).lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = %s", (base,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return base
    counter = 1
    while True:
        new_username = f"{base}{counter:02}"
        cursor.execute("SELECT id FROM users WHERE username = %s", (new_username,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return new_username
        counter += 1
        
@app.route('/check-username')
def check_username():
    username = request.args.get('username', '').lower()
    if not username:
        return jsonify({"available": False, "message": ""})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", 
                   (username, session.get('user_id')))
    exists = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if exists:
        return jsonify({"available": False, "message": "Username already taken!"})
    else:
        return jsonify({"available": True, "message": "Username is available!"})
    

def check_and_reset_quota(user_id, user_data, conn):
    last_reset = user_data['last_reset_date']
    
    if isinstance(last_reset, str):
        last_reset = datetime.strptime(last_reset, '%Y-%m-%d').date()
    
    today = datetime.now().date()
    
    if (today - last_reset).days >= 30:
        cursor = conn.cursor()
        
        if user_data['is_pro'] == 0:
            cursor.execute('''
                UPDATE users 
                SET posts_consumed = 0, last_reset_date = %s 
                WHERE id = %s
            ''', (today, user_id))
        else:
            cursor.execute('''
                UPDATE users 
                SET is_pro = 0, posts_consumed = 0, last_reset_date = %s 
                WHERE id = %s
            ''', (today, user_id))
        
        conn.commit()
        cursor.close()
        return True
    return False

@app.route('/test_route', methods=['POST'])
def test_route():
    print("!!! SERVER HIT SUCCESSFUL !!!")
    return jsonify({"message": "Server is reaching here!"})

from functools import wraps
from flask import session, redirect, url_for, abort, render_template
from sqlalchemy import text

# ✅ Admin Middleware
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('login'))
        
        sql = text("SELECT email FROM users WHERE id = :id")
        result = db.session.execute(sql, {'id': user_id}).fetchone()  # type: ignore
        
        # ✅ Admin check
        if result and result[0] == 'goskillnexa@gmail.com':
            return f(*args, **kwargs)
        
        return abort(403)
    return decorated_function


# ✅ Admin Dashboard Route (name fixed)
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = db.session.execute(text("SELECT * FROM users")).mappings().all() 
    jobs = db.session.execute(text("SELECT * FROM jobs")).mappings().all()
    support_messages = db.session.execute(text("SELECT * FROM support_message ORDER BY timestamp DESC")).mappings().all()
    return render_template('admin.html', users=users, jobs=jobs, support_messages=support_messages)

# ✅ Delete User
@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    check_sql = text("SELECT email FROM users WHERE id = :id")
    user = db.session.execute(check_sql, {'id': user_id}).fetchone()
    
    if user and user[0] == 'goskillnexa@gmail.com':
        return redirect(url_for('admin_dashboard'))
    
    db.session.execute(text("DELETE FROM users WHERE id = :id"), {'id': user_id})
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


# ✅ Delete Job
@app.route('/admin/delete_job_listing/<int:job_id>')
@admin_required
def admin_delete_job(job_id):
    db.session.execute(text("DELETE FROM jobs WHERE id = :id"), {'id': job_id})  # type: ignore
    db.session.commit()
    
    # ✅ Fixed redirect name
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/make_pro/<int:user_id>')
@admin_required
def make_pro(user_id):
    db.session.execute(
        text("UPDATE users SET is_pro = 1 WHERE id = :id"),
        {'id': user_id}
    )
    db.session.commit()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/block_user/<int:user_id>')
@admin_required
def block_user(user_id):
    db.session.execute(text("UPDATE users SET is_blocked = 1 WHERE id = :id"), {'id': user_id})
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/activate_user/<int:user_id>')
@admin_required
def activate_user(user_id):
    db.session.execute(text("UPDATE users SET is_blocked = 0 WHERE id = :id"), {'id': user_id})
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/suspend_user/<int:user_id>')
@admin_required
def suspend_user(user_id):
    db.session.execute(text("UPDATE users SET is_active = 0 WHERE id = :id"), {'id': user_id})
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/set_status/<int:user_id>/<string:new_status>')
@admin_required
def set_user_status(user_id, new_status):
    check_sql = text("SELECT email FROM users WHERE id = :id")
    user = db.session.execute(check_sql, {'id': user_id}).fetchone()
    
    if user and user[0] == 'goskillnexa@gmail.com':
        return redirect(request.referrer or url_for('admin_dashboard'))
        
    try:
        update_sql = text("UPDATE users SET status = :status WHERE id = :id")
        db.session.execute(update_sql, {'status': new_status.lower(), 'id': user_id})
        db.session.commit()
    except Exception:
        db.session.rollback()
        
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.before_request
def check_live_status():
    if 'user_id' in session:
        if request.endpoint in ['logout', 'static', 'login']:
            return

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT status FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            status = user.get('status', 'active').lower()
            
            if status == 'suspended':
                session.clear()
                flash('Your account is suspended. Please contact admin.', 'error')
                return redirect(url_for('login'))
                
            elif status == 'blocked':
                session.clear()
                flash('Your account is blocked. Please contact admin.', 'error')
                return redirect(url_for('login'))
        else:
            session.clear()
            flash('Your account is deleted. Please contact admin.', 'error')
            return redirect(url_for('login'))
                
# ----------------- STATIC ROUTES -----------------
@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        sql = text("INSERT INTO support_message (name, email, subject, message) VALUES (:name, :email, :subject, :message)")
        db.session.execute(sql, {'name': name, 'email': email, 'subject': subject, 'message': message})
        db.session.commit()
        
        return redirect(url_for('contact', success=1))
        
    return render_template('contact.html')

@app.route('/hire')
def hire(): return render_template('pricing.html')

@app.route('/privacy')
def privacy(): return render_template('privacy.html')

@app.route('/terms')
def terms(): return render_template('terms.html')

@app.route('/refund')
def refund(): return render_template('refund.html')

@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    display_name = session.get('user_name', 'Guest') 
    return render_template('403.html', name=display_name), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)