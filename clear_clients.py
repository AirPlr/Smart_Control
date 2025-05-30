from flask_sqlalchemy import SQLAlchemy
from app import app  # Replace 'your_app_file' with the actual name of your app file where the db is defined
from app import Client  # Import the Client model from your app

# Initialize the database
db = SQLAlchemy(app)

def clear_clients():
    # Clear all clients from the Client table
    try:
        db.session.query(Client).delete()
        db.session.commit()
        print("All clients have been cleared from the database.")
    except Exception as e:
        db.session.rollback()
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    with app.app_context():
        clear_clients()
