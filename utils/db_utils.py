import sqlite3
import os
from datetime import datetime

def initialize_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    
    # Employees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        emp_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        team TEXT NOT NULL,
        profile_image BLOB,
        registration_date TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Attendance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        date TEXT NOT NULL,
        entry_time TEXT,
        exit_time TEXT,
        status TEXT,  -- present/late/absent
        break_start TEXT,
        break_end TEXT,
        lunch_start TEXT,
        lunch_end TEXT,
        permission_reason TEXT,
        FOREIGN KEY (emp_id) REFERENCES employees (emp_id),
        UNIQUE(emp_id, date)  -- Ensure only one record per employee per day
    )
    ''')
    
    conn.commit()
    conn.close()

def insert_employee(emp_id, name, role, team, profile_image):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO employees (emp_id, name, role, team, profile_image)
    VALUES (?, ?, ?, ?, ?)
    ''', (emp_id, name, role, team, profile_image))
    conn.commit()
    conn.close()

def get_employee(emp_id):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM employees WHERE emp_id = ?', (emp_id,))
    employee = cursor.fetchone()
    conn.close()
    return employee

def record_attendance(emp_id, entry_time=None, exit_time=None, status=None,
                     break_start=None, break_end=None, lunch_start=None, 
                     lunch_end=None, permission_reason=None):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    
    # Check if record exists for today
    cursor.execute('''
    SELECT id FROM attendance 
    WHERE emp_id = ? AND date = ?
    ''', (emp_id, today))
    record = cursor.fetchone()
    
    if record:
        # Update existing record
        attendance_id = record[0]
        updates = []
        params = []
        
        if entry_time:
            updates.append("entry_time = ?")
            params.append(entry_time)
        if exit_time:
            updates.append("exit_time = ?")
            params.append(exit_time)
        if status:
            updates.append("status = ?")
            params.append(status)
        if break_start:
            updates.append("break_start = ?")
            params.append(break_start)
        if break_end:
            updates.append("break_end = ?")
            params.append(break_end)
        if lunch_start:
            updates.append("lunch_start = ?")
            params.append(lunch_start)
        if lunch_end:
            updates.append("lunch_end = ?")
            params.append(lunch_end)
        if permission_reason:
            updates.append("permission_reason = ?")
            params.append(permission_reason)
            
        if updates:
            query = f"UPDATE attendance SET {', '.join(updates)} WHERE id = ?"
            params.append(attendance_id)
            cursor.execute(query, params)
    else:
        # Create new record
        cursor.execute('''
        INSERT INTO attendance 
        (emp_id, date, entry_time, exit_time, status, 
         break_start, break_end, lunch_start, lunch_end, permission_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (emp_id, today, entry_time, exit_time, status, 
              break_start, break_end, lunch_start, lunch_end, permission_reason))
    
    conn.commit()
    conn.close()

def get_attendance_report(start_date, end_date):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT e.emp_id, e.name, e.role, e.team, a.date, 
           a.entry_time, a.exit_time, a.status,
           a.break_start, a.break_end, a.lunch_start, a.lunch_end,
           a.permission_reason
    FROM employees e
    LEFT JOIN attendance a ON e.emp_id = a.emp_id
    WHERE a.date BETWEEN ? AND ?
    ORDER BY a.date, e.name
    ''', (start_date, end_date))
    report = cursor.fetchall()
    conn.close()
    return report

def get_all_employees():
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT emp_id, name, role, team, profile_image, registration_date
    FROM employees
    ORDER BY name
    ''')
    employees = cursor.fetchall()
    conn.close()
    return employees

def get_today_attendance():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT e.emp_id, e.name, e.role, e.team, 
           a.entry_time, a.exit_time, a.status
    FROM employees e
    LEFT JOIN attendance a ON e.emp_id = a.emp_id AND a.date = ?
    ORDER BY e.name
    ''', (today,))
    attendance = cursor.fetchall()
    conn.close()
    return attendance