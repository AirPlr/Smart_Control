from datetime import datetime
from .database import db, appointment_consultant

class Appointment(db.Model):
    __tablename__ = 'appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    indirizzo = db.Column(db.String(200))
    numero_telefono = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    tipologia = db.Column(db.String(20))
    stato = db.Column(db.String(20), nullable=False)  # "concluso", "da richiamare", "non richiamare"
    nominativi_raccolti = db.Column(db.Integer, default=0)
    appuntamenti_personali = db.Column(db.Integer, default=0)
    venduto = db.Column(db.Boolean, default=False)
    data_appuntamento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_richiamo = db.Column(db.DateTime, nullable=True)  # Data di richiamo se "da richiamare"
    
    # Relazioni
    consultants = db.relationship('Consultant', secondary=appointment_consultant, lazy='subquery',
                                  backref=db.backref('appointments', lazy=True))

    def __repr__(self):
        return f"<Appointment {self.nome_cliente} - {self.stato}>"
    
    def to_dict(self):
        """Serializza l'appuntamento per API JSON"""
        return {
            'id': self.id,
            'nome_cliente': self.nome_cliente,
            'indirizzo': self.indirizzo,
            'numero_telefono': self.numero_telefono,
            'note': self.note,
            'tipologia': self.tipologia,
            'stato': self.stato,
            'nominativi_raccolti': self.nominativi_raccolti,
            'appuntamenti_personali': self.appuntamenti_personali,
            'venduto': self.venduto,
            'data_appuntamento': self.data_appuntamento.isoformat() if self.data_appuntamento else None,
            'data_richiamo': self.data_richiamo.isoformat() if self.data_richiamo else None,
            'consultants': [c.id for c in self.consultants]
        }

class OtherAppointment(db.Model):
    __tablename__ = 'other_appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    indirizzo = db.Column(db.String(200))
    numero_telefono = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    stato = db.Column(db.String(20), nullable=False)  # "concluso", "da richiamare", "non richiamare"
    tipologia = db.Column(db.String(20))
    nominativi_raccolti = db.Column(db.Integer, default=0)
    appuntamenti_personali = db.Column(db.Integer, default=0)
    venduto = db.Column(db.Boolean, default=False)
    data_appuntamento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_richiamo = db.Column(db.DateTime, nullable=True)  # Data di richiamo se "da richiamare"

    def __repr__(self):
        return f"<OtherAppointment {self.nome_cliente} - {self.stato}>"
    
    def to_dict(self):
        """Serializza l'altro appuntamento per API JSON"""
        return {
            'id': self.id,
            'nome_cliente': self.nome_cliente,
            'indirizzo': self.indirizzo,
            'numero_telefono': self.numero_telefono,
            'note': self.note,
            'stato': self.stato,
            'tipologia': self.tipologia,
            'nominativi_raccolti': self.nominativi_raccolti,
            'appuntamenti_personali': self.appuntamenti_personali,
            'venduto': self.venduto,
            'data_appuntamento': self.data_appuntamento.isoformat() if self.data_appuntamento else None,
            'data_richiamo': self.data_richiamo.isoformat() if self.data_richiamo else None
        }
