import sqlite3
import bcrypt
import os

# Constants
DATABASE_PATH = 'attendance.db'
TRAINING_IMAGES_PATH = 'Training_images'

def setup_database():
    # Create Training_images directory if it doesn't exist
    if not os.path.exists(TRAINING_IMAGES_PATH):
        os.makedirs(TRAINING_IMAGES_PATH)
        print(f"Created {TRAINING_IMAGES_PATH} directory")

    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    print("Setting up database...")
    
    # Drop existing tables to start fresh
    print("Removing existing tables...")
    c.execute("DROP TABLE IF EXISTS attendance")
    c.execute("DROP TABLE IF EXISTS courses")
    c.execute("DROP TABLE IF EXISTS users")
    
    print("Creating new tables...")
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT,
        registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create courses table
    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT NOT NULL,
        course_code TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        teacher_id INTEGER,
        FOREIGN KEY(teacher_id) REFERENCES users(user_id)
    )''')
    
    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        course_id INTEGER,
        time TEXT,
        date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(course_id) REFERENCES courses(course_id)
    )''')
    
    print("Adding test data...")
    
    # Add test teacher
    teacher_password = bcrypt.hashpw("teacher123".encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password, role, department) VALUES (?, ?, ?, ?)",
                 ("tiwari", teacher_password, "teacher", "Computer Science"))
        print("Added test teacher: username='tiwari', password='teacher123'")
    except sqlite3.IntegrityError:
        print("Test teacher already exists")
    
    # Get the teacher's ID
    c.execute("SELECT user_id FROM users WHERE username = ?", ("tiwari",))
    teacher_id = c.fetchone()[0]
    
    # Add test courses
    test_courses = [
    ("BCA", "BCA101", "Computer Science", teacher_id),
    ("BBA", "BBA101", "Business", teacher_id),
    ("BSc", "BSC101", "Science", teacher_id)
]

    
    for course in test_courses:
        try:
            c.execute("INSERT INTO courses (course_name, course_code, department, teacher_id) VALUES (?, ?, ?, ?)",
                     course)
            print(f"Added course: {course[0]}")
        except sqlite3.IntegrityError:
            print(f"Course {course[0]} already exists")
    
    # Add test student
    student_password = bcrypt.hashpw("student123".encode('utf-8'), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users (username, password, role, department) VALUES (?, ?, ?, ?)",
                 ("test_student", student_password, "student", "Computer Science"))
        print("Added test student: username='test_student', password='student123'")
    except sqlite3.IntegrityError:
        print("Test student already exists")
    
    conn.commit()
    
    # Verify setup
    print("\nVerifying database setup...")
    
    print("\nUsers in database:")
    c.execute("SELECT user_id, username, role, department FROM users")
    users = c.fetchall()
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[2]}, Department: {user[3]}")
    
    print("\nCourses in database:")
    c.execute("""
        SELECT c.course_id, c.course_name, c.course_code, c.department, u.username 
        FROM courses c 
        JOIN users u ON c.teacher_id = u.user_id
    """)
    courses = c.fetchall()
    for course in courses:
        print(f"ID: {course[0]}, Name: {course[1]}, Code: {course[2]}, Department: {course[3]}, Teacher: {course[4]}")
    
    conn.close()
    print("\nDatabase setup completed successfully!")

if __name__ == "__main__":
    setup_database()