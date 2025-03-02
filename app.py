from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
from io import BytesIO 
import cv2
import numpy as np
import face_recognition
import os
import sqlite3
import bcrypt
from datetime import datetime, date



app = Flask(__name__)
app.secret_key = 'admin'
os.environ.get('SECRET_KEY', 'admin')
DATABASE_PATH = 'attendance.db'
TRAINING_IMAGES_PATH = 'Training_images'





# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Ensure tables exist
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT UNIQUE, 
        password TEXT, 
        role TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        course_id INTEGER,
        time TEXT,
        date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(course_id) REFERENCES courses(course_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL
    )''')

    # Ensure predefined courses exist
    courses = [("BCA",), ("BBA",), ("BSc",)]
    for course in courses:
        try:
            c.execute("INSERT INTO courses (course_name) VALUES (?)", course)
        except sqlite3.IntegrityError:
            # Course already exists
            pass
    
    conn.commit()
    
    # Print schema for debugging
    print("Database schema:")
    c.execute("SELECT sql FROM sqlite_master WHERE type='table'")
    for table in c.fetchall():
        print(table[0])
    
    conn.close()

# Register a new user
def register_user(username, password, role):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# Verify user login
def verify_user(username, password):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, password, role FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    
    if user:
        stored_password = user[1]  # This is stored as TEXT in SQLite
        if isinstance(stored_password, str):  # Ensure it's bytes for bcrypt
            stored_password = stored_password.encode('utf-8')

        if bcrypt.checkpw(password.encode('utf-8'), stored_password):
            return {"user_id": user[0], "role": user[2]}
    
    return None


# Fetch attendance records
def get_attendance_data():
    conn = sqlite3.connect(DATABASE_PATH)
    if session.get('role') == 'teacher':
        query = '''
        SELECT users.username, courses.course_name, attendance.date, attendance.time
        FROM attendance 
        JOIN users ON attendance.user_id = users.user_id
        JOIN courses ON attendance.course_id = courses.course_id
        ORDER BY attendance.date DESC, attendance.time DESC
        '''
        df = pd.read_sql_query(query, conn)
    else:
        query = '''
        SELECT users.username, courses.course_name, attendance.date, attendance.time
        FROM attendance 
        JOIN users ON attendance.user_id = users.user_id
        JOIN courses ON attendance.course_id = courses.course_id
        WHERE users.username = ?
        ORDER BY attendance.date DESC, attendance.time DESC
        '''
        df = pd.read_sql_query(query, conn, params=(session['username'],))
    conn.close()
    return df



def load_training_images():
    images = []
    classNames = []
    
    if not os.path.exists(TRAINING_IMAGES_PATH):
        os.makedirs(TRAINING_IMAGES_PATH)  # Ensure directory exists

    image_files = os.listdir(TRAINING_IMAGES_PATH)
    
    for file in image_files:
        img = cv2.imread(os.path.join(TRAINING_IMAGES_PATH, file))
        if img is not None:
            images.append(img)
            classNames.append(os.path.splitext(file)[0])  # Remove file extension
    
    return images, classNames

def encode_faces(images):
    encoded_list = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert image to RGB (required by face_recognition)
        encodings = face_recognition.face_encodings(img)
        if encodings:
            encoded_list.append(encodings[0])  # Store first encoding
    
    return encoded_list



@app.route('/db_status')
def db_status():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Check users table
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    
    # Check attendance table
    c.execute("SELECT * FROM attendance")
    attendance = c.fetchall()
    
    # Check courses table
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    
    conn.close()
    
    return render_template('db_status.html', 
                          users=users, 
                          attendance=attendance, 
                          courses=courses)


@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT course_id, course_name FROM courses")
    courses = [{'course_id': row[0], 'course_name': row[1]} for row in c.fetchall()]
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        # For debugging
        print(f"Registering new {role}: {username}")
        
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        try:
            if role == 'student':
                course_id = request.form['course_id']
                # Insert user first
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, hashed, role))
                # Get the user_id that was just created
                c.execute("SELECT last_insert_rowid()")
                user_id = c.fetchone()[0]
                print(f"Created user_id: {user_id} for {username}")
                
                # Save the image if provided
                image = request.files.get('image')
                if image:
                    image_path = os.path.join(TRAINING_IMAGES_PATH, f"{username}.jpg")
                    image.save(image_path)
                    print(f"Saved image to {image_path}")
                    
                    # Reload face recognition data after adding a new image
                    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES
                    images, classNames = load_training_images()
                    KNOWN_FACE_ENCODINGS = encode_faces(images)
                    KNOWN_FACE_NAMES = classNames
                    print(f"Updated face recognition data, now have {len(KNOWN_FACE_NAMES)} faces")
                
                # Add a dummy attendance record to ensure the student is linked to a course
                c.execute("""
                    INSERT INTO attendance (user_id, course_id, time, date) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, course_id, datetime.now().strftime('%H:%M:%S'), 
                     date.today().strftime('%Y-%m-%d')))
                print(f"Added initial attendance record for {username} in course {course_id}")
            else:
                # Teacher registration
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                         (username, hashed, role))
                print(f"Registered teacher: {username}")
            
            conn.commit()
            print(f"Registration successful for {username}")
            
            # Verify the user was added
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_record = c.fetchone()
            print(f"Verification - User record: {user_record}")
            
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError as e:
            print(f"Registration failed due to integrity error: {e}")
            conn.rollback()
            return "Registration failed! Username already exists."
        except Exception as e:
            print(f"Registration failed due to unexpected error: {e}")
            conn.rollback()
            return f"Registration failed! Error: {e}"
        finally:
            conn.close()
    
    return render_template('register.html', courses=courses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = verify_user(username, password)
        if user:
            session['username'] = username
            session['user_id'] = user['user_id']
            session['role'] = user['role']

            return redirect(url_for('teacher_dashboard') if user['role'] == 'teacher' else url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Get attendance records
    if session['role'] == 'teacher':
        c.execute("""
            SELECT users.username, attendance.date, attendance.time 
            FROM attendance 
            JOIN users ON attendance.user_id = users.user_id
            ORDER BY attendance.date DESC, attendance.time DESC
            LIMIT 5
        """)
    else:
        c.execute("""
            SELECT users.username, attendance.date, attendance.time 
            FROM attendance 
            JOIN users ON attendance.user_id = users.user_id 
            WHERE users.username = ?
            ORDER BY attendance.date DESC, attendance.time DESC
            LIMIT 5
        """, (session['username'],))
    
    records = c.fetchall()
    
    # Get course counts for teacher view
    course_counts = {}
    if session['role'] == 'teacher':
        # Get count for BCA (course_id = 1)
        c.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM attendance 
            WHERE course_id = 1
        """)
        course_counts['bca'] = c.fetchone()[0]
        
        # Get count for BSc (course_id = 2)
        c.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM attendance 
            WHERE course_id = 2
        """)
        course_counts['bsc'] = c.fetchone()[0]
        
        # Get count for BBA (course_id = 3)
        c.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM attendance 
            WHERE course_id = 3
        """)
        course_counts['bba'] = c.fetchone()[0]
    
    conn.close()
    
    return render_template('dashboard.html', 
                         records=records, 
                         role=session['role'],
                         course_counts=course_counts)

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Calculate course counts
    course_counts = {}
    
    # Get count for BCA (course_id = 1)
    c.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM users 
        WHERE role='student' AND user_id IN (
            SELECT DISTINCT user_id FROM attendance WHERE course_id = 1
        )
    """)
    course_counts['bca'] = c.fetchone()[0]
    
    # Get count for BSc (course_id = 2)
    c.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM users 
        WHERE role='student' AND user_id IN (
            SELECT DISTINCT user_id FROM attendance WHERE course_id = 2
        )
    """)
    course_counts['bsc'] = c.fetchone()[0]
    
    # Get count for BBA (course_id = 3)
    c.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM users 
        WHERE role='student' AND user_id IN (
            SELECT DISTINCT user_id FROM attendance WHERE course_id = 3
        )
    """)
    course_counts['bba'] = c.fetchone()[0]
    
    # Rest of your existing code...
    
    # Get courses
    c.execute("SELECT course_id, course_name FROM courses")
    courses = [{'course_id': row[0], 'course_name': row[1]} for row in c.fetchall()]
    
    # Get total students
    c.execute("SELECT COUNT(DISTINCT user_id) FROM users WHERE role='student'")
    total_students = c.fetchone()[0]
    
    # Get today's attendance percentage
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("""
        SELECT COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(*) FROM users WHERE role='student')
        FROM attendance 
        WHERE date = ?
    """, (today,))
    today_attendance = round(c.fetchone()[0] or 0, 1)
    
    # Get monthly average
    month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    c.execute("""
        SELECT COUNT(DISTINCT user_id) * 100.0 / 
            (SELECT COUNT(*) FROM users WHERE role='student') / 
            (SELECT COUNT(DISTINCT date) FROM attendance WHERE date >= ?)
        FROM attendance 
        WHERE date >= ?
    """, (month_start, month_start))
    monthly_avg = round(c.fetchone()[0] or 0, 1)
    
    # Get recent records
    c.execute("""
        SELECT 
            u.username as student_name,
            c.course_name,
            a.time
        FROM attendance a
        JOIN users u ON a.user_id = u.user_id
        JOIN courses c ON a.course_id = c.course_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 5
    """)
    recent_records = [dict(zip(['student_name', 'course_name', 'time'], row)) for row in c.fetchall()]
    
    conn.close()
    
    # Pass course_counts to the template
    return render_template('teacher_dashboard.html',
                         courses=courses,
                         total_students=total_students,
                         today_attendance=today_attendance,
                         monthly_avg=monthly_avg,
                         recent_records=recent_records,
                         course_counts=course_counts)  # Added this line

@app.route('/view_records')
def view_records():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    
    if session['role'] == 'teacher':
        query = '''
        SELECT users.username, courses.course_name, attendance.date, attendance.time 
        FROM attendance 
        JOIN users ON attendance.user_id = users.user_id
        JOIN courses ON attendance.course_id = courses.course_id
        ORDER BY attendance.date DESC, attendance.time DESC
        '''
        df = pd.read_sql_query(query, conn)
    else:
        query = '''
        SELECT users.username, courses.course_name, attendance.date, attendance.time 
        FROM attendance 
        JOIN users ON attendance.user_id = users.user_id
        JOIN courses ON attendance.course_id = courses.course_id
        WHERE users.username = ?
        ORDER BY attendance.date DESC, attendance.time DESC
        '''
        df = pd.read_sql_query(query, conn, params=(session['username'],))
    
    conn.close()
    
    # Replace course names for display
    df['course_name'] = df['course_name'].replace({
        'Introduction to Python': 'BCA',
        'Data Structures': 'BBA',
        'Database Management': 'BSc'
    })
    
    # Create a formatted table for display
    if session['role'] == 'student':
        # Add delete account button for students
        delete_account_button = '<a href="/delete_account" class="text-red-600 hover:text-red-800 px-4 py-2 bg-red-100 rounded">Delete Account</a>'
        table_html = df.to_html(classes='table table-striped', index=False)
        return render_template('view_records.html', table=table_html, show_delete_account=True)
    else:
        table_html = df.to_html(classes='table table-striped', index=False)
        return render_template('view_records.html', table=table_html, show_delete_account=False)


# Global variables to store encodings
KNOWN_FACE_ENCODINGS = []
KNOWN_FACE_NAMES = []

# Load and encode faces at startup
def initialize_face_recognition():
    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES
    images, classNames = load_training_images()
    KNOWN_FACE_ENCODINGS = encode_faces(images)
    KNOWN_FACE_NAMES = classNames
    print(f"Loaded {len(KNOWN_FACE_ENCODINGS)} face encodings at startup")

# Modify your mark_attendance route
@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    # Fetch available courses
    c.execute("SELECT course_id, course_name FROM courses")
    courses = c.fetchall()

    if request.method == 'POST':
        course_id = request.form.get('course_id')
        if not course_id:
            return "Course selection is required!"

        # Use the global encodings instead of recomputing
        global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES

        cap = cv2.VideoCapture(0)

        while True:
            success, img = cap.read()
            if not success:
                break

            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            faces_cur_frame = face_recognition.face_locations(imgS)
            encodes_cur_frame = face_recognition.face_encodings(imgS, faces_cur_frame)

            for encodeFace, faceLoc in zip(encodes_cur_frame, faces_cur_frame):
                matches = face_recognition.compare_faces(KNOWN_FACE_ENCODINGS, encodeFace)
                faceDis = face_recognition.face_distance(KNOWN_FACE_ENCODINGS, encodeFace)

                matchIndex = np.argmin(faceDis) if len(faceDis) > 0 else -1
                name = KNOWN_FACE_NAMES[matchIndex].upper() if matchIndex != -1 and len(faceDis) > 0 and faceDis[matchIndex] < 0.50 else 'Unknown'

                if name != "Unknown":
                    c.execute("SELECT user_id FROM users WHERE username = ?", (name.lower(),))
                    user = c.fetchone()
                    if user:
                        user_id = user[0]
                        try:
                            c.execute("""
                                INSERT INTO attendance (user_id, course_id, time, date) 
                                VALUES (?, ?, ?, ?)
                            """, (user_id, course_id, datetime.now().strftime('%H:%M:%S'), 
                                 date.today().strftime('%Y-%m-%d')))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            pass
                        
                        cap.release()
                        cv2.destroyAllWindows()
                        return redirect(url_for('attendance_confirmation', username=name.lower()))

            cv2.imshow('Face Recognition', img)
            if cv2.waitKey(1) == 13:  # Press Enter to exit
                break

        cap.release()
        cv2.destroyAllWindows()

    conn.close()
    return render_template('mark_attendance.html', courses=courses)


@app.route('/attendance_confirmation/<string:username>')
def attendance_confirmation(username):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT time, date 
        FROM attendance 
        JOIN users ON attendance.user_id = users.user_id 
        WHERE username = ? 
        ORDER BY id DESC LIMIT 1
    """, (username,))
    record = c.fetchone()
    conn.close()
    
    if record:
        time, date = record
        return render_template('attendance_confirmation.html', username=username, time=time, date=date)
    else:
        return "No attendance record found."

@app.route('/download_csv')
def download_csv():
    if 'username' not in session:
        return redirect(url_for('login'))

    df = get_attendance_data()

    # If student, filter only their records
    if session['role'] != 'teacher':
        df = df[df['username'] == session['username']]

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='attendance_records.csv')

@app.route('/view_course_records/<int:course_id>')
def view_course_records(course_id):
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    query = '''
    SELECT 
        users.username, 
        attendance.date, 
        attendance.time 
    FROM attendance 
    JOIN users ON attendance.user_id = users.user_id
    WHERE attendance.course_id = ?
    ORDER BY attendance.date DESC, attendance.time DESC
    '''
    
    df = pd.read_sql_query(query, conn, params=(course_id,))
    conn.close()

    course_names = {
        1: 'BCA',
        2: 'BSc',
        3: 'BBA'
    }
    
    table_html = df.to_html(classes='table table-striped', index=False)
    return render_template('view_records.html', table=table_html)


@app.route('/download_course_csv/<int:course_id>')
def download_course_csv(course_id):
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    query = '''
    SELECT users.username, attendance.date, attendance.time
    FROM attendance 
    JOIN users ON attendance.user_id = users.user_id
    WHERE attendance.course_id = ?
    ORDER BY attendance.date DESC, attendance.time DESC
    '''
    
    df = pd.read_sql_query(query, conn, params=(course_id,))
    conn.close()
    
    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f'course_{course_id}_attendance.csv')

@app.route('/download_course_excel/<int:course_id>')
def download_course_excel(course_id):
    if 'username' not in session or session['role'] != 'teacher':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE_PATH)
    query = '''
    SELECT users.username, attendance.date, attendance.time
    FROM attendance 
    JOIN users ON attendance.user_id = users.user_id
    WHERE attendance.course_id = ?
    ORDER BY attendance.date DESC, attendance.time DESC
    '''
    
    df = pd.read_sql_query(query, conn, params=(course_id,))
    conn.close()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'course_{course_id}_attendance.xlsx'
    )

@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        
        try:
            # Get user_id
            c.execute("SELECT user_id FROM users WHERE username = ?", (session['username'],))
            user_id = c.fetchone()[0]
            
            # Delete attendance records first (due to foreign key constraint)
            c.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
            
            # Delete user account
            c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            # Delete training image if exists
            image_path = os.path.join(TRAINING_IMAGES_PATH, f"{session['username']}.jpg")
            if os.path.exists(image_path):
                os.remove(image_path)
            
            conn.commit()
            
            # Clear session
            session.clear()
            
            return redirect(url_for('login'))
            
        except Exception as e:
            conn.rollback()
            return "Error deleting account: " + str(e)
        
        finally:
            conn.close()
    
    return render_template('confirm_delete.html', delete_type='account')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    initialize_face_recognition()  # Add this line
    app.run(debug=True)
