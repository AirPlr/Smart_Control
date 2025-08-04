#!/usr/bin/env python3
"""
Script di migrazione per aggiungere il campo include_in_reports alla tabella appointment
"""

import sys
import os
from pathlib import Path

# Aggiungi il percorso root del progetto al sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.database import db
from models.appointment import Appointment
from app import create_app

def migrate_database():
    """Esegue la migrazione del database"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verifica se la colonna esiste già
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('appointment')]
            
            if 'include_in_reports' in columns:
                print("✓ La colonna 'include_in_reports' esiste già.")
                return
            
            print("Aggiunta della colonna 'include_in_reports' alla tabella appointment...")
            
            # Aggiungi la colonna
            db.engine.execute('ALTER TABLE appointment ADD COLUMN include_in_reports BOOLEAN DEFAULT TRUE;')
            
            # Aggiorna tutti i record esistenti
            # I consumabili (tipologia = 'Consumabili') vengono esclusi dai report di default
            db.engine.execute("""
                UPDATE appointment 
                SET include_in_reports = CASE 
                    WHEN tipologia = 'Consumabili' THEN FALSE 
                    ELSE TRUE 
                END;
            """)
            
            print("✓ Migrazione completata con successo!")
            print("- Colonna 'include_in_reports' aggiunta")
            print("- Consumabili esistenti esclusi dai report")
            print("- Altri appuntamenti inclusi nei report")
            
        except Exception as e:
            print(f"❌ Errore durante la migrazione: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("=== Migrazione Database: Campo include_in_reports ===")
    success = migrate_database()
    
    if success:
        print("\n🎉 Migrazione completata con successo!")
        print("\nOra i consumabili possono essere esclusi/inclusi nei report tramite:")
        print("1. Form di aggiunta appuntamento - checkbox 'Includi nei Report'")
        print("2. Form di modifica appuntamento - checkbox 'Includi nei Report'") 
        print("3. Generazione report - checkbox 'Includi appuntamenti esclusi dai report'")
    else:
        print("\n❌ Migrazione fallita!")
        sys.exit(1)
