from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import os
import math
from datetime import datetime
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
RESEARCH_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_data.db')

def init_research_db():
    """Initialize the research database with required tables"""
    try:
        with sqlite3.connect(RESEARCH_DB) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS research_workload (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                faculty_name TEXT NOT NULL,
                supervision_hours DECIMAL(10,2) NOT NULL,
                grants_hours DECIMAL(10,2) NOT NULL,
                papers_hours DECIMAL(10,2) NOT NULL,
                conferences_hours DECIMAL(10,2) NOT NULL,
                lab_hours DECIMAL(10,2) NOT NULL,
                collaborations_hours DECIMAL(10,2) NOT NULL,
                total_workload DECIMAL(10,2) NOT NULL
            )
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing research database: {e}")
        raise

if not os.path.exists(RESEARCH_DB):
    init_research_db()

def save_research_results(data):
    """Save research workload results to database"""
    try:
        with sqlite3.connect(RESEARCH_DB) as conn:
            conn.execute("""
                INSERT INTO research_workload VALUES (
                    NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                data['faculty_name'],
                round(float(data['supervision_hours']), 2),
                round(float(data['grants_hours']), 2),
                round(float(data['papers_hours']), 2),
                round(float(data['conferences_hours']), 2),
                round(float(data['lab_hours']), 2),
                round(float(data['collaborations_hours']), 2),
                round(float(data['total_workload']), 2)
            ])
            conn.commit()
    except Exception as e:
        print(f"Error saving research results: {e}")

def calculate_research_workload(data):
    try:
        # Supervision calculations
        supervision = round(float(data['N_phd']) * 2.5 + 
                     round(float(data['N_ms'])) * 1.5 + 
                     round(float(data['N_fd'])) * 0.75 + 
                     round(float(data['N_out'])) * 1, 2)
        
        # Corrected version:
        supervision = round(
            (float(data['N_phd']) * 2.5 + 
            float(data['N_ms']) * 1.5 + 
            float(data['N_fd']) * 0.75 + 
            float(data['N_out']) * 1), 2)
        
        # Grants calculations
        grants = round(
            (float(data['N_simple']) * 15 + 
            float(data['N_medium']) * 40 + 
            float(data['N_complex']) * 100
        ) / 52, 2)
        
        # Papers calculations
        papers = 0
        paper_count = int(data.get('paper_count', 0))
        for i in range(1, paper_count + 1):
            authorship = float(data.get(f'paper_{i}_authorship', 0.5))
            journal_quality = float(data.get(f'paper_{i}_quality', 1.0))
            papers += round(
                (7.5 * authorship * journal_quality) + 
                (journal_quality * authorship)
            , 2)
        papers = round(papers, 2)
        
        # Conferences calculations
        conferences = 0
        conf_count = int(data.get('conf_count', 0))
        for i in range(1, conf_count + 1):
            prep = float(data.get(f'conf_{i}_prep', 0))
            attend = float(data.get(f'conf_{i}_attend', 0))
            conferences += round(
                (prep + attend) / 52
            , 2)
        conferences = round(conferences, 2)
        
        # Lab/Computational work
        lab_work = round(
            (float(data['Research_type']) * 
            (float(data['N_exp']) * float(data['H_exp'])) / 
            max(1, float(data['N_people']))), 2)
        
        # Collaborations & Services
        collaborations = round(
            ((float(data['N_collab']) * float(data['H_collab'])) + 
            float(data['N_conferences_organized']) * 
            (float(data['H_conference_planning']) + 75)
        ) / 52, 2)
        
        total = round(
            supervision + grants + papers + conferences + 
            lab_work + collaborations
        , 2)
        
        detailed_calculations = {
            "Supervision & Mentorship": {
                "value": supervision,
                "description": [
                    f"PhD Students: {data['N_phd']} × 2.5 = {float(data['N_phd']) * 2.5}",
                    f"Master's Students: {data['N_ms']} × 1.5 = {float(data['N_ms']) * 1.5}",
                    f"Fd's Students: {data['N_fd']} × 0.75 = {float(data['N_fd']) * 0.75}",
                    f"Outside Students: {data['N_out']} × 1 = {float(data['N_out']) * 1}",
                    f"Total Supervision: {supervision:.2f} hours/week"
                ]
            },
            "Grant Applications": {
                "value": grants,
                "description": [
                    f"Simple Grants: {data['N_simple']} × 15 = {float(data['N_simple']) * 15} hours/year",
                    f"Medium Grants: {data['N_medium']} × 40 = {float(data['N_medium']) * 40} hours/year",
                    f"Complex Grants: {data['N_complex']} × 100 = {float(data['N_complex']) * 100} hours/year",
                    f"Total Grants: {grants:.2f} hours/week (annual total ÷ 52 weeks)"
                ]
            },
            "Research Papers": {
                "value": papers,
                "description": [
                    f"Number of papers entered: {paper_count}",
                    *[f"Paper {i}: Authorship weight {data.get(f'paper_{i}_authorship', 0.5)}, "
                      f"Journal quality {data.get(f'paper_{i}_quality', 1.0)}" 
                      for i in range(1, paper_count + 1)],
                    f"Total Paper Writing: {papers:.2f} hours/week"
                ]
            },
            "Conferences & Seminars": {
                "value": conferences,
                "description": [
                    f"Number of conferences entered: {conf_count}",
                    *[f"Conference {i}: Prep {data.get(f'conf_{i}_prep', 0)} hours, "
                      f"Attendance {data.get(f'conf_{i}_attend', 0)} hours" 
                      for i in range(1, conf_count + 1)],
                    f"Total Conference Time: {conferences:.2f} hours/week (annual total ÷ 52 weeks)"
                ]
            },
            "Lab/Computational Work": {
                "value": lab_work,
                "description": [
                    f"Research Type: {'Experimental' if data['Research_type'] == '1' else 'Theoretical'}",
                    f"Experiments/Simulations per week: {data['N_exp']}",
                    f"Hours per experiment: {data['H_exp']}",
                    f"People involved: {data['N_people']}",
                    f"Total Lab/Computational Work: {lab_work:.2f} hours/week"
                ]
            },
            "Collaborations & Services": {
                "value": collaborations,
                "description": [
                    f"Active Collaborations: {data['N_collab']}",
                    f"Hours per collaboration: {data['H_collab']} hours/week",
                    f"Conferences Organized: {data['N_conferences_organized']}",
                    f"Planning Hours: {data['H_conference_planning']} hours/year",
                    f"Total Collaborations & Services: {collaborations:.2f} hours/week"
                ]
            }
        }
        
        return {
            "supervision_hours": supervision,
            "grants_hours": grants,
            "papers_hours": papers,
            "conferences_hours": conferences,
            "lab_hours": lab_work,
            "collaborations_hours": collaborations,
            "total_workload": total,
            "detailed_calculations": detailed_calculations
        }
        
    except Exception as e:
        print(f"Error in research calculations: {str(e)}")
        return None

@app.route('/research', methods=['GET', 'POST'])
def research_workload():
    # Clear any existing session data when loading the form
    session.pop('research_result', None)
    
    if request.method == 'POST':
        data = request.form.to_dict()
        result = None
        
        if not all(data.values()):
            result = "Error: All fields are required."
        else:
            calculation_result = calculate_research_workload(data)
            if calculation_result:
                result = "Research workload calculated successfully!"
                
                # Save the results
                save_data = {
                    'faculty_name': data['faculty_name'],
                    'supervision_hours': calculation_result['supervision_hours'],
                    'grants_hours': calculation_result['grants_hours'],
                    'papers_hours': calculation_result['papers_hours'],
                    'conferences_hours': calculation_result['conferences_hours'],
                    'lab_hours': calculation_result['lab_hours'],
                    'collaborations_hours': calculation_result['collaborations_hours'],
                    'total_workload': calculation_result['total_workload'],
                    'detailed_calculations': calculation_result['detailed_calculations']
                }
                save_research_results(save_data)
                
                # Store in session for display
                session['research_result'] = {
                    'result': result,
                    'faculty_name': data['faculty_name'],
                    'total_workload': calculation_result['total_workload'],
                    'detailed_calculations': calculation_result['detailed_calculations']
                }
                return redirect(url_for('research_results'))
            else:
                result = "Error calculating research workload."
        
        return render_template('research_form.html', result=result)
    
    return render_template('research_form.html')

@app.route('/research/results')
def research_results():
    research_data = session.get('research_result')
    if not research_data:
        return redirect(url_for('research_workload'))
    return render_template('research_results.html',
                         research_data=research_data,
                         detailed_calculations=research_data['detailed_calculations'])

@app.route('/research/add_paper', methods=['POST'])
def add_paper():
    paper_count = int(request.form.get('paper_count', 0)) + 1
    return render_template('paper_entry.html', paper_num=paper_count)

@app.route('/research/add_conference', methods=['POST'])
def add_conference():
    conf_count = int(request.form.get('conf_count', 0)) + 1
    return render_template('conference_entry.html', conf_num=conf_count)

@app.route('/')
def home():
    return "Flask is running! Try accessing <a href='/research'>/research</a>"

@app.route('/test')
def test():
    return "Test route is working!"

if __name__ == '__main__':
    app.run(debug=True, port=5002)
