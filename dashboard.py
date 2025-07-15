import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import os

# Database setup
def init_db():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS userstable(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT DEFAULT 'user'
    )
    ''')
    
    # Create employees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees(
        emp_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT,
        team TEXT,
        email TEXT,
        phone TEXT,
        registration_date DATE DEFAULT CURRENT_DATE
    )
    ''')
    
    # Create attendance table with enhanced break tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        date DATE NOT NULL,
        entry_time TIME,
        exit_time TIME,
        status TEXT DEFAULT 'present',
        permission_reason TEXT,
        break_in TIME,
        break_out TIME,
        break_late BOOLEAN DEFAULT FALSE,
        lunch_in TIME,
        lunch_out TIME,
        lunch_late BOOLEAN DEFAULT FALSE,
        FOREIGN KEY(emp_id) REFERENCES employees(emp_id),
        UNIQUE(emp_id, date)
    )
    ''')
    
    # Create admin user if not exists
    cursor.execute('SELECT * FROM userstable WHERE username = "admin"')
    if not cursor.fetchone():
        cursor.execute('INSERT INTO userstable(username, password, role) VALUES (?, ?, ?)', 
                      ('admin', make_hashes('admin123'), 'admin'))
    
    conn.commit()
    conn.close()

# Password hashing
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# User management
def add_userdata(username, password, role='user'):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO userstable(username, password, role) VALUES (?,?,?)', 
                      (username, make_hashes(password), role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Username already exists")
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM userstable WHERE username = ?', (username,))
    data = cursor.fetchone()
    conn.close()
    
    if data and check_hashes(password, data[1]):
        return {'username': data[0], 'role': data[2]}
    return None

def update_password(username, new_password):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE userstable SET password = ? WHERE username = ?', 
                  (make_hashes(new_password), username))
    conn.commit()
    conn.close()

# Employee management
def add_employee(emp_id, name, role, team, email, phone):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO employees(emp_id, name, role, team, email, phone) 
        VALUES (?,?,?,?,?,?)
        ''', (emp_id, name, role, team, email, phone))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error("Employee ID already exists")
        return False
    finally:
        conn.close()

def get_employees():
    conn = sqlite3.connect('database/attendance.db')
    df = pd.read_sql('SELECT * FROM employees ORDER BY name', conn)
    conn.close()
    return df

# Attendance management with enhanced break tracking
def record_attendance(emp_id, date, entry_time, exit_time=None, status='present', 
                     permission_reason=None, break_in=None, break_out=None, break_late=False,
                     lunch_in=None, lunch_out=None, lunch_late=False):
    conn = sqlite3.connect('database/attendance.db')
    cursor = conn.cursor()
    
    # Check if record exists
    cursor.execute('SELECT * FROM attendance WHERE emp_id = ? AND date = ?', (emp_id, date))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
        cursor.execute('''
        UPDATE attendance 
        SET exit_time = COALESCE(?, exit_time),
            status = COALESCE(?, status),
            permission_reason = COALESCE(?, permission_reason),
            break_in = COALESCE(?, break_in),
            break_out = COALESCE(?, break_out),
            break_late = ?,
            lunch_in = COALESCE(?, lunch_in),
            lunch_out = COALESCE(?, lunch_out),
            lunch_late = ?
        WHERE emp_id = ? AND date = ?
        ''', (exit_time, status, permission_reason, 
              break_in, break_out, break_late,
              lunch_in, lunch_out, lunch_late,
              emp_id, date))
    else:
        # Insert new record
        cursor.execute('''
        INSERT INTO attendance(
            emp_id, date, entry_time, exit_time, status, permission_reason,
            break_in, break_out, break_late,
            lunch_in, lunch_out, lunch_late
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (emp_id, date, entry_time, exit_time, status, permission_reason,
              break_in, break_out, break_late,
              lunch_in, lunch_out, lunch_late))
    
    conn.commit()
    conn.close()

def get_attendance(start_date, end_date):
    conn = sqlite3.connect('database/attendance.db')
    query = '''
    SELECT 
        e.emp_id, e.name, e.role, e.team,
        a.date, a.entry_time, a.exit_time, a.status,
        a.permission_reason, 
        a.break_in, a.break_out, a.break_late,
        a.lunch_in, a.lunch_out, a.lunch_late
    FROM employees e
    LEFT JOIN attendance a ON e.emp_id = a.emp_id AND a.date BETWEEN ? AND ?
    WHERE a.date IS NOT NULL
    ORDER BY a.date DESC
    '''
    df = pd.read_sql(query, conn, params=(start_date, end_date))
    conn.close()
    return df

def get_permission_log(start_date, end_date):
    conn = sqlite3.connect('database/attendance.db')
    query = '''
    SELECT 
        e.emp_id, e.name, e.role, e.team,
        a.date, a.entry_time, a.exit_time,
        a.status, a.permission_reason,
        a.break_in, a.break_out, a.break_late,
        a.lunch_in, a.lunch_out, a.lunch_late
    FROM employees e
    JOIN attendance a ON e.emp_id = a.emp_id
    WHERE a.date BETWEEN ? AND ? AND a.permission_reason IS NOT NULL
    ORDER BY a.date DESC
    '''
    df = pd.read_sql(query, conn, params=(start_date, end_date))
    conn.close()
    return df

# UI Components
def login_page():
    st.subheader("Login Section")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
    
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.session_state.logged_in = True
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Invalid username or password")

def signup_page():
    st.subheader("Create New Account")
    new_user = st.text_input("Username")
    new_password = st.text_input("Password", type='password')
    confirm_password = st.text_input("Confirm Password", type='password')
    
    if st.button("Signup"):
        if new_password == confirm_password:
            if add_userdata(new_user, new_password):
                st.success("Account created successfully! Please login.")
                st.session_state.menu = "Login"
                st.rerun()
        else:
            st.error("Passwords do not match")

def forgot_password_page():
    st.subheader("Reset Password")
    username = st.text_input("Username")
    new_password = st.text_input("New Password", type='password')
    confirm_password = st.text_input("Confirm New Password", type='password')
    
    if st.button("Reset Password"):
        if new_password == confirm_password:
            update_password(username, new_password)
            st.success("Password updated successfully")
        else:
            st.error("Passwords do not match")

def dashboard_page():
    user = st.session_state.user
    st.title(f"Welcome, {user['username'].capitalize()}!")
    
    if user['role'] == 'admin':
        menu_options = ["Dashboard", "Attendance", "Employees", "Reports", "Admin"]
    else:
        menu_options = ["Dashboard", "Attendance", "Reports"]
    
    selected = st.sidebar.selectbox("Menu", menu_options, key='menu_select')
    
    if selected == "Dashboard":
        st.subheader("Attendance Overview")
        today = datetime.now().date()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Employees", get_employees().shape[0])
        with col2:
            st.metric("Present Today", get_attendance(today, today).shape[0])
        with col3:
            st.metric("On Leave", get_attendance(today, today).query("status == 'leave'").shape[0])
        
        # Quick actions
        st.subheader("Quick Actions")
        if user['role'] in ['admin', 'manager']:
            if st.button("Add New Employee"):
                st.session_state.page = "add_employee"
                st.rerun()
        
        if st.button("Mark My Attendance"):
            st.session_state.page = "mark_attendance"
            st.rerun()
    
    elif selected == "Attendance":
        attendance_page()
    
    elif selected == "Employees":
        employees_page()
    
    elif selected == "Reports":
        reports_page()
    
    elif selected == "Admin" and user['role'] == 'admin':
        admin_page()

def attendance_page():
    st.subheader("Attendance Management")
    
    tab1, tab2 = st.tabs(["Mark Attendance", "View Attendance"])
    
    with tab1:
        emp_id = st.text_input("Employee ID")
        date = st.date_input("Date", datetime.now())
        entry_time = st.time_input("Entry Time", datetime.now().time())
        exit_time = st.time_input("Exit Time (optional)", value=None)
        
        status = st.selectbox("Status", ["present", "late", "leave", "half-day"])
        permission_reason = st.text_area("Permission Reason (if applicable)")
        
        with st.expander("Break Details"):
            col1, col2 = st.columns(2)
            with col1:
                break_in = st.time_input("Break In Time")
                break_late = st.checkbox("Break Late?")
            with col2:
                break_out = st.time_input("Break Out Time")
        
        with st.expander("Lunch Details"):
            col1, col2 = st.columns(2)
            with col1:
                lunch_in = st.time_input("Lunch In Time")
                lunch_late = st.checkbox("Lunch Late?")
            with col2:
                lunch_out = st.time_input("Lunch Out Time")
        
        if st.button("Submit Attendance"):
            record_attendance(
                emp_id=emp_id,
                date=date,
                entry_time=entry_time,
                exit_time=exit_time,
                status=status,
                permission_reason=permission_reason if permission_reason else None,
                break_in=break_in,
                break_out=break_out,
                break_late=break_late,
                lunch_in=lunch_in,
                lunch_out=lunch_out,
                lunch_late=lunch_late
            )
            st.success("Attendance recorded successfully")
    
    with tab2:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", start_date)
        with col2:
            end_date = st.date_input("End Date", end_date)
        
        attendance_df = get_attendance(start_date, end_date)
        if not attendance_df.empty:
            # Format break and lunch information for display
            attendance_df['break_info'] = attendance_df.apply(
                lambda row: f"{row['break_in']} - {row['break_out']}" + (" (Late)" if row['break_late'] else ""), 
                axis=1
            )
            attendance_df['lunch_info'] = attendance_df.apply(
                lambda row: f"{row['lunch_in']} - {row['lunch_out']}" + (" (Late)" if row['lunch_late'] else ""), 
                axis=1
            )
            
            # Display only relevant columns
            display_cols = ['emp_id', 'name', 'role', 'team', 'date', 'entry_time', 'exit_time', 
                           'status', 'break_info', 'lunch_info', 'permission_reason']
            st.dataframe(attendance_df[display_cols])
            
            # Export button with all data
            csv = attendance_df.to_csv(index=False)
            st.download_button(
                label="Export to CSV",
                data=csv,
                file_name=f"attendance_{start_date}_{end_date}.csv",
                mime='text/csv'
            )
        else:
            st.warning("No attendance records found for selected period")

def employees_page():
    st.subheader("Employee Management")
    
    tab1, tab2 = st.tabs(["Add Employee", "View Employees"])
    
    with tab1:
        with st.form("employee_form"):
            emp_id = st.text_input("Employee ID*")
            name = st.text_input("Full Name*")
            role = st.text_input("Job Role")
            team = st.text_input("Team/Department")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number")
            
            if st.form_submit_button("Add Employee"):
                if emp_id and name:  # Required fields
                    if add_employee(emp_id, name, role, team, email, phone):
                        st.success("Employee added successfully")
                else:
                    st.error("Employee ID and Name are required")
    
    with tab2:
        employees_df = get_employees()
        if not employees_df.empty:
            st.dataframe(employees_df)
            
            # Export button
            csv = employees_df.to_csv(index=False)
            st.download_button(
                label="Export to CSV",
                data=csv,
                file_name="employees_list.csv",
                mime='text/csv'
            )
        else:
            st.warning("No employees registered yet")

def reports_page():
    st.subheader("Attendance Reports")
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", start_date)
    with col2:
        end_date = st.date_input("End Date", end_date)
    
    report_type = st.selectbox("Report Type", 
                             ["Attendance Summary", "Permission Log", "Late Arrivals", 
                              "Break Analysis", "Lunch Analysis"])
    
    if st.button("Generate Report"):
        if report_type == "Attendance Summary":
            df = get_attendance(start_date, end_date)
            st.dataframe(df)
        elif report_type == "Permission Log":
            df = get_permission_log(start_date, end_date)
            st.dataframe(df)
        elif report_type == "Late Arrivals":
            df = get_attendance(start_date, end_date)
            if not df.empty:
                late_df = df[df['status'] == 'late']
                st.dataframe(late_df)
        elif report_type == "Break Analysis":
            df = get_attendance(start_date, end_date)
            if not df.empty:
                break_df = df[['emp_id', 'name', 'date', 'break_in', 'break_out', 'break_late']]
                st.dataframe(break_df)
        elif report_type == "Lunch Analysis":
            df = get_attendance(start_date, end_date)
            if not df.empty:
                lunch_df = df[['emp_id', 'name', 'date', 'lunch_in', 'lunch_out', 'lunch_late']]
                st.dataframe(lunch_df)
        
        if not df.empty:
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Report",
                data=csv,
                file_name=f"{report_type.replace(' ', '_')}_{start_date}_{end_date}.csv",
                mime='text/csv'
            )

def admin_page():
    st.subheader("Admin Panel")
    st.warning("This section is for administrators only")
    
    tab1, tab2 = st.tabs(["User Management", "System Settings"])
    
    with tab1:
        st.subheader("User Accounts")
        conn = sqlite3.connect('database/attendance.db')
        users_df = pd.read_sql("SELECT username, role FROM userstable", conn)
        conn.close()
        
        st.dataframe(users_df)
        
        with st.expander("Add New User"):
            with st.form("add_user_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type='password')
                role = st.selectbox("Role", ["admin", "manager", "user"])
                
                if st.form_submit_button("Create User"):
                    if add_userdata(username, password, role):
                        st.success("User created successfully")
    
    with tab2:
        st.subheader("Database Maintenance")
        if st.button("Backup Database"):
            # In a real app, implement proper backup functionality
            st.success("Database backup initiated (mock)")
        
        if st.button("Initialize Database"):
            init_db()
            st.success("Database initialized")

# Main App Flow
def main():
    st.set_page_config(page_title="Employee Attendance System", layout="wide")
    
    if not hasattr(st.session_state, 'logged_in'):
        st.session_state.logged_in = False
        st.session_state.menu = "Login"
        st.session_state.page = "dashboard"
    
    # Initialize database
    init_db()
    
    if not st.session_state.logged_in:
        st.title("Employee Attendance System")
        
        if st.session_state.menu == "Login":
            login_page()
        elif st.session_state.menu == "SignUp":
            signup_page()
        elif st.session_state.menu == "Forgot Password":
            forgot_password_page()
        
        st.sidebar.title("Menu")
        menu = ["Login", "SignUp", "Forgot Password"]
        choice = st.sidebar.radio("Navigation", menu, index=menu.index(st.session_state.menu))
        if choice != st.session_state.menu:
            st.session_state.menu = choice
            st.rerun()
    else:
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.pop('user', None)
            st.rerun()
        
        dashboard_page()

if __name__ == "__main__":
    main()