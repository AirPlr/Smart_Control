"""
Database instance for AppointmentCRM
Separato per evitare import circolari
"""

from flask_sqlalchemy import SQLAlchemy

# Istanza SQLAlchemy condivisa
db = SQLAlchemy()

# Tabella di associazione many-to-many per appointment-consultant
appointment_consultant = db.Table('appointment_consultant',
    db.Column('appointment_id', db.Integer, db.ForeignKey('appointment.id'), primary_key=True),
    db.Column('consultant_id', db.Integer, db.ForeignKey('consultant.id'), primary_key=True)
)
