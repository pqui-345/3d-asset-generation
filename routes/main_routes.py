from flask import Blueprint, render_template, send_from_directory, current_app
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/home')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@main_bp.route('/favicon.ico')
def favicon():
    """Serves the favicon if requested."""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'img'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
