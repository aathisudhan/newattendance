import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pytz

app = Flask(__name__)
# Set a fallback secret key if environment variable is missing
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pec_attendance_system_2026")

# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    # Check if running on Vercel (look for Environment Variable)
    if os.getenv('FIREBASE_SERVICE_ACCOUNT'):
        try:
            # Parse the JSON string stored in Vercel Environment Variables
            service_account_info = json.loads(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
            cred = credentials.Certificate(service_account_info)
        except Exception as e:
            print(f"🔥 Error parsing Environment Variable: {e}")
            # Fallback to local file if parsing fails
            cred = credentials.Certificate("serviceAccountKey.json")
    else:
        # Local development fallback
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
    uid = request.form.get('username')
    pwd = request.form.get('password')
    role = request.form.get('role')

    if role == 'admin' and uid == 'admin' and pwd == 'admin':
        session.update({'user': 'Admin', 'role': 'admin'})
        return redirect(url_for('admin_page'))

    if role == 'faculty':
        f_data = db.reference(f'Faculty/{uid}').get()
        if f_data and str(f_data.get('password')) == str(pwd):
            session.update({
                'user': uid, 
                'role': 'faculty', 
                'name': f_data.get('name', 'Professor'),
                'dept': f_data.get('dept')
            })
            return redirect(url_for('faculty_page'))

    return "Login Failed. Please check credentials."

@app.route('/faculty')
def faculty_page():
    if session.get('role') != 'faculty':
        return redirect(url_for('index'))
    
    _, day_str, current_time = get_ist_info()
    timetable = db.reference('Timetable').get() or {}
    assigned_slots = []
    
    # Logic: Crawl through Dept > Batch > Year Level > Section > Day
    for dept, batches in timetable.items():
        for batch, years in batches.items():
            for year_label, sections in years.items():
                for sec, days in sections.items():
                    if day_str in days:
                        for period, info in days[day_str].items():
                            if info.get('faculty') == session['user']:
                                try:
                                    time_range = info.get('time').split('-')
                                    start = datetime.strptime(time_range[0].strip(), "%H:%M").time()
                                    end = datetime.strptime(time_range[1].strip(), "%H:%M").time()
                                    
                                    # Logic: Show card if current time is within slot
                                    if start <= current_time <= end:
                                        assigned_slots.append({
                                            'dept': dept, 
                                            'batch': batch, 
                                            'sec': sec,
                                            'period': period, 
                                            'subject': info.get('subject'), 
                                            'time': info.get('time')
                                        })
                                except:
                                    pass
    
    return render_template('faculty_mark.html', slots=assigned_slots)

@app.route('/api/get_students')
def get_students():
    dept = request.args.get('dept')
    batch = request.args.get('batch')
    sec = request.args.get('sec')
    path = f"Students/{dept}/{batch}/{sec}"
    data = db.reference(path).get()
    return jsonify(data) if data else (jsonify({}), 404)

@app.route('/api/submit_attendance', methods=['POST'])
def submit_attendance():
    d = request.json
    date_str, _, _ = get_ist_info()
    ref = db.reference(f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}")
    subject_name = d.get('subject', 'N/A')
    
    for roll, info in d['records'].items():
        ref.child(roll).update({
            "name": info['name'],
            d['period']: {
                "status": info['status'],
                "subject": subject_name
            }
        })
    return jsonify({"status": "success"})

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_stats.html')

@app.route('/api/admin/get_structure')
def get_structure():
    return jsonify(db.reference('Students').get() or {})

@app.route('/api/admin/get_report')
def get_report():
    dept, batch, sec, date = request.args.get('dept'), request.args.get('batch'), request.args.get('sec'), request.args.get('date')
    students = db.reference(f"Students/{dept}/{batch}/{sec}").get() or {}
    attendance_data = db.reference(f"Attendance/{dept}/{batch}/{sec}/{date}").get() or {}
    
    report_data = [{
        'roll': roll,
        'name': info.get('name'),
        'attendance': attendance_data.get(roll, {}) 
    } for roll, info in students.items()]
    
    return jsonify(report_data)

@app.route('/api/admin/get_student_cumulative_stats')
def get_student_cumulative_stats():
    target_roll = request.args.get('roll')
    if not target_roll: return jsonify({"error": "Roll required"}), 400

    try:
        all_data = db.reference('Attendance').get() or {}
        subject_map = {}

        # Flattened crawl to find the specific student across all dates
        for dept in all_data.values():
            for batch in dept.values():
                for sec in batch.values():
                    for date_data in sec.values():
                        if target_roll in date_data:
                            student_day = date_data[target_roll]
                            for i in range(1, 9):
                                p_key = f'P{i}'
                                if p_key in student_day:
                                    p_info = student_day[p_key]
                                    sub = p_info.get('subject', 'General')
                                    if sub not in subject_map:
                                        subject_map[sub] = {"attended": 0, "total": 0}
                                    subject_map[sub]["total"] += 1
                                    if p_info.get('status') in ['P', 'Present']:
                                        subject_map[sub]["attended"] += 1
        return jsonify(subject_map)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
