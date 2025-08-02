from datetime import datetime
from .database import db

class Position(db.Model):
    __tablename__ = 'position'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Position {self.nome}>"

class Consultant(db.Model):
    __tablename__ = 'consultant'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    posizione_id = db.Column(db.Integer, db.ForeignKey('position.id'), nullable=False)
    posizione = db.relationship('Position', backref='consultants')
    responsabile_id = db.Column(db.Integer, db.ForeignKey('consultant.id'), nullable=True)
    responsabili = db.relationship('Consultant', remote_side=[id], backref='subordinati')
    totalYearlyPay = db.Column(db.Float, default=0.0)
    residency = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    CF = db.Column(db.String(16), nullable=True)

    def __repr__(self):
        return f"<Consultant {self.nome}, {self.posizione.nome if self.posizione else 'Nessuna posizione'}, {self.responsabile_id}>"
    
    def get_appointments_stats(self):
        """Statistiche appuntamenti per il consulente"""
        from .appointment import Appointment
        
        appointments = self.appointments
        total = len(appointments)
        sold = len([a for a in appointments if a.venduto])
        
        return {
            'total': total,
            'sold': sold,
            'conversion_rate': (sold / total * 100) if total > 0 else 0,
            'assistenza': len([a for a in appointments if a.tipologia == 'Assistenza']),
            'dimostrazione': len([a for a in appointments if a.tipologia == 'Dimostrazione'])
        }
