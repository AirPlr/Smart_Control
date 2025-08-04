from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.user import User, db
from models.appointment import Appointment, OtherAppointment
from models.consultant import Consultant  
from models.client import Client
from models.note_event import note_event
from services.appointment_service import AppointmentService
from datetime import datetime
import json

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Redirect basato sul ruolo
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_dealer():
        return redirect(url_for('dealer.dashboard'))
    
    # Default per viewer o altri ruoli
    user = User.query.first()
    if not user:
        return redirect(url_for('main.settings'))
    
    # Dashboard generica
    today = datetime.today().date()
    recall_appointments = Appointment.query.filter(
        Appointment.stato.ilike('da richiamare'),
        db.func.date(Appointment.data_richiamo) == today
    ).all()
    
    current_date = today.strftime('%d/%m/%Y')
    return render_template('index.html', 
                         recall_appointments=recall_appointments, 
                         current_date=current_date, 
                         datetime=datetime)

@bp.route('/calendar', methods=['GET', 'POST'])
@login_required
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
                return redirect(url_for('main.calendar'))
                
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
                return redirect(url_for('main.calendar'))
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

@bp.route('/service')
@login_required
def service():
    appointments = Appointment.query.filter_by(venduto=True).all()
    return render_template('service.html', appointments=appointments, datetime=datetime)

@bp.route('/events/')
@login_required
def events():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify(events=[])
        
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify(events=[])
    
    # Eventi da diverse fonti
    events = []
    
    # Appuntamenti
    appointments = Appointment.query.filter(db.func.date(Appointment.data_appuntamento) == selected_date).all()
    for appointment in appointments:
        events.append({
            'id': appointment.id,
            'title': appointment.nome_cliente,
            'start': appointment.data_appuntamento.strftime('%Y-%m-%d'),
            'type': appointment.tipologia,
            'note': appointment.note
        })
    
    # Altri appuntamenti
    for oapp in OtherAppointment.query.filter(db.func.date(OtherAppointment.data_appuntamento) == selected_date).all():
        events.append({
            'id': oapp.id,
            'title': oapp.nome_cliente,
            'start': oapp.data_appuntamento.strftime('%Y-%m-%d'),
            'type': oapp.tipologia,
            'note': oapp.note
        })
    
    # Note eventi
    for note in note_event.query.filter(db.func.date(note_event.data) == selected_date).all():
        events.append({
            'id': note.id,
            'title': note.note,
            'start': note.data.strftime('%Y-%m-%d'),
            'type': 'note',
            'note': note.note
        })
    
    # Follow-up
    from models.followup import FollowUp
    for fu in FollowUp.query.filter(db.func.date(FollowUp.data_prevista) == selected_date, FollowUp.done == False).all():
        events.append({
            'id': f'f{fu.id}',
            'title': f"Follow-up {fu.numero} - {fu.appointment.nome_cliente}",
            'start': fu.data_prevista.strftime('%Y-%m-%d'),
            'type': 'followup'
        })
    
    return jsonify(events=events)

@bp.route('/clients', methods=['GET'])
@login_required
def clients():
    all_clients = Client.query.all()
    
    # Clienti con vendite
    sold_appts = Appointment.query.filter_by(venduto=True).with_entities(Appointment.nome_cliente).all()
    sold_other = OtherAppointment.query.filter_by(venduto=True).with_entities(OtherAppointment.nome_cliente).all()
    sold_names = set([name for (name,) in sold_appts] + [name for (name,) in sold_other])
    
    # Filtri
    search = request.args.get('search', '').strip().lower()
    venduto_arg = request.args.get('venduto')
    
    filtered = []
    for client in all_clients:
        # Ricerca
        fields = [
            client.nome,
            client.indirizzo or '', 
            client.numero_telefono or '', 
            client.email or '',
            client.data_registrazione.strftime('%d/%m/%Y'),
            client.note or ''
        ]
        text = ' '.join(fields).lower()
        
        if search and search not in text:
            continue
            
        # Filtro venduto
        if venduto_arg == 'true' and client.nome not in sold_names:
            continue
        if venduto_arg == 'false' and client.nome in sold_names:
            continue
            
        filtered.append(client)
    
    clients = filtered
    if not clients:
        flash("Nessun cliente trovato.")
    
    return render_template('clients.html', 
                         clients=clients, 
                         sold_names=sold_names, 
                         datetime=datetime,
                         search=search, 
                         venduto=venduto_arg)

@bp.route('/consultants', methods=['GET'])
@login_required
def consultants():
    consultants = Consultant.query.all()
    return render_template('consultants.html', consultants=consultants)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = current_user
    license_status = 'ok'
    license_message = ''
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        theme = request.form.get('theme')
        if theme:
            user.settings['theme'] = theme
        db.session.commit()
        flash("Impostazioni salvate con successo!")
        return redirect(url_for('main.settings'))
    
    # Verifica licenza (simulata per preview)
    expiration_days = None
    if user.license_expiry:
        expiration_days = (user.license_expiry - datetime.today()).days
        if expiration_days < 0:
            license_status = 'expired'
            license_message = 'Licenza scaduta.'
    
    return render_template('settings.html', 
                         user=user, 
                         datetime=datetime, 
                         expiration_days=expiration_days, 
                         license_status=license_status, 
                         license_message=license_message)

@bp.route('/onboarding')
@login_required
def onboarding():
    user = current_user
    if not user.settings.get('onboarding_complete'):
        if 'complete' in request.args:
            user.settings['onboarding_complete'] = True
            db.session.commit()
            return redirect(url_for('main.index'))
        return render_template('onboarding.html', user=user)
    return redirect(url_for('main.index'))

# Gestione Appuntamenti
@bp.route('/add_appointment', methods=['GET', 'POST'])
@login_required
def add_appointment():
    """Aggiungi nuovo appuntamento"""
    consultants = Consultant.query.all()
    clients = Client.query.all()
    
    if request.method == 'POST':
        try:
            # Raccogli dati dal form
            data = {
                'nome_cliente': request.form.get('nome_cliente'),
                'indirizzo': request.form.get('indirizzo', ''),
                'numero_telefono': request.form.get('numero_telefono'),
                'note': request.form.get('note', ''),
                'tipologia': request.form.get('tipologia'),
                'stato': request.form.get('stato'),
                'nominativi_raccolti': request.form.get('nominativi_raccolti', 0, type=int),
                'appuntamenti_personali': request.form.get('appuntamenti_personali', 0, type=int),
                'venduto': request.form.get('venduto') == 'on',
                'include_in_reports': request.form.get('include_in_reports') == 'on',
                'data_appuntamento': request.form.get('data_appuntamento'),
                'data_richiamo': request.form.get('data_richiamo') if request.form.get('data_richiamo') else None
            }
            
            # Consulenti selezionati
            consultant_ids = request.form.get('consultants')
            if consultant_ids:
                try:
                    data['consultant_ids'] = json.loads(consultant_ids)
                except (json.JSONDecodeError, TypeError):
                    data['consultant_ids'] = []
            else:
                data['consultant_ids'] = []
            
            if not data['consultant_ids']:
                flash("Seleziona almeno un consulente valido!", 'error')
                return render_template('add_appointment.html', consultants=consultants, clients=clients)
            
            # Crea appuntamento usando il service
            appointment = AppointmentService.create_appointment(data, current_user.id)
            flash("Appuntamento aggiunto correttamente!", 'success')
            return redirect(url_for('main.appointments'))
            
        except ValueError as e:
            flash(f"Errore: {str(e)}", 'error')
        except Exception as e:
            flash(f"Errore imprevisto: {str(e)}", 'error')
    
    return render_template('add_appointment.html', consultants=consultants, clients=clients)

@bp.route('/appointments')
@login_required
def appointments():
    """Lista appuntamenti"""
    day = request.args.get('day')
    
    if day:
        try:
            day_date = datetime.strptime(day, '%Y-%m-%d').date()
            apps = Appointment.query.filter(
                db.func.date(Appointment.data_appuntamento) == day_date
            ).all()
        except ValueError:
            flash("Formato data non valido, usare YYYY-MM-DD", 'error')
            return redirect(url_for('main.appointments'))
    else:
        apps = Appointment.query.all()
    
    return render_template('appointments.html', appointments=apps)

@bp.route('/modify_appointment/<int:id>', methods=['GET', 'POST'])
@login_required
def modify_appointment(id):
    """Modifica appuntamento esistente"""
    appointment = Appointment.query.get_or_404(id)
    consultants = Consultant.query.all()
    clients = Client.query.all()
    
    if request.method == 'POST':
        try:
            # Raccogli dati dal form
            data = {
                'nome_cliente': request.form.get('nome_cliente'),
                'indirizzo': request.form.get('indirizzo', ''),
                'numero_telefono': request.form.get('numero_telefono'),
                'note': request.form.get('note', ''),
                'tipologia': request.form.get('tipologia'),  
                'stato': request.form.get('stato'),
                'nominativi_raccolti': request.form.get('nominativi_raccolti', 0, type=int),
                'appuntamenti_personali': request.form.get('appuntamenti_personali', 0, type=int),
                'venduto': request.form.get('venduto') == 'on',
                'include_in_reports': request.form.get('include_in_reports') == 'on',
                'data_appuntamento': request.form.get('data_appuntamento'),
                'data_richiamo': request.form.get('data_richiamo') if request.form.get('data_richiamo') else None
            }
            
            # Consulenti selezionati
            consultant_ids = request.form.get('consultants')
            if consultant_ids:
                try:
                    data['consultant_ids'] = json.loads(consultant_ids)
                except (json.JSONDecodeError, TypeError):
                    data['consultant_ids'] = []
            else:
                data['consultant_ids'] = []
                
            if not data['consultant_ids']:
                flash("Seleziona almeno un consulente valido!", 'error')
                return render_template('modify_appointment.html', 
                                     appointment=appointment, 
                                     consultants=consultants, 
                                     clients=clients)
            
            # Aggiorna appuntamento usando il service
            AppointmentService.update_appointment(id, data, current_user.id)
            flash("Appuntamento modificato correttamente!", 'success')
            return redirect(url_for('main.appointments'))
            
        except ValueError as e:
            flash(f"Errore: {str(e)}", 'error')
        except Exception as e:
            flash(f"Errore imprevisto: {str(e)}", 'error')
    
    return render_template('modify_appointment.html', 
                         appointment=appointment, 
                         consultants=consultants, 
                         clients=clients)

@bp.route('/delete_appointment/<int:id>')
@login_required
def delete_appointment(id):
    """Elimina appuntamento"""
    try:
        AppointmentService.delete_appointment(id, current_user.id)
        flash("Appuntamento eliminato con successo!", 'success')
    except ValueError as e:
        flash(f"Errore: {str(e)}", 'error')
    except Exception as e:
        flash(f"Errore imprevisto: {str(e)}", 'error')
    
    return redirect(url_for('main.appointments'))

# Altre funzionalità dall'app originale
@bp.route('/marketing')
@login_required
def marketing():
    """Pagina marketing"""
    return render_template('marketing.html')

@bp.route('/license')
@login_required  
def license():
    """Pagina licenza"""
    return render_template('license.html')

@bp.route('/report')
@login_required
def report():
    """Genera report Excel come nell'app originale"""
    # TODO: Implementare generazione Excel con xlsxwriter
    # Per ora redirect al sistema di report dell'admin
    if current_user.is_admin():
        return redirect(url_for('admin.reports'))
    else:
        flash("Solo gli amministratori possono generare report completi", 'info')
        return redirect(url_for('main.index'))

@bp.route('/provvigioni', methods=['GET', 'POST'])
@login_required
def provvigioni():
    """Gestione provvigioni (solo admin)"""
    if not current_user.is_admin():
        flash("Accesso negato", 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Implementazione semplificata - nell'originale c'era controllo password
        consultants = Consultant.query.all()
        appointments = Appointment.query.all()
        consultant_id = request.form.get('consultant', type=int)
        return render_template('provvigioni.html', 
                             consultants=consultants, 
                             appointments=appointments, 
                             consultant_id=consultant_id)
    
    return render_template('login.html')

# Gestione Consulenti
@bp.route('/add_consultant', methods=['GET', 'POST'])
@login_required
def add_consultant():
    """Aggiungi nuovo consulente"""
    if not current_user.is_admin():
        flash("Solo gli amministratori possono aggiungere consulenti", 'error')
        return redirect(url_for('main.index'))
    
    consultants = Consultant.query.all()
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        posizione = request.form.get('posizione')
        responsabile_id = request.form.get('responsabile_id')
        
        if not nome:
            flash("Il nome del consulente è obbligatorio", 'error')
            return render_template('add_consultant.html', consultants=consultants)
        
        new_consultant = Consultant(
            nome=nome,
            posizione=posizione,
            responsabile_id=int(responsabile_id) if responsabile_id else None
        )
        
        try:
            db.session.add(new_consultant)
            db.session.commit()
            flash("Consulente aggiunto con successo!", 'success')
            return redirect(url_for('main.consultants'))
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nell'aggiungere il consulente: {str(e)}", 'error')
    
    return render_template('add_consultant.html', consultants=consultants)

@bp.route('/modify_consultant/<int:id>', methods=['GET', 'POST'])
@login_required
def modify_consultant(id):
    """Modifica consulente esistente"""
    if not current_user.is_admin():
        flash("Solo gli amministratori possono modificare consulenti", 'error')
        return redirect(url_for('main.index'))
    
    consultant = Consultant.query.get_or_404(id)
    consultants = Consultant.query.filter(Consultant.id != id).all()
    
    if request.method == 'POST':
        consultant.nome = request.form.get('nome')
        consultant.posizione = request.form.get('posizione')
        responsabile_id = request.form.get('responsabile_id')
        consultant.responsabile_id = int(responsabile_id) if responsabile_id else None
        
        try:
            db.session.commit()
            flash("Consulente modificato con successo!", 'success')
            return redirect(url_for('main.consultants'))
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nella modifica: {str(e)}", 'error')
    
    return render_template('modify_consultant.html', consultant=consultant, consultants=consultants)

@bp.route('/delete_consultant/<int:id>')
@login_required
def delete_consultant(id):
    """Elimina consulente"""
    if not current_user.is_admin():
        flash("Solo gli amministratori possono eliminare consulenti", 'error')
        return redirect(url_for('main.index'))
    
    consultant = Consultant.query.get_or_404(id)
    
    try:
        # Sposta appuntamenti venduti al mentor se presente
        mentor = Consultant.query.get(consultant.responsabile_id) if consultant.responsabile_id else None
        if mentor:
            for appointment in consultant.appointments:
                if appointment.venduto:
                    appointment.consultants.remove(consultant)
                    appointment.consultants.append(mentor)
        
        # Rimuovi responsabile dai subordinati
        for subordinato in consultant.subordinati:
            subordinato.responsabile_id = None
        
        db.session.delete(consultant)
        db.session.commit()
        flash("Consulente eliminato con successo!", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Errore nell'eliminazione: {str(e)}", 'error')
    
    return redirect(url_for('main.consultants'))

# Gestione Eventi/Note
@bp.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    """Aggiungi nuovo evento/nota"""
    if request.method == 'POST':
        nota = request.form.get('note')
        data_str = request.form.get('data')
        
        if not nota or not data_str:
            flash("Nota e data sono obbligatori", 'error')
            return render_template('add_event.html')
        
        try:
            data_evento = datetime.strptime(data_str, '%Y-%m-%d')
            
            new_event = note_event(
                note=nota,
                data=data_evento
            )
            
            db.session.add(new_event)
            db.session.commit()
            flash("Evento aggiunto con successo!", 'success')
            return redirect(url_for('main.calendar'))
        except ValueError:
            flash("Formato data non valido", 'error')
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nell'aggiungere l'evento: {str(e)}", 'error')
    
    return render_template('add_event.html')

@bp.route('/modify_event/<int:id>', methods=['GET', 'POST'])
@login_required
def modify_event(id):
    """Modifica evento esistente"""
    event = note_event.query.get_or_404(id)
    
    if request.method == 'POST':
        event.note = request.form.get('note')
        data_str = request.form.get('data')
        
        if not event.note or not data_str:
            flash("Nota e data sono obbligatori", 'error')
            return render_template('modify_event.html', event=event)
        
        try:
            event.data = datetime.strptime(data_str, '%Y-%m-%d')
            db.session.commit()
            flash("Evento modificato con successo!", 'success')
            return redirect(url_for('main.calendar'))
        except ValueError:
            flash("Formato data non valido", 'error')
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nella modifica: {str(e)}", 'error')
    
    return render_template('modify_event.html', event=event)