from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "pec_attendance_system_2026"

# --- FIREBASE SETUP ---
# Ensure serviceAccountKey.json is in the same directory as this file
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# Helper for IST Time & Day
def get_ist_info():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    # Returns: Date (2026-04-08), Day (Wednesday), and current time object
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

    # 1. Admin Login (Hardcoded)
    if role == 'admin' and uid == 'admin' and pwd == 'admin':
        session.update({'user': 'Admin', 'role': 'admin'})
        return redirect(url_for('admin_page'))

    # 2. Faculty Login (Dynamic from Firebase)
    if role == 'faculty':
        f_data = db.reference(f'Faculty/{uid}').get()
        if f_data and f_data.get('password') == pwd:
            session.update({
                'user': uid, 
                'role': 'faculty', 
                'name': f_data.get('name', 'Professor'),
                'dept': f_data.get('dept')
            })
            return redirect(url_for('faculty_page'))

    return "Login Failed. Please check credentials."

# --- FACULTY SECTION ---

@app.route('/faculty')
def faculty_page():
    if session.get('role') != 'faculty':
        return redirect(url_for('index'))
    
    date_str, day_str, current_time = get_ist_info()
    timetable = db.reference('Timetable').get() or {}
    
    assigned_slots = []
    
    # Logic: Crawl Timetable with nested Year Level (Year III) support
    for dept, batches in timetable.items():
        for batch, years in batches.items():
            for year_label, sections in years.items():
                for sec, days in sections.items():
                    if day_str in days:
                        for period, info in days[day_str].items():
                            # 1. Check if the logged-in Faculty ID matches the slot
                            if info.get('faculty') == session['user']:
                                try:
                                    # 2. Time Filter logic
                                    time_range = info.get('time').split('-')
                                    start = datetime.strptime(time_range[0].strip(), "%H:%M").time()
                                    end = datetime.strptime(time_range[1].strip(), "%H:%M").time()
                                    
                                    # Shows the card only if the current time falls within the period
                                    if start <= current_time <= end:
                                        assigned_slots.append({
                                            'dept': dept, 
                                            'batch': batch, 
                                            'sec': sec,
                                            'period': period, 
                                            'subject': info.get('subject'), 
                                            'time': info.get('time')
                                        })
                                except Exception as e:
                                    print(f"Time Parse Error: {e}")
                                    pass
    
    return render_template('faculty_mark.html', slots=assigned_slots)

@app.route('/api/get_students')
def get_students():
    dept = request.args.get('dept')
    batch = request.args.get('batch')
    sec = request.args.get('sec')
    
    # Debugging: Check your terminal to see if these values are correct
    print(f"🔍 Searching for: Dept={dept}, Batch={batch}, Sec={sec}")
    
    # Path: Students/AI&DS/2027/A
    path = f"Students/{dept}/{batch}/{sec}"
    data = db.reference(path).get()
    
    if not data:
        print(f"❌ No data found at path: {path}")
        return jsonify({}), 404
        
    return jsonify(data)

# @app.route('/api/submit_attendance', methods=['POST'])
# def submit_attendance():
#     d = request.json
#     date_str, _, _ = get_ist_info()
    
#     # Path: Attendance/Dept/Batch/Sec/Date
#     ref = db.reference(f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}")
    
#     # Update individual student records without overwriting other periods
#     for roll, info in d['records'].items():
#         ref.child(roll).update({
#             "name": info['name'],
#             d['period']: info['status'] # e.g., P1: "P", P2: "A"
#         })
        
#     return jsonify({"status": "success"})


@app.route('/api/submit_attendance', methods=['POST'])
def submit_attendance():
    d = request.json
    date_str, _, _ = get_ist_info()
    
    # Path: Attendance/Dept/Batch/Sec/Date
    ref = db.reference(f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}")
    
    # We get the subject name from the request sent by the frontend
    subject_name = d.get('subject', 'N/A')
    
    # Update individual student records
    for roll, info in d['records'].items():
        # Option A: Save as a nested object (Recommended for cleaner data)
        # Result: P4: { "status": "P", "subject": "Deep Learning" }
        ref.child(roll).update({
            "name": info['name'],
            d['period']: {
                "status": info['status'],
                "subject": subject_name
            }
        })
        
    return jsonify({"status": "success"})

# --- ADMIN SECTION ---

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_stats.html')

@app.route('/api/admin/get_structure')
def get_structure():
    # Fetch student tree to build dynamic dropdowns (Dept > Batch > Sec)
    return jsonify(db.reference('Students').get() or {})

# @app.route('/api/admin/get_report')
# def get_report():
#     dept = request.args.get('dept')
#     batch = request.args.get('batch')
#     sec = request.args.get('sec')
#     date = request.args.get('date')
    
#     students = db.reference(f"Students/{dept}/{batch}/{sec}").get() or {}
#     attendance = db.reference(f"Attendance/{dept}/{batch}/{sec}/{date}").get() or {}
    
#     report_data = []
#     for roll, info in students.items():
#         report_data.append({
#             'roll': roll,
#             'name': info.get('name'),
#             'attendance': attendance.get(roll, {}) 
#         })
#     return jsonify(report_data)

@app.route('/api/admin/get_report')
def get_report():
    dept = request.args.get('dept')
    batch = request.args.get('batch')
    sec = request.args.get('sec')
    date = request.args.get('date')

    # 1. Fetch Students
    students = db.reference(f"Students/{dept}/{batch}/{sec}").get() or {}
    # 2. Fetch Attendance (Correct path based on your submit_attendance route)
    attendance_data = db.reference(f"Attendance/{dept}/{batch}/{sec}/{date}").get() or {}
    
    report_data = []
    for roll, info in students.items():
        # Each student row contains their roll, name, and the P1-P8 object from Firebase
        report_data.append({
            'roll': roll,
            'name': info.get('name'),
            'attendance': attendance_data.get(roll, {}) 
        })
    return jsonify(report_data)

@app.route('/api/admin/get_student_cumulative_stats')
def get_student_cumulative_stats():
    target_roll = request.args.get('roll')
    if not target_roll:
        return jsonify({"error": "Roll number required"}), 400

    try:
        # Structure: Attendance / Dept / Batch / Sec / Date / Roll / Period
        attendance_ref = db.reference('Attendance')
        all_data = attendance_ref.get() or {}
        subject_map = {}

        for dept, batches in all_data.items():
            for batch, sections in batches.items():
                for sec, dates in sections.items():
                    for date, rolls in dates.items():
                        if target_roll in rolls:
                            student_day_data = rolls[target_roll]
                            # Iterate P1 to P8
                            for i in range(1, 9):
                                p_key = f'P{i}'
                                if p_key in student_day_data:
                                    p_info = student_day_data[p_key]
                                    sub_name = p_info.get('subject', 'General')
                                    status = p_info.get('status')

                                    if sub_name not in subject_map:
                                        subject_map[sub_name] = {"attended": 0, "total": 0}
                                    
                                    subject_map[sub_name]["total"] += 1
                                    if status in ['P', 'Present']:
                                        subject_map[sub_name]["attended"] += 1

        return jsonify(subject_map)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # host='0.0.0.0' allows access from any device on the same local network
    app.run(debug=True, host='0.0.0.0', port=5000)