# Faculty Workload Estimation - README

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

# Deployment


## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd faculty-workload-system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project root:
   ```bash
   touch .env
   ```

2. Add the following configuration (modify values as needed):
   ```
   SPREADSHEET_ID='1lXvk0dmhF49cb0o_9gqiigD-re6Vgh-vS5YVWSl8b4g'
   SHEET_NAME=Workload_Automatic
   GOOGLE_CREDS_PATH=credentials.json
   SECRET_KEY=os.urandom(24)
   DEBUG=False
   ```

3. Place your Google service account credentials file (`credentials.json`) in the project root

4. Place `Logo_horizontal_ShortFormat.png` in a folder named `static` in the same directory

## Deployment Options

### Option 1: Development Server

For testing and development:
```bash
python app.py
```
The application will be available at `http://localhost:5001`

### Option 2: Production with Gunicorn

1. Install Gunicorn:
   ```bash
   pip install gunicorn
   ```

2. Create a WSGI entry point (`wsgi.py`):
   ```python
   from app import app

   if __name__ == "__main__":
       app.run()
   ```

3. Run the application:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5001 wsgi:app
   ```

### Option 3: Production with Nginx Reverse Proxy

1. Install Nginx:
   ```bash
   sudo apt update
   sudo apt install nginx
   ```

2. Create a configuration file at `/etc/nginx/sites-available/workload`:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://localhost:5001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
   }
   ```

3. Enable the site and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/workload /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. Run Gunicorn with:
   ```bash
   gunicorn -w 4 -b 127.0.0.1:5001 wsgi:app
   ```

### Option 4: Docker Deployment

1. Create a `Dockerfile`:
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app
   COPY . .

   RUN pip install -r requirements.txt gunicorn

   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "wsgi:app"]
   ```

2. Build and run:
   ```bash
   docker build -t workload-app .
   docker run -d -p 5001:5001 --env-file .env workload-app
   ```


### Common Issues


1. **Permission Errors**:
   ```bash
   sudo chown -R www-data:www-data /path/to/app
   sudo chmod -R 755 /path/to/app
   ```

2. **Port Conflicts**:
   - Check running processes: `sudo lsof -i :5001`
   - Kill conflicting process: `sudo kill <PID>`

## Maintenance

1. **Logs**:
   - Gunicorn logs: Typically in `/var/log/gunicorn/`
   - Application logs: Configure in `app.py`

2. **Updates**:
   ```bash
   git pull origin main
   pip install -r requirements.txt
   sudo systemctl restart gunicorn
   ```
