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

# adding new course 
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


# editing existing course
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


# deleting existing course
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


# create new examination
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
        flash('Examination was created successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('exam_form.html', exam=None, courses=courses)


# edit existing examination
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
        flash('Examination details and timelines updated successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('exam_form.html', exam=exam, courses=courses)


# status update for examination
@app.route('/admin/exam/<int:id>/status', methods=['POST'])
def update_exam_status(id):
    exam = Examination.query.get_or_404(id)
    new_status = request.form.get('status')
    if new_status in ['Draft', 'Slot Creation', 'Booking Open', 'Closed', 'Completed']:
        exam.status = new_status
        db.session.commit()
        flash(f'Status of examination "{exam.name}" updated to "{new_status}".', 'success')
    return redirect(url_for('admin_dashboard'))


# delete existing examination
@app.route('/admin/exam/<int:id>/delete', methods=['POST'])
def delete_exam(id):
    exam = Examination.query.get_or_404(id)
    if exam.slots:
        flash('Slots already exist for this examination, so it cannot be deleted.', 'warning')
        return redirect(url_for('admin_dashboard'))
    db.session.delete(exam)
    db.session.commit()
    flash('Examination deleted successfully.', 'info')
    return redirect(url_for('admin_dashboard'))


# 3. Manage Examination Rubrics

# rubric criteria 
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
        flash('Rubric criterion added successfully.', 'success')
        return redirect(url_for('manage_rubrics', exam_id=exam.id))

    return render_template('manage_rubrics.html', exam=exam)


# delete rubric criterion
@app.route('/admin/rubric/<int:id>/delete', methods=['POST'])
def delete_rubric(id):
    rubric = Rubric.query.get_or_404(id)
    exam_id = rubric.exam_id
    db.session.delete(rubric)
    db.session.commit()
    flash('Rubric criterion deleted successfully.', 'info')
    return redirect(url_for('manage_rubrics', exam_id=exam_id))



# 4. Adding, Approve or Deactivate Examiners

# adding new examiner by admin
@app.route('/admin/examiner/add', methods=['POST'])
def admin_add_examiner():
    name = request.form.get('name').strip()
    username = request.form.get('username').strip()
    password = request.form.get('password')

    if User.query.filter_by(username=username).first():
        flash('Username already exists!', 'danger')
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
    flash(f'Examiner {name} added successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


# approving or deactivating existing examiner by admin
@app.route('/admin/examiner/<int:id>/toggle', methods=['POST'])
def toggle_examiner(id):
    examiner = User.query.get_or_404(id)
    if examiner.role == 'examiner':
        examiner.is_approved = not examiner.is_approved
        db.session.commit()
        status_text = "Approved" if examiner.is_approved else "Deactivated"
        flash(f'Examiner {examiner.name} is now {status_text}.', 'info')
    return redirect(url_for('admin_dashboard'))



# 5. Reschedule Booking & Reassign Examiner


@app.route('/admin/booking/<int:id>/reschedule', methods=['GET', 'POST'])
def reschedule_booking(id):
    booking = Booking.query.get_or_404(id)
    current_slot = booking.slot

    if request.method == 'POST':
        action = request.form.get('action_type')

        # first: changing the examiner for the slot
        if action == 'change_examiner':
            current_slot.examiner_id = int(request.form.get('new_examiner_id'))
            db.session.commit()
            flash('Examiner successfully changed!', 'success')
            return redirect(url_for('admin_dashboard'))

        # second: rescheduling the student to a new slot
        if action == 'reschedule_slot':
            new_slot = Slot.query.get_or_404(int(request.form.get('new_slot_id')))

            # agar naye slot mein seat nahi hai
            if new_slot.available_seats <= 0:
                flash('Slot is full!', 'danger')
                return redirect(url_for('admin_dashboard'))

            # to ek seat current slot me add karo or uska status update karo
            current_slot.available_seats += 1
            current_slot.status = 'Available'

            # student ko naye slot mein bhejo
            booking.slot_id = new_slot.id

            # naye slot ki ek seat kam karo
            new_slot.available_seats -= 1
            if new_slot.available_seats == 0:
                new_slot.status = 'Full'

            db.session.commit()
            flash('Student successfully rescheduled to a new slot!', 'success')
            return redirect(url_for('admin_dashboard'))

    # GET request: dropdown ke liye data nikalna
    available_slots = Slot.query.filter_by(exam_id=current_slot.exam_id).all()
    approved_examiners = User.query.filter_by(role='examiner', is_approved=True).all()
    
    return render_template('reschedule.html', 
                           booking=booking, 
                           slots=available_slots, 
                           examiners=approved_examiners
                           )




# ==================== EXAMINER ROUTES ====================


# examiner dashbord
@app.route('/examiner/dashboard')
def examiner_dashboard():
    slots = Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date.asc(), Slot.start_time.asc()).all()
    return render_template('examiner_dashboard.html', slots=slots)


# slot managing route for examiner
@app.route('/examiner/slot/<int:id>/manage')
def manage_slot(id):
    slot = Slot.query.get_or_404(id)
    if slot.examiner_id != current_user.id:
        flash('You are not the owner of this slot.', 'danger')
        return redirect(url_for('examiner_dashboard'))
    
    # slot mein booked sabhi students ko nikalna
    bookings = Booking.query.filter_by(slot_id=id).all()
    return render_template('slot_form.html', slot=slot, bookings=bookings)


# evaluation route for examiner to evaluate student
@app.route('/examiner/evaluate/<int:booking_id>', methods=['GET', 'POST'])
def evaluate_student(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    slot = booking.slot
    
    if slot.examiner_id != current_user.id:
        flash('You are not the owner of this slot.', 'danger')
        return redirect(url_for('examiner_dashboard'))
        
    # exam marking scheme nikalna
    rubrics = Rubric.query.filter_by(exam_id=slot.exam_id).all()
    
    if request.method == 'POST':
        total_score = 0
        remarks = request.form.get('remarks', '')
        
        # har rubric ka score form se nikal kar total karna
        for rubric in rubrics:
            score = request.form.get(f'rubric_{rubric.id}', type=float)
            if score is not None:
                total_score += score
        
        # pehle se evaluation bani hui h ya nayi banani hai
        evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()
        if not evaluation:
            evaluation = Evaluation(booking_id=booking.id, examiner_id=current_user.id)
            db.session.add(evaluation)
        
        evaluation.marks_obtained = total_score
        evaluation.remarks = remarks
        booking.status = 'Evaluated'
        
        db.session.commit()
        flash('Evaluation saved successfully!', 'success')
        return redirect(url_for('manage_slot', id=slot.id))
        
    return render_template('evaluate_student.html', booking=booking, rubrics=rubrics)



# ==================== STUDENT ROUTES ====================


# student dashboard route
@app.route('/student/dashboard')
def student_dashboard():
    q = request.args.get('q', '').strip()

    my_bookings = Booking.query.filter_by(student_id=current_user.id).all()
    booked_slot_ids = [b.slot_id for b in my_bookings]
    
    if q:
        available_slots = Slot.query.join(Examination).filter(
            Slot.available_seats > 0, 
            Examination.name.ilike(f'%{q}%')
        ).filter(~Slot.id.in_(booked_slot_ids) if booked_slot_ids else True).order_by(Slot.date.asc()).all()
    else:
        available_slots = Slot.query.filter(Slot.available_seats > 0).filter(~Slot.id.in_(booked_slot_ids) if booked_slot_ids else True).order_by(Slot.date.asc()).all()
    
    return render_template('student_dashboard.html', bookings=my_bookings, available_slots=available_slots)


# student slot booking route
@app.route('/student/slot/<int:slot_id>/book', methods=['POST'])
def book_slot(slot_id):
    slot = Slot.query.get_or_404(slot_id)
    
    # agar slot full h ya already booked h
    if slot.available_seats <= 0:
        flash('This slot is full!', 'danger')
        return redirect(url_for('student_dashboard'))
    
    existing_booking = Booking.query.filter_by(student_id=current_user.id, slot_id=slot_id).first()
    if existing_booking:
        flash('You have already booked this slot.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # booking create karna
    new_booking = Booking(student_id=current_user.id, slot_id=slot_id)
    db.session.add(new_booking)
    
    # available seats update karna
    slot.available_seats -= 1
    if slot.available_seats == 0:
        slot.status = 'Full'
    
    db.session.commit()
    flash('Slot booked successfully!', 'success')
    return redirect(url_for('student_dashboard'))


# student slot cancellation route
@app.route('/student/booking/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # agar student ka booking h to hi cancel kar sakta h
    if booking.student_id != current_user.id:
        flash('You are not authorized to cancel this booking.', 'danger')
        return redirect(url_for('student_dashboard'))
    
    slot = booking.slot

    # deadline checking
    from datetime import datetime
    if datetime.now() >= slot.date:
        flash('The deadline to cancel this booking has passed.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    if booking.status == 'Evaluated':
        flash('The exam has already been evaluated; you can no longer cancel this booking.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # available seats update karna
    slot.available_seats += 1
    if slot.status == 'Full':
        slot.status = 'Available'
    
    db.session.delete(booking)
    db.session.commit()
    flash('Booking cancelled successfully.', 'info')
    return redirect(url_for('student_dashboard'))


# edit profile route
@app.route('/student/profile', methods=['GET', 'POST'])
def edit_profile():
    if request.method == 'POST':
        new_name = request.form.get('name')
        new_username = request.form.get('username')
        
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Username already exists.', 'danger')
        else:
            current_user.name = new_name
            current_user.username = new_username
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('student_dashboard'))
            
    return render_template('edit_profile.html')


# student result viewing route
@app.route('/student/result/<int:booking_id>')
def view_result(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # security check
    if booking.student_id != current_user.id:
        flash('You are not authorized', 'danger')
        return redirect(url_for('student_dashboard'))

    if booking.status != 'Evaluated':
        flash('Your result is not declared.', 'warning')
        return redirect(url_for('student_dashboard'))

    evaluation = Evaluation.query.filter_by(booking_id=booking.id).first()
    return render_template('view_result.html', booking=booking, evaluation=evaluation)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)