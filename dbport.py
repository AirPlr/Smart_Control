from app import db, User, Consultant, Appointment, Client, Position, app
from sqlalchemy import inspect

def add_missing_columns(model):
    table = model.__table__
    table_name = table.name
    inspector = inspect(db.engine)
    try:
        current_columns = [col["name"] for col in inspector.get_columns(table_name)]
    except Exception as e:
        print(f"Errore nell'ispezionare la tabella {table_name}: {e}")
        return
    for column in table.columns:
        if column.name not in current_columns:
            # Genera la porzione di definizione SQL per la colonna
            col_spec = f"{column.name} {column.type}"
            # Se la colonna è nullable, non serve specificare nulla; altrimenti per SQLite è meglio non avere restrizioni severe
            if not column.nullable:
                col_spec += " DEFAULT NULL"
            alter_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col_spec};"
            try:
                db.engine.execute(alter_stmt)
                print(f"Aggiunta la colonna '{column.name}' alla tabella '{table_name}'.")
            except Exception as e:
                print(f"Errore durante l'aggiunta della colonna '{column.name}' a '{table_name}': {e}")

def delete_column(model, column_name):
    # Funzione per eliminare una colonna da un modello
    table = model.__table__
    table_name = table.name
    inspector = inspect(db.engine)
    try:
        current_columns = [col["name"] for col in inspector.get_columns(table_name)]
    except Exception as e:
        print(f"Errore nell'ispezionare la tabella {table_name}: {e}")
        return
    if column_name in current_columns:
        # Genera la porzione di definizione SQL per eliminare la colonna
        drop_stmt = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
        try:
            db.engine.execute(drop_stmt)
            print(f"Colonna '{column_name}' eliminata dalla tabella '{table_name}'.")
        except Exception as e:
            print(f"Errore durante l'eliminazione della colonna '{column_name}' da '{table_name}': {e}")

def create_new_tables():
    # Crea le tabelle se non esistono già
    db.create_all()


if __name__ == "__main__":
    from app import app  # Assicurati di importare l'app
    with app.app_context():
        print("Inizio aggiornamento schema database...")
        # Verifica ed aggiorna per ciascun modello
        for model in [User, Consultant, Appointment, Client, Position]:
            
            add_missing_columns(model)
        delete_column(Consultant, "posizione")
        print("Aggiornamento completato.")