from flask import Flask, render_template
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

def create_app(config_name='default'):
    """Factory Pattern per creare l'applicazione Flask"""
    
    app = Flask(__name__)
    
    # Configurazione
    app.config['SECRET_KEY'] = 'dev-key-12345-not-for-production'  # Hardcoded per preview
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Inizializza estensioni
    db.init_app(app)
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    limiter.init_app(app)
    
    # Security Headers
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Logging Setup
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('AppointmentCRM startup')
    
    # Context Processors
    @app.context_processor
    def inject_globals():
        """Variabili globali disponibili in tutti i template"""
        return {
            'app_name': 'AppointmentCRM',
            'version': '2.0',
            'current_year': datetime.now().year
        }
    
    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    # Registra Blueprint
    from routes.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from routes.dealer import bp as dealer_bp
    app.register_blueprint(dealer_bp, url_prefix='/dealer')
    
    from routes.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from routes.ai import bp as ai_bp
    app.register_blueprint(ai_bp, url_prefix='/ai')
    
    # Inizializza database
    with app.app_context():
        db.create_all()
        
        # Crea utente admin se non esiste
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@appointmentcrm.com',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')  # Password di default per preview
            db.session.add(admin_user)
            db.session.commit()
            app.logger.info('Utente admin creato con password di default')
    
    return app

if __name__ == '__main__':
    from datetime import datetime
    from flask import render_template
    
    app = create_app()
    
    # Socket.IO per funzionalità real-time (se necessario)
    try:
        from flask_socketio import SocketIO
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
        
        @socketio.on('connect')
        def handle_connect():
            """Gestisce connessione Socket.IO"""
            pass
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Gestisce disconnessione Socket.IO"""
            pass
        
        if __name__ == '__main__':
            socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except ImportError:
        # Se Socket.IO non è disponibile, usa Flask normale
        app.run(debug=True, host='0.0.0.0', port=5000)
