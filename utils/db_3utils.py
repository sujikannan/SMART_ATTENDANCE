import sqlite3
from datetime import datetime

DB_PATH = "database/attendance.db"

def log_attendance(emp_id, name, role, status, time_str, late):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            role TEXT,
            status TEXT,
            time TEXT,
            late TEXT
        )
    ''')

    cursor.execute('''
        INSERT INTO attendance_log (emp_id, name, role, status, time, late)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (emp_id, name, role, status, time_str, late))

    conn.commit()
    conn.close()

def log_permission(emp_id, name, permission_type, reason, time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permission_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            permission_type TEXT,
            reason TEXT,
            time TEXT
        )
    ''')

    cursor.execute('''
        INSERT INTO permission_log (emp_id, name, permission_type, reason, time)
        VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, name, permission_type, reason, time))

    conn.commit()
    conn.close()

def get_permission_logs(start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM permission_log 
        WHERE date(time) BETWEEN ? AND ?
        ORDER BY time DESC
    ''', (start_date, end_date))
    logs = cursor.fetchall()
    conn.close()
    return logs