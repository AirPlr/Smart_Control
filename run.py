#!/usr/bin/env python3
"""
App Ristrutturata - Sistema di Gestione Appuntamenti Multiuser
Versione Preview con Sicurezza Migliorata

Caratteristiche:
- Architettura modulare con Factory Pattern
- Sistema multiuser (Admin, Dealer, Viewer)
- Dashboard mobile-ottimizzata per dealer
- Console sistema sicura per admin
- Gestione VPN/Tailscale integrata
- API REST sicure con rate limiting

Avvio: python run.py
"""

import os
import sys
from flask import Flask, request, render_template
from flask_migrate import Migrate

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.user import db

# Socket.IO per funzionalità real-time
try:
    from flask_socketio import SocketIO
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

# Crea l'applicazione
app = create_app(os.getenv('FLASK_ENV', 'development'))

# Inizializza Flask-Migrate per gestione database
migrate = Migrate(app, db)

# Inizializza SocketIO se disponibile
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
    
    @socketio.on('connect')
    def handle_connect():
        """Gestisce connessione Socket.IO"""
        pass
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Gestisce disconnessione Socket.IO"""
        pass
else:
    socketio = None

# Context processors per template
@app.context_processor
def inject_user_data():
    """Inietta dati utente comuni in tutti i template"""
    from flask_login import current_user
    return {
        'current_user': current_user,
        'user_role': current_user.role if current_user.is_authenticated else None,
        'is_mobile': request.user_agent.platform in ['android', 'iphone'] if request else False
    }

# Filtri personalizzati per template
@app.template_filter('datetime_format')
def datetime_format(value, format='%d/%m/%Y %H:%M'):
    """Formatta datetime per i template"""
    if value:
        return value.strftime(format)
    return ''

@app.template_filter('currency')
def currency_format(value):
    """Formatta valute"""
    if value:
        return f"€ {value:,.2f}"
    return "€ 0,00"

# Error handlers
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

# Security headers
@app.after_request
def after_request(response):
    """Aggiunge security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # CSP per permettere gli assets esterni (Bootstrap, FontAwesome, etc.)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:;"
    )
    
    return response

# CLI Commands per gestione app
@app.cli.command()
def create_admin():
    """Crea un utente amministratore"""
    from models.user import User
    import getpass
    
    username = input("Username admin: ")
    email = input("Email admin: ")
    password = getpass.getpass("Password admin: ")
    
    if User.query.filter_by(username=username).first():
        print("❌ Username già esistente")
        return
    
    admin = User(
        username=username,
        email=email,
        role='admin',
        license_code='ADMIN-LICENSE'
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"✅ Admin {username} creato con successo!")

@app.cli.command()
def init_demo_data():
    """Inizializza dati demo per test"""
    from models.user import User
    from models.consultant import Consultant, Position
    from models.appointment import Appointment
    from datetime import datetime, timedelta
    import random
    
    print("🚀 Inizializzando dati demo...")
    
    # Crea posizioni
    positions = ['Responsabile', 'Senior', 'Junior', 'Stagista']
    for pos_name in positions:
        if not Position.query.filter_by(nome=pos_name).first():
            pos = Position(nome=pos_name)
            db.session.add(pos)
    
    db.session.commit()
    
    # Crea consulenti demo
    consultant_names = ['Mario Rossi', 'Giulia Bianchi', 'Luca Verdi', 'Sara Neri']
    for name in consultant_names:
        if not Consultant.query.filter_by(nome=name).first():
            consultant = Consultant(
                nome=name,
                posizione_id=random.randint(1, 4),
                email=f"{name.lower().replace(' ', '.')}@company.com",
                phone=f"33912345{random.randint(10, 99)}"
            )
            db.session.add(consultant)
    
    db.session.commit()
    
    # Crea utenti dealer demo
    consultants = Consultant.query.all()
    for consultant in consultants[:2]:  # Solo primi 2
        username = consultant.nome.lower().replace(' ', '.')
        if not User.query.filter_by(username=username).first():
            user = User(
                username=username,
                email=consultant.email,
                role='dealer',
                consultant_id=consultant.id,
                license_code='DEALER-LICENSE'
            )
            user.set_password('demo123')
            db.session.add(user)
    
    db.session.commit()
    
    # Crea appuntamenti demo
    for i in range(20):
        appointment = Appointment(
            nome_cliente=f"Cliente Demo {i+1}",
            numero_telefono=f"333123456{i:02d}",
            indirizzo=f"Via Demo {i+1}, Milano",
            tipologia=random.choice(['Assistenza', 'Dimostrazione', 'Consumabili']),
            stato=random.choice(['concluso', 'da richiamare', 'non richiamare']),
            venduto=random.choice([True, False]),
            data_appuntamento=datetime.now() - timedelta(days=random.randint(0, 30)),
            note=f"Note demo per appuntamento {i+1}"
        )
        
        # Associa consulente random
        consultant = random.choice(consultants)
        appointment.consultants.append(consultant)
        
        db.session.add(appointment)
    
    db.session.commit()
    print("✅ Dati demo creati con successo!")
    print("\n👥 Utenti demo creati:")
    print("- admin/admin123 (Amministratore)")
    for consultant in consultants[:2]:
        username = consultant.nome.lower().replace(' ', '.')
        print(f"- {username}/demo123 (Dealer - {consultant.nome})")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='App Ristrutturata')
    parser.add_argument('--host', default='127.0.0.1', help='Host address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--demo', action='store_true', help='Initialize with demo data')
    
    args = parser.parse_args()
    
    if args.demo:
        with app.app_context():
            from flask.cli import with_appcontext
            init_demo_data()
    
    print(f"""
🚀 App Ristrutturata con AI Assistant in avvio...

📱 Dashboard Dealer (Mobile + AI): http://{args.host}:{args.port}/dealer/dashboard  
🔧 Pannello Admin: http://{args.host}:{args.port}/admin/dashboard
🌐 VPN Management + AI: http://{args.host}:{args.port}/admin/vpn
📡 API Endpoints: http://{args.host}:{args.port}/api/
🤖 AI Assistant API: http://{args.host}:{args.port}/ai/

🔐 Credenziali default:
   Admin: admin / admin123
   
🤖 AI Assistant Features:
   • Chat testuale con streaming
   • Elaborazione vocale bidirezionale  
   • Analisi contestuali automatiche
   • Supporto mobile-first per dealer
   • Integrazione VPN e sistema per admin
   • Scorciatoia: Ctrl+K per aprire ovunque
   
💡 Usa --demo per inizializzare con dati di esempio
""")
    
    # Avvia l'applicazione
    if SOCKETIO_AVAILABLE and socketio:
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug
        )
    else:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug
        )
