from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'success': False, 'error': 'Endpoint not found.'}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'success': False, 'error': 'File too large. Max 50MB.'}), 413

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'success': False, 'error': str(e)}), 400

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'success': False, 'error': 'Internal server error.'}), 500
