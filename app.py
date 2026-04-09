import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pec_attendance_system_2026")

# Debug (VERY IMPORTANT for error tracing)
app.config['PROPAGATE_EXCEPTIONS'] = True


# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    service_account_info = os.getenv('FIREBASE_SERVICE_ACCOUNT')

    try:
        if service_account_info:
            key_dict = json.loads(service_account_info)

            # Fix newline issue (Vercel fix)
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace('\\n', '\n')

            cred = credentials.Certificate(key_dict)
            print("✅ Firebase Loaded from ENV")

        else:
            cred = credentials.Certificate("serviceAccountKey.json")
            print("✅ Firebase Loaded from Local File")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app'
        })

    except Exception as e:
        print(f"🔥 Firebase Init Error: {e}")


# --- IST TIME HELPER ---
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
    try:
        uid = request.form.get('username', '').strip()
        pwd = request.form.get('password', '').strip()
        role = request.form.get('role')

        # ADMIN LOGIN
        if role == 'admin' and uid == 'admin' and pwd == 'admin':
            session.update({
                'user': 'admin',
                'role': 'admin',
                'name': 'Administrator',
                'dept': 'System'
            })
            return redirect(url_for('admin_page'))

        # FACULTY LOGIN
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

        return "Login Failed"

    except Exception as e:
        print(f"Login Error: {e}")
        return "Internal Server Error", 500


@app.route('/faculty')
def faculty_page():
    try:
        if session.get('role') != 'faculty':
            return redirect(url_for('index'))

        _, day_str, current_time = get_ist_info()
        timetable = db.reference('Timetable').get()

        if not isinstance(timetable, dict):
            return render_template('faculty_mark.html', slots=[])

        assigned_slots = []

        for dept, batches in timetable.items():
            if not isinstance(batches, dict):
                continue

            for batch, years in batches.items():
                if not isinstance(years, dict):
                    continue

                for year_label, sections in years.items():
                    if not isinstance(sections, dict):
                        continue

                    # Case 1: Day directly inside
                    if day_str in sections:
                        process_slots(sections[day_str], dept, batch, year_label, assigned_slots, current_time)
                    else:
                        # Case 2: Section -> Day
                        for sec, days in sections.items():
                            if isinstance(days, dict) and day_str in days:
                                process_slots(days[day_str], dept, batch, sec, assigned_slots, current_time)

        return render_template('faculty_mark.html', slots=assigned_slots)

    except Exception as e:
        print(f"🔥 Faculty Page Error: {e}")
        return "Internal Server Error", 500


def process_slots(day_data, dept, batch, sec, assigned_slots, current_time):
    if not isinstance(day_data, dict):
        return

    current_user = str(session.get('user') or "").lower()

    for period, info in day_data.items():
        if not isinstance(info, dict):
            continue

        faculty_name = str(info.get('faculty') or "").lower()

        if faculty_name == current_user:
            try:
                time_str = info.get('time')

                if not time_str or '-' not in time_str:
                    continue

                start_str, end_str = time_str.split('-')

                start = datetime.strptime(start_str.strip(), "%H:%M").time()
                end = datetime.strptime(end_str.strip(), "%H:%M").time()

                if start <= current_time <= end:
                    assigned_slots.append({
                        'dept': dept,
                        'batch': batch,
                        'sec': sec,
                        'period': period,
                        'subject': info.get('subject', 'N/A'),
                        'time': time_str
                    })

            except Exception as e:
                print(f"Time Error: {e}")


# --- API ---

@app.route('/api/get_students')
def get_students():
    try:
        dept = request.args.get('dept')
        batch = request.args.get('batch')
        sec = request.args.get('sec')

        path = f"Students/{dept}/{batch}/{sec}"
        data = db.reference(path).get()

        return jsonify(data if data else {})

    except Exception as e:
        print(f"Get Students Error: {e}")
        return jsonify({"error": "Server error"}), 500


@app.route('/api/submit_attendance', methods=['POST'])
def submit_attendance():
    try:
        d = request.json
        date_str, _, _ = get_ist_info()

        ref_path = f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}"
        ref = db.reference(ref_path)

        subject_name = d.get('subject', 'N/A')

        for roll, info in d['records'].items():
            ref.child(roll).update({
                "name": info.get('name'),
                d['period']: {
                    "status": info.get('status'),
                    "subject": subject_name
                }
            })

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"Submit Error: {e}")
        return jsonify({"error": str(e)}), 500


# --- ADMIN ---

@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return render_template('admin_stats.html')


@app.route('/api/admin/get_structure')
def get_structure():
    try:
        data = db.reference('Students').get()
        return jsonify(data if data else {})
    except Exception as e:
        print(f"Structure Error: {e}")
        return jsonify({})


@app.route('/api/admin/get_report')
def get_report():
    try:
        dept = request.args.get('dept')
        batch = request.args.get('batch')
        sec = request.args.get('sec')
        date = request.args.get('date')

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

    except Exception as e:
        print(f"Report Error: {e}")
        return jsonify([])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# --- RUN ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
