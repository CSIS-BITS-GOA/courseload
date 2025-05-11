from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, jsonify, send_file
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
import sqlite3
from contextlib import closing
from pathlib import Path

# Use the blueprint from __init__.py
from . import research_bp

#research_bp = Blueprint('research', __name__, template_folder='templates')

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database setup
RESEARCH_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'research_workload_data.db')

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
                collaborations_hours DECIMAL(10,2) NOT NULL,
                total_workload DECIMAL(10,2) NOT NULL
            )
            """)
            conn.commit()
    except Exception as e:
        print(f"Error initializing research database: {e}")
        raise

# initialization 
if not os.path.exists(RESEARCH_DB):
    os.makedirs(os.path.dirname(RESEARCH_DB), exist_ok=True)  # Ensure directory exists
    init_research_db()
else:
    print(f"Using existing database at {os.path.abspath(RESEARCH_DB)}")
    # Verify the table exists
    try:
        with sqlite3.connect(RESEARCH_DB) as conn:
            conn.execute("SELECT 1 FROM research_workload LIMIT 1")
    except sqlite3.OperationalError:
        init_research_db()  # Table doesn't exist, initialize it

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
        supervision = round(
            (float(data['N_phd']) * 3 + 
            float(data['N_ms']) * 1.5 + 
            float(data['N_fd']) * 1 + 
            float(data['N_out']) * 1.25), 2)
        
        # Grants calculations
        grants = round(
            (float(data['N_simple']) * 30 + 
            float(data['N_medium']) * 80 + 
            float(data['N_complex']) * 150
        ) / 52, 2)
        
        # Papers calculations
        papers = 0
        paper_count = int(data.get('paper_count', 0))
        for i in range(1, paper_count + 1):
            authorship = float(data.get(f'paper_{i}_authorship', 0.5))
            journal_quality = float(data.get(f'paper_{i}_quality', 1.0))
            papers += (journal_quality * authorship)/52
        papers = round(papers, 2)
        
        # Conferences calculations
        conferences = 0
        conf_count = int(data.get('conf_count', 0))
        for i in range(1, conf_count + 1):
            attend = float(data.get(f'conf_{i}_attend', 0))
            conferences += (24 + attend * 24) / 52
        conferences = round(conferences, 2)
        
        # Collaborations & Services
        collaborations = round(
            (((float(data['N_collab']) * float(data['H_collab'])) + 
            (float(data['N_conferences_organized']) * 1.5 + float(data['H_conference']) * 7)) / 52)
            , 2)
        
        total = round(
            (supervision + grants + papers + conferences + collaborations)
        , 2)
        
        detailed_calculations = {
            "Supervision & Mentorship": {
                "value": supervision,
                "description": [
                    "Based on your input:",
                    f"You are supervising {data['N_phd']} PhD students, {data['N_ms']} Master's students, {data['N_fd']} Fd's students, and {data['N_out']} outside students.",
                    "",
                    "Considering the students degree and the supervision time required according, your total weekly supervision time is estimated to be:",
                    f"{supervision:.2f} hours/week"
                ]
            },
            "Grant Applications": {
                "value": grants,
                "description": [
                    "Based on your input:",
                    f"You apply for {data['N_simple']} simple grants, {data['N_medium']} medium-complexity grants and {data['N_complex']} complex grants per year.",
                    "",
                    "When spread evenly across the year, your weekly grant application workload is:",
                    f"{grants:.2f} hours/week"
                ]
            },
            "Research Papers": {
                "value": papers,
                "description": [
                    "Based on your input:",
                    f"You are working on {paper_count} research papers with varying authorship roles and journal quality levels.",
                    "",
                    "From our calculations:",
                    "Paper writing involves both initial drafting and revisions, higher quality journals typically require more time for revisions and improvements, as a lead author, you typically invest more time than as a co-author.",
                    "",
                    "Your total weekly paper writing time is estimated to be:",
                    f"{papers:.2f} hours/week"
                ]
            },
            "Conferences & Seminars": {
                "value": conferences,
                "description": [
                    "Based on your input:",
                    f"You participate in {conf_count} conferences with varying preparation and attendance requirements.",
                    "",
                    "From our calculations:",
                    "Conference participation includes both preparation time (writing papers, preparing presentations) according to the conference quality and actual attendance time (travel, presentations, networking).",
                    "",
                    "When spread evenly across the year, your weekly conference participation time is:",
                    f"{conferences:.2f} hours/week"
                ]
            },
            "Collaborations & Services": {
                "value": collaborations,
                "description": [
                    "Based on your input:",
                    f"You have {data['N_collab']} active collaborations and organize {data['N_conferences_organized']} conferences per year.",
                    "",
                    "From our calculations:",
                    "Collaborations require regular meetings, discussions, and joint work sessions. Conference organization involves significant planning time before the event.",
                    "",
                    "When spread evenly across the year, your weekly collaboration and service time is:",
                    f"{collaborations:.2f} hours/week"
                ]
            },
            "Total Research Workload": {
                "value": total,
                "description": [
                    "Combining all components, your total weekly research workload includes: Student supervision, Grant application preparation, Research paper writing, Conference participation and Collaborations and academic services",
                    "",
                    "Your complete weekly research workload is estimated to be:",
                    f"{total:.2f} hours/week"
                ]
            }
        }
        
        return {
            "supervision_hours": supervision,
            "grants_hours": grants,
            "papers_hours": papers,
            "conferences_hours": conferences,
            "collaborations_hours": collaborations,
            "total_workload": total,
            "detailed_calculations": detailed_calculations
        }
        
    except Exception as e:
        print(f"Error in research calculations: {str(e)}")
        return None

@research_bp.route('/', methods=['GET', 'POST'])
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
                return redirect(url_for('research.research_results'))
            else:
                result = "Error calculating research workload."
        
        return render_template('research_form.html', result=result)
    
    return render_template('research_form.html')

@research_bp.route('/results')
def research_results():
    research_data = session.get('research_result')
    if not research_data:
        return redirect(url_for('research.research_workload'))
    return render_template('research_results.html',
                         research_data=research_data,
                         detailed_calculations=research_data['detailed_calculations'])

@research_bp.route('/add_paper', methods=['POST'])
def add_paper():
    paper_count = int(request.form.get('paper_count', 0)) + 1
    return render_template('paper_entry.html', paper_num=paper_count)

@research_bp.route('/add_conference', methods=['POST'])
def add_conference():
    conf_count = int(request.form.get('conf_count', 0)) + 1
    return render_template('conference_entry.html', conf_num=conf_count)

@research_bp.route('/download_csv', methods=['POST'])
def download_research_csv():
    try:
        if 'research_result' not in session:
            return "No data to download", 400
            
        research_data = session['research_result']
        faculty_name = research_data['faculty_name']
        detailed_calculations = research_data['detailed_calculations']
        
        # Prepare CSV data
        csv_content = []
        csv_content.append("Research Workload Calculation Report")
        csv_content.append(f"Faculty: {faculty_name}")
        csv_content.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        csv_content.append("")
        csv_content.append(f"Total Research Workload: {research_data['total_workload']:.2f} hours per week")
        csv_content.append("")
        
        # Add each section
        section_order = [
            "Supervision & Mentorship",
            "Grant Applications",
            "Research Papers",
            "Conferences & Seminars",
            "Collaborations & Services"
        ]
        
        for section in section_order:
            if section in detailed_calculations:
                csv_content.append(section)
                for line in detailed_calculations[section]['description']:
                    csv_content.append(line)
                csv_content.append(f"Weekly Hours: {detailed_calculations[section]['value']:.2f}")
                csv_content.append("")
        
        # Create BytesIO buffer
        output = BytesIO()
        output.write("\n".join(csv_content).encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'research_workload_{faculty_name.replace(" ", "_")}.csv'
        )
        
    except Exception as e:
        print(f"Error generating research CSV: {str(e)}")
        return "Error generating file. Please try again.", 500

@research_bp.route('/download_pdf', methods=['POST'])
def download_research_pdf():
    try:
        if 'research_result' not in session:
            return "No data available for PDF generation. Please submit the form first.", 400
            
        research_data = session['research_result']
        faculty_name = research_data['faculty_name']
        detailed_calculations = research_data['detailed_calculations']
        
        # Create PDF in memory
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
            title=f"Research Workload Calculation for {faculty_name}"
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
            f"Detailed Research Workload Calculation for {faculty_name}",
            styles['Title']
        ))
        elements.append(Paragraph(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 12))
        
        # Total workload
        elements.append(Paragraph(
            f"Total Research Workload: {research_data['total_workload']:.2f} hours per week",
            styles['Heading2']
        ))
        elements.append(Spacer(1, 12))
        
        # Add each calculation section
        section_order = [
            "Supervision & Mentorship",
            "Grant Applications",
            "Research Papers",
            "Conferences & Seminars",
            "Collaborations & Services"
        ]
        
        for section in section_order:
            if section in detailed_calculations:
                # Section header
                elements.append(Paragraph(
                    f"<b>{section}</b>",
                    styles['Heading2']
                ))
                
                # Add description
                for line in detailed_calculations[section]['description']:
                    elements.append(Paragraph(
                        line,
                        styles['NaturalLanguage']
                    ))
                
                # Add weekly hours
                elements.append(Paragraph(
                    f"Weekly Hours: {detailed_calculations[section]['value']:.2f}",
                    styles['NaturalLanguage']
                ))
                
                elements.append(Spacer(1, 12))
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'research_workload_{faculty_name.replace(" ", "_")}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating research PDF: {str(e)}")
        return "Error generating PDF. Please try again.", 500

@research_bp.route('/admin/data')
def research_admin_data():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        with sqlite3.connect(RESEARCH_DB) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM research_workload")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT * FROM research_workload 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (per_page, (page-1)*per_page))
            data = cursor.fetchall()
            
        # Debug output
        print(f"Data fetched: {len(data)} records")
        for row in data:
            print(dict(row))
            
        return render_template('research/admin_data.html', 
                            data=data,
                            page=page,
                            per_page=per_page,
                            total=total)
    except Exception as e:
        print(f"Error in research_admin_data: {str(e)}")
        return f"Database error: {str(e)}", 500

@research_bp.route('/admin/download_all')
def research_download_all_data():
    try:
        with sqlite3.connect(RESEARCH_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM research_workload ORDER BY timestamp DESC")
            data = cursor.fetchall()
        if not data:
            return "No data available to download", 404
            
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Timestamp', 'Faculty Name', 'Supervision Hours', 
            'Grants Hours', 'Papers Hours', 'Conferences Hours',
            'Collaborations Hours', 'Total Workload'
        ])
        
        # Write data
        writer.writerows(data)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='research_workload_data.csv'
        )
    except Exception as e:
        print(f"Download error: {str(e)}")
        return f"Error generating download: {str(e)}", 500
