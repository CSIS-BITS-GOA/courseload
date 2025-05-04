from flask import Blueprint

# Create the blueprint first
research_bp = Blueprint('research', __name__,
                       template_folder='templates',
                       static_folder='static')

# Now import the routes after creating the blueprint
from . import research_workload
