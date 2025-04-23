from flask import Flask, jsonify, Blueprint, request
import logging
from logging.handlers import RotatingFileHandler
import os
from flask_cors import CORS
from dotenv import load_dotenv
import importlib
import sys

load_dotenv()

# Configure logger
def setup_logger():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10000000,  # 10MB
        backupCount=5
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Also log to console in development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Create Flask app
def create_app():
    app = Flask(__name__)
    logger = logging.getLogger(__name__)
    
    CORS(app)
    
    # Dynamically load blueprints from the routes folder
    blueprints_folder = os.environ.get('FLASK_BLUEPRINTS_PATH', 'routes')
    logger.info(f"Looking for blueprints in: {blueprints_folder}")
    
    # Ensure the blueprints folder exists
    if not os.path.exists(blueprints_folder):
        logger.error(f"Blueprints folder '{blueprints_folder}' does not exist!")
        # Create the directory to avoid errors
        os.makedirs(blueprints_folder)
    
    # Try to import from routes/__init__.py first (preferred method)
    try:
        routes_module = importlib.import_module('routes')
        if hasattr(routes_module, 'all_blueprints'):
            logger.info("Found all_blueprints in routes/__init__.py")
            for blueprint in routes_module.all_blueprints:
                logger.info(f"Registering blueprint: {blueprint.name} with url_prefix: {blueprint.url_prefix}")
                app.register_blueprint(blueprint)
            logger.info("Successfully registered blueprints from routes/__init__.py")
        else:
            logger.info("No all_blueprints found in routes/__init__.py, falling back to dynamic loading")
            # Fall back to dynamic loading
            _load_blueprints_dynamically(app, blueprints_folder, logger)
    except ImportError as e:
        logger.warning(f"Could not import routes package: {str(e)}")
        logger.info("Falling back to dynamic blueprint loading")
        # Fall back to dynamic loading
        _load_blueprints_dynamically(app, blueprints_folder, logger)
    
    # Add a test route to verify the app is working
    @app.route('/api/ping')
    def ping():
        return jsonify({'status': 'ok', 'message': 'Flask app is running'}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 error: {request.path}")
        return jsonify({'error': 'Not found', 'path': request.path}), 404
        
    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500
    
    # Print all registered routes for debugging
    logger.info("Registered routes:")
    for rule in app.url_map.iter_rules():
        logger.info(f"Route: {rule.rule}, Methods: {rule.methods}, Endpoint: {rule.endpoint}")
    
    return app

def _load_blueprints_dynamically(app: Flask, blueprints_folder: str, logger: logging.Logger):
    """Helper function to dynamically load blueprints from files"""
    try:
        # Add the current directory to the Python path if it's not already there
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        for filename in os.listdir(blueprints_folder):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]  # Remove .py extension
                module_path = f'{blueprints_folder}.{module_name}'
                
                logger.info(f"Attempting to import: {module_path}")
                
                try:
                    module = importlib.import_module(module_path)
                    
                    # Register all blueprints in the module
                    blueprint_found = False
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        if isinstance(attribute, Blueprint):
                            logger.info(f"Registering blueprint: {attribute_name} with url_prefix: {attribute.url_prefix}")
                            app.register_blueprint(attribute, url_prefix=f"/api{attribute.url_prefix or ''}")
                            blueprint_found = True
                    
                    if not blueprint_found:
                        logger.warning(f"No blueprints found in {module_path}")
                except Exception as e:
                    logger.error(f"Error importing {module_path}: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"Error loading blueprints: {str(e)}", exc_info=True)

if __name__ == '__main__':
    logger = setup_logger()
    app = create_app()
    
    # Get configuration from environment or use defaults
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting application on {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)