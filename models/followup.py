from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from .database import db

class FollowUp(db.Model):
    __tablename__ = 'follow_up'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    data_prevista = db.Column(db.DateTime, nullable=False)
    done = db.Column(db.Boolean, default=False)
    note = db.Column(db.Text, nullable=True)
    
    # Relazioni
    appointment = db.relationship('Appointment', backref=db.backref('followups', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<FollowUp {self.numero} for {self.appointment.nome_cliente if self.appointment else 'Unknown'}>"
    
    def is_overdue(self):
        """Controlla se il follow-up è in ritardo"""
        return not self.done and self.data_prevista < datetime.utcnow()
    
    def days_until_due(self):
        """Giorni rimanenti prima della scadenza"""
        if self.done:
            return 0
        
        delta = self.data_prevista - datetime.utcnow()
        return delta.days
    
    def mark_completed(self):
        """Segna il follow-up come completato"""
        self.done = True
        db.session.commit()
        
    def to_dict(self):
        """Serializza il follow-up per API JSON"""
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'numero': self.numero,
            'data_prevista': self.data_prevista.isoformat() if self.data_prevista else None,
            'done': self.done,
            'note': self.note,
            'is_overdue': self.is_overdue(),
            'days_until_due': self.days_until_due(),
            'client_name': self.appointment.nome_cliente if self.appointment else None
        }

def schedule_followups(appointment):
    """
    Pianifica automaticamente i follow-up per un appuntamento venduto
    
    Schema follow-up:
    - 1° dopo 2 giorni dalla vendita
    - 2° dopo 21 giorni dalla vendita  
    - 3°-13° ogni 3 mesi dopo la vendita
    - 14° 14 giorni prima dei 3 anni (fine garanzia)
    """
    if not appointment.venduto:
        return
        
    base = appointment.data_appuntamento
    
    # Definisce le finestre temporali per i follow-up
    windows = [
        (1, timedelta(days=2)),
        (2, timedelta(days=21))
    ] + [
        (i, relativedelta(months=3 * (i - 2))) for i in range(3, 14)
    ] + [
        (14, relativedelta(years=3, days=-14))
    ]
    
    # Crea i follow-up
    for num, delta in windows:
        existing = FollowUp.query.filter_by(
            appointment_id=appointment.id, 
            numero=num
        ).first()
        
        if not existing:  # Evita duplicati
            fu = FollowUp(
                appointment_id=appointment.id, 
                numero=num, 
                data_prevista=base + delta
            )
            db.session.add(fu)
    
    db.session.commit()

def get_pending_followups(limit=None):
    """Ottieni follow-up pendenti ordinati per data"""
    query = FollowUp.query.filter_by(done=False).order_by(FollowUp.data_prevista)
    
    if limit:
        query = query.limit(limit)
        
    return query.all()

def get_overdue_followups():
    """Ottieni follow-up in ritardo"""
    return FollowUp.query.filter(
        FollowUp.done == False,
        FollowUp.data_prevista < datetime.utcnow()
    ).order_by(FollowUp.data_prevista).all()
