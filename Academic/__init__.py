from flask import Blueprint

# Create the blueprint first
academic_bp = Blueprint('academic', __name__,
                       template_folder='templates',
                       static_folder='static')

# Now import the routes after creating the blueprint
from . import academic_workload