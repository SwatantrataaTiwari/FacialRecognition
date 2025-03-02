import sqlite3
import bcrypt
from datetime import datetime, timedelta

def add_students_and_attendance():
    DATABASE_PATH = 'attendance.db'
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # List of test students
    test_students = [
        ("john_doe", "student123", "Computer Science"),
        ("jane_smith", "student123", "Computer Science"),
        ("mike_wilson", "student123", "Computer Science"),
        ("sara_jones", "student123", "Computer Science")
    ]
    
    # Add students
    student_ids = []
    for username, password, department in test_students:
        try:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            c.execute("""
                INSERT INTO users (username, password, role, department) 
                VALUES (?, ?, 'student', ?)
            """, (username, hashed_password, department))
            print(f"Added student: {username}")
            
            # Get the student's ID
            c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            student_ids.append(c.fetchone()[0])
        except sqlite3.IntegrityError:
            print(f"Student {username} already exists")
            # Get existing student's ID
            c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            student_ids.append(c.fetchone()[0])
    
    # Get all courses
    c.execute("SELECT course_id, course_name FROM courses")
    courses = c.fetchall()
    
    # Generate attendance records for the last 7 days
    today = datetime.now()
    
    for student_id in student_ids:
        for course_id, course_name in courses:
            # Add attendance for random days in the last week
            for i in range(7):
                # Simulate some missing attendance (70% attendance rate)
                if __import__('random').random() < 0.7:
                    date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                    time = f"{__import__('random').randint(8,10):02d}:{__import__('random').randint(0,59):02d}"
                    
                    try:
                        c.execute("""
                            INSERT INTO attendance (user_id, course_id, time, date)
                            VALUES (?, ?, ?, ?)
                        """, (student_id, course_id, time, date))
                        print(f"Added attendance record for student ID {student_id} in course {course_name} on {date}")
                    except sqlite3.IntegrityError:
                        print(f"Attendance record already exists")
    
    conn.commit()
    
    # Verify the data
    print("\nVerifying student attendance records:")
    c.execute("""
        SELECT 
            u.username,
            c.course_name,
            COUNT(a.id) as attendance_count,
            GROUP_CONCAT(a.date) as dates
        FROM users u
        JOIN attendance a ON u.user_id = a.user_id
        JOIN courses c ON a.course_id = c.course_id
        WHERE u.role = 'student'
        GROUP BY u.username, c.course_name
    """)
    
    records = c.fetchall()
    for record in records:
        print(f"\nStudent: {record[0]}")
        print(f"Course: {record[1]}")
        print(f"Attendance Count: {record[2]}")
        print(f"Dates: {record[3]}")
    
    conn.close()

if __name__ == "__main__":
    add_students_and_attendance()