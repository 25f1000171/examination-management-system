from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Course, Examination, Rubric, Slot, Booking, Evaluation
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'emp-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



# database aur login manager initialization
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================================================


# restriction for unauthorized access
@app.before_request
def restrict_access():
    if request.path.startswith('/admin'):
        if not current_user.is_authenticated:
            flash('Login required!', 'warning')
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            flash('You are not authorized to access this page.', 'danger')
            return redirect(url_for('home'))




# programmatically database aur pre-existing admin create karne wala function
def init_db():
    with app.app_context():
        db.create_all()
        # Check karein ki Admin pehle se exist karta hai ya nahi
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            default_admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                is_approved=True,
                name='System Administrator'
            )
            db.session.add(default_admin)
            db.session.commit()
            

@app.route('/')
def home():
    return render_template('home.html')


# registration route for students and examiners

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        username = request.form.get('username').strip()
        password = request.form.get('password')
        role = request.form.get('role')

        if role not in ['student', 'examiner']:
            flash('Invalid role selected.', 'warning')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('User already exists.', 'danger')
            return redirect(url_for('register'))

        # student auto-approved h, examiner ko admin approve karega
        is_approved = True if role == 'student' else False

        new_user = User(
            name=name,
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            is_approved=is_approved
        )
        db.session.add(new_user)
        db.session.commit()

        if role == 'examiner':
            flash('Registration successful! Admin approval pending.', 'info')
        else:
            flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# login route for all users

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.role == 'examiner' and not user.is_approved:
                flash('Your examiner account is pending admin approval.', 'warning')
                return redirect(url_for('login'))

            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'examiner':
                return redirect(url_for('examiner_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')


# logout route for all users

@app.route('/logout')
def logout():
    logout_user()
    flash('You have successfully logged out.', 'info')
    return redirect(url_for('login'))



# Helper function for datetime-local inputs
def parse_datetime(dt_str):
    return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')


# ==================== ADMIN ROUTES ====================


@app.route('/admin/dashboard')
def admin_dashboard():
    q = request.args.get('q', '').strip()

    # Dashboard Summary Counts
    stats = {
        'courses': Course.query.count(),
        'exams': Examination.query.count(),
        'examiners': User.query.filter_by(role='examiner').count(),
        'students': User.query.filter_by(role='student').count(),
        'slots': Slot.query.count(),
        'bookings': Booking.query.count()
    }

    # searchbar / search filter for admin 
     
    if q:
        if q.isdigit():
            q_id = int(q)
            courses = Course.query.filter((Course.id == q_id) | (Course.name.ilike(f'%{q}%')) | (Course.course_code.ilike(f'%{q}%'))).all()
            exams = Examination.query.filter((Examination.id == q_id) | (Examination.name.ilike(f'%{q}%'))).all()
            examiners = User.query.filter_by(role='examiner').filter((User.id == q_id) | (User.name.ilike(f'%{q}%'))).all()
            students = User.query.filter_by(role='student').filter((User.id == q_id) | (User.name.ilike(f'%{q}%'))).all()
            bookings = Booking.query.filter(Booking.id == q_id).all()
        else:
            courses = Course.query.filter((Course.name.ilike(f'%{q}%')) | (Course.course_code.ilike(f'%{q}%'))).all()
            exams = Examination.query.filter(Examination.name.ilike(f'%{q}%')).all()
            examiners = User.query.filter_by(role='examiner').filter((User.name.ilike(f'%{q}%')) | (User.username.ilike(f'%{q}%'))).all()
            students = User.query.filter_by(role='student').filter((User.name.ilike(f'%{q}%')) | (User.username.ilike(f'%{q}%'))).all()
            bookings = Booking.query.join(User, Booking.student_id == User.id).filter(User.name.ilike(f'%{q}%')).all()
    else:
        courses = Course.query.all()
        exams = Examination.query.all()
        examiners = User.query.filter_by(role='examiner').all()
        students = User.query.filter_by(role='student').all()
        bookings = Booking.query.order_by(Booking.booking_date.desc()).all()

    slots = Slot.query.order_by(Slot.date.asc(), Slot.start_time.asc()).all()

    return render_template(
        'admin_dashboard.html',
        stats=stats, courses=courses, exams=exams,
        examiners=examiners, students=students,
        slots=slots, bookings=bookings, q=q
    )

# 1. Course Create, Edit, Delete
@app.route('/admin/course/new', methods=['GET', 'POST'])
def create_course():
    if request.method == 'POST':
        code = request.form.get('course_code').strip().upper()
        name = request.form.get('name').strip()
        description = request.form.get('description').strip()
        status = request.form.get('status', 'Active')

        if Course.query.filter_by(course_code=code).first():
            flash('Course code already exists!', 'danger')
            return redirect(url_for('create_course'))

        course = Course(course_code=code, name=name, description=description, status=status)
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('course_form.html', course=None)

@app.route('/admin/course/<int:id>/edit', methods=['GET', 'POST'])
def edit_course(id):
    course = Course.query.get_or_404(id)
    if request.method == 'POST':
        course.course_code = request.form.get('course_code').strip().upper()
        course.name = request.form.get('name').strip()
        course.description = request.form.get('description').strip()
        course.status = request.form.get('status')
        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('course_form.html', course=course)



@app.route('/admin/course/<int:id>/delete', methods=['POST'])
def delete_course(id):
    course = Course.query.get_or_404(id)
    if course.examinations:
        flash('Cannot delete course with existing examinations.', 'warning')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully.', 'info')
    return redirect(url_for('admin_dashboard'))

# 2. Examination Create, Edit, Delete & Status Control
@app.route('/admin/exam/new', methods=['GET', 'POST'])
def create_exam():
    courses = Course.query.filter_by(status='Active').all()
    if request.method == 'POST':
        exam = Examination(
            course_id=int(request.form.get('course_id')),
            name=request.form.get('name').strip(),
            exam_type=request.form.get('exam_type'),
            duration=int(request.form.get('duration')),
            max_marks=int(request.form.get('max_marks')),
            slot_creation_start=parse_datetime(request.form.get('slot_creation_start')),
            slot_creation_end=parse_datetime(request.form.get('slot_creation_end')),
            slot_booking_start=parse_datetime(request.form.get('slot_booking_start')),
            slot_booking_end=parse_datetime(request.form.get('slot_booking_end')),
            status=request.form.get('status', 'Draft')
        )
        db.session.add(exam)
        db.session.commit()
        flash('Examination create ho gaya! Ab aap iske Rubrics add kar sakte hain.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('exam_form.html', exam=None, courses=courses)

@app.route('/admin/exam/<int:id>/edit', methods=['GET', 'POST'])
def edit_exam(id):
    exam = Examination.query.get_or_404(id)
    courses = Course.query.all()
    if request.method == 'POST':
        exam.course_id = int(request.form.get('course_id'))
        exam.name = request.form.get('name').strip()
        exam.exam_type = request.form.get('exam_type')
        exam.duration = int(request.form.get('duration'))
        exam.max_marks = int(request.form.get('max_marks'))
        exam.slot_creation_start = parse_datetime(request.form.get('slot_creation_start'))
        exam.slot_creation_end = parse_datetime(request.form.get('slot_creation_end'))
        exam.slot_booking_start = parse_datetime(request.form.get('slot_booking_start'))
        exam.slot_booking_end = parse_datetime(request.form.get('slot_booking_end'))
        exam.status = request.form.get('status')
        db.session.commit()
        flash('Examination details aur timelines update ho gayi!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('exam_form.html', exam=exam, courses=courses)

@app.route('/admin/exam/<int:id>/status', methods=['POST'])
def update_exam_status(id):
    exam = Examination.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status in ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']:
        exam.status = new_status
        db.session.commit()
        flash(f'Exam "{exam.name}" ka status ab "{new_status}" kar diya gaya hai.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/exam/<int:id>/delete', methods=['POST'])
def delete_exam(id):
    exam = Examination.query.get_or_404(id)
    if exam.slots:
        flash('Is exam ke slots ban chuke hain, isliye delete nahi kiya ja sakta.', 'warning')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(exam)
    db.session.commit()
    flash('Examination delete kar diya gaya.', 'info')
    return redirect(url_for('admin_dashboard'))

# 3. Manage Examination Rubrics
@app.route('/admin/exam/<int:exam_id>/rubrics', methods=['GET', 'POST'])
def manage_rubrics(exam_id):
    exam = Examination.query.get_or_404(exam_id)
    if request.method == 'POST':
        criterion_name = request.form.get('criterion_name').strip()
        max_marks = int(request.form.get('max_marks'))
        weightage = float(request.form.get('weightage'))

        rubric = Rubric(
            exam_id=exam.id,
            criterion_name=criterion_name,
            max_marks=max_marks,
            weightage=weightage
        )
        db.session.add(rubric)
        db.session.commit()
        flash('Rubric criterion add ho gaya!', 'success')
        return redirect(url_for('manage_rubrics', exam_id=exam.id))

    return render_template('manage_rubrics.html', exam=exam)

@app.route('/admin/rubric/<int:id>/delete', methods=['POST'])
def delete_rubric(id):
    rubric = Rubric.query.get_or_404(id)
    exam_id = rubric.exam_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion hata diya gaya.', 'info')
    return redirect(url_for('manage_rubrics', exam_id=exam_id))

# 4. Add, Approve or Deactivate Examiners
@app.route('/admin/examiner/add', methods=['POST'])
def admin_add_examiner():
    name = request.form.get('name').strip()
    username = request.form.get('username').strip()
    password = request.form.get('password')

    if User.query.filter_by(username=username).first():
        flash('Username pehle se maujood hai!', 'danger')
        return redirect(url_for('admin_dashboard'))

    examiner = User(
        name=name,
        username=username,
        password_hash=generate_password_hash(password),
        role='examiner',
        is_approved=True
    )
    db.session.add(examiner)
    db.session.commit()
    flash(f'Examiner {name} ko add aur approve kar diya gaya!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/examiner/<int:id>/toggle', methods=['POST'])
def toggle_examiner(id):
    examiner = User.query.get_or_404(id)
    if examiner.role == 'examiner':
        examiner.is_approved = not examiner.is_approved
        db.session.commit()
        status_text = "Approved" if examiner.is_approved else "Deactivated"
        flash(f'Examiner {examiner.name} ka status {status_text} kar diya gaya.', 'info')
    return redirect(url_for('admin_dashboard'))

# 5. Reschedule Booking & Reassign Examiner
@app.route('/admin/booking/<int:id>/reschedule', methods=['GET', 'POST'])
def reschedule_booking(id):
    booking = Booking.query.get_or_404(id)
    current_slot = booking.slot
    # Usi exam ke baaki slots
    available_slots = Slot.query.filter_by(exam_id=current_slot.exam_id).all()
    approved_examiners = User.query.filter_by(role='examiner', is_approved=True).all()

    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'reschedule_slot':
            new_slot_id = int(request.form.get('new_slot_id'))
            new_slot = Slot.query.get_or_404(new_slot_id)

            if new_slot.id != current_slot.id:
                if new_slot.available_seats <= 0:
                    flash('Selected slot mein seats khali nahi hain!', 'danger')
                    return redirect(url_for('reschedule_booking', id=booking.id))

                # Purane slot ki seat wapas badhayein
                current_slot.available_seats += 1
                if current_slot.status == 'Full':
                    current_slot.status = 'Available'

                # Naye slot mein assign karein
                booking.slot_id = new_slot.id
                new_slot.available_seats -= 1
                if new_slot.available_seats == 0:
                    new_slot.status = 'Full'

                db.session.commit()
                flash('Student ki booking naye slot mein reschedule ho gayi!', 'success')
                return redirect(url_for('admin_dashboard'))

        elif action_type == 'change_examiner':
            new_examiner_id = int(request.form.get('new_examiner_id'))
            current_slot.examiner_id = new_examiner_id
            db.session.commit()
            flash('Slot ka assigned examiner successfully change kar diya gaya!', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template(
        'reschedule_booking.html',
        booking=booking,
        available_slots=available_slots,
        approved_examiners=approved_examiners
    )

@app.route('/examiner/dashboard')
def examiner_dashboard():
    return "<h1>Examiner Dashboard Connected!</h1>"

@app.route('/student/dashboard')
def student_dashboard():
    return "<h1>Student Dashboard Connected!</h1>"

if __name__ == '__main__':
    init_db()  # App run hote hi DB aur Admin automatically ban jayenge
    app.run(debug=True)