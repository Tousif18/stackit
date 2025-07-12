
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Question, Answer, Vote, Notification
from datetime import datetime
from sqlalchemy import desc
import os
import re
import uuid

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stackit.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)

def extract_mentions(content):
    return re.findall(r'@(\w+)', content)

def notify_mentioned_users(content, current_user_id, context_message):
    mentions = extract_mentions(content)
    for username in mentions:
        user = User.query.filter_by(username=username).first()
        if user and user.id != current_user_id:
            create_notification(user.id, f"You were mentioned: {context_message}")

# Init extensions
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create admin on first run
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@stackit.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# ------------------------------
# 🔷 INDEX Route with UI Focus
# ------------------------------
@app.route('/')
def index():
    questions = Question.query.order_by(desc(Question.timestamp)).all()
    return render_template('index.html', questions=questions)

# ------------------------------
# 🧑 Signup/Login/Logout
# ------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('signup.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('signup.html')

        user = User(username=username, email=email)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
        except:
            db.session.rollback()
            flash('Failed to create account', 'error')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_banned:
                flash('Your account has been banned', 'error')
                return render_template('login.html')
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# ------------------------------
# ❓ Question/Answer System
# ------------------------------
@app.route('/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        tags = request.form.get('tags')

        if not title or not description:
            flash('Title and description are required', 'error')
            return render_template('ask.html')

        question = Question(title=title, description=description, tags=tags, user_id=current_user.id)
        try:
            db.session.add(question)
            db.session.commit()
            notify_mentioned_users(description, current_user.id, f"{current_user.username} mentioned you in question: {title}")
            db.session.commit()
            flash('Question posted!', 'success')
            return redirect(url_for('view_question', id=question.id))
        except:
            db.session.rollback()
            flash('Failed to post question', 'error')

    return render_template('ask.html')

@app.route('/question/<int:id>')
def view_question(id):
    question = Question.query.get_or_404(id)
    question.views += 1
    db.session.commit()
    answers = Answer.query.filter_by(question_id=id).order_by(desc(Answer.votes), desc(Answer.timestamp)).all()
    return render_template('question.html', question=question, answers=answers)

@app.route('/question/<int:id>/answer', methods=['POST'])
@login_required
def submit_answer(id):
    question = Question.query.get_or_404(id)
    content = request.form.get('content')

    if not content:
        flash('Answer content required', 'error')
        return redirect(url_for('view_question', id=id))

    answer = Answer(question_id=id, content=content, user_id=current_user.id)
    try:
        db.session.add(answer)
        db.session.commit()
        if question.user_id != current_user.id:
            create_notification(question.user_id, f'{current_user.username} answered your question: {question.title}')
        notify_mentioned_users(content, current_user.id, f"{current_user.username} mentioned you in an answer")
        db.session.commit()
        flash('Answer submitted!', 'success')
    except:
        db.session.rollback()
        flash('Failed to submit answer', 'error')

    return redirect(url_for('view_question', id=id))

# ------------------------------
# 🗳️ Voting System
# ------------------------------
@app.route('/vote', methods=['POST'])
@login_required
def vote():
    answer_id = request.form.get('answer_id')
    vote_type = int(request.form.get('vote_type'))
    
    if vote_type not in [-1, 1]:
        return jsonify({'error': 'Invalid vote type'}), 400
    
    answer = Answer.query.get_or_404(answer_id)
    
    # Check if user already voted
    existing_vote = Vote.query.filter_by(answer_id=answer_id, user_id=current_user.id).first()
    
    if existing_vote:
        # Update existing vote
        old_vote = existing_vote.vote_type
        existing_vote.vote_type = vote_type
        answer.votes += (vote_type - old_vote)
    else:
        # Create new vote
        new_vote = Vote(answer_id=answer_id, user_id=current_user.id, vote_type=vote_type)
        db.session.add(new_vote)
        answer.votes += vote_type
    
    try:
        db.session.commit()
        return jsonify({'votes': answer.votes})
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to vote'}), 500

# ------------------------------
# ✅ Accept Answer
# ------------------------------
@app.route('/accept_answer', methods=['POST'])
@login_required
def accept_answer():
    answer_id = request.form.get('answer_id')
    answer = Answer.query.get_or_404(answer_id)
    question = Question.query.get_or_404(answer.question_id)
    
    # Only question author can accept answers
    if question.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Unaccept any previously accepted answer
    previous_accepted = Answer.query.filter_by(question_id=question.id, is_accepted=True).first()
    if previous_accepted:
        previous_accepted.is_accepted = False
    
    # Accept this answer
    answer.is_accepted = True
    
    try:
        db.session.commit()
        # Notify answer author
        if answer.user_id != current_user.id:
            create_notification(answer.user_id, f'Your answer was accepted for question: {question.title}')
            db.session.commit()
        return jsonify({'message': 'Answer accepted'})
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to accept answer'}), 500

# ------------------------------
# 📩 Upload Image
# ------------------------------
@app.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'url': url_for('static', filename=f'uploads/{filename}', _external=True)})

    return jsonify({'error': 'Invalid file type'}), 400

# ------------------------------
# 🔔 Notification System
# ------------------------------
@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(desc(Notification.timestamp)).all()
    for notification in user_notifications:
        notification.seen = True
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/api/notifications')
@login_required
def api_notifications():
    try:
        notifications = current_user.get_recent_notifications(5)
        unread_count = current_user.get_unread_notifications()
        return jsonify({
            'notifications': [{
                'id': n.id,
                'message': n.message,
                'timestamp': n.timestamp.strftime('%Y-%m-%d %H:%M'),
                'seen': n.seen
            } for n in notifications],
            'unread_count': unread_count
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch notifications', 'unread_count': 0})

# ------------------------------
# 🛠️ Admin Dashboard
# ------------------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    questions = Question.query.order_by(desc(Question.timestamp)).all()
    answers = Answer.query.order_by(desc(Answer.timestamp)).all()
    
    return render_template('admin.html', users=users, questions=questions, answers=answers)

# ------------------------------
# 🧪 Run Flask App
# ------------------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
