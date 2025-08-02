from datetime import datetime
from .database import db

class Client(db.Model):
    __tablename__ = 'client'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    indirizzo = db.Column(db.String(200), nullable=True)
    numero_telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    data_registrazione = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Client {self.nome}>"
    
    def get_appointments(self):
        """Ottieni tutti gli appuntamenti del cliente"""
        from .appointment import Appointment, OtherAppointment
        
        appointments = Appointment.query.filter_by(nome_cliente=self.nome).all()
        other_appointments = OtherAppointment.query.filter_by(nome_cliente=self.nome).all()
        
        return {
            'appointments': appointments,
            'other_appointments': other_appointments,
            'total': len(appointments) + len(other_appointments)
        }
    
    def has_sold_appointment(self):
        """Controlla se il cliente ha almeno un appuntamento venduto"""
        from .appointment import Appointment, OtherAppointment
        
        sold_regular = Appointment.query.filter_by(nome_cliente=self.nome, venduto=True).first()
        sold_other = OtherAppointment.query.filter_by(nome_cliente=self.nome, venduto=True).first()
        
        return sold_regular is not None or sold_other is not None
    
    def to_dict(self):
        """Serializza il cliente per API JSON"""
        return {
            'id': self.id,
            'nome': self.nome,
            'indirizzo': self.indirizzo,
            'numero_telefono': self.numero_telefono,
            'email': self.email,
            'data_registrazione': self.data_registrazione.isoformat() if self.data_registrazione else None,
            'note': self.note,
            'has_purchases': self.has_sold_appointment()
        }
