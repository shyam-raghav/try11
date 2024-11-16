from flask import Flask, render_template, redirect, url_for, flash, request, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import smtplib
from flask_apscheduler import APScheduler
from email.mime.text import MIMEText
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = '4e4f7a3f49c658f7e2f2e3be3c6e3d2e682c1c3e4e2fcd11f40c3b487c3a19c5'  # Replace with your generated key



# Token serializer
s = URLSafeTimedSerializer(app.secret_key)

# SQLite connection function
def get_db_connection():
    conn = sqlite3.connect('habit_tracker.db',timeout=10)
    conn.row_factory = sqlite3.Row  # To fetch rows as dictionaries
    return conn



# Initialize APScheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

alerts = []

# Function to check deadlines and update tables
def check_goal_deadlines():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get today's date
    today = datetime.now().date()

    # Check for goals due today
    cursor.execute('''
        SELECT goal_id, user_id, goal_description 
        FROM Goals 
        WHERE target_date = ? AND status = 'Active'
    ''', (today,))
    due_goals = cursor.fetchall()

    for goal in due_goals:
        user_id = goal['user_id']
        cursor.execute('''
            SELECT email, first_name, last_name 
            FROM Users 
            WHERE user_id = ?
        ''', (user_id,))
        user = cursor.fetchone()

        if user:
            # Step 2.2: Get the email from the user details
            email = user['email']
            first_name = user['first_name']
            last_name = user['last_name']

            # Step 2.3: Create the email content
            message_content = f"""
            Dear {first_name} {last_name},

            This is a reminder that your goal is due today:

            Goal: {goal['goal_description']}
            
            Please make sure to complete it on time.

            Best regards,
            HabitQuest Team
            """

            # Notify the user (e.g., update their session flash or send an email)
            print(f"Goal due today for user {goal['user_id']}: {goal['goal_description']}")
            alerts.append(f"Goal due today for user {goal['user_id']}: {goal['goal_description']}")
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login( 'habitquestforkids@gmail.com','fyze mugm ulmu dlsm')

    # Construct the MIMEText object for the email body
            msg = MIMEText(message_content)

    # Set the sender, recipient, and subject of the email
            msg['From'] = 'habitquestforkids@gmail.com'
            msg['To'] = email
            msg['Subject'] = 'Password Reset Request'
            server.sendmail('habitquestforkids@gmail.com', email, msg.as_string())# Send the email
            server.quit()
            
            # Update status in Goals and Tasks tables if required
            cursor.execute('''
                UPDATE Goals
                SET status = 'Completed'
                WHERE goal_id = ?
            ''', (goal['goal_id'],))


        conn.commit()
        conn.close()
    

# Schedule the goal deadline check task to run daily
scheduler.add_job(id='check_goal_deadlines', func=check_goal_deadlines, trigger='interval', minutes=1)



@app.route('/', methods=['GET','POST'])
def index():
    print(session)
    #session.clear()
    if 'email' in session:
        user_id = session['user_id']
        
        # Fetch counts and course names
        conn = get_db_connection()
        cursor = conn.cursor()
        role = session['role']
           
            
        # Redirect to the appropriate dashboard based on role
        if role == 'Child':
            # Get count of enrolled courses
            cursor.execute('SELECT COUNT(*) as enrolled_count FROM Habits WHERE user_id = ?', (user_id,))
            enrolled_count = cursor.fetchone()['enrolled_count']
            print(user_id)
        # Get count of completed courses
            cursor.execute('SELECT COUNT(*) as completed_count FROM Tasks WHERE user_id = ? AND status = ?', 
                        (user_id, 'Completed'))
            completed_count = cursor.fetchone()[0] # Access the first element to get the count
            print(f'Number of completed courses: {completed_count}')

            if completed_count is None:
                completed_count = 0
            # Fetch enrolled courses and their progress
            cursor.execute('SELECT task_name, status, content_id FROM Tasks WHERE user_id = ?', (user_id,))
            enrolled_courses = cursor.fetchall()
            print(completed_count)
            conn.close()
            current_alerts = alerts.copy()
            alerts.clear()  
            return render_template('home.html', user=session, user_id=user_id,
                                enrolled_count=enrolled_count, 
                                completed_count=completed_count,
                                enrolled_courses=enrolled_courses,alerts=current_alerts)
           
    if 'parent_email' in session:
        parent_id = session['parent_id']
        
        # Fetch counts and course names
        conn = get_db_connection()
        cursor = conn.cursor()
        role = session['parent_role']
        print(role)
        if role == 'Parent':
            return redirect(url_for('parental_monitoring'))
        
        else:
            # User not found, clear the session and redirect to login
            session.clear()
            #flash('Session expired or user not found. Please log in again.')
            return redirect(url_for('login'))
       
    else:
        return render_template('index.html', user=None)

    


# Signup route for users to sign up manually
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')  # Child, Parent, Teacher
        phone=request.form.get('phone')
        registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Hash the password before storing
        hashed_password = generate_password_hash(password)

        try:
            # Connect to the database
            conn = get_db_connection()
            cursor = conn.cursor()

            if role == 'Parent':
                # Insert parent into the Parents table
                cursor.execute('''
                    INSERT INTO Parents (name, email, password, registration_date,phone)
                    VALUES (?,?, ?, ?, ?)
                ''', (name, email, hashed_password, registration_date,phone))
                conn.commit()
                    # Fetch the newly created user or parent to create a session
                cursor.execute('SELECT * FROM Parents WHERE email = ?', (email,))
                user = cursor.fetchone()
                print(user)
                # Close the connection
                conn.close()

                # Store user information in session
                session['parent_id'] = user['id']
                session['parent_email'] = user['email']
                session['parent_name'] = user['name']
                session['parent_phone']=user['phone']
                session['parent_role'] = 'Parent'
                print('Signup successful! Please log in.')
                return redirect(url_for('index'))
                

            elif role == 'Child':
                date_of_birth = request.form.get('date_of_birth')
                gender = request.form.get('gender')
                parent_id = request.form.get('parent_id')  # Assume parent_id is selected from dropdown

                # Insert child into the Users table
                cursor.execute('''
                    INSERT INTO Users (name, email, password, registration_date, date_of_birth, gender, parent_id, phone)
                    VALUES (?, ?, ?, ?, ?, ?, ?,?)
                ''', (name, email, hashed_password, registration_date, date_of_birth, gender, parent_id,phone))
                conn.commit()

                # Fetch the newly created user or parent to create a session
                cursor.execute('SELECT * FROM Users WHERE email = ?', (email,))
                user = cursor.fetchone()

                # Close the connection
                conn.close()

                # Store user information in session
                session['user_id'] = user['user_id']
                session['email'] = user['email']
                session['name'] = user['name']
                session['phone']=user['phone']
                session['date_of_birth'] = user['date_of_birth']
                session['gender'] = user['gender']
                session['parent_id'] = user['parent_id']
                session['role']='Child'
                #flash('Signup successful! Please log in')
                return redirect(url_for('index'))

        except Exception as e:
            flash('An error occurred during signup. Please try again.')
            print(e)
            return redirect(url_for('signup'))

    # On GET request, render the signup form
    # Fetch parents to populate the dropdown if needed
    parents = get_parents()  # Assume you have a function to fetch parents for the dropdown
    return render_template('signup.html', parents=parents)

def get_parents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM Parents')
    parents = cursor.fetchall()
    conn.close()
    return parents

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check in the Users table
        cursor.execute('SELECT * FROM Users WHERE email = ?', (email,))
        user = cursor.fetchone()

        # Check in the Parents table if not found in Users
        parent = None
        if not user:
            cursor.execute('SELECT * FROM Parents WHERE email = ?', (email,))
            parent = cursor.fetchone()

        conn.close()

        if user:
            # Verify the password for the user
            if check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                session['email'] = user['email']
                session['name'] = user['name']
                session['role']='Child'

                # Navigate based on role
                if session['role'] == 'Child':
                    return redirect(url_for('index'))  # Replace with child's home page
                
            else:
               # flash('Invalid password. Please try again.')
                return redirect(url_for('login'))

        elif parent:
            # Verify the password for the parent
            if check_password_hash(parent['password'], password):
                session['parent_id'] = parent['id']
                session['parent_email'] = parent['email']
                session['parent_name'] = parent['name']
                session['parent_role'] = 'Parent'

                # Redirect to parental monitoring page
                return redirect(url_for('parental_monitoring'))
            else:
                #flash('Invalid password. Please try again.')
                return redirect(url_for('login'))

        else:
            # If no record is found in either table
            #flash('No account found with this email. Please sign up.')
            return redirect(url_for('signup'))

    return render_template('login.html')





@app.route('/profile_update', methods=['GET', 'POST'])
def profile_update():
    if 'user_id' not in session:
       # flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch the user from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone=request.form.get('phone')
        gender=request.form.get('gender')
        dob=request.form.get('dob')
        print(name, email, password,phone,gender,dob)

        # Update user details
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE Users SET name = ?, email = ?, phone=?, gender=?, date_of_birth=? WHERE user_id = ?', (name, email,phone,gender,dob, user_id))
        if password:  
            hashed_password = generate_password_hash(password)
            cursor.execute('UPDATE Users SET password = ? WHERE user_id = ?', (hashed_password, user_id))

        conn.commit()
        conn.close()
        #flash('Profile updated successfully!')
        return redirect(url_for('index'))

    return render_template('profile_update.html', user=user)


# Password recovery route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM Users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Generate a token
            token = s.dumps(email, salt='password-reset-salt')
            reset_link = url_for('reset_password', token=token, _external=True)
            print(97)
            print(reset_link)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login( 'habitquestforkids@gmail.com','fyze mugm ulmu dlsm')
            message_content = f'Your password reset link is: {reset_link}'

# Construct the MIMEText object for the email body
            msg = MIMEText(message_content)

# Set the sender, recipient, and subject of the email
            msg['From'] = 'habitquestforkids@gmail.com'
            msg['To'] = email
            msg['Subject'] = 'Password Reset Request'
            server.sendmail('habitquestforkids@gmail.com', email, msg.as_string())# Send the email
            flash('A password reset link has been sent to your email address.')
            return redirect(url_for('login'))
        else:
            flash('No account associated with this email.')
            return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')

# Password reset route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # Token valid for 1 hour
    except Exception:
        flash('The password reset link is invalid or has expired.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Users SET password = ? WHERE email = ?', (hashed_password, email))
        conn.commit()
        conn.close()

        flash('Your password has been updated successfully! Please log in.')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


@app.route('/setgoals')
def setgoals():
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch active goals for the user
    cursor.execute('''
        SELECT *
        FROM Goals
        WHERE user_id = ? AND status = 'Active'
    ''', (user_id,))
    active_goals = cursor.fetchall()
    print(active_goals)
    conn.close()
    
    return render_template('set_goals.html', active_goals=active_goals)


@app.route('/add_goal', methods=['POST'])
def add_goal():
    user_id = session['user_id'] # Example: Get the logged-in user ID from session
    goal_description = request.form['goal_title']
    target_date = request.form['goal_deadline']

    # Insert the new goal into the database
    conn = sqlite3.connect('habit_tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Goals (user_id, goal_description, target_date)
        VALUES (?, ?, ?)
    ''', (user_id, goal_description, target_date))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('courses'))


@app.route('/progress')
def progress():
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch enrolled habits (courses) for the user
    cursor.execute('''SELECT * FROM HabitProgress WHERE user_id = ?''', (user_id,))
    enrolled_habits = cursor.fetchall()
    
    progress_data = []

    for habit in enrolled_habits:
        habit_id = habit['content_id']
        
        # Calculate total tasks and completed tasks for each habit
        cursor.execute('SELECT COUNT(*) as total_tasks FROM Tasks WHERE content_id = ? AND user_id = ?', (habit_id, user_id))
        total_tasks = cursor.fetchone()['total_tasks']
        
        cursor.execute('SELECT COUNT(*) as completed_tasks FROM Tasks WHERE content_id = ? AND user_id = ? AND status = ?', 
                       (habit_id, user_id, 'Completed'))
        completed_tasks = cursor.fetchone()['completed_tasks']
        
        # Calculate completion percentage
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Add additional progress details from HabitProgress
        progress_data.append({
            'habit_name': habit['title'],
            'completion_percentage': completion_percentage,
            'last_assessment_score': habit['last_assessment_score'] or 0,
            'progress_level': habit['progress_level'],
            'rewards_earned': habit['rewards_earned'],
            'time_spent': habit['time_spent'] or 0
        })

    conn.close()
    
    return render_template('progress.html', progress_data=progress_data, user=session)



# Route to display content dynamically
@app.route('/course_content/<int:content_id>', methods=['GET'])
def course_content(content_id):
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    # Fetch course (habit) content
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM CourseContent WHERE content_id = ?
    ''', (content_id,))
    content1 = cursor.fetchone()

    conn.close()

    return render_template('course_content.html', content=content1, user=session)


# Route to display and handle assessments dynamically for a specific habit
@app.route('/assessment/<int:content_id>', methods=['GET', 'POST'])
def assessment(content_id):
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    print(content_id)
    # Fetch habit assessments
    cursor.execute('''
        SELECT a.assessment_id, a.question, a.option1, a.option2, a.option3, a.option4, a.correct_option, a.course_id
        FROM Assessments a
        WHERE a.course_id = ?
    ''', (content_id,))
    assessment_questions = cursor.fetchall()
    conn.commit()
    conn.close()
    return render_template('assessment.html', assessment_questions=assessment_questions, user=session, content_id=content_id)


@app.route('/assessment/<int:content_id>/submit', methods=['POST'])
def submit_assessment(content_id):
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch assessment questions with correct answers
    cursor.execute('''
        SELECT a.assessment_id, a.correct_option
        FROM Assessments a
        WHERE a.course_id = ? 
    ''', (content_id,))
    assessment_questions = cursor.fetchall()

    # Calculate score
    score = 0
    total_questions = len(assessment_questions)

    # Create a dictionary to store correct answers for easier lookup
    correct_answers = {question['assessment_id']: question['correct_option'] for question in assessment_questions}
    print('-'*50)
    print(correct_answers)
    # Get time spent from the form
    time_spent = request.form.get('time_spent', type=int)

    for assessment_id, correct_option in correct_answers.items():
        selected_option = request.form.get(f'question_{assessment_id}')
        print(selected_option)
        print(correct_option)
        if selected_option == correct_option:
            score += 1
    print(score)
    # Calculate score percentage
    score_percentage = round((score / total_questions) * 100) if total_questions > 0 else 0
    print(score_percentage)
    #flash(f'You scored {score} out of {total_questions} ({score_percentage:.2f}%)')

    # Update progress or rewards based on score
    cursor.execute('SELECT * FROM HabitProgress WHERE user_id = ? AND content_id = ?', (user_id, content_id))
    progress = cursor.fetchone()
    print(progress)
    reward = None
    progress_level = progress["progress_level"] if progress else 0

    if score_percentage >= 80:
        reward = "Gold Star"
        progress_level += 1
    elif score_percentage >= 50:
        reward = "Silver Star"
        progress_level += 1
    else:
        reward = "Encouragement Badge"

    # Insert or update progress record
    if progress:
        cursor.execute('''
            UPDATE HabitProgress
            SET last_assessment_score = ?, progress_level = ?, rewards_earned = ?, time_spent = ?,
                last_updated = ?
            WHERE user_id = ? AND content_id = ?
        ''', (score_percentage, progress_level, reward, time_spent, datetime.now(), user_id, content_id))
    else:
        cursor.execute('''
            INSERT INTO HabitProgress (user_id,title, content_id, last_assessment_score, progress_level, rewards_earned, time_spent, last_updated)
             VALUES (?,?,?, ?, ?, ?, ?, ?)
        ''', (user_id, content_id,content_id, score_percentage, progress_level, reward, time_spent, datetime.now()))

    if score_percentage == 100:
        cursor.execute('''UPDATE Tasks SET status = 'Completed', completion_date = ?, time_spent = ? WHERE content_id = ? AND user_id = ? AND status = 'Active' ''',
                       (datetime.now(), time_spent, content_id, user_id))
        
        # Update Habits table to mark the habit as completed
        cursor.execute('''UPDATE Habits SET status = 'Completed' WHERE content_id = ? AND user_id = ? AND status = 'Active' ''',
                       (content_id, user_id))

    conn.commit()
    conn.close()

    print(f'You earned a {reward}! Your progress level is now {progress_level}. Time spent: {time_spent} seconds.')
    return redirect(url_for('progress'))


@app.route('/sync')
def sync():
    return render_template('sync.html')



@app.route('/notification')
def notification():
    if 'user_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch notifications for the user
    cursor.execute('''
        SELECT *
        FROM Goals 
        WHERE user_id = ? and status='Completed'
        ORDER BY target_date DESC
    ''', (user_id,))

    notifications = cursor.fetchall()
    conn.close()

    return render_template('notification.html', notifications=notifications, user=session)


@app.route('/parental_monitoring')
def parental_monitoring():
    print("Session data:", session)  # Debugging session data
    if 'parent_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    parent_id = session['parent_id']
    print("Parent ID:", parent_id)  # Debugging parent_id
    # Fetch users' tasks and goals for a given parent ID

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all users who have the specified parent ID
    cursor.execute('''SELECT * FROM Users WHERE parent_id = ?''', (parent_id,))
    users = cursor.fetchall()

    all_user_tasks = []
    all_user_goals = []

    for user in users:
        user_id = user['user_id']

        # Fetch tasks for each user
        cursor.execute('''SELECT task_name, due_date, status, completion_date FROM Tasks WHERE user_id = ?''', (user_id,))
        tasks = cursor.fetchall()

        # Append the tasks with the associated user details
        all_user_tasks.append({'user': user, 'tasks': tasks})

        # Fetch goals for each user
        cursor.execute('''SELECT goal_description, target_date, status FROM Goals WHERE user_id = ?''', (user_id,))
        goals = cursor.fetchall()

        # Append the goals with the associated user details
        all_user_goals.append({'user': user, 'goals': goals})
        print(users)
    conn.close()

    # Render the data to the template
    return render_template('parental_monitoring.html', all_user_tasks=all_user_tasks, all_user_goals=all_user_goals, users=users,parent_id=parent_id)



@app.route('/show_courses<int:parent_id>', methods=['GET','POST'])
def show_courses(parent_id):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM CourseContent where user_id=?''',(parent_id,))  # Adjust table name/columns as needed
    courses = cursor.fetchall()
    conn.close()
    return render_template('edit_courses_table.html', courses=courses)


@app.route('/edit_course/<int:course_id>', methods=['GET','POST'])
def edit_course(course_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM CourseContent WHERE course_id = ?', (course_id,))
    course = cursor.fetchone()
    conn.close()
    return render_template('edit_course.html', course=course)

@app.route('/update_course/<int:course_id>', methods=['GET','POST'])
def update_course(course_id):
    title = request.form['title']
    description = request.form['description']
    content_learning = request.form['content_learning']
    content_type = request.form['content_type']
    content_url = request.form['content_url']
    frequency = request.form['frequency']
    start_date = request.form['start_date']
    end_date = request.form['end_date']
    status = request.form['status']
    parent_id = session['parent_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE CourseContent
        SET title = ?, description = ?, content_learning = ?, content_type = ?, content_url = ?, 
            frequency = ?, start_date = ?, end_date = ?, status = ?
        WHERE course_id = ?
    ''', (title, description, content_learning, content_type, content_url, frequency, start_date, end_date, status, course_id))
    conn.commit()
    conn.close()

    return redirect(url_for('show_courses',parent_id=parent_id))



@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        email = request.form['email']
        feedback_description = request.form['feedback_description']
        rating = request.form['rating']

        # Construct the email content
        subject = f"New Feedback from {name}"
        body = f"""
        You have received new feedback:

        Name: {name}
        Email: {email}
        Rating: {rating} stars

        Feedback Message:
        {feedback_description}
        """

        # Send the email using Flask-Mail (you can use SMTP as shown earlier as well)
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login( 'habitquestforkids@gmail.com','fyze mugm ulmu dlsm')

    # Construct the MIMEText object for the email body
            msg = MIMEText(body)

    # Set the sender, recipient, and subject of the email
            msg['From'] = 'habitquestforkids@gmail.com'
            msg['To'] = email
            msg['Subject'] = subject
            server.sendmail('habitquestforkids@gmail.com', email, msg.as_string())# Send the email
            server.quit()
            
            flash('Thank you for your feedback! We have received your message.')
            return redirect(url_for('thank_you'))
        except Exception as e:
            flash(f'Error sending feedback: {e}')
            return redirect(url_for('feedback'))

    return render_template('feedback.html')

@app.route('/thank_you')
def thank_you():
    return "<h1>Thank you for your feedback!</h1>"




@app.route('/user_analysis')
def user_analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user's tasks with time spent
    cursor.execute('''
        SELECT status, due_date, completion_date, time_spent
        FROM Tasks
        WHERE user_id = ?
    ''', (user_id,))
    tasks = cursor.fetchall()

    # Calculate tasks completed percentage
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task['status'] == 'Completed'])
    tasks_completed_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Calculate habit streak (assuming it's the count of consecutive days with completed tasks)
    completed_dates = [task['completion_date'] for task in tasks if task['status'] == 'Completed']
    completed_dates = sorted(set(completed_dates))  # Remove duplicates and sort the dates

    habit_streak = 0
    if completed_dates:
        # Count streak of consecutive days
        current_streak = 1
        for i in range(1, len(completed_dates)):
            # Convert string dates to datetime objects
            from datetime import datetime, timedelta
            prev_date = datetime.strptime(completed_dates[i-1], '%Y-%m-%d')
            curr_date = datetime.strptime(completed_dates[i], '%Y-%m-%d')
            
            if (curr_date - prev_date).days == 1:  # Check if the current date is the next day
                current_streak += 1
            else:
                break  # Break on the first non-consecutive day
        
        habit_streak = current_streak

    # Calculate average task time
    # Ensure that time_spent is an integer in minutes; you can adjust this based on your actual data type.
    total_time_spent = sum(task['time_spent'] for task in tasks if task['time_spent'] is not None)
    completed_task_times = len([task for task in tasks if task['status'] == 'Completed' and task['time_spent'] is not None])
    average_task_time = (total_time_spent / completed_task_times) if completed_task_times > 0 else 0

    conn.close()

    return render_template('user_analysis.html', total_tasks=total_tasks, completed_tasks=completed_tasks,
                        tasks_completed_percentage=tasks_completed_percentage,
                        habit_streak=habit_streak,
                        average_task_time=average_task_time)



@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        habit_name = request.form['habit_name']
        description = request.form['description']
        frequency = request.form['frequency']

        # Insert new course into the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Habits (habit_name, description, frequency, status)
            VALUES (?, ?, ?, 'Active')
        ''', (habit_name, description, frequency))
        conn.commit()
        conn.close()

        return redirect(url_for('courses'))  # Redirect to the course listing page after adding

    return render_template('add_course.html')  # Render the add course page




@app.route('/enroll/<course_name>', methods=['GET', 'POST'])
def enroll(course_name):
    conn = get_db_connection()
    cursor = conn.cursor()
        # Check if the user is already enrolled in the course (habit)
    cursor.execute('SELECT * FROM CourseContent WHERE title = ?', 
                   (course_name,))
    c=cursor.fetchone()
    # Check if the user is already enrolled in the course (habit)
    cursor.execute('SELECT * FROM Tasks WHERE user_id = ? AND task_name = ?', 
                   (session['user_id'], course_name))
    habit = cursor.fetchone()

    if not habit:
        # If the user is not enrolled, create a new habit
        cursor.execute('INSERT INTO Habits (user_id, habit_name, description, frequency, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                       (session['user_id'], course_name, f"Study {course_name}", 'Weekly', datetime.now().strftime("%Y-%m-%d"), None, 'Active'))
        content_id = cursor.lastrowid

        # Create initial tasks for the course
        cursor.execute('INSERT INTO Tasks (content_id, user_id, task_name, due_date, status) VALUES (?, ?, ?, ?, ?)', 
                       (c['content_id'], session['user_id'], course_name, datetime.now().strftime("%Y-%m-%d"), 'Active'))
       
        cursor.execute('''
        INSERT INTO HabitProgress (user_id, content_id, title, time_spent, last_assessment_score, progress_level, rewards_earned, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], c['content_id'], course_name, 0, 0, 0, None, datetime.now()))


        conn.commit()
        start_date = datetime.today().strftime('%Y-%m-%d')
       # flash(f'Successfully enrolled in {course_name}!', 'success')
        return render_template('course_enroll.html', course_name=course_name, content_id=content_id,start_date=start_date)
    else:
        # If already enrolled, check if all tasks are completed
        cursor.execute('SELECT COUNT(*) as completed_count FROM Tasks WHERE content_id = ? AND status = ?', 
                       (habit['content_id'], 'Completed'))
        completed_count = cursor.fetchone()['completed_count'] or 0  # Use 0 if None

        cursor.execute('SELECT COUNT(*) as total_tasks FROM Tasks WHERE content_id = ?', 
                       (habit['content_id'],))
        total_tasks = cursor.fetchone()['total_tasks'] or 0  # Use 0 if None

        if total_tasks > 0:  # Ensure there are tasks to check
            if completed_count == total_tasks:
                print(f'You have completed the course {course_name}!', 'info')
            else:
                print(f'You are already enrolled in {course_name} but have not completed all tasks!', 'info')
        else:
            print(f'You are already enrolled in {course_name}!', 'info')

    conn.close()
    return redirect(url_for('courses'))


@app.route('/courses')
def courses():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all courses (habits)
    cursor.execute('SELECT * FROM CourseContent')
    habits = cursor.fetchall()

    # Prepare a list to hold course information with enrollment status
    courses = []
    
    # Fetch all user enrolled habits
    cursor.execute('SELECT content_id FROM Tasks WHERE user_id = ?', (session['user_id'],))
    enrolled_habits = cursor.fetchall()
    enrolled_content_ids = {habit['content_id'] for habit in enrolled_habits}

    for habit in habits:
        # Initialize the habit information
        habit_info = {
            'content_id': habit['content_id'],
            'habit_name': habit['title'],
            'description': habit['description'],
            'is_enrolled': habit['content_id'] in enrolled_content_ids,
            'is_completed': False
        }

        # Check if the user has completed all tasks for the enrolled habit
        if habit_info['is_enrolled']:
            cursor.execute('SELECT COUNT(*) as completed_count FROM Tasks WHERE content_id = ? AND user_id = ? AND status = ?', 
                           (habit['content_id'], session['user_id'], 'Completed'))
            completed_count = cursor.fetchone()['completed_count'] or 0  # Handle None

            cursor.execute('SELECT COUNT(*) as total_tasks FROM Tasks WHERE content_id = ? AND user_id = ?', 
                           (habit['content_id'], session['user_id']))
            total_tasks = cursor.fetchone()['total_tasks'] or 0  # Handle None

            if completed_count == total_tasks and total_tasks > 0:
                habit_info['is_completed'] = True

        # Check if a habit with the same name already exists in the courses list
        existing_habit = next((course for course in courses if course['habit_name'] == habit_info['habit_name']), None)
        if existing_habit is None:
            # If it does not exist, append this habit info to the courses list
            courses.append(habit_info)
        elif habit_info['is_enrolled']:
            # If it exists and this habit is enrolled, replace it
            existing_habit.update(habit_info)

    conn.close()
    return render_template('course.html', courses=courses, user=session,user_id=session['user_id'])


@app.route('/content_delivery/<int:content_id>',methods=['GET', 'POST'])
def content_delivery(content_id):
    conn = get_db_connection()
    cursor = conn.cursor()

   # Fetch the content associated with the specified content_id
    cursor.execute('''
        SELECT c.content_id, c.title, c.description, c.content_type, c.content_url, c.upload_date
        FROM CourseContent c
        JOIN Habits h ON c.course_id = h.content_id
        WHERE h.content_id = ?
    ''', (content_id,))
    content = cursor.fetchall()

    # Fetch the habit details to display on the page
    cursor.execute('SELECT habit_name, description FROM Habits WHERE content_id = ?', (content_id,))
    habit = cursor.fetchone()


    conn.close()

    return render_template('content_delivery.html', content=content,content_id=content_id, habit=habit)


reward_images = {
    "Gold Star": "https://via.placeholder.com/40/FFD700/FFFFFF?text=G",
    "Silver Star": "https://via.placeholder.com/40/C0C0C0/FFFFFF?text=S",
    "Bronze Star": "https://via.placeholder.com/40/CD7F32/FFFFFF?text=B",
    "Platinum Star": "https://via.placeholder.com/40/E5E4E2/FFFFFF?text=P"  # Add more as needed
}


reward_points = {
    "Gold Star": 100,
    "Silver Star": 80
}

def get_user_rewards(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query to fetch rewards for the given user
    cursor.execute("""
        SELECT title, rewards_earned
        FROM HabitProgress
        WHERE user_id = ?
    """, (user_id,))

    rewards = cursor.fetchall()
    conn.close()
    return rewards


@app.route('/rewards<int:user_id>')
def rewards(user_id):
    rewards = get_user_rewards(user_id)
    total_points = sum(reward_points.get(reward[1], 0) for reward in rewards)  # Calculate total points

    return render_template('rewards.html', rewards=rewards, reward_points=reward_points, total_points=total_points, reward_images=reward_images)


@app.route('/calendar')
def calendar():
    return render_template('google_calender.html')  # Page containing the calendar iframe


@app.route('/add_course_content', methods=['GET', 'POST'])
def add_course_content():
    if 'parent_id' not in session:
        flash('You need to log in first.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        user_id = session['parent_id']
        course_id = request.form['course_id']
        title = request.form['title']
        description = request.form['description']
        content_learning=request.form['content_learning']
        content_type = request.form['content_type']
        content_url = request.form['content_url']
        frequency = request.form['frequency']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        status = request.form['status']

        # Insert the new course content into the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO CourseContent (course_id, title, description, content_type, content_url, content_learning,frequency, start_date, end_date, status, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (course_id, title, description, content_type, content_url, content_learning,frequency, start_date, end_date, status, user_id))

        conn.commit()
        conn.close()

        #flash('Course content added successfully!')
        return redirect(url_for('index'))  # Redirect to an appropriate page

    return render_template('add_course_content.html')



@app.route('/add_assessment', methods=['GET', 'POST'])
def add_assessment():
    if request.method == 'POST':
        course_id = request.form['course_id']
        question = request.form['question']
        options = [request.form['option_1'], request.form['option_2'], request.form['option_3'], request.form['option_4']]
        correct_option = request.form['correct_option']

        conn = sqlite3.connect('habit_tracker.db')
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO Assessments (course_id, question, option1, option2, option3, option4, correct_option) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (course_id, question, options[0], options[1], options[2], options[3], correct_option))

        conn.commit()
        conn.close()

        return redirect(url_for('add_assessment'))

    return render_template('add_assessment.html')



@app.route('/logout')
def logout():
    session.clear()  # Clears all session data
    #flash('Logged out successfully.')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
