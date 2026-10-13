# 🩺 Nexus Health - Patient Appointment Booking Platform

A clean, modern patient appointment booking web application built using **Python (Flask)** and **SQLite**, designed with rich healthcare aesthetics and an innovative **Smart Clinical Triage & Digital Boarding Pass** creative feature.

---

## 🌟 Key Features

1. **Simple & Intuitive Appointment Booking**:
   - Choose from pre-configured clinic specialists (Cardiologist, Dermatologist, Orthopedic, Pediatrician, Neurologist, General Physician).
   - Select appointment date with real-time dynamic slot availability (9:00 AM – 4:30 PM).
   - Intelligent slot conflict prevention (locks booked slots in SQLite in real time).

2. **Creative Feature: Smart Clinical Triage & Digital Pass**:
   - **Interactive Symptom Triage**: As the patient types symptoms or clicks quick tags (e.g., *"Chest Discomfort"*, *"Skin Rash & Itch"*, *"Persistent Migraine"*), the system dynamically evaluates clinical urgency (`Urgent Care`, `Priority Consultation`, `Routine Care`) and suggests the best-suited specialist with a 1-click **"Auto-Select This Doctor"** feature.
   - **Digital Appointment Boarding Pass**: Upon confirmation, patients receive an Apple Wallet-style digital pass featuring complete doctor and room details, official reference code, and 1-click **Add to Calendar (.ics)** download.

3. **Appointment Management Dashboard**:
   - Real-time search across all booked appointments by patient name, booking reference (`MED-XXXX-MMDD`), or phone number.
   - Filter by status (`Confirmed`, `Completed`, `Cancelled`).
   - Direct status updates (Mark as Completed or Cancel appointment).

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- Flask & qrcode (already installed in your environment)

### 2. Launch the Application
Run the Flask server with:
```bash
py app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```
Appointment system/
├── app.py                      # Flask routes, triage logic, and SQLite database handlers
├── appointments.db             # SQLite database storing doctors and appointments
├── requirements.txt            # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css           # Premium medical styling & responsive design system
│   └── js/
│       └── main.js             # Real-time slot fetching & dynamic triage interactivity
└── templates/
    ├── base.html               # Shared layout, navigation bar, and alerts
    ├── book.html               # Patient booking form with live triage engine
    ├── pass.html               # Digital Boarding Pass with calendar export (.ics)
    └── appointments.html       # Clinic directory & appointment status manager
```
