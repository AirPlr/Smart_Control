from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
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

__version__ = "v1.0"

def get_latest_version():
    url = "https://api.github.com/repos/tuo-username/Controllo/releases/latest"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("tag_name", __version__)
    except Exception as e:
        print("Errore durante il controllo della versione:", e)
    return __version__

def download_release(url):
    print("Download della nuova release da GitHub...")
    resp = requests.get(url)
    if resp.status_code == 200:
        print("Download completato.")
        return BytesIO(resp.content)
    else:
        print("Errore nel download:", resp.status_code)
        return None

def update_files(zip_file):
    with zipfile.ZipFile(zip_file) as z:
        # La cartella estratta potrebbe avere un prefisso es. "Controllo-1.1/"
        root_folder = z.namelist()[0].split('/')[0]
        for member in z.infolist():
            filename = member.filename
            # Aggiorna solo i file .py e i file .html nella cartella templates
            if filename.endswith(".py") or ("/templates/" in filename and filename.endswith(".html")):
                rel_path = os.path.relpath(filename, start=root_folder)
                dest_path = os.path.join(os.getcwd(), rel_path)
                dest_dir = os.path.dirname(dest_path)
                os.makedirs(dest_dir, exist_ok=True)
                print(f"Aggiornamento di {dest_path}...")
                with z.open(member) as source, open(dest_path, "wb") as target:
                    shutil.copyfileobj(source, target)
    print("Aggiornamento completato.")

def check_for_update():
    latest = get_latest_version()
    if latest != __version__:
        print(f"Nuova release disponibile: {latest}")
        release_url = f"https://github.com/tuo-username/Controllo/archive/refs/tags/{latest}.zip"
        zip_file = download_release(release_url)
        if zip_file:
            update_files(zip_file)
            print("Avvio di dbport.py...")
            subprocess.run(["python", "dbport.py"], check=True)
            print("Riavvio dell'applicazione aggiornata...")
            subprocess.Popen(["python", sys.argv[0]])
            sys.exit(0)
    else:
        print("Nessun aggiornamento disponibile.")


    
    
    
# Generate a key for encryption/decryption
# You must store and keep this key safe. If you lose it, you won't be able to decrypt your data.
key = b'KrBNJNSPev7iSQFFISdi0JvvMWYzeM6HMGdejH_o8Sg='





app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'  # Cambia la chiave in produzione
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'appointments.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
    


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

    def __repr__(self):
        return f"<Client {self.nome}>"







with app.app_context():
    db.create_all()

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = User.query.first()  # Assuming there's only one user for simplicity
    if not user:
        user = User(username='username', email='email', language='it', license_code='ABC123', license_expiry=datetime(2025, 12, 31))
        db.session.add(user)
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

    return render_template('settings.html', user=user, datetime=datetime, expiration_days=(user.license_expiry - datetime.today()).days)

@app.route('/')
def index():
    user = User.query.first()
    if not user:
        return redirect(url_for('settings'))
    if user.license_code != 'ABC123':
        return redirect(url_for('license'))
    else:
        user.license_expiry = datetime(2025, 12, 31)
        expiration_days = (user.license_expiry - datetime.today()).days
        if expiration_days < 0:
            return redirect(url_for('license'))
        db.session.commit()
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
        return redirect(url_for('index'))
    return render_template('calendar.html', appointments=appointments, oapps=oapps, datetime=datetime)



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
    clients = Client.query.all()
    Appointments = Appointment.query.all()
    OtherAppointments = OtherAppointment.query.all()
    
    if not clients:
        flash("Nessun cliente trovato.")
        return redirect(url_for('index'))
    return render_template('clients.html', clients=clients, Appointments=Appointments, OtherAppointments=OtherAppointments, datetime=datetime)


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
    
    return {"appointments": appts, "otherAppointments": other_appts}


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

@app.route('/modify_consultant/<int:id>', methods=['GET', 'POST'])
def modify_consultant(id):
    consultant = Consultant.query.get(id)
    consultants = Consultant.query.all()
    if request.method == 'POST':
        consultant.nome = request.form.get('nome')
        consultant.posizione = request.form.get('posizione')
        consultant.responsabile_id = request.form.get('responsabile_id')
        consultant.residency = request.form.get('residency')
        consultant.phone = request.form.get('phone')
        consultant.email = request.form.get('email')
        consultant.CF = request.form.get('CF')
        db.session.commit()
        flash("Consulente modificato con successo!")
        return redirect(url_for('consultants'))
    return render_template('modify_consultant.html', consultant=consultant, consultants=consultants)

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
            new_client = Client(nome=nome_cliente, indirizzo=indirizzo, numero_telefono=numero_telefono)
            db.session.add(new_client)
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
        flash("Appuntamento aggiunto correttamente!")
        return redirect(url_for('index'))
    
    return render_template('add_appointment.html', consultants=consultants, clients=clients)

@app.route('/add_consultant', methods=['GET', 'POST'])
def add_consultant():
    consultants = Consultant.query.all()
    if request.method == 'POST':
        nome = request.form.get('nome')
        posizione = request.form.get('posizione')
        responsabile_id = request.form.get('responsabile_id')
        residency = request.form.get('residency')
        phone = request.form.get('phone')
        email = request.form.get('email')
        CF = request.form.get('CF')
        if not nome:
            flash("Il nome del consulente è obbligatorio!")
            return redirect(url_for('add_consultant'))
        if not posizione:
            flash("La posizione del consulente è obbligatoria!")
            return redirect(url_for('add_consultant'))
        new_consultant = Consultant(nome=nome, posizione=posizione, responsabile_id=responsabile_id, residency=residency, phone=phone, email=email, CF=CF)
        db.session.add(new_consultant)
        db.session.commit()
        flash("Consulente aggiunto con successo!")
        return redirect(url_for('index'))
    return render_template('add_consultant.html', consultants=consultants)

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
    consultants_by_position = {"Manager Main Office": [],"Assistenza: Tecnici Main Office": [],"Social Media": [],"Dealers Con Campionario Main Office": [],"Consulenti DPS Main Office": [],"Consulenti Kirby Life": [],"DT+Managers+Dealers Ufficio di Carmagnola": [],"Campionari da Ritirare": []}
    consultants = Consultant.query.all()

    for consultant in consultants:
        if consultant.posizione == "1":
            consultants_by_position["Manager Main Office"].append(consultant)
        elif consultant.posizione == "2":
            consultants_by_position["Assistenza: Tecnici Main Office"].append(consultant)
        elif consultant.posizione == "3":
            consultants_by_position["Social Media"].append(consultant)
        elif consultant.posizione == "4":
            consultants_by_position["Dealers Con Campionario Main Office"].append(consultant)
        elif consultant.posizione == "5":
            consultants_by_position["Consulenti DPS Main Office"].append(consultant)
        elif consultant.posizione == "6":
            consultants_by_position["Consulenti Kirby Life"].append(consultant)
        elif consultant.posizione == "7":
            consultants_by_position["DT+Managers+Dealers Ufficio di Carmagnola"].append(consultant)
        elif consultant.posizione == "8":
            consultants_by_position["Campionari da Ritirare"].append(consultant)

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
    header_format.set_text_wrap()
    header_format.set_align('center')
    header_format.set_align('vcenter')
    position_format = workbook.add_format({'bold': True, 'bg_color': '#ADD8E6'})
    worksheet.set_row(0, 25)
    worksheet.set_column(0, 0, 38)
    worksheet.set_column(1, 16, 6)

    headers = ['Consulente','P','A','Ass. G.','Ass. M.','Dim. G.','Dim. M.','Vend Ass. G.','Vend Ass. M.','Vend Dim. G.','Vend Dim. M.','Nom. G.','Nom. M.','App. Pers. G.','App. Pers. M.','Tot. App.','Vend Gruppo']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header, header_format)

    row = 1
    for posizione, consultants in consultants_by_position.items():
        worksheet.write(row, 0, posizione, position_format)
        row += 1
        for consultant in consultants:
            appointments = consultant.appointments
            today = datetime.today().date()
            start_of_month = today.replace(day=1)

            daily_assistance = [app for app in appointments if app.data_appuntamento.date() == today and app.tipologia == 'Assistenza']
            monthly_assistance = [app for app in appointments if app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Assistenza']
            daily_demonstration = [app for app in appointments if app.data_appuntamento.date() == today and app.tipologia == 'Dimostrazione']
            monthly_demonstration = [app for app in appointments if app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Dimostrazione']

            daily_sales_assistance = sum(1 for app in daily_assistance if app.venduto)
            monthly_sales_assistance = sum(1 for app in monthly_assistance if app.venduto)
            daily_sales_demonstration = sum(1 for app in daily_demonstration if app.venduto)
            monthly_sales_demonstration = sum(1 for app in monthly_demonstration if app.venduto)

            daily_names = sum(app.nominativi_raccolti for app in daily_assistance)
            monthly_names = sum(app.nominativi_raccolti for app in monthly_assistance)
            daily_names += sum(app.nominativi_raccolti for app in daily_demonstration)
            monthly_names += sum(app.nominativi_raccolti for app in monthly_demonstration)

            daily_personal_appointments = sum(app.appuntamenti_personali for app in daily_assistance)
            monthly_personal_appointments = sum(app.appuntamenti_personali for app in monthly_assistance)
            daily_personal_appointments += sum(app.appuntamenti_personali for app in daily_demonstration)
            monthly_personal_appointments += sum(app.appuntamenti_personali for app in monthly_demonstration)

            group_sales = monthly_sales_assistance + monthly_sales_demonstration
            for subordinato in consultant.subordinati:
                subordinato_appointments = subordinato.appointments
                subordinato_monthly_sales_assistance = sum(1 for app in subordinato_appointments if app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Assistenza' and app.venduto)
                subordinato_monthly_sales_demonstration = sum(1 for app in subordinato_appointments if app.data_appuntamento.date() >= start_of_month and app.tipologia == 'Dimostrazione' and app.venduto)
                group_sales += subordinato_monthly_sales_assistance + subordinato_monthly_sales_demonstration

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
            worksheet.write(row, 16, group_sales if posizione == "Manager Main Office" else "")
            row += 1

    workbook.close()
    output.seek(0)

    response = make_response(output.read())
    now = datetime.today().strftime("%Y-%m-%d")
    response.headers['Content-Disposition'] = f'attachment; filename=report {now}.xlsx'
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response

if __name__ == '__main__':
    check_for_update()
    app.run(debug=True)
