# Examination Management System (KTA)

A web application built with Flask and SQLAlchemy for managing examinations, rubrics, time slots, student bookings, and evaluations. Designed with role-based access control for **Admins**, **Examiners**, and **Students**.

---

## Features

### Admin Portal
* **Dashboard & Analytics:** Real-time summary counters for courses, examinations, examiners, students, slots, and bookings.
* **Global Search:** Search across courses, examinations, examiners, students, and bookings by name or ID.
* **Course & Examination Management:** Full CRUD operations for courses and examinations, including configurable **Slot Creation** and **Student Booking** timeline windows.
* **Rubric Configuration:** Define custom marking criteria (`criterion_name`, `max_marks`, and `weightage`) for each examination.
* **Examiner Management:** Approve or deactivate self-registered examiners, or add pre-approved examiners directly.
* **Slot & Booking Control:** Create, edit, or delete examination slots; reschedule student bookings to different slots or reassign examiners.

### Examiner Portal
* **Approval-Based Access:** Self-registration with mandatory admin approval before login.
* **Slot Management:** Create, edit, and delete slots for active examinations within the designated slot creation window (editing/deletion locks once student booking begins).
* **Student Evaluation:** View booked students per slot and submit rubric-wise marks along with overall remarks/feedback.

### Student Portal
* **Quick Registration & Profile:** Auto-approved student registration with profile and password management.
* **Slot Discovery & Booking:** Browse and search available examination slots, book seats within the booking window, and cancel bookings prior to the exam date.
* **Result Viewing:** View total obtained marks and examiner remarks once evaluated.

### Security & Access Control
* **Role-Based Route Protection:** Global `@app.before_request` middleware restricts `/admin`, `/examiner`, and `/student` routes to authenticated users with matching roles.
* **Password Hashing:** Secure password storage using `werkzeug.security`.
* **Integrity Checks:** Prevents duplicate bookings, overbooking beyond slot capacity, and deletion of courses/exams/slots with active dependencies.

---

## Tech Stack

* **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
* **Database:** SQLite (`instance/emp.db`)
* **Frontend:** HTML5, Jinja2 Templates, Bootstrap 5
* **Security:** Werkzeug Password Hashing

---

## Database Schema

The application uses SQLite managed via SQLAlchemy ORM (`models.py`):

| Model | Description |
| :--- | :--- |
| `User` | Stores Admin, Examiner, and Student accounts with roles and approval status. |
| `Course` | Academic courses with unique course codes and status. |
| `Examination` | Exams linked to courses with duration, max marks, and slot/booking timelines. |
| `Rubric` | Evaluation criteria linked to an examination (`criterion_name`, `max_marks`, `weightage`). |
| `Slot` | Scheduled exam sessions assigned to an examiner with date, time, capacity, and available seats. |
| `Booking` | Links a student to a slot and tracks status (`Booked` / `Evaluated`). |
| `Evaluation` | Stores rubric-wise `marks_obtained` and `remarks` for each student booking. |

---

## Project Structure

```text
examination-management-system/
├── app.py                  # Main Flask application & routes
├── models.py               # SQLAlchemy database models
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── instance/
│   └── emp.db              # Auto-generated SQLite database
├── static/                 # Static assets (CSS)
└── templates/              # Jinja2 HTML templates
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── examiner_dashboard.html
    ├── student_dashboard.html
    ├── course_form.html
    ├── exam_form.html
    ├── create_slot.html
    ├── edit_slot.html
    ├── examiner_create_slot.html
    ├── slot_form.html
    ├── manage_rubrics.html
    ├── evaluate_student.html
    ├── reschedule_booking.html
    ├── edit_profile.html
    └── view_result.html
```

---

## Getting Started

### Prerequisites
* Python 3.8 or higher
* `pip` package manager

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/25f1000171/examination-management-system.git
   cd examination-management-system
   ```

2. **Create and activate a virtual environment:**
   * **Windows (Git Bash):**
     ```bash
     python -m venv venv
     source venv/Scripts/activate
     ```
   * **Windows (Command Prompt / PowerShell):**
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

## Default Admin Credentials

On the first run, the database (`instance/emp.db`) and a default administrator account are created automatically:

* **Username:** `admin`
* **Password:** `admin123`

> **Note:** Change the default admin password and `SECRET_KEY` in `app.py` before deploying to production.