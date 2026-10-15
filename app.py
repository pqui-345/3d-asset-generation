import os
from flask import Flask, jsonify
from routes.main_routes import main_bp
from routes.api_routes import api_bp

def create_app():
    # Initialize the Flask application
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Configure secrets and limits
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '3dgame_edu_secret_key_9918')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB maximum upload size
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # Global error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "An internal server error occurred"}), 500
        
    return app

if __name__ == '__main__':
    app = create_app()
    # Create static directories just in case they aren't generated yet
    os.makedirs(os.path.join(app.root_path, 'static', 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'models'), exist_ok=True)
    
    print("\n" + "="*50)
    print(" 3DGame Asset Generator is starting!")
    print(" URL: http://127.0.0.1:5000")
    print("="*50 + "\n")
    
    app.run(host='127.0.0.1', port=5000, debug=True)
