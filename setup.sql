DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS teacher_courses;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    roll_number TEXT,
    department TEXT,
    course TEXT,
    registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    department TEXT NOT NULL
);

-- Pre-populate courses
INSERT INTO courses (course_name, department) VALUES 
('BCA', 'Computer Applications'),
('BBA', 'Business Administration'),
('BSc', 'Science');