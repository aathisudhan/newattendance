import firebase_admin
from firebase_admin import credentials, db

# 1. Setup Firebase Admin
cred = credentials.Certificate("serviceAccountKey.json") 
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://newattendance-39e26-default-rtdb.asia-southeast1.firebasedatabase.app'
})

def seed_faculty():
    # Consolidated unique list from all provided data
    raw_staff_names = [
        # AI&DS Core & Subject Handling
        "DR. S. MALATHI", "DR. I. THAMARAI", "DR. A. JOSHI", "DR. K. JAYASHREE", 
        "DR. S. CHAKARAVARTHI", "DR. W.GRACY THERESA", "DR. T. KALAICHELVI", 
        "DR. S. KALAIMAGAL", "DR. P. KAVITHA", "DR. N. SIVAKUMAR", 
        "DR. C. GNANAPRAKASAM", "MRS. S. VIMALA", "DR. C. BHARANIDHARAN", 
        "DR. M. S. MAHARAJAN", "DR. E. BHUVANESWARI", "DR. MARIA MANUEL VIANNY", 
        "DR. S. RENUGA", "DR. T. VEERAMANI", "DR. S. LEELAVATHY", "DR. C. VIVEK", 
        "DR. D S SHAJI", "DR. T. SELVABANUPRIYA", "DR. M. VIDHYASREE", 
        "DR. V. MAHAVAISHNAVI", "DR. B. CHITRA", "DR. V. RATHINAPRIYA", 
        "MRS. R. PRIYA", "MR. P. BALAJI", "MRS. D. AISHWARYA", "MRS. K. MALVIKA", 
        "MR. M. VETRI SELVAN", "MRS. S. SRINIDHI", "MRS. S. SWATHI", 
        "MRS. C. GOMATHI", "MRS. J. ANITHA", "MS. R. S. ANURADHA", 
        "MRS. S. DHIVYA", "MR. M.VENKATESAN", "MR. G. SAISANJAY", 
        "MR. P. KALIAPPAN", "MRS. P. MISBA MARYBAI", "MR. K. VIJAYAKUMAR", 
        "MS. P. SHYAMALA", "MRS. M. MEGALA", "MR. S. SURESH", "MR. S. ARULANANDAN", 
        "MRS. P. RANJIDHA", "MRS. K. ANUSIYA", "MRS. R. VIDHYA MUTHULAKSHMI", 
        "MRS. B. BALA ABIRAMI", "MRS. K. SARANYA", "MRS. K. TAMILSELVI", 
        "MRS. V. REKHA", "MRS. C. M. HILDA JERLIN", "MRS. A. V. ADLIN GRACE", 
        "MS. S. SANDHIYA", "MS. M. POVANESWARI", "MR. S. DINESH", "MRS. A. DIVYA", 
        "MR. C. P. RONALD REGAN", "MR. M. PRASANTH", "MR. M. SADHASIVAM", 
        "MRS. R. GLORY SANGEETHA", "MRS. R. VASANTHI", "MRS. K. SUGANYA", 
        "MR. K. DEEPAK KUMAR", "MR. I. NOOR MOHAMED", "MRS. V. PRIYA", 
        "MRS. S. PADMA PRIYA", "MR. A. SANKARAN", "MR. J. STEPHAN", "MR. R. SELVAM", 
        "MRS. S. MAHALAKSHMI", "MR. R. RAJALINGAM", "MRS. G. YASIKA", 
        "MR. A. VIJAYA MAHENDRA VARMAN",
        # First Year Faculty
        "MRS. A.BABISHA", "MRS. B.NARMADA", "MS. K CHARULATHA", "MRS. D KALAIMANI", 
        "MRS. P AMBIGA", "MR. V SIVAKUMAR", "MR. KRISHNA HARIHARAN L", "MR. S. VIGNESH",
        # Names from original list for completeness
        "DR. A. THIRUPATHI", "DR. E. JANAKI", "DR. R. JEGAN", "MS. KARTHIKA", 
        "MRS. SENTAHAMILDASAN", "MRS. YASHIKA", "MR. SENTHAMIZHDASAN", "MRS. YAHIKA", 
        "MRS. TAMILSELVI", "DR. THAMARAI"
    ]

    # Clean duplicates and sort alphabetically
    unique_staff = sorted(list(set([name.strip().upper() for name in raw_staff_names])))
    total_unique = len(unique_staff)

    print("-" * 65)
    print(f"REPORT: {total_unique} Unique Staff Names Extracted")
    print("-" * 65)

    faculty_node = {}
    current_id_num = 101

    for name in unique_staff:
        faculty_id = f"F{current_id_num}"
        
        # Displaying the exact format requested for management
        print(f"faculty id: {faculty_id} name: {name} password: {faculty_id}")
        
        faculty_node[faculty_id] = {
            "name": name,
            "dept": "AI&DS",
            "password": faculty_id
        }
        current_id_num += 1

    # Update to Firebase
    db.reference('Faculty').update(faculty_node)
    
    print("-" * 65)
    print(f"✅ Database Update Complete. {total_unique} Faculty members registered.")

if __name__ == "__main__":
    seed_faculty()