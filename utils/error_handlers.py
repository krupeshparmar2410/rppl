import pymongo.errors
from flask import jsonify, request, g
from utils.logger import get_logger

logger = get_logger("error_handlers")

def register_error_handlers(app):
    """
    Registers global exception handlers for Flask.
    Ensures tracebacks are logged with Request ID context and returns uniform JSON responses.
    """
    @app.errorhandler(404)
    def not_found(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.warning(f"RequestID={req_id} | 404 Not Found: {request.method} {request.path}")
        return jsonify({
            'success': False, 
            'message': 'Endpoint not found.',
            'error': 'Endpoint not found.'
        }), 404

    @app.errorhandler(413)
    def too_large(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.warning(f"RequestID={req_id} | 413 Payload Too Large: {e}")
        return jsonify({
            'success': False, 
            'message': 'File too large. Max 50MB.',
            'error': 'File too large. Max 50MB.'
        }), 413

    @app.errorhandler(400)
    def bad_request(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.warning(f"RequestID={req_id} | 400 Bad Request: {e}")
        return jsonify({
            'success': False, 
            'message': str(e),
            'error': str(e)
        }), 400

    @app.errorhandler(pymongo.errors.PyMongoError)
    def database_error(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.exception(f"RequestID={req_id} | MongoDB database error occurred: {e}")
        return jsonify({
            'success': False, 
            'message': 'Database error occurred.',
            'error': 'Database error occurred.'
        }), 500

    @app.errorhandler(ValueError)
    @app.errorhandler(KeyError)
    def validation_error(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.exception(f"RequestID={req_id} | Validation error: {e}")
        return jsonify({
            'success': False, 
            'message': f"Validation error: {str(e)}",
            'error': f"Validation error: {str(e)}"
        }), 400

    @app.errorhandler(Exception)
    def server_error(e):
        req_id = getattr(g, 'request_id', 'N/A')
        logger.exception(f"RequestID={req_id} | Uncaught internal server exception: {e}")
        return jsonify({
            'success': False, 
            'message': 'Internal server error.',
            'error': 'Internal server error.'
        }), 500
