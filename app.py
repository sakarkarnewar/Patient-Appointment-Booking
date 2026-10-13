import os
import sqlite3
import uuid
import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
import qrcode
import qrcode.image.svg

app = Flask(__name__)
app.secret_key = "super-secret-clinic-key-appointment-system"
DB_PATH = os.path.join(os.path.dirname(__file__), "appointments.db")

# ----------------- DATABASE HELPERS -----------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Doctors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                qualification TEXT NOT NULL,
                room_number TEXT NOT NULL,
                consultation_fee INTEGER NOT NULL,
                avatar_color TEXT NOT NULL,
                bio TEXT,
                experience_years INTEGER DEFAULT 10
            )
        """)
        
        # Appointments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_ref TEXT UNIQUE NOT NULL,
                patient_name TEXT NOT NULL,
                patient_email TEXT NOT NULL,
                patient_phone TEXT NOT NULL,
                doctor_id INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                symptoms TEXT,
                triage_level TEXT DEFAULT 'Routine',
                triage_badge TEXT DEFAULT 'badge-routine',
                triage_notes TEXT,
                status TEXT DEFAULT 'Confirmed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            )
        """)
        
        # Seed doctors if table is empty
        cursor.execute("SELECT COUNT(*) FROM doctors")
        if cursor.fetchone()[0] == 0:
            doctors_data = [
                (
                    "Dr. Sarah Jenkins",
                    "General Physician",
                    "MD, Internal Medicine (Johns Hopkins)",
                    "Suite 102 - Ground Floor",
                    60,
                    "#0ea5e9",
                    "Comprehensive primary care, seasonal flu, health checkups, and chronic disease management.",
                    12
                ),
                (
                    "Dr. Marcus Vance",
                    "Cardiologist",
                    "MD, FACC - Cardiovascular Specialist",
                    "Heart Wing, Suite 305",
                    120,
                    "#e11d48",
                    "Heart rhythm diagnostics, hypertension management, cholesterol care, and preventative cardiology.",
                    16
                ),
                (
                    "Dr. Elena Rostova",
                    "Dermatologist",
                    "MD, Board Certified Dermatologist",
                    "Aesthetics & Skin Clinic, Suite 204",
                    90,
                    "#8b5cf6",
                    "Skin allergies, acne, eczema, dermatitis, mole screenings, and corrective skin therapies.",
                    9
                ),
                (
                    "Dr. Daniel Chen",
                    "Orthopedic Specialist",
                    "MS Orthopedics, Sports Medicine Fellow",
                    "Bone & Joint Center, Suite 110",
                    100,
                    "#10b981",
                    "Joint pain, sports injury rehabilitation, fracture care, arthritis, and spine mobility.",
                    14
                ),
                (
                    "Dr. Priya Sharma",
                    "Pediatrician",
                    "MD Pediatrics, Child Health Specialist",
                    "Children's Care Zone, Suite 108",
                    75,
                    "#f59e0b",
                    "Infant and adolescent wellness, vaccinations, pediatric infections, and developmental growth.",
                    11
                ),
                (
                    "Dr. Robert Hayes",
                    "Neurologist",
                    "MD, PhD Clinical Neurology",
                    "Neuroscience Wing, Suite 402",
                    130,
                    "#6366f1",
                    "Migraines, nerve conditions, sleep disturbances, tremors, and cognitive assessments.",
                    18
                )
            ]
            cursor.executemany("""
                INSERT INTO doctors (name, specialty, qualification, room_number, consultation_fee, avatar_color, bio, experience_years)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, doctors_data)
        
        conn.commit()

# Available standard slots
STANDARD_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "02:00 PM", "02:30 PM",
    "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM"
]

# ----------------- CREATIVE FEATURE: SMART TRIAGE ENGINE -----------------

TRIAGE_RULES = [
    {
        "keywords": ["chest pain", "heart", "palpitation", "shortness of breath", "high blood pressure", "hypertension", "angina", "irregular heartbeat"],
        "specialty": "Cardiologist",
        "level": "Urgent Care",
        "badge": "badge-urgent",
        "notes": "Cardiovascular indicators flagged. Recommended to see Cardiology promptly."
    },
    {
        "keywords": ["skin", "rash", "itching", "acne", "mole", "eczema", "hives", "dermatitis", "dry skin", "blister"],
        "specialty": "Dermatologist",
        "level": "Routine Care",
        "badge": "badge-routine",
        "notes": "Dermatological symptom identified. Recommended specialist: Dermatology."
    },
    {
        "keywords": ["joint", "knee", "bone", "back pain", "fracture", "shoulder", "ankle", "sprain", "arthritis", "hip pain", "swollen joint"],
        "specialty": "Orthopedic Specialist",
        "level": "Priority Consultation",
        "badge": "badge-priority",
        "notes": "Musculoskeletal strain or joint concern. Recommended specialist: Orthopedics."
    },
    {
        "keywords": ["child", "baby", "infant", "toddler", "pediatric", "vaccine", "measles", "teething"],
        "specialty": "Pediatrician",
        "level": "Routine Care",
        "badge": "badge-routine",
        "notes": "Pediatric care case. Child health specialist recommended."
    },
    {
        "keywords": ["headache", "migraine", "dizziness", "numbness", "seizure", "tingling", "vertigo", "concussion", "memory"],
        "specialty": "Neurologist",
        "level": "Priority Consultation",
        "badge": "badge-priority",
        "notes": "Neurological patterns identified. Recommended specialist: Neurology."
    },
    {
        "keywords": ["fever", "cough", "cold", "flu", "sore throat", "fatigue", "general", "stomach", "nausea", "vomiting", "weakness"],
        "specialty": "General Physician",
        "level": "Standard Care",
        "badge": "badge-routine",
        "notes": "General illness indicators. Recommended primary care physician evaluation."
    }
]

def analyze_symptoms(text):
    text_lower = (text or "").lower()
    if not text_lower.strip():
        return {
            "matched_specialty": None,
            "level": "Routine",
            "badge": "badge-routine",
            "notes": "General routine checkup.",
            "recommended_doctor_id": None
        }

    matched_rule = None
    for rule in TRIAGE_RULES:
        for kw in rule["keywords"]:
            if kw in text_lower:
                matched_rule = rule
                break
        if matched_rule:
            break

    if not matched_rule:
        matched_rule = {
            "specialty": "General Physician",
            "level": "Routine Care",
            "badge": "badge-routine",
            "notes": "Symptoms suggest primary evaluation by our General Physician."
        }

    # Find doctor with matched specialty
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM doctors WHERE specialty = ? LIMIT 1", (matched_rule["specialty"],))
        doc = cursor.fetchone()
        doc_id = doc["id"] if doc else None
        doc_name = doc["name"] if doc else None

    return {
        "matched_specialty": matched_rule["specialty"],
        "level": matched_rule["level"],
        "badge": matched_rule["badge"],
        "notes": matched_rule["notes"],
        "recommended_doctor_id": doc_id,
        "recommended_doctor_name": doc_name
    }


# ----------------- ROUTES -----------------

@app.route("/")
def index():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM doctors ORDER BY id ASC")
        doctors = cursor.fetchall()
    
    # default min date is today
    today_str = datetime.date.today().isoformat()
    return render_template("book.html", doctors=doctors, min_date=today_str, slots=STANDARD_SLOTS)

@app.route("/api/triage", methods=["POST"])
def api_triage():
    data = request.get_json() or {}
    symptoms = data.get("symptoms", "")
    analysis = analyze_symptoms(symptoms)
    return jsonify(analysis)

@app.route("/api/available-slots")
def available_slots():
    doctor_id = request.args.get("doctor_id", type=int)
    date_str = request.args.get("date", "")
    
    if not doctor_id or not date_str:
        return jsonify({"slots": STANDARD_SLOTS, "booked": []})
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT time_slot FROM appointments
            WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled'
        """, (doctor_id, date_str))
        booked_rows = cursor.fetchall()
        booked_slots = [r["time_slot"] for r in booked_rows]
    
    available = [slot for slot in STANDARD_SLOTS if slot not in booked_slots]
    return jsonify({
        "all_slots": STANDARD_SLOTS,
        "booked_slots": booked_slots,
        "available_slots": available
    })

@app.route("/book", methods=["POST"])
def book_appointment():
    patient_name = request.form.get("patient_name", "").strip()
    patient_email = request.form.get("patient_email", "").strip()
    patient_phone = request.form.get("patient_phone", "").strip()
    doctor_id = request.form.get("doctor_id", type=int)
    appointment_date = request.form.get("appointment_date", "").strip()
    time_slot = request.form.get("time_slot", "").strip()
    symptoms = request.form.get("symptoms", "").strip()
    
    if not all([patient_name, patient_email, patient_phone, doctor_id, appointment_date, time_slot]):
        flash("Please fill in all required fields before confirming your appointment.", "danger")
        return redirect(url_for("index"))
    
    # Check date isn't past
    try:
        app_date_obj = datetime.date.fromisoformat(appointment_date)
        if app_date_obj < datetime.date.today():
            flash("Appointment date cannot be in the past.", "danger")
            return redirect(url_for("index"))
    except ValueError:
        flash("Invalid date format selected.", "danger")
        return redirect(url_for("index"))

    # Triage analysis
    triage_result = analyze_symptoms(symptoms)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check slot conflict
        cursor.execute("""
            SELECT id FROM appointments
            WHERE doctor_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'
        """, (doctor_id, appointment_date, time_slot))
        existing = cursor.fetchone()
        
        if existing:
            flash("The selected slot was just booked by another patient! Please pick another slot.", "warning")
            return redirect(url_for("index"))
        
        # Unique booking reference: e.g. APT-8924-X
        random_suffix = uuid.uuid4().hex[:4].upper()
        booking_ref = f"MED-{random_suffix}-{datetime.date.today().strftime('%m%d')}"
        
        cursor.execute("""
            INSERT INTO appointments (
                booking_ref, patient_name, patient_email, patient_phone,
                doctor_id, appointment_date, time_slot, symptoms,
                triage_level, triage_badge, triage_notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed')
        """, (
            booking_ref, patient_name, patient_email, patient_phone,
            doctor_id, appointment_date, time_slot, symptoms,
            triage_result["level"], triage_result["badge"], triage_result["notes"]
        ))
        conn.commit()
    
    flash("Appointment booked successfully! Here is your digital boarding pass.", "success")
    return redirect(url_for("view_pass", booking_ref=booking_ref))

@app.route("/pass/<booking_ref>")
def view_pass(booking_ref):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, d.name as doctor_name, d.specialty, d.qualification, d.room_number, d.consultation_fee
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.booking_ref = ?
        """, (booking_ref,))
        appointment = cursor.fetchone()
    
    if not appointment:
        flash("Appointment not found or expired.", "danger")
        return redirect(url_for("index"))
    
    return render_template("pass.html", appointment=appointment)

@app.route("/appointments")
def list_appointments():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    
    query = """
        SELECT a.*, d.name as doctor_name, d.specialty, d.room_number
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (a.patient_name LIKE ? OR a.booking_ref LIKE ? OR a.patient_phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    
    if status_filter:
        query += " AND a.status = ?"
        params.append(status_filter)
        
    query += " ORDER BY a.appointment_date DESC, a.time_slot DESC"
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        appointments = cursor.fetchall()
        
    return render_template("appointments.html", appointments=appointments, search=search, status_filter=status_filter)

@app.route("/appointments/cancel/<int:app_id>", methods=["POST"])
def cancel_appointment(app_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?", (app_id,))
        conn.commit()
    flash("Appointment has been cancelled successfully.", "info")
    return redirect(request.referrer or url_for("list_appointments"))

@app.route("/appointments/complete/<int:app_id>", methods=["POST"])
def complete_appointment(app_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE appointments SET status = 'Completed' WHERE id = ?", (app_id,))
        conn.commit()
    flash("Appointment marked as completed.", "success")
    return redirect(request.referrer or url_for("list_appointments"))

@app.route("/download-ics/<booking_ref>")
def download_ics(booking_ref):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, d.name as doctor_name, d.specialty, d.room_number
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.booking_ref = ?
        """, (booking_ref,))
        app_data = cursor.fetchone()
    
    if not app_data:
        return "Appointment not found", 404
        
    # Construct iCalendar (.ics) format
    date_parts = app_data["appointment_date"].split("-")
    time_str = app_data["time_slot"]
    
    # parse time e.g. "09:30 AM"
    time_part, ampm = time_str.split(" ")
    hour, minute = [int(x) for x in time_part.split(":")]
    if ampm == "PM" and hour < 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0
        
    start_dt = datetime.datetime(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]), hour, minute)
    end_dt = start_dt + datetime.timedelta(minutes=30)
    
    dtstamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")
    
    summary = f"Doctor Appointment: {app_data['doctor_name']} ({app_data['specialty']})"
    location = f"{app_data['room_number']}, Nexus Health Medical Center"
    description = f"Patient: {app_data['patient_name']}\\nBooking Reference: {app_data['booking_ref']}\\nSymptoms: {app_data['symptoms'] or 'Routine visit'}"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Nexus Health//Patient Appointment System//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{app_data['booking_ref']}@nexushealth.org
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
LOCATION:{location}
DESCRIPTION:{description}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=appointment_{booking_ref}.ics"}
    )

if __name__ == "__main__":
    init_db()
    print("Nexus Health Appointment Server is running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
