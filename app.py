import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import pytz
import traceback

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "pec_attendance_system_2026")

# DEBUG ENABLE
app.config['PROPAGATE_EXCEPTIONS'] = True


# 🔥 GLOBAL ERROR HANDLER (VERY IMPORTANT)
@app.errorhandler(Exception)
def handle_exception(e):
    print("🔥 ERROR OCCURRED:")
    traceback.print_exc()
    return "Internal Server Error - Check Terminal", 500


# --- FIREBASE SETUP ---
# --- FIREBASE SETUP ---
if not firebase_admin._apps:
    try:
        service_account_info = os.getenv('FIREBASE_SERVICE_ACCOUNT')

        if service_account_info:
            # Clean potential hidden wrapping quotes from Vercel env vars
            service_account_info = service_account_info.strip()
            if service_account_info.startswith('"') and service_account_info.endswith('"'):
                service_account_info = service_account_info[1:-1]
            
            key_dict = json.loads(service_account_info)

            if "private_key" in key_dict:
                # Fixes the JWT Signature error
                key_dict["private_key"] = key_dict["private_key"].replace('\\n', '\n')

            cred = credentials.Certificate(key_dict)
        else:
            # Local fallback
            cred = credentials.Certificate("serviceAccountKey.json")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
        print("✅ Firebase Connected Successfully")

    except Exception as e:
        print("🔥 CRITICAL: Firebase Initialization Failed!")
        traceback.print_exc()


# --- IST TIME ---
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

    print("LOGIN:", uid, role)

    # ADMIN
    if role == 'admin' and uid == 'admin' and pwd == 'admin':
        session['user'] = 'admin'
        session['role'] = 'admin'
        session['name'] = 'Administrator'
        session['dept'] = 'System'
        return redirect('/admin')

    # FACULTY
    if role == 'faculty':
        f_data = db.reference(f'Faculty/{uid}').get()
        print("FACULTY DATA:", f_data)

        if f_data and str(f_data.get('password')) == str(pwd):
            session['user'] = uid
            session['role'] = 'faculty'
            session['name'] = f_data.get('name', 'Professor')
            session['dept'] = f_data.get('dept', 'General')
            return redirect('/faculty')

    return "Login Failed"


@app.route('/faculty')
def faculty_page():
    print("SESSION:", session)

    if session.get('role') != 'faculty':
        return redirect('/')

    try:
        _, day_str, current_time = get_ist_info()
        timetable = db.reference('Timetable').get()

        print("TIMETABLE:", timetable)

        assigned_slots = []

        if not isinstance(timetable, dict):
            return render_template('faculty_mark.html', slots=[])

        current_user = str(session.get('user') or "").lower()

        for dept, batches in timetable.items():
            if not isinstance(batches, dict):
                continue

            for batch, years in batches.items():
                if not isinstance(years, dict):
                    continue

                for year_label, sections in years.items():
                    if not isinstance(sections, dict):
                        continue

                    # CASE 1: Day directly
                    if day_str in sections:
                        process_slots(
                            sections[day_str], dept, batch, year_label,
                            assigned_slots, current_time, current_user
                        )
                    else:
                        # CASE 2: Section -> Day
                        for sec, days in sections.items():
                            if isinstance(days, dict) and day_str in days:
                                process_slots(
                                    days[day_str], dept, batch, sec,
                                    assigned_slots, current_time, current_user
                                )

        print("SLOTS:", assigned_slots)

        return render_template('faculty_mark.html', slots=assigned_slots)

    except Exception:
        traceback.print_exc()
        return "Faculty Page Error", 500


def process_slots(day_data, dept, batch, sec, assigned_slots, current_time, current_user):
    if not isinstance(day_data, dict):
        return

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
                        'subject': info.get('subject') or 'N/A',
                        'time': time_str
                    })

            except Exception as e:
                print("Time Error:", e)


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

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Server error"}), 500


@app.route('/api/submit_attendance', methods=['POST'])
def submit_attendance():
    try:
        d = request.json
        date_str, _, _ = get_ist_info()

        ref = db.reference(f"Attendance/{d['dept']}/{d['batch']}/{d['sec']}/{date_str}")

        for roll, info in d['records'].items():
            ref.child(roll).update({
                "name": info.get('name'),
                d['period']: {
                    "status": info.get('status'),
                    "subject": d.get('subject', 'N/A')
                }
            })

        return jsonify({"status": "success"})

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Failed"}), 500


@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template('admin_stats.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
