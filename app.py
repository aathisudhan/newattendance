import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pytz

app = Flask(__name__)
# Security: Use environment variable for secret key on Vercel
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pec_attendance_system_2026")

# --- FIREBASE SECURE SETUP ---
if not firebase_admin._apps:
    service_account_info = os.getenv('FIREBASE_SERVICE_ACCOUNT')
    
    if service_account_info:
        try:
            # Fix for Vercel: ensure the JSON string is clean
            key_dict = json.loads(service_account_info.strip(), strict=False)
            cred = credentials.Certificate(key_dict)
        except Exception as e:
            print(f"🔥 Error parsing FIREBASE_SERVICE_ACCOUNT: {e}")
            cred = credentials.Certificate("serviceAccountKey.json")
    else:
        cred = credentials.Certificate("serviceAccountKey.json")

    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

# Helper for IST Time & Day
def get_ist_info():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%A"), now.time()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    uid = request.form.get('username', '').strip()
    pwd = request.form.get('password', '').strip()
    role = request.form.get('role')

    if role == 'admin' and uid == 'admin' and pwd == 'admin':
        session.update({'user': 'Admin', 'role': 'admin', 'name': 'Administrator', 'dept': 'System'})
        return redirect(url_for('admin_page'))

    if role == 'faculty':
        f_data = db.reference(f'Faculty/{uid}').get()
        if f_data and str(f_data.get('password')) == str(pwd):
            session.update({
                'user': uid, 
                'role': 'faculty', 
                'name': f_data.get('name', 'Professor'),
                'dept': f_data.get('dept', 'General')
            })
            return redirect(url_for('faculty_page'))

    return "Login Failed. Please check credentials."

@app.route('/faculty')
def faculty_page():
    if session.get('role') != 'faculty':
        return redirect(url_for('index'))
    
    _, day_str, current_time = get_ist_info()
    timetable = db.reference('Timetable').get()
    
    # Pre-emptive safety check
    if not isinstance(timetable, dict):
        return render_template('faculty_mark.html', slots=[])

    assigned_slots = []
    
    try:
        for dept, batches in timetable.items():
            if not isinstance(batches, dict): continue
            for batch, years in batches.items():
                if not isinstance(years, dict): continue
                for year_label, sections in years.items():
                    if not isinstance(sections, dict): continue
                    
                    # Logic: Check if current level is Day (Monday/Tuesday) or a Section (A/B)
                    if day_str in sections:
                        process_slots(sections[day_str], dept, batch, year_label, assigned_slots, current_time)
                    else:
                        for sec, days in sections.items():
                            if isinstance(days, dict) and day_str in days:
                                process_slots(days[day_str], dept, batch, sec, assigned_slots, current_time)
    except Exception as e:
        print(f"Timetable logic failure: {e}")

    return render_template('faculty_mark.html', slots=assigned_slots)

def process_slots(day_data, dept, batch, sec, assigned_slots, current_time):
    if not isinstance(day_data, dict): return
    
    for period, info in day_data.items():
        # Case insensitive faculty check
        if str(info.get('faculty')).lower() == str(session.get('user')).lower():
            try:
                time_range = info.get('time', '').split('-')
                if len(time_range) == 2:
                    start = datetime.strptime(time_range[0].strip(), "%H:%M").time()
                    end = datetime.strptime(time_range[1].strip(), "%H:%M").time()
                    if start <= current_time <= end:
                        assigned_slots.append({
                            'dept': dept, 'batch': batch, 'sec': sec,
                            'period': period, 'subject': info.get('subject'), 
                            'time': info.get('time')
                        })
            except Exception as e:
                print(f"Time comparison error: {e}")

@app.route('/api/get_students')
def get_students():
    dept = request.args.get('dept')
    batch = request.args.get('batch')
    sec = request.args.get('sec')
    
    # Reference path for students
    path = f"Students/{dept}/{batch}/{sec}"
    try:
        data = db.reference(path).get()
        return jsonify(data if data else {})
    except:
        return jsonify({"error": "Path error"}), 500

@app.route('/api/submit_attendance', methods=['POST'])
def submit_attendance():
    d = request.json
    date_str, _, _ = get_ist_info()
    
    # Path: Attendance/Dept/Batch/Section/Date
    ref_path = f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}"
    ref = db.reference(ref_path)
    subject_name = d.get('subject', 'N/A')
    
    try:
        for roll, info in d['records'].items():
            ref.child(roll).update({
                "name": info['name'],
                d['period']: {"status": info['status'], "subject": subject_name}
            })
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ADMIN SECTION ---

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_stats.html')

@app.route('/api/admin/get_structure')
def get_structure():
    data = db.reference('Students').get()
    return jsonify(data if data else {})

@app.route('/api/admin/get_report')
def get_report():
    dept, batch, sec, date = request.args.get('dept'), request.args.get('batch'), request.args.get('sec'), request.args.get('date')
    students = db.reference(f"Students/{dept}/{batch}/{sec}").get() or {}
    attendance_data = db.reference(f"Attendance/{dept}/{batch}/{sec}/{date}").get() or {}
    
    report_data = []
    for roll, info in students.items():
        report_data.append({
            'roll': roll,
            'name': info.get('name'),
            'attendance': attendance_data.get(roll, {}) 
        })
    return jsonify(report_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
