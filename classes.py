from app import db
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class note_event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Note {self.note}>"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=True)
    company_address = db.Column(db.String(200), nullable=True)
    company_phone = db.Column(db.String(20), nullable=True)
    license_expiry = db.Column(db.DateTime, nullable=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(2), nullable=False)
    license_code = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<User {self.username}, {self.email}, {self.language}, {self.license_code}>"

class Consultant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    posizione = db.Column(db.String(20), nullable=False)
    responsabile_id = db.Column(db.Integer, db.ForeignKey('consultant.id'), nullable=True)
    responsabili = db.relationship('Consultant', remote_side=[id], backref='subordinati')
    totalYearlyPay = db.Column(db.Float, default=0.0)
    residency = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    CF = db.Column(db.String(16), nullable=True)

    def __repr__(self):
        return f"<Consultant {self.nome}, {self.posizione}, {self.responsabile_id}>"

appointment_consultant = db.Table('appointment_consultant',
    db.Column('appointment_id', db.Integer, db.ForeignKey('appointment.id'), primary_key=True),
    db.Column('consultant_id', db.Integer, db.ForeignKey('consultant.id'), primary_key=True)
)

class Appointment(db.Model):
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
    consultants = db.relationship('Consultant', secondary=appointment_consultant, lazy='subquery',
                                  backref=db.backref('appointments', lazy=True))

    def __repr__(self):
        return f"<Appointment {self.nome_cliente} - {self.stato}>"

class OtherAppointment(db.Model):
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


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    indirizzo = db.Column(db.String(200), nullable=True)
    numero_telefono = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    data_registrazione = db.Column(db.DateTime, default=datetime.utcnow)
    note= db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Client {self.nome}>"

class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    data_prevista = db.Column(db.DateTime, nullable=False)
    done = db.Column(db.Boolean, default=False)
    appointment = db.relationship('Appointment', backref=db.backref('followups', lazy=True, cascade="all, delete-orphan"))


def schedule_followups(appointment):
    base = appointment.data_appuntamento
    # Follow-up schedule: 1st after 2 days of sale, 2nd after 21 days of sale, 3rd to 11th every 3 months after the sale, and at the end of warranty, 14 days before the 3 years mark
    windows = [

            (1, timedelta(days=2)),
            (2, timedelta(days=21))
        ] + [
            (i, relativedelta(months=3 * (i - 2))) for i in range(3, 14)
        ] + [
            (14, relativedelta(years=3, days=-14))
        ]
    
    for num, delta in windows:
        fu = FollowUp(appointment_id=appointment.id, numero=num, data_prevista=base + delta)
        db.session.add(fu)
    db.session.commit()

