"""
Script per ricreare e inizializzare il database
AppointmentCRM - Versione Ristrutturata con IA Locale
"""

import os
import sys
from pathlib import Path

# Aggiungi il percorso dell'app al PYTHONPATH
app_path = Path(__file__).parent
sys.path.insert(0, str(app_path))

def create_database():
    """Crea e inizializza il database"""
    print("🗄️  INIZIALIZZAZIONE DATABASE")
    print("=" * 50)
    
    try:
        # Import delle componenti necessarie
        print("📦 Importando componenti...")
        from app import create_app
        from models import db, User, Appointment, Client, Consultant, Position
        
        print("✅ Componenti importate con successo")
        
        # Crea l'app
        print("\n🏗️  Creando applicazione...")
        app = create_app()
        
        with app.app_context():
            print("✅ Contesto applicazione creato")
            
            # Rimuovi database esistente se presente
            db_path = Path('appointments.db')
            if db_path.exists():
                print(f"🗑️  Rimuovendo database esistente: {db_path}")
                db_path.unlink()
            
            # Crea tutte le tabelle
            print("\n🏗️  Creando tabelle database...")
            db.create_all()
            print("✅ Tabelle create con successo")
            
            # Crea utente admin di default
            print("\n👤 Creando utente admin di default...")
            
            # Verifica se admin esiste già
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@appointmentcrm.local',
                    role='admin'
                )
                admin_user.set_password('admin123')  # Password di default
                db.session.add(admin_user)
                print("✅ Admin creato - Username: admin, Password: admin123")
            else:
                print("✅ Admin già esistente")
            
            # Crea utente dealer di default
            print("\n🤝 Creando utente dealer di default...")
            dealer_user = User.query.filter_by(username='dealer').first()
            if not dealer_user:
                dealer_user = User(
                    username='dealer',
                    email='dealer@appointmentcrm.local',
                    role='dealer'
                )
                dealer_user.set_password('dealer123')  # Password di default
                db.session.add(dealer_user)
                print("✅ Dealer creato - Username: dealer, Password: dealer123")
            else:
                print("✅ Dealer già esistente")
            
            # Crea alcuni dati di esempio
            print("\n📝 Creando dati di esempio...")
            
            # Crea alcune posizioni prima dei consulenti
            if Position.query.count() == 0:
                positions = [
                    Position(nome='Medico Generale'),
                    Position(nome='Cardiologo'),
                    Position(nome='Dermatologo')
                ]
                for position in positions:
                    db.session.add(position)
                db.session.flush()  # Per ottenere gli ID
                print("✅ Posizioni create")
            
            # Consulenti di esempio
            if Consultant.query.count() == 0:
                positions = Position.query.all()
                consultants_data = [
                    {
                        'nome': 'Dr. Mario Rossi',
                        'posizione_id': positions[0].id,
                        'phone': '+39 123 456 7890',
                        'email': 'mario.rossi@clinic.it'
                    },
                    {
                        'nome': 'Dr.ssa Anna Bianchi',
                        'posizione_id': positions[1].id,
                        'phone': '+39 123 456 7891',
                        'email': 'anna.bianchi@clinic.it'
                    },
                    {
                        'nome': 'Dr. Giuseppe Verdi',
                        'posizione_id': positions[2].id,
                        'phone': '+39 123 456 7892',
                        'email': 'giuseppe.verdi@clinic.it'
                    }
                ]
                
                for consultant_data in consultants_data:
                    consultant = Consultant(**consultant_data)
                    db.session.add(consultant)
                
                print("✅ Consulenti di esempio creati")
            
            # Clienti di esempio
            if Client.query.count() == 0:
                clients_data = [
                    {
                        'nome': 'Marco Neri',
                        'numero_telefono': '+39 334 567 8901',
                        'email': 'marco.neri@email.it',
                        'note': 'Cliente abituale, preferisce appuntamenti mattutini'
                    },
                    {
                        'nome': 'Laura Gialli',
                        'numero_telefono': '+39 335 567 8902',
                        'email': 'laura.gialli@email.it',
                        'note': 'Nuova cliente, controllo periodico'
                    },
                    {
                        'nome': 'Roberto Blu',
                        'numero_telefono': '+39 336 567 8903',
                        'email': 'roberto.blu@email.it',
                        'note': 'Cliente VIP, massima priorità'
                    }
                ]
                
                for client_data in clients_data:
                    client = Client(**client_data)
                    db.session.add(client)
                
                print("✅ Clienti di esempio creati")
            
            # Commit delle modifiche
            print("\n💾 Salvando modifiche...")
            db.session.commit()
            print("✅ Database inizializzato con successo!")
            
            # Statistiche finali
            print("\n📊 STATISTICHE DATABASE:")
            print(f"• Utenti: {User.query.count()}")
            print(f"• Consulenti: {Consultant.query.count()}")
            print(f"• Clienti: {Client.query.count()}")
            print(f"• Appuntamenti: {Appointment.query.count()}")
            
        return True
        
    except Exception as e:
        print(f"❌ Errore durante la creazione del database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database dopo la creazione"""
    print("\n" + "=" * 50)
    print("🧪 TEST DATABASE")
    print("=" * 50)
    
    try:
        from app import create_app
        from models import db, User, Consultant, Client
        
        app = create_app()
        
        with app.app_context():
            # Test connessione
            print("🔌 Test connessione database...")
            users_count = User.query.count()
            print(f"✅ Connessione OK - {users_count} utenti trovati")
            
            # Test login admin
            admin = User.query.filter_by(username='admin').first()
            if admin and admin.check_password('admin123'):
                print("✅ Login admin verificato")
            else:
                print("❌ Problema login admin")
            
            # Test login dealer
            dealer = User.query.filter_by(username='dealer').first()
            if dealer and dealer.check_password('dealer123'):
                print("✅ Login dealer verificato")
            else:
                print("❌ Problema login dealer")
            
            print("\n✅ Database pronto per l'uso!")
            return True
            
    except Exception as e:
        print(f"❌ Errore test database: {e}")
        return False

def main():
    """Procedura principale"""
    print("🏥 APPOINTMENTCRM - SETUP DATABASE")
    print("🤖 Con IA Locale Integrata")
    print("=" * 60)
    
    # Verifica prerequisiti
    print("🔍 Verifica prerequisiti...")
    
    required_files = [
        'app.py',
        'models/__init__.py',
        'config.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ File mancanti: {', '.join(missing_files)}")
        return False
    
    print("✅ Prerequisiti OK")
    
    # Crea database
    if not create_database():
        print("\n❌ Errore nella creazione del database")
        return False
    
    # Test database
    if not test_database():
        print("\n❌ Errore nel test del database")
        return False
    
    # Successo finale
    print("\n" + "🎉" * 20)
    print("DATABASE PRONTO!")
    print("🎉" * 20)
    
    print("\n📋 INFORMAZIONI LOGIN:")
    print("• Admin: username='admin', password='admin123'")
    print("• Dealer: username='dealer', password='dealer123'")
    
    print("\n🚀 PROSSIMI PASSI:")
    print("1. python app.py  # Avvia applicazione")
    print("2. http://localhost:5000  # Accedi all'interfaccia")
    print("3. Clicca l'icona IA 🤖 per testare l'assistente")
    
    print("\n🤖 IA LOCALE CARATTERISTICHE:")
    print("• Assistente completamente offline")
    print("• Elaborazione vocale integrata")
    print("• Knowledge base CRM specializzato")
    print("• Streaming risposta in tempo reale")
    print("• Privacy garantita - zero dati esterni")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n⚠️  Setup non completato. Verifica errori sopra.")
        sys.exit(1)
    
    print("\n✅ Setup completato con successo!")
    input("\nPremi Enter per continuare...")
