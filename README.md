# Faculty Workload Estimation System - README

## Overview

This Flask-based web application is designed to help faculty members estimate their teaching workload. The system collects course and teaching-related information through a form, calculates the estimated workload, and stores the data in a Google Sheet for further analysis.

## Key Features

1. **User-Friendly Form Interface**:
   - Collects detailed course information (name, code, credits, L-T-P values)
   - Captures faculty teaching details (preparation time, evaluation time, etc.)
   - Includes WILP thesis supervision information
   - Accounts for TA (Teaching Assistant) support

2. **Automatic Course Details**:
   - Pre-populates course code and L-T-P values when a course is selected from a dropdown
   - Course data is loaded from `Course details.txt`

3. **Workload Calculation**:
   - Converts all time inputs to minutes for consistency
   - Calculates both classroom hours and total workload
   - Accounts for TA support reductions

4. **Data Storage**:
   - Stores all submitted data in a Google Sheet
   - Uses Google Sheets API for secure data transfer

5. **Responsive Design**:
   - Works on both desktop and mobile devices
   - Clean, intuitive interface with clear sections

## Technical Components

### Main Files

1. **app.py** - The main Flask application containing:
   - Form rendering and handling
   - Google Sheets integration
   - Workload calculation logic
   - Route handlers

2. **Course details.txt** - Contains course information (name, ID, L-T-P values)

3. **credentials.json** - Service account credentials for Google Sheets API

4. **Logo_horizontal_ShortFormat.png** - Institution logo displayed in the form

### Dependencies

- Flask (web framework)
- google-api-python-client (Google Sheets API)
- python-dotenv (environment variables)

## Installation and Setup

1. **Install dependencies**:
   ```bash
   pip install flask google-api-python-client python-dotenv
   ```

2. **Configuration**:
   - Place `credentials.json` in the project root
   - Place `Logo_horizontal_ShortFormat.png` in a folder named `static` in the same directory

4. **Running the application**:
   ```bash
   python app.py
   ```

## Usage Flow

1. Faculty member accesses the web form
2. Selects a course from the dropdown (auto-fills code and L-T-P)
3. Enters course details (year, credits, sections, students)
4. Provides teaching information (prep time, evaluation time)
5. Adds WILP thesis details if applicable
6. Specifies TA support percentages
7. Submits the form
8. System calculates and displays:
   - Classroom hours per week
   - Total workload hours per week
9. Data is stored in Google Sheets for record-keeping

## Google Sheets Integration

The application writes data to the Google Sheet (https://docs.google.com/spreadsheets/d/1lXvk0dmhF49cb0o_9gqiigD-re6Vgh-vS5YVWSl8b4g/edit?gid=1572370607#gid=1572370607) 

Calculated values (workload estimates) are computed in the Google Sheet.
