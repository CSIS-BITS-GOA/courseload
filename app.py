from flask import Flask, render_template
from Academic.academic_workload import academic_bp
from Research.research_workload import research_bp

app = Flask(__name__)
app.secret_key = '579f3853c5285aec8c5defc608314204a525c22cc1e0b27be84896a998311ef9'

# Register blueprints with explicit names
app.register_blueprint(academic_bp, url_prefix='/academic')
app.register_blueprint(research_bp, url_prefix='/research')

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)