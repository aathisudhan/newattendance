import firebase_admin
from firebase_admin import credentials, db

# 1. Setup Firebase Admin
# Make sure serviceAccountKey.json is in the parent directory or the same folder
cred = credentials.Certificate("serviceAccountKey.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app' # REPLACE THIS
})

def seed_database():
    print("🚀 Starting Database Seeding...")

    # --- 1. FACULTY DATA ---
    # Node: Faculty/ID
    faculty_data = {
        "F001": {
            "name": "Dr. Vetri Selvan",
            "dept": "AI&DS",
            "password": "123"
        },
        "F002": {
            "name": "Prof. Suresh S",
            "dept": "AI&DS",
            "password": "123"
        }
    }
    db.reference("Faculty").set(faculty_data)
    print("✅ Faculty uploaded.")

    # --- 2. STUDENT DATA ---
    # Node: Students/Dept/Batch/Section/RollNo
    student_data = {
        "AI&DS": {
            "2027": {
                "A": {
                    "23AD101": {"name": "Arun Kumar", "password": "123", "reg_no": "2023PECAI101"},
                    "23AD102": {"name": "Bhavana R", "password": "123", "reg_no": "2023PECAI102"},
                    "23AD103": {"name": "Chandru M", "password": "123", "reg_no": "2023PECAI103"},
                    "23AD104": {"name": "Dinesh K", "password": "123", "reg_no": "2023PECAI104"},
                    "23AD105": {"name": "Ezhil V", "password": "123", "reg_no": "2023PECAI105"}
                },
                "B": {
                    "23AD201": {"name": "Fahad Khan", "password": "123", "reg_no": "2023PECAI201"},
                    "23AD202": {"name": "Gokul N", "password": "123", "reg_no": "2023PECAI202"},
                    "23AD203": {"name": "Harini S", "password": "123", "reg_no": "2023PECAI203"},
                    "23AD204": {"name": "Ishwar P", "password": "123", "reg_no": "2023PECAI204"},
                    "23AD205": {"name": "Janani T", "password": "123", "reg_no": "2023PECAI205"}
                }
            }
        }
    }
    db.reference("Students").set(student_data)
    print("✅ Student database (Sections A & B) uploaded.")

    # --- 3. TIMETABLE DATA ---
    # Node: Timetable/Dept/Batch/YearLevel/Section/Day/Period
    # We will map Dr. Vetri (F001) to several periods across A and B sections
    timetable_data = {
        "AI&DS": {
            "2027": {
                "Year III": {
                    "A": {
                        "Monday": {
                            "P1": {"subject": "Artificial Intelligence", "faculty": "F001", "time": "08:30-09:20"},
                            "P2": {"subject": "Data Science", "faculty": "F002", "time": "09:20-10:10"},
                            "P3": {"subject": "Machine Learning", "faculty": "F001", "time": "10:30-11:20"},
                            "P4": {"subject": "Cloud Computing", "faculty": "F002", "time": "11:20-12:10"},
                            "P5": {"subject": "AI Lab", "faculty": "F001", "time": "01:00-01:50"},
                            "P6": {"subject": "AI Lab", "faculty": "F001", "time": "01:50-02:40"},
                            "P7": {"subject": "Library", "faculty": "F001", "time": "02:40-03:30"},
                            "P8": {"subject": "Counseling", "faculty": "F002", "time": "03:30-04:20"}
                        },
                        "Wednesday": { # Testing for today
                            "P1": {"subject": "Deep Learning", "faculty": "F001", "time": "08:30-09:20"},
                            "P2": {"subject": "Ethics in AI", "faculty": "F001", "time": "09:20-10:10"},
                            "P4": {"subject": "Testing Now", "faculty": "F001", "time": "16:00-17:00"}
                        }
                    },
                    "B": {
                        "Monday": {
                            "P1": {"subject": "Computer Networks", "faculty": "F002", "time": "08:30-09:20"},
                            "P2": {"subject": "Artificial Intelligence", "faculty": "F001", "time": "09:20-10:10"}
                        },
                        "Wednesday": { # Testing for today
                            "P3": {"subject": "Big Data", "faculty": "F001", "time": "10:30-11:20"}
                        }
                    }
                }
            }
        }
    }
    db.reference("Timetable").set(timetable_data)
    print("✅ Temporary Timetable (8 Periods) uploaded.")
    print("\n🎉 All set! You can now login with F001 / 123 as Faculty.")

if __name__ == "__main__":
    seed_database()