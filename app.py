from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
import xlsxwriter
from io import BytesIO
from cryptography.fernet import Fernet
import funzioni
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
import os
import sys
import zipfile
import requests
import shutil
import subprocess
from io import BytesIO
from dateutil.relativedelta import relativedelta
from flask_socketio import SocketIO, emit  # added for live terminal
import platform
import psutil
import socket
from theme_tools import patch_css, CSS_PATH




    
# Generate a key for encryption/decryption
# You must store and keep this key safe. If you lose it, you won't be able to decrypt your data.
key = b'KrBNJNSPev7iSQFFISdi0JvvMWYzeM6HMGdejH_o8Sg='

call_check_license = False

if not call_check_license:
    original_get = requests.get

    def fake_get(url, params=None, **kwargs):
        if 'check_license' in url:
            class FakeResponse:
                status_code = 200

                def json(self):
                    return {'expiration_date': '2050-12-31'}
            return FakeResponse()
        return original_get(url, params=params, **kwargs)

    requests.get = fake_get


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'  # Cambia la chiave in produzione
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'appointments.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, async_mode='eventlet')  # initialize socketio
    


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

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Position {self.nome}>"

class Consultant(db.Model):
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



with app.app_context():
    db.create_all()


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = User.query.first()  # Assuming there's only one user for simplicity
    if not user:
        # Set a default license expiry in case none is provided
        user = User(username='username', email='email', language='it', license_code='ABC123', license_expiry=datetime(2025, 12, 31))
        db.session.add(user)
        db.session.commit()
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.language = request.form.get('language')
        user.license_code = request.form.get('license_code')
        user.company_name = request.form.get('company_name')
        user.company_address = request.form.get('company_address')
        user.company_phone = request.form.get('company_phone')
        if 'company_logo' in request.files:
            logo = request.files['company_logo']
            if logo:
                funzioni.changelogo(logo.read())
            print("Logo cambiato")
        db.session.commit()
        flash("Impostazioni salvate con successo!")
        return redirect(url_for('settings'))

    # Retrieve the license expiration date from the external server
    try:
        resp = requests.get('http://localhost:5100/check_license', params={'license': user.license_code})
        if resp.status_code == 200:
            data = resp.json()
            expiration_str = data.get('expiration_date')
            if expiration_str:
                license_expiry = datetime.strptime(expiration_str, '%Y-%m-%d')
            else:
                license_expiry = user.license_expiry
        else:
            license_expiry = user.license_expiry
    except Exception:
        license_expiry = user.license_expiry

    expiration_days = (license_expiry - datetime.today()).days if license_expiry else None
    return render_template('settings.html', user=user, datetime=datetime, expiration_days=expiration_days)

@app.route('/')
def index():
    user = User.query.first()
    if not user:
        return redirect(url_for('settings'))
    # Attempt license verification but do not block access
    try:
        resp = requests.get('http://localhost:5100/check_license', params={'license': user.license_code})
        if resp.status_code == 200:
            data = resp.json()
            expiration_str = data.get('expiration_date')
            if expiration_str:
                user.license_expiry = datetime.strptime(expiration_str, '%Y-%m-%d')
                db.session.commit()
        else:
            raise Exception("License check failed")
    except Exception:
        return redirect(url_for('license'))
    expiration_days = (user.license_expiry.date() - datetime.today().date()).days if user.license_expiry else None
    today = datetime.today().date()
    recall_appointments = Appointment.query.filter(
        Appointment.stato.ilike('da richiamare'),
        db.func.date(Appointment.data_richiamo) == today
    ).all()
    current_date = today.strftime('%d/%m/%Y')
    return render_template('index.html', recall_appointments=recall_appointments, current_date=current_date, datetime=datetime)


@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if request.method == 'POST':
        month = request.form.get('month')
        year = request.form.get('year')
        if month and year:
            try:
                month = int(month)
                year = int(year)
                if month < 1 or month > 12 or year < 2000:
                    raise ValueError
            except ValueError:
                flash("Data non valida")
                return redirect(url_for('calendar'))
            appointments = Appointment.query.filter(
                db.func.extract('month', Appointment.data_appuntamento) == month,
                db.func.extract('year', Appointment.data_appuntamento) == year
            ).all()
            oapps = OtherAppointment.query.filter(
                db.func.extract('month', OtherAppointment.data_appuntamento) == month,
                db.func.extract('year', OtherAppointment.data_appuntamento) == year
            ).all()
            if not appointments and not oapps:
                flash("Nessun appuntamento trovato per questa data.")
                return redirect(url_for('calendar'))

        else:
            appointments = Appointment.query.all()
            oapps = OtherAppointment.query.all()
    else:
        appointments = Appointment.query.all()
        oapps = OtherAppointment.query.all()
    if not appointments and not oapps:
        flash("Nessun appuntamento trovato.")
        return render_template('calendar.html', appointments=[], oapps=[], datetime=datetime)
    return render_template('calendar.html', appointments=appointments, oapps=oapps, datetime=datetime)

@app.route('/service')
def service():
    appointments = Appointment.query.filter_by(venduto=True).all()
    return render_template('service.html', appointments=appointments, datetime=datetime)

@app.route('/events/')
def events():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify(events=[])
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify(events=[])
    appointments = Appointment.query.filter(db.func.date(Appointment.data_appuntamento) == selected_date).all()
    events = []
    for appointment in appointments:
        events.append({
            'id': appointment.id,
            'title': appointment.nome_cliente,
            'start': appointment.data_appuntamento.strftime('%Y-%m-%d'),
            'type': appointment.tipologia,
            'note': appointment.note
        })
    for oapp in OtherAppointment.query.filter(db.func.date(OtherAppointment.data_appuntamento) == selected_date).all():
        events.append({
            'id': oapp.id,
            'title': oapp.nome_cliente,
            'start': oapp.data_appuntamento.strftime('%Y-%m-%d'),
            'type': oapp.tipologia,
            'note': oapp.note
        })
    for note in note_event.query.filter(db.func.date(note_event.data) == selected_date).all():
        events.append({
            'id': note.id,
            'title': note.note,
            'start': note.data.strftime('%Y-%m-%d'),
            'type': 'note',
            'note': note.note
        })
    for fu in FollowUp.query.filter(db.func.date(FollowUp.data_prevista) == selected_date, FollowUp.done == False).all():
        events.append({
            'id': f'f{fu.id}',
            'title': f"Follow-up {fu.numero} - {fu.appointment.nome_cliente}",
            'start': fu.data_prevista.strftime('%Y-%m-%d'),
            'type': 'followup'
        })
    return jsonify(events=events)


@app.route('/events/add/', methods=['POST'])
def add_note_event():
    date_str = request.form.get('date')
    notes = request.form.get('notes')
    if not date_str or not notes:
        return jsonify({'status': 'error', 'message': 'Missing date or notes.'}), 400
    try:
        event_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format, use YYYY-MM-DD.'}), 400
    new_event = note_event(note=notes, data=event_date)
    db.session.add(new_event)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Note event created successfully.'})


@app.route('/clients', methods=['GET'])
def clients():
    all_clients = Client.query.all()
    # compute clients with at least one sold appointment
    sold_appts = Appointment.query.filter_by(venduto=True).with_entities(Appointment.nome_cliente).all()
    sold_other = OtherAppointment.query.filter_by(venduto=True).with_entities(OtherAppointment.nome_cliente).all()
    sold_names = set([name for (name,) in sold_appts] + [name for (name,) in sold_other])
    # handle search and venduto filters
    search = request.args.get('search', '').strip().lower()
    venduto_arg = request.args.get('venduto')  # 'true', 'false', or None
    filtered = []
    for client in all_clients:
        # aggregate searchable fields
        fields = [
            client.nome,
            client.indirizzo or '', client.numero_telefono or '', client.email or '',
            client.data_registrazione.strftime('%d/%m/%Y'),
            client.note or ''
        ]
        text = ' '.join(fields).lower()
        # search match
        if search and search not in text:
            continue
        # venduto filter
        if venduto_arg == 'true' and client.nome not in sold_names:
            continue
        if venduto_arg == 'false' and client.nome in sold_names:
            continue
        filtered.append(client)
    clients = filtered
    if not clients:
        flash("Nessun cliente trovato.")
        return redirect(url_for('index'))
    return render_template('clients.html', clients=clients, sold_names=sold_names, datetime=datetime,
                           search=search, venduto=venduto_arg)


@app.route('/client_service/<int:id>', methods=['GET'])
def client_service(id):
    client = Client.query.get_or_404(id)
    # Retrieve all appointments and their follow-ups for this client
    appointments = Appointment.query.filter_by(nome_cliente=client.nome).all()
    return render_template('client_service.html', client=client, appointments=appointments, datetime=datetime)

@app.route('/client_actions', methods=['GET'])
def client_actions():
    client_id = request.args.get('id')
    if not client_id:
        return {"appointments": [], "otherAppointments": []}
    
    client = Client.query.get(client_id)
    if not client:
        return {"appointments": [], "otherAppointments": []}
    
    appointments = Appointment.query.filter(Appointment.nome_cliente == client.nome).all()
    other_appointments = OtherAppointment.query.filter(OtherAppointment.nome_cliente == client.nome).all()
    
    appts = [f"{appt.data_appuntamento.strftime('%Y-%m-%d')} - Tipologia: {appt.tipologia}" for appt in appointments]
    other_appts = [f"{oappt.data_appuntamento.strftime('%Y-%m-%d')} - Tipologia: {oappt.tipologia}" for oappt in other_appointments]
    # Build list of follow-ups for this client's appointments
    followups = []
    for appt in appointments:
        for fu in appt.followups:
            if fu.done:
                followups.append(f"{fu.data_prevista.strftime('%Y-%m-%d')} - Follow-up {fu.numero}")
    # No follow-ups for OtherAppointment, so empty list
    other_followups = []
    
    return {"appointments": appts, "otherAppointments": other_appts, "followups": followups, "otherFollowups": other_followups}


@app.route('/submit-license', methods=['POST'])
def submit_license():
    license_code = request.form.get('license_code')
    user = User.query.first()
    if user:
        user.license_code = license_code
        
        db.session.commit()
        return redirect(url_for('index'))
    return redirect(url_for('settings'))


@app.route('/consultants', methods=['GET'])
def consultants():
    consultants = Consultant.query.all()
    return render_template('consultants.html', consultants=consultants)

@app.route('/consultantsdb', methods=['GET'])
def consultantsdb():
    consultants = Consultant.query.all()
    consultants_list = [
        {
            "id": consultant.id,
            "nome": consultant.nome,
            "posizione": consultant.posizione,
            "responsabile_id": consultant.responsabile_id,
            "totalYearlyPay": consultant.totalYearlyPay,
            "residency": consultant.residency,
            "phone": consultant.phone,
            "email": consultant.email,
            "CF": consultant.CF
        } for consultant in consultants
    ]
    response = make_response(json.dumps(consultants_list))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=consultants.json'
    return response

@app.route('/modify_consultant/<int:id>', methods=['GET', 'POST'])
def modify_consultant(id):
    consultant = Consultant.query.get(id)
    consultants = Consultant.query.all()
    positions = Position.query.all()
    if request.method == 'POST':
        consultant.nome = request.form.get('nome')
        posizione_id = request.form.get('posizione_id', type=int)
        consultant.posizione_id = posizione_id if posizione_id else get_or_create_default_position().id
        consultant.responsabile_id = request.form.get('responsabile_id')
        consultant.residency = request.form.get('residency')
        consultant.phone = request.form.get('phone')
        consultant.email = request.form.get('email')
        consultant.CF = request.form.get('CF')
        db.session.commit()
        flash("Consulente modificato con successo!")
        return redirect(url_for('consultants'))
    return render_template('modify_consultant.html', consultant=consultant, consultants=consultants, positions=positions)

# Endpoint per gestire le posizioni (aggiungi, elimina)
@app.route('/positions', methods=['GET', 'POST', 'DELETE'])
def manage_positions():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome:
            pos = Position(nome=nome)
            db.session.add(pos)
            db.session.commit()
            return jsonify({'success': True, 'id': pos.id, 'nome': pos.nome})
        return jsonify({'success': False, 'error': 'Nome mancante'}), 400
    elif request.method == 'DELETE':
        pos_id = request.form.get('id', type=int)
        pos = Position.query.get(pos_id)
        if pos:
            default = get_or_create_default_position()
            for consultant in pos.consultants:
                consultant.posizione_id = default.id
            db.session.delete(pos)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Posizione non trovata'}), 404
    else:
        positions = Position.query.all()
        return jsonify([{'id': p.id, 'nome': p.nome} for p in positions])


@app.route('/license', methods=['GET'])
def license():
    return render_template('license.html')

@app.route('/delete_consultant/<int:id>', methods=['GET'])
def delete_consultant(id):
    consultant = Consultant.query.get_or_404(id)
    mentor = Consultant.query.get(consultant.responsabile_id)
    if mentor:
        for appointment in consultant.appointments:
            if appointment.venduto:
                mentor.appointments.append(appointment)
    for subordinato in consultant.subordinati:
        subordinato.responsabile_id = None
    db.session.delete(consultant)
    db.session.commit()
    flash("Consulente eliminato con successo!")
    return redirect(url_for('consultants'))

@app.route('/add', methods=['GET', 'POST'])
def add_appointment():
    consultants = Consultant.query.all()
    clients = Client.query.all()
    if request.method == 'POST':
        nome_cliente = request.form.get('nome_cliente')
        consultant_ids = request.form.get('consultants')
        if consultant_ids:
            consultant_ids = json.loads(consultant_ids)
            if not isinstance(consultant_ids, list) or not consultant_ids:
                flash("Seleziona almeno un consulente valido!")
                return redirect(url_for('add_appointment'))
        else:
            flash("Seleziona almeno un consulente valido!")
            return redirect(url_for('add_appointment'))
        
        indirizzo = request.form.get('indirizzo')
        numero_telefono = request.form.get('numero_telefono')
        note = request.form.get('note')
        tipologia = request.form.get('tipologia')
        stato = request.form.get('stato')
        nominativi_raccolti = request.form.get('nominativi_raccolti', 0, type=int)
        appuntamenti_personali = request.form.get('appuntamenti_personali', 0, type=int)
        venduto = True if request.form.get('venduto') == 'on' else False
        
        data_appuntamento_str = request.form.get('data_appuntamento')
        data_richiamo_str = request.form.get('data_richiamo')
        
        try:
            data_appuntamento = datetime.strptime(data_appuntamento_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            flash("Formato data appuntamento non valido, usare YYYY-MM-DD")
            return redirect(url_for('add_appointment'))
        
        if stato.lower() == 'da richiamare':
            if not data_richiamo_str:
                flash("Per appuntamenti 'da richiamare' inserire la data di richiamo!")
                return redirect(url_for('add_appointment'))
            try:
                data_richiamo = datetime.strptime(data_richiamo_str, '%Y-%m-%d')
            except ValueError:
                flash("Formato data richiamo non valido, usare YYYY-MM-DD")
                return redirect(url_for('add_appointment'))
        else:
            data_richiamo = None
        
        if not nome_cliente or not consultant_ids or not numero_telefono:
            flash("Il nome del cliente, il consulente e il numero di telefono sono obbligatori!")
            return redirect(url_for('add_appointment'))
        
        # Check if the client exists; if not, add the new client.
        client = Client.query.filter_by(nome=nome_cliente).first()
        if not client:
            new_client = Client(nome=nome_cliente, indirizzo=indirizzo, numero_telefono=numero_telefono, note=note)
            db.session.add(new_client)
            db.session.commit()
        else:
            client.note = note
            db.session.commit()
        
        if tipologia.lower() not in ['assistenza', 'dimostrazione']:
            new_other_app = OtherAppointment(
                nome_cliente=nome_cliente,
                indirizzo=indirizzo,
                numero_telefono=numero_telefono,
                note=note,
                stato=stato,
                tipologia=tipologia,
                nominativi_raccolti=nominativi_raccolti,
                appuntamenti_personali=appuntamenti_personali,
                venduto=venduto,
                data_appuntamento=data_appuntamento,
                data_richiamo=data_richiamo
            )
            db.session.add(new_other_app)
            db.session.commit()
            flash("Aggiunto come Post Demo!")
            return redirect(url_for('index'))
        
        new_app = Appointment(
            nome_cliente=nome_cliente,
            indirizzo=indirizzo,
            numero_telefono=numero_telefono,
            note=note,
            stato=stato,
            tipologia=tipologia,
            nominativi_raccolti=nominativi_raccolti,
            appuntamenti_personali=appuntamenti_personali,
            venduto=venduto,
            data_appuntamento=data_appuntamento,
            data_richiamo=data_richiamo
        )
        db.session.add(new_app)
        db.session.commit()
        
        for consultant_id in consultant_ids:
            consultant = Consultant.query.get(consultant_id)
            if consultant:
                new_app.consultants.append(consultant)
        
        db.session.commit()
        schedule_followups(new_app)
        flash("Appuntamento aggiunto correttamente!")
        return redirect(url_for('index'))
    
    return render_template('add_appointment.html', consultants=consultants, clients=clients)


@app.route('/add_consultant', methods=['GET', 'POST'])
def add_consultant():
    consultants = Consultant.query.all()
    positions = Position.query.all()
    if request.method == 'POST':
        try:
            nome = request.form.get('nome')
            posizione_id = request.form.get('posizione_id', type=int)
            responsabile_id = request.form.get('responsabile_id')
            residency = request.form.get('residency')
            phone = request.form.get('phone')
            email = request.form.get('email')
            CF = request.form.get('CF')
            if not nome:
                flash("Il nome del consulente è obbligatorio!")
                return redirect(url_for('add_consultant'))
            if not posizione_id:
                posizione_id = get_or_create_default_position().id
            # Se posizione_id ancora non esiste, crea la posizione di default
            if not Position.query.get(posizione_id):
                default_pos = get_or_create_default_position()
                posizione_id = default_pos.id
            # CORREZIONE: se responsabile_id è vuoto o non valido, metti None
            if not responsabile_id or str(responsabile_id).strip() == '' or str(responsabile_id).lower() == 'none':
                responsabile_id = None
            new_consultant = Consultant(
                nome=nome,
                posizione_id=posizione_id,
                responsabile_id=responsabile_id,
                residency=residency,
                phone=phone,
                email=email,
                CF=CF
            )
            db.session.add(new_consultant)
            db.session.commit()
            flash("Consulente aggiunto con successo!")
            return redirect(url_for('index'))
        except Exception as e:
            import traceback
            print('Errore durante l\'aggiunta del consulente:', e)
            traceback.print_exc()
            flash(f"Errore durante l'aggiunta del consulente: {e}")
            return redirect(url_for('add_consultant'))
    return render_template('add_consultant.html', consultants=consultants, positions=positions)
# ...existing code...

@app.route('/appointments', methods=['GET'])
def appointments():
    day = request.args.get('day')
    if day:
        try:
            day_date = datetime.strptime(day, '%Y-%m-%d').date()
        except ValueError:
            flash("Formato data non valido, usare YYYY-MM-DD")
            return redirect(url_for('appointments'))
        apps = Appointment.query.filter(
            db.func.date(Appointment.data_appuntamento) == day_date
        ).all()
    else:
        apps = Appointment.query.all()
    return render_template('appointments.html', appointments=apps)


######################################################################
######################################################################
######################################################################

            #########   ########   ##  ########
            ##     ##   ##     ##  ##  ##
            #########   ########   ##  ########
            #      ##   ##         ##        ##
            ##     ##   ##         ##  ########    APIS
            
######################################################################
######################################################################
######################################################################


# API endpoints for external integrations with documentation on how to use them.

# Endpoint: /api/appointments
# Methods:
#   GET - Retrieves all appointments.
#         URL: /api/appointments
#         Response: JSON { "appointments": [ {appointment_obj}, ... ] }
#
#   POST - Creates a new appointment.
#         URL: /api/appointments
#         Request JSON Body example:
#         {
#             "nome_cliente": "Customer Name",         # Required
#             "indirizzo": "Address",
#             "numero_telefono": "Phone Number",        # Required
#             "note": "Notes",
#             "tipologia": "Type",
#             "stato": "Status",
#             "nominativi_raccolti": 0,                  # Optional, default 0
#             "appuntamenti_personali": 0,               # Optional, default 0
#             "venduto": false,                        # Optional, default false
#             "data_appuntamento": "YYYY-MM-DD",         # Required
#             "data_richiamo": "YYYY-MM-DD",             # Optional
#             "consultants": [1, 2]                      # List of consultant IDs
#         }
#         Response: JSON { "message": "Appointment created", "id": <new_appt_id> }

@app.route('/api/appointments', methods=['GET', 'POST'])
def api_appointments():
    if request.method == 'GET':
        appointments = Appointment.query.all()
        result = [
            {
                'id': appt.id,
                'nome_cliente': appt.nome_cliente,
                'indirizzo': appt.indirizzo,
                'numero_telefono': appt.numero_telefono,
                'note': appt.note,
                'tipologia': appt.tipologia,
                'stato': appt.stato,
                'nominativi_raccolti': appt.nominativi_raccolti,
                'appuntamenti_personali': appt.appuntamenti_personali,
                'venduto': appt.venduto,
                'data_appuntamento': appt.data_appuntamento.strftime('%Y-%m-%d'),
                'data_richiamo': appt.data_richiamo.strftime('%Y-%m-%d') if appt.data_richiamo else None,
                'consultants': [consultant.id for consultant in appt.consultants]
            } for appt in appointments
        ]
        return jsonify(appointments=result)

    elif request.method == 'POST':
        data = request.get_json()
        if not data.get('nome_cliente') or not data.get('numero_telefono') or not data.get('data_appuntamento'):
            return jsonify(error='Missing required fields'), 400
        try:
            data_appuntamento = datetime.strptime(data.get('data_appuntamento'), '%Y-%m-%d')
            data_richiamo = datetime.strptime(data.get('data_richiamo'), '%Y-%m-%d') if data.get('data_richiamo') else None
        except Exception:
            return jsonify(error='Invalid date format. Use YYYY-MM-DD.'), 400

        new_appt = Appointment(
            nome_cliente=data.get('nome_cliente'),
            indirizzo=data.get('indirizzo'),
            numero_telefono=data.get('numero_telefono'),
            note=data.get('note'),
            tipologia=data.get('tipologia'),
            stato=data.get('stato'),
            nominativi_raccolti=data.get('nominativi_raccolti', 0),
            appuntamenti_personali=data.get('appuntamenti_personali', 0),
            venduto=data.get('venduto', False),
            data_appuntamento=data_appuntamento,
            data_richiamo=data_richiamo
        )
        consultant_ids = data.get('consultants', [])
        for cid in consultant_ids:
            consultant = Consultant.query.get(cid)
            if consultant:
                new_appt.consultants.append(consultant)

        db.session.add(new_appt)
        db.session.commit()
        schedule_followups(new_appt)
        return jsonify(message='Appointment created', id=new_appt.id), 201

# Endpoint: /api/appointments/<id>
# Methods:
#   GET - Retrieve a specific appointment.
#         URL: /api/appointments/<id>
#         Response: JSON appointment object.
#
#   PUT - Update a specific appointment.
#         URL: /api/appointments/<id>
#         Request JSON Body: Any appointment fields that need updating.
#         Response: JSON { "message": "Appointment updated" }
#
#   DELETE - Delete a specific appointment.
#         URL: /api/appointments/<id>
#         Response: JSON { "message": "Appointment deleted" }

@app.route('/api/appointments/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_appointment_detail(id):
    appt = Appointment.query.get_or_404(id)
    if request.method == 'GET':
        data = {
            'id': appt.id,
            'nome_cliente': appt.nome_cliente,
            'indirizzo': appt.indirizzo,
            'numero_telefono': appt.numero_telefono,
            'note': appt.note,
            'tipologia': appt.tipologia,
            'stato': appt.stato,
            'nominativi_raccolti': appt.nominativi_raccolti,
            'appuntamenti_personali': appt.appuntamenti_personali,
            'venduto': appt.venduto,
            'data_appuntamento': appt.data_appuntamento.strftime('%Y-%m-%d'),
            'data_richiamo': appt.data_richiamo.strftime('%Y-%m-%d') if appt.data_richiamo else None,
            'consultants': [consultant.id for consultant in appt.consultants]
        }
        return jsonify(data)

    elif request.method == 'PUT':
        data = request.get_json()
        if data.get('nome_cliente'):
            appt.nome_cliente = data.get('nome_cliente')
        if data.get('indirizzo'):
            appt.indirizzo = data.get('indirizzo')
        if data.get('numero_telefono'):
            appt.numero_telefono = data.get('numero_telefono')
        if data.get('note'):
            appt.note = data.get('note')
        if data.get('tipologia'):
            appt.tipologia = data.get('tipologia')
        if data.get('stato'):
            appt.stato = data.get('stato')
        if data.get('nominativi_raccolti') is not None:
            appt.nominativi_raccolti = data.get('nominativi_raccolti')
        if data.get('appuntamenti_personali') is not None:
            appt.appuntamenti_personali = data.get('appuntamenti_personali')
        if data.get('venduto') is not None:
            appt.venduto = data.get('venduto')
        if data.get('data_appuntamento'):
            try:
                appt.data_appuntamento = datetime.strptime(data.get('data_appuntamento'), '%Y-%m-%d')
            except Exception:
                return jsonify(error='Invalid data_appuntamento format'), 400
        if 'data_richiamo' in data:
            try:
                appt.data_richiamo = datetime.strptime(data.get('data_richiamo'), '%Y-%m-%d') if data.get('data_richiamo') else None
            except Exception:
                return jsonify(error='Invalid data_richiamo format'), 400
        if data.get('consultants'):
            appt.consultants = []
            for cid in data.get('consultants'):
                consultant = Consultant.query.get(cid)
                if consultant:
                    appt.consultants.append(consultant)
        db.session.commit()
        return jsonify(message='Appointment updated')

    elif request.method == 'DELETE':
        db.session.delete(appt)
        db.session.commit()
        return jsonify(message='Appointment deleted')

# Endpoint: /api/consultants
# Methods:
#   GET - Retrieves all consultants.
#         URL: /api/consultants
#         Response: JSON { "consultants": [ {consultant_obj}, ... ] }
#
#   POST - Creates a new consultant.
#         URL: /api/consultants
#         Request JSON Body example:
#         {
#             "nome": "Consultant Name",           # Required
#             "posizione": "Position",               # Required
#             "responsabile_id": 1,                  # Optional
#             "residency": "Residency",
#             "phone": "Phone Number",
#             "email": "Email",
#             "CF": "CF Value"
#         }
#         Response: JSON { "message": "Consultant created", "id": <new_consultant_id> }

@app.route('/api/consultants', methods=['GET', 'POST'])
def api_consultants():
    if request.method == 'GET':
        consultants = Consultant.query.all()
        result = []
        for consultant in consultants:
            result.append({
                'id': consultant.id,
                'nome': consultant.nome,
                'posizione': consultant.posizione.nome if consultant.posizione else None,
                'posizione_id': consultant.posizione_id,
                'responsabile_id': consultant.responsabile_id,
                'totalYearlyPay': consultant.totalYearlyPay,
                'residency': consultant.residency,
                'phone': consultant.phone,
                'email': consultant.email,
                'CF': consultant.CF
            })
        return jsonify(consultants=result)

    elif request.method == 'POST':
        data = request.get_json()
        if not data.get('nome'):
            return jsonify(error='Missing required field: nome'), 400

        posizione_id = data.get('posizione_id')
        if not posizione_id and data.get('posizione'):
            pos = Position.query.filter_by(nome=data.get('posizione')).first()
            if not pos:
                pos = Position(nome=data.get('posizione'))
                db.session.add(pos)
                db.session.commit()
            posizione_id = pos.id
        if not posizione_id:
            posizione_id = get_or_create_default_position().id

        responsabile_id = data.get('responsabile_id')
        if responsabile_id in [None, '', 'null']:
            responsabile_id = None

        new_consultant = Consultant(
            nome=data.get('nome'),
            posizione_id=posizione_id,
            responsabile_id=responsabile_id,
            residency=data.get('residency'),
            phone=data.get('phone'),
            email=data.get('email'),
            CF=data.get('CF')
        )
        db.session.add(new_consultant)
        db.session.commit()
        return jsonify(message='Consultant created', id=new_consultant.id), 201

# Endpoint: /api/consultants/<id>
# Methods:
#   GET - Retrieve a specific consultant.
#         URL: /api/consultants/<id>
#         Response: JSON consultant object.
#
#   PUT - Update a specific consultant.
#         URL: /api/consultants/<id>
#         Request JSON Body: Any consultant fields to update.
#         Response: JSON { "message": "Consultant updated" }
#
#   DELETE - Delete a specific consultant.
#         URL: /api/consultants/<id>
#         Response: JSON { "message": "Consultant deleted" }

@app.route('/api/consultants/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def api_consultant_detail(id):
    consultant = Consultant.query.get_or_404(id)
    if request.method == 'GET':
        data = {
            'id': consultant.id,
            'nome': consultant.nome,
            'posizione': consultant.posizione,
            'responsabile_id': consultant.responsabile_id,
            'totalYearlyPay': consultant.totalYearlyPay,
            'residency': consultant.residency,
            'phone': consultant.phone,
            'email': consultant.email,
            'CF': consultant.CF
        }
        return jsonify(data)

    elif request.method == 'PUT':
        data = request.get_json()
        if data.get('nome'):
            consultant.nome = data.get('nome')
        if data.get('posizione'):
            consultant.posizione = data.get('posizione')
        if 'responsabile_id' in data:
            consultant.responsabile_id = data.get('responsabile_id')
        if data.get('residency'):
            consultant.residency = data.get('residency')
        if data.get('phone'):
            consultant.phone = data.get('phone')
        if data.get('email'):
            consultant.email = data.get('email')
        if data.get('CF'):
            consultant.CF = data.get('CF')
        db.session.commit()
        return jsonify(message='Consultant updated')

    elif request.method == 'DELETE':
        db.session.delete(consultant)
        db.session.commit()
        return jsonify(message='Consultant deleted')


'''
######################################################################
######################################################################
######################################################################

           ##########   ##     ##   ########    #########
          ###           ##     ##   ##    ##        ##
          ##            #########   ########        ##
          ###           ##     ##   ##    ##        ##
           ##########   ##     ##   ##    ##        ##
           
######################################################################
######################################################################
######################################################################


# Make sure your chatbot logic is importable
from apis import *
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import requests


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    user_message = request.json.get("message", "")
    command = interpret_command(user_message)
    args = extract_arguments(command, user_message)

    try:
        if command == "list appointments":
            response = list_appointments()
        elif command == "get appointment":
            response = get_appointment(args.get("appointment_id", ""))
        elif command == "create appointment":
            response = create_appointment(args)
        elif command == "update appointment":
            response = update_appointment(args.get("appointment_id", ""), args)
        elif command == "delete appointment":
            response = delete_appointment(args.get("appointment_id", ""))
        elif command == "list consultants":
            response = list_consultants()
        elif command == "get consultant":
            response = get_consultant(args.get("consultant_id", ""))
        elif command == "create consultant":
            response = create_consultant(args)
        elif command == "update consultant":
            response = update_consultant(args.get("consultant_id", ""), args)
        elif command == "delete consultant":
            response = delete_consultant(args.get("consultant_id", ""))
        elif command == "help":
            response = "Available commands: list appointments, get appointment <id>, create appointment, ..."
        elif command == "quit":
            response = "Session ended. Refresh to restart."
        else:
            response = "🤖 I'm not sure how to help with that."
    except Exception as e:
        response = f"⚠️ Error while executing command: {str(e)}"

    return jsonify({"response": response})

'''

@app.route('/followup/complete/<int:id>', methods=['POST'])
def complete_followup(id):
    fu = FollowUp.query.get_or_404(id)
    fu.done = True
    db.session.commit()
    if fu.numero >= 5:
        next_date = fu.data_prevista + relativedelta(months=12)
        new_fu = FollowUp(appointment_id=fu.appointment_id, numero=fu.numero+1, data_prevista=next_date)
        db.session.add(new_fu)
        db.session.commit()
    return redirect(url_for('service'))

@app.route('/followup/edit/<int:id>', methods=['POST'])
def edit_followup(id):
    fu = FollowUp.query.get_or_404(id)
    date_str = request.form.get('data_prevista')
    try:
        fu.data_prevista = datetime.strptime(date_str, '%Y-%m-%d')
        db.session.commit()
    except ValueError:
        flash('Formato data non valido')
    return redirect(url_for('service'))

@app.route('/add_followup/<int:id>', methods=['POST'])
def add_followup(id):
    appointment = Appointment.query.get_or_404(id)
    # Trova l'ultimo follow-up esistente
    last_fu = FollowUp.query.filter_by(appointment_id=id).order_by(FollowUp.numero.desc()).first()
    if last_fu:
        next_num = last_fu.numero + 1
        next_date = last_fu.data_prevista + relativedelta(months=12)
    else:
        # Se non ci sono follow-up, crea il primo dopo 3 giorni
        next_num = 1
        next_date = appointment.data_appuntamento + relativedelta(days=3)
    new_fu = FollowUp(appointment_id=id, numero=next_num, data_prevista=next_date)
    db.session.add(new_fu)
    db.session.commit()
    return redirect(url_for('service'))


@app.route('/update_client_note', methods=['POST'])
def update_client_note():
    client_id = request.form.get('id', type=int)
    new_note = request.form.get('note')
    client = Client.query.get_or_404(client_id)
    client.note = new_note
    db.session.commit()
    return jsonify(success=True)

# Utility per ottenere o creare la posizione "Nessuna posizione"
def get_or_create_default_position():
    default = Position.query.filter_by(nome="Nessuna posizione").first()
    if not default:
        default = Position(nome="Nessuna posizione")
        db.session.add(default)
        db.session.commit()
    return default


# Utility per ottenere o creare la posizione "Nessuna posizione"
def get_or_create_default_position():
    default = Position.query.filter_by(nome="Nessuna posizione").first()
    if not default:
        default = Position(nome="Nessuna posizione")
        db.session.add(default)
        db.session.commit()
    return default

@app.route('/modify_appointment/<int:id>', methods=['GET', 'POST'])
def modify_appointments(id):
    appointment = Appointment.query.get_or_404(id)
    consultants = Consultant.query.all()
    if request.method == 'POST':
        appointment.nome_cliente = request.form.get('nome_cliente')
        appointment.indirizzo = request.form.get('indirizzo')
        appointment.numero_telefono = request.form.get('numero_telefono')
        appointment.note = request.form.get('note')
        appointment.tipologia = request.form.get('tipologia')
        appointment.stato = request.form.get('stato')
        appointment.nominativi_raccolti = request.form.get('nominativi_raccolti', 0, type=int)
        appointment.appuntamenti_personali = request.form.get('appuntamenti_personali', 0, type=int)
        appointment.venduto = True if request.form.get('venduto') == 'on' else False

        data_appuntamento_str = request.form.get('data_appuntamento')
        data_richiamo_str = request.form.get('data_richiamo')

        try:
            appointment.data_appuntamento = datetime.strptime(data_appuntamento_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            flash("Formato data appuntamento non valido, usare YYYY-MM-DD")
            return redirect(url_for('modify_appointments', id=id))

        if appointment.stato.lower() == 'da richiamare':
            if not data_richiamo_str:
                flash("Per appuntamenti 'da richiamare' inserire la data di richiamo!")
                return redirect(url_for('modify_appointments', id=id))
            try:
                appointment.data_richiamo = datetime.strptime(data_richiamo_str, '%Y-%m-%d')
            except ValueError:
                flash("Formato data richiamo non valido, usare YYYY-MM-DD")
                return redirect(url_for('modify_appointments', id=id))
        else:
            appointment.data_richiamo = None

        consultant_ids = request.form.get('consultants')
        if consultant_ids:
            consultant_ids = json.loads(consultant_ids)
            if not isinstance(consultant_ids, list) or not consultant_ids:
                flash("Seleziona almeno un consulente valido!")
                return redirect(url_for('modify_appointments', id=id))
        else:
            flash("Seleziona almeno un consulente valido!")
            return redirect(url_for('modify_appointments', id=id))

        appointment.consultants = []
        for consultant_id in consultant_ids:
            consultant = Consultant.query.get(consultant_id)
            if consultant:
                appointment.consultants.append(consultant)

        db.session.commit()
        flash("Appuntamento modificato correttamente!")
        return redirect(url_for('appointments'))

    return render_template('modify_appointment.html', appointment=appointment, consultants=consultants)
    

@app.route('/delete_appointment/<int:id>', methods=['GET'])
def delete_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    db.session.delete(appointment)
    db.session.commit()
    flash("Appuntamento eliminato con successo!")
    return redirect(url_for('appointments'))    
    



    
@app.route('/marketing', methods=['GET'])
def marketing():
    return render_template('marketing.html')

@app.route('/provvigioni', methods=['GET', 'POST'])
def provvigioni():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == funzioni.decrypt(key):
            consultants = Consultant.query.all()
            appointments = Appointment.query.all()
            consultant_id = request.form.get('consultant', type=int)
            return render_template('provvigioni.html', consultants=consultants, appointments=appointments, consultant_id=consultant_id, password=password)
        else:
            flash("Password errata, riprova.")
            return redirect(url_for('index'))
    return render_template('login.html')




@app.route('/edit_payments', methods=['POST'])

def edit_payments():
    appointment_ids = request.form.getlist('appointment_ids')
    appointment_ids = [int(id.strip().strip(',')) for id in appointment_ids]
    consultant_id = request.form.get('consultant_id', type=int)
    appointments = Appointment.query.filter(Appointment.id.in_(appointment_ids)).all()
    return render_template('edit_payments.html', appointments=appointments, consultant_id=consultant_id)
    

@app.route('/print_payments', methods=['POST'])
def print_payments():
    appointment_ids = request.form.getlist('appointment_ids')
    appointment_ids = [id.strip() for id in appointment_ids[0].split(',')]
    
    appointments = Appointment.query.filter(Appointment.id.in_(appointment_ids)).all()
    
    payments = {}
    for appointment_id in appointment_ids:
        payment = request.form.get(f'payment_{appointment_id}')
        if payment:
            payments[appointment_id] = float(payment)
    
    consultant_id = request.form.get('consultant_id', type=int)
    person = Consultant.query.get(consultant_id) if consultant_id else None
    
    extra = request.form.get('extra')
    if extra:
        payments['extra'] = float(extra)
    
    acconto = request.form.get('acconto')
    if acconto:
        payments['acconto'] = float(acconto)
    
    if person:
        today = datetime.today()
        if today.month == 1:
            person.totalYearlyPay = 0.0
        person.totalYearlyPay += sum(payments.values())
        db.session.commit()
    
    pdf_content = funzioni.genera_fattura(appointments, payments, person)
    
    response = make_response(pdf_content)
    response.headers['Content-Disposition'] = 'attachment; filename=quietanza_pagamento.pdf'
    response.headers['Content-Type'] = 'application/pdf'
    return response


@app.route('/report', methods=['GET'])
def generate_report():
    # Ottieni tutte le posizioni dal database, inclusa la posizione di default
    positions = Position.query.all()
    default_position = get_or_create_default_position()
    # Crea un dizionario per raggruppare i consulenti per nome posizione
    consultants_by_position = {pos.nome: [] for pos in positions}
    consultants_by_position[default_position.nome] = []
    consultants = Consultant.query.all()

    # Raggruppa i consulenti per nome posizione (se non hanno posizione, "Nessuna posizione")
    for consultant in consultants:
        pos_name = consultant.posizione.nome if consultant.posizione else default_position.nome
        if pos_name not in consultants_by_position:
            consultants_by_position[pos_name] = []
        consultants_by_position[pos_name].append(consultant)

    # Prepara il file Excel in memoria
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # Formattazione delle intestazioni e delle posizioni
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
    header_format.set_text_wrap()
    header_format.set_align('center')
    header_format.set_align('vcenter')
    position_format = workbook.add_format({'bold': True, 'bg_color': '#ADD8E6'})
    worksheet.set_row(0, 25)
    worksheet.set_column(0, 0, 38)
    worksheet.set_column(1, 16, 6)

    # Intestazioni delle colonne
    headers = ['Consulente','P','A','Ass. G.','Ass. M.','Dim. G.','Dim. M.','Vend Ass. G.','Vend Ass. M.','Vend Dim. G.','Vend Dim. M.','Nom. G.','Nom. M.','App. Pers. G.','App. Pers. M.','Tot. App.','Vend Gruppo']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    row = 1
    # Per ogni posizione, scrivi la riga di intestazione e poi i consulenti
    for posizione, consultants in consultants_by_position.items():
        if not consultants:
            continue  # Salta le posizioni senza consulenti
        worksheet.write(row, 0, posizione, position_format)
        row += 1
        for consultant in consultants:
            appointments = consultant.appointments
            today = datetime.today().date()
            start_of_month = today.replace(day=1)

            # Filtra appuntamenti per tipologia e periodo
            daily_assistance = [app for app in appointments if app.data_appuntamento and app.data_appuntamento.date() == today and app.tipologia == 'Assistenza']
            monthly_assistance = [app for app in appointments if app.data_appuntamento and app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Assistenza']
            daily_demonstration = [app for app in appointments if app.data_appuntamento and app.data_appuntamento.date() == today and app.tipologia == 'Dimostrazione']
            monthly_demonstration = [app for app in appointments if app.data_appuntamento and app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Dimostrazione']

            # Calcola vendite e raccolte
            daily_sales_assistance = sum(1 for app in daily_assistance if app.venduto)
            monthly_sales_assistance = sum(1 for app in monthly_assistance if app.venduto)
            daily_sales_demonstration = sum(1 for app in daily_demonstration if app.venduto)
            monthly_sales_demonstration = sum(1 for app in monthly_demonstration if app.venduto)

            daily_names = sum(app.nominativi_raccolti or 0 for app in daily_assistance)
            monthly_names = sum(app.nominativi_raccolti or 0 for app in monthly_assistance)
            daily_names += sum(app.nominativi_raccolti or 0 for app in daily_demonstration)
            monthly_names += sum(app.nominativi_raccolti or 0 for app in monthly_demonstration)

            daily_personal_appointments = sum(app.appuntamenti_personali or 0 for app in daily_assistance)
            monthly_personal_appointments = sum(app.appuntamenti_personali or 0 for app in monthly_assistance)
            daily_personal_appointments += sum(app.appuntamenti_personali or 0 for app in daily_demonstration)
            monthly_personal_appointments += sum(app.appuntamenti_personali or 0 for app in monthly_demonstration)

            # Calcola vendite di gruppo (inclusi subordinati)
            group_sales = monthly_sales_assistance + monthly_sales_demonstration
            for subordinato in getattr(consultant, 'subordinati', []):
                subordinato_appointments = subordinato.appointments
                subordinato_monthly_sales_assistance = sum(1 for app in subordinato_appointments if app.data_appuntamento and app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Assistenza' and app.venduto)
                subordinato_monthly_sales_demonstration = sum(1 for app in subordinato_appointments if app.data_appuntamento and app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Dimostrazione' and app.venduto)
                group_sales += subordinato_monthly_sales_assistance + subordinato_monthly_sales_demonstration

            # Scrivi i dati del consulente nella riga
            worksheet.write(row, 0, consultant.nome)
            worksheet.write(row, 3, len(daily_assistance))
            worksheet.write(row, 4, len(monthly_assistance))
            worksheet.write(row, 5, len(daily_demonstration))
            worksheet.write(row, 6, len(monthly_demonstration))
            worksheet.write(row, 7, daily_sales_assistance)
            worksheet.write(row, 8, monthly_sales_assistance)
            worksheet.write(row, 9, daily_sales_demonstration)
            worksheet.write(row, 10, monthly_sales_demonstration)
            worksheet.write(row, 11, daily_names)
            worksheet.write(row, 12, monthly_names)
            worksheet.write(row, 13, daily_personal_appointments)
            worksheet.write(row, 14, monthly_personal_appointments)
            worksheet.write(row, 15, monthly_personal_appointments+len(monthly_assistance)+len(monthly_demonstration))
            # Mostra Vend Gruppo solo per i manager (modifica la logica se necessario)
            worksheet.write(row, 16, group_sales if posizione.lower().startswith("manager") else "")
            row += 1

    # Chiudi e restituisci il file Excel
    workbook.close()
    output.seek(0)

    response = make_response(output.read())
    now = datetime.today().strftime("%Y-%m-%d")
    response.headers['Content-Disposition'] = f'attachment; filename=report {now}.xlsx'
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response

@app.route('/serverconsole', methods=['GET', 'POST'])
def serverconsole():
    if request.method == 'POST':
        command = request.form.get('command')
        if command:
            try:
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                output = result.decode('utf-8')
            except subprocess.CalledProcessError as e:
                output = f"Error: {e.output.decode('utf-8')}"
        else:
            output = "No command provided."
        return render_template('serverconsole.html', output=output)
    return render_template('serverconsole.html')


# Event handler for live terminal commands
@socketio.on('run_command')
def handle_run_command(data):
    command = data.get('command')
    if not command:
        emit('command_output', {'output': 'No command provided.\n'})
        return
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        emit('command_output', {'output': line})
    proc.wait()
    emit('command_done')


@app.route('/system_info', methods=['GET'])
def system_info():
    info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Hostname": socket.gethostname(),
        "IP Address": socket.gethostbyname(socket.gethostname()),
        "RAM Size (GB)": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "CPU Cores": psutil.cpu_count(logical=True),
        "CPU Usage (%)": psutil.cpu_percent(interval=1),
        "Disk Usage (%)": psutil.disk_usage('/').percent,
        "Disk Size (GB)": round(psutil.disk_usage('/').total / (1024 ** 3), 2),
        "Disk Free Space (GB)": round(psutil.disk_usage('/').free / (1024 ** 3), 2)
    }
    return jsonify(info)

root_block = '''
:root {
--main-btn-radius: 10px;
--main-btn-padding: 10px 10px;
--main-btn-font: 18px;
--main-navbar-radius: 0px;
--main-btn-margin-bottom: 30px;
}

.spaced-section {
        margin-top: 3rem;
        margin-bottom: 3rem;
    }

.container {
    padding: 1.5rem !important;
    border-radius: 20px;
}

h1 {
    margin-top: 32px;
  }
'''

@app.route('/set_theme', methods=['POST'])
def set_theme():
    data = request.get_json()
    theme = data.get('theme')
    mode = data.get('mode')  # 'light' o 'dark'
    patch_css()  # Aggiorna il CSS con il blocco base
    # Dopo patch_css, aggiorna anche tutti i 'button' inline se necessario
    # (nessuna azione extra richiesta perché ora la regola button è inclusa nel THEME_BLOCK)
    with open(CSS_PATH, 'r', encoding='utf-8') as f:
        css = f.read()
    # Rimuovi eventuali classi tema precedenti
    for t in ['theme-dark', 'theme-sunny', 'theme-blue', 'theme-sunset', 'theme-dark-dark', 'theme-sunny-dark', 'theme-blue-dark', 'theme-sunset-dark']:
        css = css.replace(f':root.{t}', ':root')
    # Applica la classe tema selezionata
    if theme in ['dark', 'sunny', 'blue', 'sunset']:
        if mode == 'dark':
            css = css.replace(':root {', f':root.theme-{theme}-dark {{')
        else:
            css = css.replace(':root {', f':root.theme-{theme} {{')
    # Aggiorna il CSS
    with open(CSS_PATH, 'w', encoding='utf-8') as f:
        f.write(root_block + css)
    return jsonify({'success': True})


if __name__ == '__main__':
    socketio.run(app, debug=True)
