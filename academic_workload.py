from flask import Flask, request, render_template, redirect, url_for, session, jsonify, send_file, request
from werkzeug.utils import secure_filename
import os
import re
import math
import pandas as pd
import csv
from io import BytesIO
from datetime import datetime, timedelta 
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import mysql
from contextlib import closing
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# Database setup
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workload_data.db')

def init_db():
    """Initialize the database with required tables"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS workload (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                faculty_name TEXT NOT NULL,
                course_name TEXT NOT NULL,
                course_id TEXT NOT NULL,
                preparation_time REAL NOT NULL,
                instructor_charge REAL NOT NULL,
                teaching_load REAL NOT NULL,
                evaluation_time REAL NOT NULL,
                wilp_time REAL NOT NULL,
                student_engagement REAL NOT NULL,
                total_workload REAL NOT NULL
            )
            """)
            conn.commit()
        print(f"Database initialized at {os.path.abspath(DATABASE)}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# At startup
if not os.path.exists(DATABASE):
    init_db()
else:
    print(f"Using existing database at {os.path.abspath(DATABASE)}")


# Constants
C_max = 5  # Maximum number of credits of a course
CY_max = 4  # Maximum year of a course
NID = 0.9  # Adjustment for non-instructional days

# Course Type Weights (K_ct)
COURSE_TYPE_WEIGHTS = {
    "cdc_with_lab": 2.5,      # CDC courses with lab component
    "regular_cdc": 1.8,       # Regular CDC courses without lab
    "masters_cdc": 1.2,       # Masters-level CDC courses
    "elective": 1.0,          # All electives
    "masters_elective": 0.8   # Masters-level electives
}

# Class Size Weights (K_cs) - based on number of sections (NSC)
CLASS_SIZE_WEIGHTS = {
    "small": 0.9,    # NSC < 2
    "medium": 1.0,   # 2 <= NSC < 4
    "large": 1.3,    # 4 <= NSC < 6
    "xlarge": 1.6,   # 6 <= NSC < 8
    "xxlarge": 2.0   # NSC >= 8
}

filename = 'Course details.txt'
RESULTS_FILE = 'workload_results.csv'

def parse_courses_file(filename):
    courses = []
    try:
        # Read the CSV file using pandas
        df = pd.read_csv(filename)
        
        # Convert to list of dictionaries
        for _, row in df.iterrows():
            course = {
                'name': row['Course Name'],
                'id': row['Course ID'],
                'L': str(row['L']),
                'T': str(row['T']),
                'P': str(row['P'])
            }
            courses.append(course)
            
        return sorted(courses, key=lambda x: x['name'])
    
    except Exception as e:
        print(f"Error parsing course file: {str(e)}")
        return []

def save_results_to_file(data):
    """Save to both CSV and database with error handling"""
    try:
        # Extract values
        prep_time = float(data['detailed_calculations']['Preparation Time']['NATURAL_LANGUAGE'][-1].split()[0])
        instr_charge = float(data['detailed_calculations']['Instructor In-Charge']['NATURAL_LANGUAGE'][-1].split()[0])
        eval_time = float(data['detailed_calculations']['Evaluation Time']['NATURAL_LANGUAGE'][-1].split()[0])
        wilp_time = float(data['detailed_calculations']['WILP Thesis Supervision']['NATURAL_LANGUAGE'][-1].split()[0])
        stud_engage = float(data['detailed_calculations']['Student Engagement']['NATURAL_LANGUAGE'][-1].split()[0])

        # Save to database (with explicit error handling)
        try:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute("""
                    INSERT INTO workload VALUES (
                        NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, [
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    data['faculty_name'],
                    data['course_name'],
                    data['course_id'],
                    prep_time,
                    instr_charge,
                    float(data['teaching_load']),
                    eval_time,
                    wilp_time,
                    stud_engage,
                    float(data['total_workload'])
                ])
                conn.commit()  # THIS IS CRUCIAL
                
            print(f"Data saved to database at {DATABASE}")  # Debug confirmation
            
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if "no such table" in str(e):
                init_db()
                return save_results_to_file(data)  # Retry after creating table
            
    except Exception as e:
        print(f"Error in save_results_to_file: {e}")

    try:
        file_exists = os.path.isfile(RESULTS_FILE)
        
        with open(RESULTS_FILE, 'a', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'faculty_name', 'course_name', 'course_id', 'course_code', 
                'teaching_load', 'total_workload', 'preparation_time',
                'instructor_charge', 'evaluation_time', 'wilp_time', 'student_engagement'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            # Extract the numeric values from the results
            prep_time = float(data['detailed_calculations']['Preparation Time']['NATURAL_LANGUAGE'][-1].split()[0])
            instr_charge = float(data['detailed_calculations']['Instructor In-Charge']['NATURAL_LANGUAGE'][-1].split()[0])
            eval_time = float(data['detailed_calculations']['Evaluation Time']['NATURAL_LANGUAGE'][-1].split()[0])
            wilp_time = float(data['detailed_calculations']['WILP Thesis Supervision']['NATURAL_LANGUAGE'][-1].split()[0])
            stud_engage = float(data['detailed_calculations']['Student Engagement']['NATURAL_LANGUAGE'][-1].split()[0])
            
            writer.writerow({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'faculty_name': data['faculty_name'],
                'course_name': data['course_name'],
                'course_id': data['course_id'],
                'course_code': data['course_code'],
                'teaching_load': float(data['teaching_load']),
                'total_workload': float(data['total_workload']),
                'preparation_time': prep_time,
                'instructor_charge': instr_charge,
                'evaluation_time': eval_time,
                'wilp_time': wilp_time,
                'student_engagement': stud_engage
            })
            
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        raise  # Re-raise to see in console

# Load courses at startup
all_courses = parse_courses_file('courses.csv')
if not all_courses:
    print("Warning: No courses were loaded. Check the course file format.")

def convert_to_minutes(value, unit):
    try:
        if unit == "hours":
            return float(value) * 60
        return float(value)
    except:
        return 0

def calculate_workload(data):
    try:
        # Course Data
        C = float(data['course_credits'])
        #CY = float(data['course_year'])
        L = float(data['course_lectures'])
        T = float(data['course_tutorials'])
        P = float(data['course_practicals'])
        P_H = convert_to_minutes(data['practical_hours'], data['practical_hours_unit'])
        N_q = float(data['num_quizzes'])
        N_as = float(data['num_assignments'])
        N_hw = float(data['num_homework'])
        N_mid = float(data['num_midsem'])
        N_end = 1  # Assuming 1 endsem
        T_q = convert_to_minutes(data['quiz_duration'], data['quiz_duration_unit'])
        T_mid = convert_to_minutes(data['midsem_duration'], data['midsem_duration_unit'])
        T_end = convert_to_minutes(data['endsem_duration'], data['endsem_duration_unit'])
        NSC = float(data['num_sections'])
        NS = float(data['total_students']) / NSC if NSC > 0 else 0
        TS = float(data['total_students'])
        
        # Faculty Data
        CC = float(data['content_change']) / 100
        IC = 1 if data.get('is_ic') == 'YES' else 0
        TP = float(data['total_professors'])
        NP = TP / NSC if NSC > 0 else 0
        D_base = 2  # Base hours for doubt-solving
        Y_current = float(data['years_current'])
        Y_1 = float(data['years_break1'])
        Y_2 = float(data['years_break2'])
        t_1 = float(data['break1_years'])
        t_2 = float(data['break2_years'])
        PT_f = convert_to_minutes(data['tutorial_prep_time'], data['tutorial_prep_time_unit'])
        PP_f = convert_to_minutes(data['lab_prep_time'], data['lab_prep_time_unit'])
        E_q = convert_to_minutes(data['quiz_eval_time'], data['quiz_eval_time_unit'])
        E_as = convert_to_minutes(data['assignment_eval_time'], data['assignment_eval_time_unit'])
        E_hw = convert_to_minutes(data['homework_eval_time'], data['homework_eval_time_unit'])
        E_mid = convert_to_minutes(data['midsem_eval_time'], data['midsem_eval_time_unit'])
        E_end = convert_to_minutes(data['endsem_eval_time'], data['endsem_eval_time_unit'])
        QP_q = convert_to_minutes(data['quiz_qp_time'], data['quiz_qp_time_unit'])
        QP_as = convert_to_minutes(data['assignment_qp_time'], data['assignment_qp_time_unit'])
        QP_hw = convert_to_minutes(data['homework_qp_time'], data['homework_qp_time_unit'])
        QP_mid = convert_to_minutes(data['midsem_qp_time'], data['midsem_qp_time_unit'])
        QP_end = convert_to_minutes(data['endsem_qp_time'], data['endsem_qp_time_unit'])
        D_mid = 60 * NSC  
        RC_mid = convert_to_minutes(data['midsem_recheck_time'], data['midsem_recheck_time_unit'])
        D_end = 60 * NSC
        RC_end = convert_to_minutes(data['endsem_recheck_time'], data['endsem_recheck_time_unit'])
        N_WT = float(data['wilp_thesis'])
        WT_ap = convert_to_minutes(data['wilp_approval_time'], data['wilp_approval_time_unit'])
        WT_mid = convert_to_minutes(data['wilp_midterm_eval_time'], data['wilp_midterm_eval_time_unit'])
        WT_fin = convert_to_minutes(data['wilp_final_eval_time'], data['wilp_final_eval_time_unit'])
        
        # TA Data
        RT_ta = float(data['ta_tutorial_reduction']) / 100 if 'ta_tutorial_reduction' in data and data['ta_tutorial_reduction'] else 0
        RP_ta = float(data['ta_lab_reduction']) / 100 if 'ta_lab_reduction' in data and data['ta_lab_reduction'] else 0
        RE_q = float(data['ta_quiz_reduction']) / 100 if 'ta_quiz_reduction' in data and data['ta_quiz_reduction'] else 0
        RE_as = float(data['ta_assignment_reduction']) / 100 if 'ta_assignment_reduction' in data and data['ta_assignment_reduction'] else 0
        RE_hw = float(data['ta_homework_reduction']) / 100 if 'ta_homework_reduction' in data and data['ta_homework_reduction'] else 0
        RE_mid = float(data['ta_midsem_reduction']) / 100 if 'ta_midsem_reduction' in data and data['ta_midsem_reduction'] else 0
        RE_end = float(data['ta_endsem_reduction']) / 100 if 'ta_endsem_reduction' in data and data['ta_endsem_reduction'] else 0
        
        course_id = data['course_code']
        CY = int(re.search(r'\d', course_id).group()[0]) if re.search(r'\d', course_id) else 1
        course_type = data.get('course_type', 'regular_cdc')

        # Determine class size category based on NSC
        if NS < 50:
            class_size = 'small'
        elif 50 <= NS < 100:
            class_size = 'medium'
        elif 100 <= NS < 200:
            class_size = 'large'
        elif 200 <= NS < 300:
            class_size = 'xlarge'
        else:
            class_size = 'xxlarge'

        K_ct = COURSE_TYPE_WEIGHTS.get(course_type, 1.0)
        K_cs = CLASS_SIZE_WEIGHTS.get(class_size, 1.0)

        # Derived calculations
        P_T = P * P_H / 60  # Total practical hours per week per section
        H = L + T + P_T  # Total hours per week per section
        D_percent = (C / C_max) * (CY / CY_max)  # Difficulty percentage
        if NSC / NP <= 1:
            H_base = L * (K_ct * K_cs + D_percent) * NSC / NP  # Base preparation time
        else:
            H_base = L * (K_ct * K_cs + D_percent)  #exception: if 1 professor is delivering the same same lecture multiple times, preparation timw will only be needed once
        
        # Load reduction calculations
        k = (C_max * CY_max * (1 - D_percent) - (C_max * CY_max) / 2) / 100
        L_Y_current = (1 - 0.5) * math.exp(-k * Y_current) + 0.5
        L_Y_1 = (1 - 0.5) * math.exp(-k * Y_1) + 0.5
        L_Y_2 = (1 - 0.5) * math.exp(-k * Y_2) + 0.5
        B_1 = math.exp(-1 / t_1) / 10 if t_1 > 0 else 0
        B_2 = math.exp(-1 / t_2) / 10 if t_2 > 0 else 0
        L_Y = L_Y_current - (L_Y_1 * B_1 + L_Y_2 * B_2)
        
        # IC calculations
        IC_base = C * D_percent
        IC_extra = IC_base * NP / NSC if NSC > 0 else 0
        IC_total = IC_base + IC_extra * (NSC - 1) if IC else 0
        
        # Evaluation time calculations
        T_eval = (E_q * (1 - RE_q) * N_q + 
                 E_as * (1 - RE_as) * N_as + 
                 E_hw * (1 - RE_hw) * N_hw + 
                 E_mid * (1 - RE_mid) * N_mid + 
                 E_end * (1 - RE_end) * N_end)
        T_inv = N_q * T_q + N_mid * T_mid + N_end * T_end
        T_qp = (QP_q * N_q + QP_as * N_as + QP_hw * N_hw + 
               QP_mid * N_mid + QP_end * N_end)
        
        # Preparation Time
        HP = (H_base * L_Y * (1 + CC) + 
             (PT_f * (1 - RT_ta) * T +
             PP_f * (1 - RP_ta) * P)) / 60
        
        # Classroom Hours
        TL = (L + T + P_T) * NID * (NSC / TP)
        
        # WILP Thesis Time calculations
        WT_total = (WT_ap + WT_mid + WT_fin) * N_WT / 60  # Convert to hours
        WT_weekly = WT_total / 12  # Spread over semester
        
        # Evaluation Time (now excluding WILP)
        ET_semester = (T_eval * (TS / TP) + T_inv + T_qp + 
                      D_mid + RC_mid + D_end + RC_end) / 60
        ET = ET_semester / 12
        
        # Student Engagement
        SE = D_base + (0.01 * D_percent * (TS / TP))
        
        # Total Workload
        total_workload = HP + IC_total + TL + ET + WT_weekly + SE
        
        # Prepare detailed breakdown in the specified order
        detailed_calculations = {
            "Enhanced Calculation Structure": {
                "description": "The detailed calculations now include the 6 factors we have divided the total workload into namely, Preparation Time, Instructor Charge, Teaching Load, Evaluation Time, WILP Thesis Supervision, and Student Engagement:"
            },
            "Preparation Time": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"Your course type is {course_type.replace('_', ' ').title()} with {NS:.2f} number of students and {CC*100:.2f}% of content changes compared to previous offerings.",
                    "",
                    "From your experience and other factors:",
                    f"Your experience with this course results in a {L_Y:.2f} preparation efficiency factor.",
                    f"You spend {PT_f:.2f} minutes preparing for each tutorial session and {PP_f:.2f} minutes for each lab session.",
                    f"Teaching assistants help reduce your preparation time by {RT_ta*100:.2f}% for tutorials and {RP_ta*100:.2f}% for labs.",
                    "",
                    "Considering all these factors, your total weekly preparation time is estimated to be:",
                    f"{HP:.2f} hours/week"
                ]
            },
            "Instructor In-Charge": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"You are coordinating {NSC:.0f} sections of this course.",
                    "",
                    "From our calculations:",
                    f"The base coordination workload is {IC_base:.2f} hours, with an additional {IC_extra:.2f} hours per extra section.",
                    "",
                    "Your total weekly coordination workload is estimated to be:",
                    f"{IC_total:.2f} hours/week"
                ]
            },
            "Classroom Hours": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"Your course includes {L:.2f} lecture hours, {T:.2f} tutorial hours, and {P_T:.2f} practical hours per week.",
                    f"You teach {NSC:.0f} sections with {TP:.0f} professors sharing the teaching.",
                    "",
                    "From our calculations:",
                    f"After accounting for your course load and shared teaching responsibilities, your actual classroom hours is estimated.",
                    "",
                    "Your weekly classroom teaching load is estimated to be:",
                    f"{TL:.2f} hours/week"
                ]
            },
            "Evaluation Time": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"You evaluate work for {TS:.0f} students, shared among {TP:.0f} professors.",
                    "",
                    "From our calculations:",
                    "Your evaluation activities include grading quizzes, assignments, and exams. Spread evenly across the semester, this workload averages out to:",
                    "",
                    "Your weekly evaluation time is estimated to be:",
                    f"{ET:.2f} hours/week"
                ]
            },
            "WILP Thesis Supervision": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"You are supervising {N_WT:.0f} WILP thesis.",
                    "",
                    "From our calculations:",
                    f"Your WILP supervision activities include approval, midterm evaluation, and final evaluation, totaling {WT_total:.2f} hours per semester.",
                    "",
                    "Spread evenly across the semester, your weekly WILP supervision time is estimated to be:",
                    f"{WT_weekly:.2f} hours/week"
                ]
            },
            "Student Engagement": {
                "NATURAL_LANGUAGE": [
                    "Based on your input:",
                    f"You have {TS:.0f} students in your course, with teaching shared among {TP:.0f} professors.",
                    "",
                    "From our calculations:",
                    f"Your base office hours are {D_base:.1f} hours, with additional time needed based on class size and course difficulty.",
                    "",
                    "Your weekly student engagement time is estimated to be:",
                    f"{SE:.2f} hours/week"
                ]
            },
            "Total Workload": {
                "NATURAL_LANGUAGE": [
                    "Combining all components, your total weekly workload includes preparation time, classroom teaching, evaluation activities, WILP supervision, student engagement, and coordination duties.",
                    "",
                    "Your complete weekly workload is estimated to be:",
                    f"{total_workload:.2f} hours/week"
                ]
            }
        }
        
        # Prepare intermediate results for display
        intermediate_results = {
            "Course Difficulty (D%)": f"{D_percent:.2%}",
            "Base Preparation Time (H_base)": f"{H_base:.2f} hours/week",
            "Load Reduction Factor (L(Y))": f"{L_Y:.2f}",
            "Preparation Time": f"{HP:.2f} hours/week",
            "Instructor Charge Duties (IC)": f"{IC_total:.2f} hours/week",
            "Classroom Hours": f"{TL:.2f} hours/week",
            "Evaluation Time": f"{ET:.2f} hours/week",
            "Student Engagement": f"{SE:.2f} hours/week",
            "Total Practical Hours (P_T)": f"{P_T:.2f} hours/week/section",
            "Total Hours (H)": f"{H:.2f} hours/week/section",
            "Evaluation Time per Semester": f"{ET_semester:.2f} hours/semester",
            "Invigilation Time": f"{T_inv/60:.2f} hours/semester",
            "Question Paper Preparation": f"{T_qp/60:.2f} hours/semester",
            "WILP Thesis Time": f"{(WT_ap + WT_mid + WT_fin) * N_WT / 60:.2f} hours/semester"
        }
        
        return {
            "teaching_load": TL,
            "total_workload": total_workload,
            "intermediate_results": intermediate_results,
            "detailed_calculations": detailed_calculations
        }
        
    except Exception as e:
        print(f"Error in calculations: {str(e)}")
        return None

@app.route('/get_course_details/<course_name>')
def get_course_details(course_name):
    course_name = course_name.split(' (')[0].strip()
    course = next((c for c in all_courses if c['name'] == course_name), None)
    if course:
        return jsonify({
            'id': course['id'],
            'L': course['L'],
            'T': course['T'],
            'P': course['P']
        })
    return jsonify({'error': 'Course not found'}), 404

@app.route('/download_csv', methods=['POST'])
def download_csv():
    try:
        if 'detailed_calculations' not in session:
            return "No data to download", 400
        
        # Verify all required session data exists
        required_keys = ['course_name', 'course_id', 'faculty_name', 'detailed_calculations']
        if not all(key in session for key in required_keys):
            return redirect(url_for('index'))
            
        faculty_name = session['faculty_name']
        course_name = session['course_name']
        course_id = session['course_id']
        data = session['detailed_calculations']
        
        # Define the order of sections
        section_order = [
            "Preparation Time",
            "Instructor In-Charge",
            "Classroom Hours",
            "Evaluation Time",
            "WILP Thesis Supervision",
            "Student Engagement",
            "Total Workload"
        ]
        
        # Prepare CSV data as a single string with proper line endings
        csv_content = []
        
        # Add header
        csv_content.append("Workload Calculation Report")
        csv_content.append(f"Faculty: {session.get('faculty_name', 'N/A')}")
        csv_content.append(f"Course Name: {session.get('course_name', 'N/A')}")
        csv_content.append(f"Course ID: {session.get('course_id', 'N/A')}")
        csv_content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        csv_content.append("")
        
        # Add each section in the specified order
        for section in section_order:
            if section not in data:
                continue
                
            section_data = data[section]
            csv_content.append(section)
            
            # Add NATURAL_LANGUAGE section if it exists
            if 'NATURAL_LANGUAGE' in section_data:
                for line in section_data['NATURAL_LANGUAGE']:
                    if line.strip() == "":
                        csv_content.append("")
                    else:
                        csv_content.append(line)
            csv_content.append("")
        
        # Convert list to a single string with newlines
        csv_string = "\n".join(csv_content)
        
        # Create BytesIO buffer with encoded content
        output = BytesIO()
        output.write(csv_string.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='workload_calculations.csv'
        )
        
    except Exception as e:
        print(f"Error generating CSV: {str(e)}")
        return "Error generating file. Please try again.", 500

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    try:
        if 'detailed_calculations' not in session:
            return "No data available for PDF generation. Please submit the form first.", 400
        
        required_keys = ['course_name', 'course_id', 'faculty_name', 'detailed_calculations']
        if not all(key in session for key in required_keys):
            return redirect(url_for('index'))  # Redirect back if data is missing
            
        faculty_name = session['faculty_name']
        course_name = session['course_name']
        course_id = session['course_id']
        data = session['detailed_calculations']
        faculty_name = session.get('faculty_name', 'Faculty')
        
        # Create PDF in memory
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
            title=f"Workload Calculation for {faculty_name}"
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='NaturalLanguage',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=6
        ))
        
        elements = []
        
        # Title
        elements.append(Paragraph(
            f"Detailed Workload Calculation for {faculty_name}",
            styles['Title']
        ))
        elements.append(Paragraph(
            f"Course: {session.get('course_name', 'N/A')} ({session.get('course_id', 'N/A')})",
            styles['Normal']
        ))
        elements.append(Paragraph(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             styles['Normal']
        ))
        elements.append(Spacer(1, 12))
        
        # Add each calculation section in the specified order
        section_order = [
            "Preparation Time",
            "Instructor In-Charge",
            "Classroom Hours",
            "Evaluation Time",
            "WILP Thesis Supervision",
            "Student Engagement",
            "Total Workload"
        ]
        
        for section in section_order:
            if section not in data:
                continue
                
            section_data = data[section]
            
            # Section header
            elements.append(Paragraph(
                f"<b>{section}</b>",
                styles['Heading2']
            ))
            
            # Add NATURAL_LANGUAGE section if it exists
            if 'NATURAL_LANGUAGE' in section_data:
                for line in section_data['NATURAL_LANGUAGE']:
                    if line.strip() == "":
                        elements.append(Spacer(1, 6))
                    else:
                        elements.append(Paragraph(
                            line,
                            styles['NaturalLanguage']
                        ))
                elements.append(Spacer(1, 12))
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'workload_calculation_{faculty_name.replace(" ", "_")}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return "Error generating PDF. Please try again.", 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form.to_dict()
        result = None
        teaching_load = None
        total_workload = None
        intermediate_results = None
        detailed_calculations = None
        
        course_full = data.get('course_name', '')
        course_parts = course_full.split(' (')
        course_name = course_parts[0].strip() if course_parts else ''
        course_id = data['course_code']

        if 'course_type' not in data or not data['course_type']:
            data['course_type'] = 'regular_cdc'
        
        # Validate that all fields are filled
        if not all(data.values()):
            result = "Error: All fields are required."
        else:
            # Validate numeric inputs
            for key, value in data.items():
                if key.endswith('_unit') or key == 'is_ic':
                    continue
                if value.isdigit() and int(value) < 0:
                    result = "Error: Negative values are not allowed."
                    break
            else:
                # Validate course code format
                course_id = data['course_code']
                if not re.match(r'^[A-Za-z]+\s[A-Za-z]+\d{3}$', course_id):
                    result = "Error: Please select a valid course from the dropdown."
                else:
                    # Perform calculations
                    calculation_result = calculate_workload(data)
                    if calculation_result:
                        result = "Thank you for submitting!"
                        teaching_load = f"{calculation_result['teaching_load']:.2f}"
                        total_workload = f"{calculation_result['total_workload']:.2f}"
                        intermediate_results = calculation_result['intermediate_results']
                        detailed_calculations = calculation_result['detailed_calculations']
                        
                        # Save the results
                        save_data = {
                            'faculty_name': data['faculty_name'],
                            'course_name': course_name,  
                            'course_id': course_id,
                            'course_code': data['course_code'],
                            'teaching_load': teaching_load,
                            'total_workload': total_workload,
                            'detailed_calculations': detailed_calculations
                        }
                        save_results_to_file(save_data)
                    else:
                        result = "Error calculating workload."
        
        # Store the result in session
        session['submission_data'] = {
            'result': result,
            'teaching_load': teaching_load,
            'total_workload': total_workload,
            'intermediate_results': intermediate_results,
            'detailed_calculations': detailed_calculations,
            'course_id': course_id,
            'course_name': course_name,  # Store course name in session
            'faculty_name': data['faculty_name']
        }

        session['course_id'] = course_id
        session['course_name'] = course_name
        session['faculty_name'] = data['faculty_name']
        session['detailed_calculations'] = detailed_calculations
        return redirect(url_for('index'))
    
    # Check for stored submission result
    submission_data = session.pop('submission_data', None)
    if submission_data:
        # Store data in session for downloads
        if submission_data['intermediate_results']:
            session['intermediate_results'] = submission_data['intermediate_results']
            session['detailed_calculations'] = submission_data['detailed_calculations']
            session['faculty_name'] = submission_data['faculty_name']
        
        return render_template('result.html', 
                            submission_data=submission_data,
                            intermediate_results=submission_data['intermediate_results'],
                            detailed_calculations=submission_data['detailed_calculations'])
    
    # Show the form for the first time
    return render_template('form.html', courses=all_courses)

@app.route('/admin/data')
def admin_data():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50  # Items per page
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count for pagination
            cursor.execute("SELECT COUNT(*) FROM workload")
            total = cursor.fetchone()[0]
            
            # Get paginated data
            cursor.execute("""
                SELECT * FROM workload 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (per_page, (page-1)*per_page))
            data = cursor.fetchall()
            
        return render_template('admin_data.html', 
                            data=data,
                            page=page,
                            per_page=per_page,
                            total=total)
    except Exception as e:
        return f"Database error: {str(e)}", 500

@app.route('/admin/download_all')
def download_all_data():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workload ORDER BY timestamp DESC")
            data = cursor.fetchall()
            
        # Create CSV in memory
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Timestamp', 'Faculty Name', 'Course Name', 'Course ID',
            'Preparation Time', 'Instructor Charge', 'Teaching Load',
            'Evaluation Time', 'WILP Time', 'Student Engagement', 'Total Workload'
        ])
        
        # Write data
        for row in data:
            writer.writerow(row)
            
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='all_workload_data.csv'
        )
    except Exception as e:
        return f"Error generating download: {str(e)}", 500
    
@app.route('/debug_db')
def debug_db():
    """Debug route to check database contents"""
    try:
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row  # For nicer dictionary output
            cursor = conn.cursor()
            
            # First show all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            # Then show workload data if table exists
            workload_data = []
            if any(t['name'] == 'workload' for t in tables):
                cursor.execute("SELECT * FROM workload ORDER BY timestamp DESC")
                workload_data = [dict(row) for row in cursor.fetchall()]
            
            return render_template_string('''
                <h1>Database Debug</h1>
                <h2>Tables in Database</h2>
                <pre>{{ tables|tojson(indent=2) }}</pre>
                <h2>Workload Data ({{ workload_data|length }} rows)</h2>
                <pre>{{ workload_data|tojson(indent=2) }}</pre>
                <h2>Database Location</h2>
                <p>{{ db_path }}</p>
            ''', 
            tables=tables,
            workload_data=workload_data,
            db_path=os.path.abspath(DATABASE))
            
    except Exception as e:
        return f"<h1>Database Error</h1><pre>{str(e)}</pre>", 500
    
@app.route('/db_info')
def db_info():
    db_status = {
        "database_path": os.path.abspath(DATABASE),
        "exists": os.path.exists(DATABASE),
        "size": os.path.getsize(DATABASE) if os.path.exists(DATABASE) else 0,
        "tables": []
    }
    
    if db_status["exists"]:
        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                db_status["tables"] = [row[0] for row in cursor.fetchall()]
        except Exception as e:
            db_status["error"] = str(e)
    
    return jsonify(db_status)

@app.route('/clear_session')
def clear_session():
    session.clear()
    return "Session cleared"

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create results file if it doesn't exist
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'faculty_name', 'course_name','course_id', 'course_code',
                'teaching_load', 'total_workload', 'preparation_time',
                'instructor_charge', 'evaluation_time', 'student_engagement'
            ])
    
    print("Starting application...")
    app.run(debug=True, host='0.0.0.0', port=5001)