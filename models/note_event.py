from datetime import datetime
from .database import db

class note_event(db.Model):
    __tablename__ = 'note_event'
    
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campi aggiuntivi per eventi
    categoria = db.Column(db.String(50), default='generale')  # generale, importante, reminder
    colore = db.Column(db.String(7), default='#4f46e5')  # Colore hex per visualizzazione
    completato = db.Column(db.Boolean, default=False)
    
    # Associazione utente (opzionale)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self):
        return f"<Note {self.note[:50]}{'...' if len(self.note) > 50 else ''}>"
    
    def is_today(self):
        """Controlla se l'evento è oggi"""
        if not self.data:
            return False
        return self.data.date() == datetime.today().date()
    
    def is_overdue(self):
        """Controlla se l'evento è scaduto (e non completato)"""
        if self.completato:
            return False
        return self.data < datetime.utcnow()
    
    def mark_completed(self):
        """Segna l'evento come completato"""
        self.completato = True
        db.session.commit()
    
    def to_dict(self):
        """Serializza l'evento per API JSON"""
        return {
            'id': self.id,
            'note': self.note,
            'data': self.data.isoformat() if self.data else None,
            'categoria': self.categoria,
            'colore': self.colore,
            'completato': self.completato,
            'is_today': self.is_today(),
            'is_overdue': self.is_overdue(),
            'user_id': self.user_id
        }

def get_events_for_date(date):
    """Ottieni tutti gli eventi per una data specifica"""
    return note_event.query.filter(db.func.date(note_event.data) == date).all()

def get_upcoming_events(days=7):
    """Ottieni eventi dei prossimi N giorni"""
    from datetime import timedelta
    
    today = datetime.today()
    future_date = today + timedelta(days=days)
    
    return note_event.query.filter(
        note_event.data >= today,
        note_event.data <= future_date,
        note_event.completato == False
    ).order_by(note_event.data).all()

def get_overdue_events():
    """Ottieni eventi scaduti non completati"""
    return note_event.query.filter(
        note_event.data < datetime.utcnow(),
        note_event.completato == False
    ).order_by(note_event.data).all()
