from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler
import os

# Istanze globali
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='default'):
    """Factory function per creare l'app Flask"""
    app = Flask(__name__)
    
    # Configurazione
    from config import config
    app.config.from_object(config[config_name])
    
    # Inizializza estensioni
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")
    limiter.init_app(app)
    
    # Configurazione Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models.user import User
        return User.query.get(int(user_id))
    
    # Registra Blueprint
    from routes.auth import bp as auth_bp
    from routes.main import bp as main_bp
    from routes.admin import bp as admin_bp
    from routes.dealer import bp as dealer_bp
    from routes.api import bp as api_bp
    from routes.system import bp as system_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(dealer_bp, url_prefix='/dealer')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(system_bp, url_prefix='/system')
    
    # Configura logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Applicazione avviata')
    
    # Crea tabelle del database
    with app.app_context():
        db.create_all()
        
        # Crea utente admin di default se non esiste
        from models.user import User
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                license_code='PREVIEW-LICENSE'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            app.logger.info('Utente admin creato con credenziali: admin/admin123')
    
    return app
