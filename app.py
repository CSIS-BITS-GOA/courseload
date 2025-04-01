from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for, session, jsonify
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
import time
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Define Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Spreadsheet ID and sheet name
SPREADSHEET_ID = '1lXvk0dmhF49cb0o_9gqiigD-re6Vgh-vS5YVWSl8b4g'
SHEET_NAME = 'Workload_Automatic'

# Starting column (B corresponds to index 2)
column_counter = 3

# Parse course details from the text file
def parse_course_details():
    courses = []
    with open('Course details.txt', 'r', encoding='utf-8-sig') as file:
        content = file.read()
    
    # Split by double newlines to separate each course
    course_blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in course_blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) >= 3:
            course = {}
            course['name'] = lines[0].replace('Course Name: ', '')
            course['id'] = lines[1].replace('Course ID: ', '')
            
            # Parse L, T, P values
            for line in lines[2:]:
                if line.startswith('L:'):
                    course['L'] = line.split(':')[1].strip()
                elif line.startswith('T:'):
                    course['T'] = line.split(':')[1].strip()
                elif line.startswith('P:'):
                    course['P'] = line.split(':')[1].strip()
            
            # Ensure all fields are present
            if 'L' in course and 'T' in course and 'P' in course:
                courses.append(course)
    
    return courses

# Get all courses
all_courses = parse_course_details()

def verify_google_sheets_access():
    try:
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        # Test reading a cell
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="'Workload_Automatic'!A1"
        ).execute()
        
        print("✅ Successful connection to Google Sheets")
        print("Test read result:", result)
        return True
    except Exception as e:
        print("❌ Failed to access Google Sheets:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        return False

# Authenticate with Google Sheets API
def authenticate_google_sheets():
    try:
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"Error authenticating: {e}")
        return None

# Convert column index to letter (e.g., 2 -> B, 27 -> AA)
def column_to_letter(column):
    letter = ''
    while column > 0:
        column, remainder = divmod(column - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter

def update_google_sheet(data):
    global column_counter
    print("\n=== Starting update_google_sheet ===")
    print(f"Current column counter: {column_counter}")
    
    # Verify we have the sheet name
    if 'SHEET_NAME' not in globals():
        print("❌ Error: SHEET_NAME is not defined")
        return False
        
    service = authenticate_google_sheets()
    if service is None:
        print("❌ Failed to authenticate with Google Sheets")
        return False

    try:
        # Debug: Print received data
        print("\nReceived form data:")
        for key, value in data.items():
            print(f"{key}: {value}")

        # Convert time inputs to minutes
        def convert_to_minutes(value, unit):
            try:
                if unit == "hours":
                    return int(float(value) * 60)
                return int(value)
            except Exception as e:
                print(f"⚠️ Conversion error for {value} {unit}: {str(e)}")
                return 0  # Default to 0 if conversion fails

        # Convert YES/NO to 1/0
        is_ic = 1 if data.get('is_ic') == 'YES' else 0
        
        # Prepare the data for the Google Sheet according to the specified breakdown
        values = [
            # 1. Professor Name
            data['faculty_name'],  # F - Faculty name
            
            # 2. Course Information
            data['course_code'],    # C_code - course code
            data['course_year'],    # CY - Course year
            data['course_credits'], # C - Course credits
            data['course_lectures'],  # L - Lectures
            data['course_tutorials'],  # T - Tutorials
            data['course_practicals'],   # P - Practicals
            convert_to_minutes(data['practical_hours'], data['practical_hours_unit']),  # P_H - Number of hours of each practical
            data['num_quizzes'],    # N_q - Number of quizzes in the semester
            data['num_assignments'], # N_as - Number of assignments (in lab) in the semester
            data['num_homework'],   # N_hw - Number of homework/project in the semester
            data['num_midsem'],     # N_mid - Number of midsem exam in the semester
            convert_to_minutes(data['quiz_duration'], data['quiz_duration_unit']),  # T_q - Duration of each quiz (in minutes)
            convert_to_minutes(data['midsem_duration'], data['midsem_duration_unit']),  # T_mid - Duration of midsem exam (in minutes)
            convert_to_minutes(data['endsem_duration'], data['endsem_duration_unit']),  # T_end - Duration of comprehensive exam (endsem) (in minutes)
            data['num_sections'],   # NSC - Number of sections in the course
            data['total_students'], # TS - Total number of students in the course
            
            # 3. Faculty Information
            is_ic,                  # IC - Whether professor is IC (1/0)
            data['content_change'], # CC% - Percentage of content change
            data['total_professors'], # TP - Total number of professors
            data['years_current'],  # Y_current - Years teaching continuously
            data['years_break1'],   # Y_1 - Years teaching after first break
            data['years_break2'],   # Y_2 - Years teaching after second break
            data['break1_years'],   # t_1 - Years since first break
            data['break2_years'],   # t_2 - Years since second break
            convert_to_minutes(data['tutorial_prep_time'], data['tutorial_prep_time_unit']),  # PT_f - Tutorial prep time (minutes)
            convert_to_minutes(data['lab_prep_time'], data['lab_prep_time_unit']),  # PP_f - Practical prep time (minutes)
            convert_to_minutes(data['quiz_eval_time'], data['quiz_eval_time_unit']),  # E_q - Quiz eval time (minutes)
            convert_to_minutes(data['assignment_eval_time'], data['assignment_eval_time_unit']),  # E_as - Assignment eval time (minutes)
            convert_to_minutes(data['homework_eval_time'], data['homework_eval_time_unit']),  # E_hw - Homework eval time (minutes)
            convert_to_minutes(data['midsem_eval_time'], data['midsem_eval_time_unit']),  # E_mid - Midsem eval time (minutes)
            convert_to_minutes(data['endsem_eval_time'], data['endsem_eval_time_unit']),  # E_end - Endsem eval time (minutes)
            convert_to_minutes(data['quiz_qp_time'], data['quiz_qp_time_unit']),  # QP_q - Quiz QP prep time (minutes)
            convert_to_minutes(data['assignment_qp_time'], data['assignment_qp_time_unit']),  # QP_as - Assignment QP prep time (minutes)
            convert_to_minutes(data['homework_qp_time'], data['homework_qp_time_unit']),  # QP_hw - Homework QP prep time (minutes)
            convert_to_minutes(data['midsem_qp_time'], data['midsem_qp_time_unit']),  # QP_mid - Midsem QP prep time (minutes)
            convert_to_minutes(data['endsem_qp_time'], data['endsem_qp_time_unit']),  # QP_end - Endsem QP prep time (minutes)
            convert_to_minutes(data['midsem_recheck_time'], data['midsem_recheck_time_unit']),  # RC_mid - Midsem recheck time (minutes)
            convert_to_minutes(data['endsem_recheck_time'], data['endsem_recheck_time_unit']),  # RC_end - Endsem recheck time (minutes)
            
            # 4. WILP Thesis Information
            data['wilp_thesis'],    # N_WT - Number of WILP Thesis
            convert_to_minutes(data['wilp_approval_time'], data['wilp_approval_time_unit']),  # WT_ap - Approval time (minutes)
            convert_to_minutes(data['wilp_midterm_eval_time'], data['wilp_midterm_eval_time_unit']),  # WT_mid - Midterm eval time (minutes)
            convert_to_minutes(data['wilp_final_eval_time'], data['wilp_final_eval_time_unit']),  # WT_fin - Final eval time (minutes)
            
            # 5. TA Information
            data['ta_tutorial_reduction'],  # RT_ta - Tutorial prep reduction %
            data['ta_lab_reduction'],       # RP_ta - Practical prep reduction %
            data['ta_quiz_reduction'],      # RE_q - Quiz eval reduction %
            data['ta_assignment_reduction'], # RE_as - Assignment eval reduction %
            data['ta_homework_reduction'],  # RE_hw - Homework eval reduction %
            data['ta_midsem_reduction'],    # RE_mid - Midsem eval reduction %
            data['ta_endsem_reduction']     # RE_end - Endsem eval reduction %
        ]

        # Debug: Print prepared values
        print("\nPrepared values for sheet:")
        for i, value in enumerate(values, 1):
            print(f"Row {i}: {value}")

        column_letter = column_to_letter(column_counter)
        range_name = f"'{SHEET_NAME}'!{column_letter}1:{column_letter}71"
        
        print(f"\nAttempting to write to range: {range_name}")  # Debug

        body = {
            'values': [[value] for value in values]
        }

        # Debug: Print request body
        print("\nRequest body:")
        print(body)

        # Execute the update
        request = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body
        )
        
        print("\nExecuting API request...")  # Debug
        response = request.execute()
        
        print("\n✅ Success! API Response:")  # Debug
        print(response)
        
        column_counter += 1
        return True

    except Exception as e:
        print("\n❌ Error in update_google_sheet:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Print detailed traceback
        import traceback
        traceback.print_exc()
        
        return False

@app.route('/get_course_details/<course_name>')
def get_course_details(course_name):
    course = next((c for c in all_courses if c['name'] == course_name), None)
    if course:
        return jsonify({
            'id': course['id'],
            'L': course['L'],
            'T': course['T'],
            'P': course['P']
        })
    return jsonify({'error': 'Course not found'}), 404

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

         # Check if this is a resubmission (not needed anymore as we'll clear the session)
        if 'submitted' in session:
            session.pop('submitted', None)  # Clear the submitted flag
        
        data = request.form.to_dict()
        result = None
        teaching_load = None
        total_workload = None
        
        # Validate that all fields are filled
        if not all(data.values()):
            result = "Error: All fields are required."
        else:
            # Validate numeric inputs to ensure they are non-negative
            for key, value in data.items():
                if key.endswith('_unit') or key == 'is_ic':  # Skip unit fields and IC status
                    continue
                if value.isdigit() and int(value) < 0:
                    result = "Error: Negative values are not allowed."
                    break
            else:
                if update_google_sheet(data):
                    session['submitted'] = True  # Mark as submitted
                    result = "Thank you for submitting!"
                    # Wait for 10 seconds to allow Google Sheets to calculate values
                    time.sleep(10)
                    
                    # Fetch the calculated values from the sheet
                    service = authenticate_google_sheets()
                    if service:
                        # Get teaching load from row 129 and total workload from row 169
                        range_string = f"{SHEET_NAME}!{column_to_letter(column_counter - 1)}129:{column_to_letter(column_counter - 1)}169"
                        response = service.spreadsheets().values().get(
                            spreadsheetId=SPREADSHEET_ID,
                            range=range_string
                        ).execute()
                        values = response.get('values', [])
                        
                        if values and len(values) >= 41:  # 169-129+1=41 rows
                            try:
                                teaching_load = values[0][0] if len(values[0]) > 0 else "N/A"  # Row 129
                            except IndexError:
                                teaching_load = "N/A"
                            
                            try:
                                total_workload = values[40][0] if len(values[40]) > 0 else "N/A"  # Row 169
                            except IndexError:
                                total_workload = "N/A"
                        else:
                            teaching_load = "N/A"
                            total_workload = "N/A"
                else:
                    result = "Error submitting data."
        
        # Store the result in session to display after redirect
        session['submission_data'] = {
            'result': result,
            'teaching_load': teaching_load,
            'total_workload': total_workload,
            'faculty_name': data['faculty_name']
        }
        return redirect(url_for('index'))
    
    # Check for stored submission result to display
    submission_data = session.pop('submission_data', None)
    if submission_data:
        return render_template_string('''
            <html>
                <head>
                    <title>Faculty Workload Estimation</title>
                    <style>
                        body {
                            font-family: Calibri, modern sans-serif;
                            background-color: #f4f4f4;
                            margin: 0;
                            padding: 20px;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            flex-direction: column;
                        }
                        .container {
                            background-color: #fff;
                            padding: 20px;
                            border-radius: 8px;
                            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                            width: 90%;
                            max-width: 600px;
                        }
                        h2 {
                            color: #333;
                            text-align: center;
                            margin-bottom: 20px;
                        }
                        .result {
                            margin-top: 20px;
                            color: #28a745;
                            font-weight: bold;
                            text-align: center;
                        }
                        .workload-result {
                            margin-top: 20px;
                            color: #333;
                            font-weight: bold;
                            text-align: center;
                            background-color: #e9f7ef;
                            padding: 15px;
                            border-radius: 5px;
                            border: 1px solid #28a745;
                        }
                        .logo {
                            max-width: 200px;
                            margin-bottom: 20px;
                            display: block;
                            margin-left: auto;
                            margin-right: auto;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <img src="{{ url_for('static', filename='Logo_horizontal_ShortFormat.png') }}" alt="BITS Logo" class="logo">
                        <h2>Faculty Workload Estimation</h2>
                        <p class="result">{{ submission_data.result }}</p>
                        {% if submission_data.result == "Thank you for submitting!" %}
                        <div class="workload-result">
                            <p>Prof. {{ submission_data.faculty_name }}, your CLASSROOM HOURS is {{ submission_data.teaching_load }} hours per week.</p>
                            <p>Your TOTAL WORKLOAD is {{ submission_data.total_workload }} hours per week.</p>
                        </div>
                        {% endif %}
                    </div>
                </body>
            </html>
        ''', submission_data=submission_data)
    
    # Show the form for the first time
    return render_template_string('''
        <html>
            <head>
                <title>Faculty Workload Estimation</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        flex-direction: column;
                    }
                    .container {
                        background-color: #fff;
                        padding: 25px;
                        border-radius: 8px;
                        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                        width: 90%;
                        max-width: 800px;
                    }
                    h2 {
                        color: #333;
                        text-align: center;
                        margin-bottom: 20px;
                    }
                    .section {
                        margin-bottom: 20px;
                        padding: 15px;
                        border-radius: 8px;
                        background-color: #f9f9f9;
                    }
                    .section h3 {
                        color: #fff;
                        background-color: #007BFF;
                        padding: 10px;
                        border-radius: 5px;
                        text-align: center;
                        margin-top: 0;
                    }
                    .form-group {
                        display: flex;
                        flex-wrap: wrap;
                        align-items: center;
                        margin-bottom: 12px;
                        gap: 10px;
                    }
                    label {
                        font-weight: bold;
                        color: #333;
                        width: 65%;
                        min-width: 300px;
                    }
                    input[type="text"], 
                    input[type="number"], 
                    select {
                        padding: 8px;
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        box-sizing: border-box;
                        flex: 1;
                        min-width: 100px;
                        max-width: 200px;
                    }
                    input[type="submit"] {
                        background-color: #28a745;
                        color: white;
                        padding: 12px 20px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        margin-top: 20px;
                        width: 100%;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    input[type="submit"]:hover {
                        background-color: #218838;
                    }
                    .logo {
                        max-width: 200px;
                        margin-bottom: 20px;
                        display: block;
                        margin-left: auto;
                        margin-right: auto;
                    }
                    .instruction-box {
                        background-color: #f8f9fa;
                        border-left: 4px solid #007bff;
                        padding: 15px;
                        margin-bottom: 20px;
                        border-radius: 4px;
                    }
                    #loading {
                        display: none;
                        text-align: center;
                        margin: 20px 0;
                        font-weight: bold;
                        color: #007BFF;
                    }
                    @media (max-width: 768px) {
                        .form-group {
                            flex-direction: column;
                            align-items: flex-start;
                        }
                        label {
                            width: 100%;
                            min-width: auto;
                        }
                        input[type="text"],
                        input[type="number"],
                        select {
                            width: 100%;
                            max-width: 100%;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <img src="{{ url_for('static', filename='Logo_horizontal_ShortFormat.png') }}" alt="BITS Logo" class="logo">
                    <h2>Faculty Workload Estimation</h2>
                    
                    <form action="" method="post" onsubmit="return validateForm()" id="workloadForm">
                        <!-- 1. Professor Name -->
                        <div class="section">
                            <div class="form-group">
                                <label for="faculty_name">Professor Name:</label>
                                <input type="text" id="faculty_name" name="faculty_name" required>
                            </div>
                        </div>
                        
                        <!-- 2. Course Information -->
                        <div class="section">
                            <h3>Course Information</h3>
                            <div class="form-group">
                                <label for="course_name">Course Name:</label>
                                <select id="course_name" name="course_name" required onchange="fillCourseDetails()">
                                    <option value="">-- Select a Course --</option>
                                    {% for course in courses %}
                                    <option value="{{ course.name }}">{{ course.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="course_code">Course Code:</label>
                                <input type="text" id="course_code" name="course_code" readonly required>
                            </div>
                            <div class="form-group">
                                <label for="course_year">Course Year:</label>
                                <input type="number" id="course_year" name="course_year" min="1" max="4" required>
                            </div>
                            <div class="form-group">
                                <label for="course_credits">Course Credits:</label>
                                <input type="number" id="course_credits" name="course_credits" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="course_lectures">Lectures (L):</label>
                                <input type="number" id="course_lectures" name="course_lectures" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="course_tutorials">Tutorials (T):</label>
                                <input type="number" id="course_tutorials" name="course_tutorials" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="course_practicals">Practicals (P):</label>
                                <input type="number" id="course_practicals" name="course_practicals" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="practical_hours">Number of hours of each practical:</label>
                                <input type="number" id="practical_hours" name="practical_hours" min="0" required>
                                <select id="practical_hours_unit" name="practical_hours_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="num_quizzes">Number of quizzes in the semester:</label>
                                <input type="number" id="num_quizzes" name="num_quizzes" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="num_assignments">Number of assignments (in lab):</label>
                                <input type="number" id="num_assignments" name="num_assignments" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="num_homework">Number of homework/project:</label>
                                <input type="number" id="num_homework" name="num_homework" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="num_midsem">Number of midsem exams:</label>
                                <input type="number" id="num_midsem" name="num_midsem" value="1" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="quiz_duration">Duration of each quiz:</label>
                                <input type="number" id="quiz_duration" name="quiz_duration" min="0" required>
                                <select id="quiz_duration_unit" name="quiz_duration_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="midsem_duration">Duration of midsem exam:</label>
                                <input type="number" id="midsem_duration" name="midsem_duration" value="90" min="0" required>
                                <select id="midsem_duration_unit" name="midsem_duration_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="endsem_duration">Duration of comprehensive exam (endsem):</label>
                                <input type="number" id="endsem_duration" name="endsem_duration" value="180" min="0" required>
                                <select id="endsem_duration_unit" name="endsem_duration_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="num_sections">Number of sections in the course:</label>
                                <input type="number" id="num_sections" name="num_sections" min="1" required>
                            </div>
                            <div class="form-group">
                                <label for="total_students">Total number of students in the course:</label>
                                <input type="number" id="total_students" name="total_students" min="1" required>
                            </div>
                        </div>
                        
                        <!-- 3. Faculty Information -->
                        <div class="section">
                            <h3>Faculty Information</h3>
                            <div class="instruction-box">
                                <p><strong>Important:</strong> Please answer the following questions assuming you have no TA or other help. (We will take the TA information in the next section)</p>
                            </div>
                            <div class="form-group">
                                <label for="is_ic">Are you an IC (In-Charge)?</label>
                                <select id="is_ic" name="is_ic" required>
                                    <option value="YES">Yes</option>
                                    <option value="NO">No</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="content_change">Percentage of content changes in the course compared to the previous time:</label>
                                <input type="number" id="content_change" name="content_change" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="total_professors">Total number of professors teaching the course:</label>
                                <input type="number" id="total_professors" name="total_professors" min="1" required>
                            </div>
                            <div class="form-group">
                                <label for="years_current">Number of previous continuous year/s  (semester/s if the course is offered both semesters) of teaching the course:</label>
                                <input type="number" id="years_current" name="years_current" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="years_break1">Number of prev continuous year/s (semester/s if the course is offered both semesters) of teaching the course after the first break:</label>
                                <input type="number" id="years_break1" name="years_break1" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="years_break2">Number of continuous year/s (semester/s if the course is offered both semesters) of teaching the course after the second break:</label>
                                <input type="number" id="years_break2" name="years_break2" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="break1_years">Number of break year/s (semester/s if the course is offered both semesters) from teaching the course from now to the 1st break from teaching:</label>
                                <input type="number" id="break1_years" name="break1_years" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="break2_years">Number of break year/s (semester/s if the course is offered both semesters) from teaching the course from now to the 2nd break from teaching:</label>
                                <input type="number" id="break2_years" name="break2_years" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="tutorial_prep_time">Preparation time for each tutorial session:</label>
                                <input type="number" id="tutorial_prep_time" name="tutorial_prep_time" min="0" required>
                                <select id="tutorial_prep_time_unit" name="tutorial_prep_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="lab_prep_time">Preparation time for each practicals (labs) session:</label>
                                <input type="number" id="lab_prep_time" name="lab_prep_time" min="0" required>
                                <select id="lab_prep_time_unit" name="lab_prep_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="quiz_eval_time">Evaluation time for correcting quiz for each student:</label>
                                <input type="number" id="quiz_eval_time" name="quiz_eval_time" min="0" required>
                                <select id="quiz_eval_time_unit" name="quiz_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="assignment_eval_time">Evaluation time for correcting assignment (in lab) for each student:</label>
                                <input type="number" id="assignment_eval_time" name="assignment_eval_time" min="0" required>
                                <select id="assignment_eval_time_unit" name="assignment_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="homework_eval_time">Evaluation time for correcting homework for each student:</label>
                                <input type="number" id="homework_eval_time" name="homework_eval_time" min="0" required>
                                <select id="homework_eval_time_unit" name="homework_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="midsem_eval_time">Evaluation time for correcting midsem exam for each student:</label>
                                <input type="number" id="midsem_eval_time" name="midsem_eval_time" min="0" required>
                                <select id="midsem_eval_time_unit" name="midsem_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="endsem_eval_time">Evaluation time for correcting comprehensive exam (endsem) for each student:</label>
                                <input type="number" id="endsem_eval_time" name="endsem_eval_time" min="0" required>
                                <select id="endsem_eval_time_unit" name="endsem_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="quiz_qp_time">Question Paper preparation time for each quiz:</label>
                                <input type="number" id="quiz_qp_time" name="quiz_qp_time" min="0" required>
                                <select id="quiz_qp_time_unit" name="quiz_qp_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="assignment_qp_time">Question Paper preparation time for each assignment:</label>
                                <input type="number" id="assignment_qp_time" name="assignment_qp_time" min="0" required>
                                <select id="assignment_qp_time_unit" name="assignment_qp_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="homework_qp_time">Question Paper preparation time for each homework:</label>
                                <input type="number" id="homework_qp_time" name="homework_qp_time" min="0" required>
                                <select id="homework_qp_time_unit" name="homework_qp_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="midsem_qp_time">Question Paper preparation time for midsem:</label>
                                <input type="number" id="midsem_qp_time" name="midsem_qp_time" min="0" required>
                                <select id="midsem_qp_time_unit" name="midsem_qp_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="endsem_qp_time">Question Paper preparation time for comprehensive exam (endsem):</label>
                                <input type="number" id="endsem_qp_time" name="endsem_qp_time" min="0" required>
                                <select id="endsem_qp_time_unit" name="endsem_qp_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="midsem_recheck_time">Time taken for all midsem rechecks:</label>
                                <input type="number" id="midsem_recheck_time" name="midsem_recheck_time" min="0" required>
                                <select id="midsem_recheck_time_unit" name="midsem_recheck_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="endsem_recheck_time">Time taken for comprehensive exam (endsem) rechecks:</label>
                                <input type="number" id="endsem_recheck_time" name="endsem_recheck_time" min="0" required>
                                <select id="endsem_recheck_time_unit" name="endsem_recheck_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- 4. WILP Thesis Information -->
                        <div class="section">
                            <h3>WILP Thesis Information</h3>
                            <div class="form-group">
                                <label for="wilp_thesis">Number of WILP Thesis you are supervising:</label>
                                <input type="number" id="wilp_thesis" name="wilp_thesis" min="0" required>
                            </div>
                            <div class="form-group">
                                <label for="wilp_approval_time">Time taken for approving each WILP Thesis proposal:</label>
                                <input type="number" id="wilp_approval_time" name="wilp_approval_time" min="0" required>
                                <select id="wilp_approval_time_unit" name="wilp_approval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="wilp_midterm_eval_time">Time taken for each midterm evaluation of WILP Thesis:</label>
                                <input type="number" id="wilp_midterm_eval_time" name="wilp_midterm_eval_time" min="0" required>
                                <select id="wilp_midterm_eval_time_unit" name="wilp_midterm_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="wilp_final_eval_time">Time taken for each final evaluation (viva) of WILP Thesis:</label>
                                <input type="number" id="wilp_final_eval_time" name="wilp_final_eval_time" min="0" required>
                                <select id="wilp_final_eval_time_unit" name="wilp_final_eval_time_unit">
                                    <option value="minutes">Minutes</option>
                                    <option value="hours">Hours</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- 5. TA Information -->
                        <div class="section">
                            <h3>TA Information</h3>
                            <div class="instruction-box">
                                <p>Please indicate what percentage of each task is helped by TAs (Teaching Assistants) or any other external help.</p>
                            </div>
                            <div class="form-group">
                                <label for="ta_tutorial_reduction">Percentage reduction of tutorial preparation time by TAs:</label>
                                <input type="number" id="ta_tutorial_reduction" name="ta_tutorial_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_lab_reduction">Percentage reduction of practicals (labs) preparation time by TAs:</label>
                                <input type="number" id="ta_lab_reduction" name="ta_lab_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_quiz_reduction">Percentage reduction of evaluation time of quizzes by TAs:</label>
                                <input type="number" id="ta_quiz_reduction" name="ta_quiz_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_assignment_reduction">Percentage reduction of evaluation time of assignment (in lab) by TAs:</label>
                                <input type="number" id="ta_assignment_reduction" name="ta_assignment_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_homework_reduction">Percentage reduction of evaluation time of homework by TAs:</label>
                                <input type="number" id="ta_homework_reduction" name="ta_homework_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_midsem_reduction">Percentage reduction of evaluation time of midsem exam by TAs:</label>
                                <input type="number" id="ta_midsem_reduction" name="ta_midsem_reduction" min="0" max="100" required> %
                            </div>
                            <div class="form-group">
                                <label for="ta_endsem_reduction">Percentage reduction of evaluation time of comprehensive exam (endsem) by TAs:</label>
                                <input type="number" id="ta_endsem_reduction" name="ta_endsem_reduction" min="0" max="100" required> %
                            </div>
                        </div>
                        
                        <div id="loading">Calculating workload... Please wait.</div>
                        <input type="submit" value="Submit" id="submitBtn">
                    </form>
                </div>
                <script>
                    function validateForm() {
                        const inputs = document.querySelectorAll('input[required], select[required]');
                        for (const input of inputs) {
                            if (!input.value) {
                                alert("Please fill out all fields before submitting.");
                                return false;
                            }
                        }
                        
                        // Disable submit button and show loading
                        document.getElementById('submitBtn').disabled = true;
                        document.getElementById('loading').style.display = 'block';
                        
                        return true;
                    }
                    
                    function fillCourseDetails() {
                        const courseName = document.getElementById('course_name').value;
                        if (!courseName) return;
                        
                        fetch(`/get_course_details/${encodeURIComponent(courseName)}`)
                            .then(response => response.json())
                            .then(data => {
                                if (data.error) {
                                    alert(data.error);
                                    return;
                                }
                                
                                document.getElementById('course_code').value = data.id;
                                document.getElementById('course_lectures').value = data.L;
                                document.getElementById('course_tutorials').value = data.T;
                                document.getElementById('course_practicals').value = data.P;
                            })
                            .catch(error => {
                                console.error('Error fetching course details:', error);
                            });
                    }
                </script>
            </body>
        </html>
    ''', courses=all_courses)

if __name__ == '__main__':
    print("Starting application...")
    if verify_google_sheets_access():
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("Failed to verify Google Sheets access. Exiting.")