import os

class Config:
    # Google Sheets Configuration
    SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '1lXvk0dmhF49cb0o_9gqiigD-re6Vgh-vS5YVWSl8b4g')
    SHEET_NAME = os.getenv('SHEET_NAME', 'Workload_Automatic')
    
    # Database Configuration
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'workload_user')
    DB_PASS = os.getenv('DB_PASS', 'secure_password')
    DB_NAME = os.getenv('DB_NAME', 'workload_db')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
