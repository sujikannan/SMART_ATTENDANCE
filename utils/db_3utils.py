import sqlite3
from datetime import datetime

DB_PATH = "database/attendance.db"

def log_attendance(emp_id, name, role, status, time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            role TEXT,
            status TEXT,
            time TEXT
        )
    ''')

    cursor.execute('''
        INSERT INTO attendance_log (emp_id, name, role, status, time)
        VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, name, role, status, time))

    conn.commit()
    conn.close()

def log_permission(emp_id, name, role, reason, time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permission_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            role TEXT,
            reason TEXT,
            time TEXT
        )
    ''')

    cursor.execute('''
        INSERT INTO permission_log (emp_id, name, role, reason, time)
        VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, name, role, reason, time))

    conn.commit()
    conn.close()
