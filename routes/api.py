from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models.appointment import Appointment, OtherAppointment
from models.consultant import Consultant
from models.client import Client
from models.user import db
from datetime import datetime

bp = Blueprint('api', __name__)

# Rate limiting per API
limiter = Limiter(key_func=get_remote_address)

@bp.route('/appointments', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per minute")
def api_appointments():
    """API per gestione appuntamenti"""
    
    if request.method == 'GET':
        # Filtra per permessi utente
        if current_user.is_admin():
            appointments = Appointment.query.all()
        elif current_user.is_dealer() and current_user.consultant:
            appointments = current_user.consultant.appointments
        else:
            return jsonify({'error': 'Accesso negato'}), 403
        
        result = [appointment.to_dict() for appointment in appointments]
        return jsonify({'appointments': result})
    
    elif request.method == 'POST':
        if not current_user.has_permission('manage_appointments'):
            return jsonify({'error': 'Permessi insufficienti'}), 403
        
        data = request.get_json()
        if not data or not data.get('nome_cliente') or not data.get('numero_telefono'):
            return jsonify({'error': 'Dati mancanti: nome_cliente e numero_telefono richiesti'}), 400
        
        try:
            data_appuntamento = datetime.strptime(data.get('data_appuntamento'), '%Y-%m-%d')
            data_richiamo = datetime.strptime(data.get('data_richiamo'), '%Y-%m-%d') if data.get('data_richiamo') else None
        except (ValueError, TypeError):
            return jsonify({'error': 'Formato data non valido. Usare YYYY-MM-DD'}), 400
        
        new_appt = Appointment(
            nome_cliente=data.get('nome_cliente'),
            indirizzo=data.get('indirizzo'),
            numero_telefono=data.get('numero_telefono'),
            note=data.get('note'),
            tipologia=data.get('tipologia'),
            stato=data.get('stato', 'concluso'),
            nominativi_raccolti=data.get('nominativi_raccolti', 0),
            appuntamenti_personali=data.get('appuntamenti_personali', 0),
            venduto=data.get('venduto', False),
            data_appuntamento=data_appuntamento,
            data_richiamo=data_richiamo
        )
        
        # Associa consulenti
        consultant_ids = data.get('consultants', [])
        for cid in consultant_ids:
            consultant = Consultant.query.get(cid)
            if consultant:
                new_appt.consultants.append(consultant)
        
        db.session.add(new_appt)
        db.session.commit()
        
        # Pianifica follow-up se venduto
        if new_appt.venduto:
            from models.followup import schedule_followups
            schedule_followups(new_appt)
        
        return jsonify({
            'message': 'Appuntamento creato con successo',
            'id': new_appt.id,
            'appointment': new_appt.to_dict()
        }), 201

@bp.route('/appointments/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@limiter.limit("100 per minute")
def api_appointment_detail(id):
    """API per singolo appuntamento"""
    
    appointment = Appointment.query.get_or_404(id)
    
    # Controlli permessi
    if not current_user.is_admin():
        if current_user.is_dealer():
            if not current_user.consultant or appointment not in current_user.consultant.appointments:
                return jsonify({'error': 'Accesso negato'}), 403
        else:
            return jsonify({'error': 'Accesso negato'}), 403
    
    if request.method == 'GET':
        return jsonify(appointment.to_dict())
    
    elif request.method == 'PUT':
        if not current_user.has_permission('manage_appointments'):
            return jsonify({'error': 'Permessi insufficienti'}), 403
        
        data = request.get_json()
        
        # Aggiorna campi
        for field in ['nome_cliente', 'indirizzo', 'numero_telefono', 'note', 'tipologia', 'stato']:
            if field in data:
                setattr(appointment, field, data[field])
        
        for field in ['nominativi_raccolti', 'appuntamenti_personali']:
            if field in data and data[field] is not None:
                setattr(appointment, field, int(data[field]))
        
        if 'venduto' in data:
            appointment.venduto = bool(data['venduto'])
        
        # Aggiorna date
        if 'data_appuntamento' in data:
            try:
                appointment.data_appuntamento = datetime.strptime(data['data_appuntamento'], '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Formato data_appuntamento non valido'}), 400
        
        if 'data_richiamo' in data:
            try:
                appointment.data_richiamo = datetime.strptime(data['data_richiamo'], '%Y-%m-%d') if data['data_richiamo'] else None
            except ValueError:
                return jsonify({'error': 'Formato data_richiamo non valido'}), 400
        
        # Aggiorna consulenti
        if 'consultants' in data:
            appointment.consultants = []
            for cid in data['consultants']:
                consultant = Consultant.query.get(cid)
                if consultant:
                    appointment.consultants.append(consultant)
        
        db.session.commit()
        return jsonify({
            'message': 'Appuntamento aggiornato con successo',
            'appointment': appointment.to_dict()
        })
    
    elif request.method == 'DELETE':
        if not current_user.has_permission('manage_appointments'):
            return jsonify({'error': 'Permessi insufficienti'}), 403
        
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'message': 'Appuntamento eliminato con successo'})

@bp.route('/consultants', methods=['GET', 'POST'])
@login_required
@limiter.limit("100 per minute")
def api_consultants():
    """API per gestione consulenti"""
    
    if request.method == 'GET':
        if current_user.is_admin():
            consultants = Consultant.query.all()
        elif current_user.is_dealer() and current_user.consultant:
            consultants = [current_user.consultant]
        else:
            return jsonify({'error': 'Accesso negato'}), 403
        
        result = []
        for consultant in consultants:
            data = {
                'id': consultant.id,
                'nome': consultant.nome,
                'posizione': consultant.posizione.nome if consultant.posizione else None,
                'posizione_id': consultant.posizione_id,
                'responsabile_id': consultant.responsabile_id,
                'totalYearlyPay': consultant.totalYearlyPay,
                'residency': consultant.residency,
                'phone': consultant.phone,
                'email': consultant.email,
                'CF': consultant.CF,
                'stats': consultant.get_appointments_stats()
            }
            result.append(data)
        
        return jsonify({'consultants': result})
    
    elif request.method == 'POST':
        if not current_user.has_permission('manage_consultants'):
            return jsonify({'error': 'Permessi insufficienti'}), 403
        
        data = request.get_json()
        if not data or not data.get('nome'):
            return jsonify({'error': 'Campo nome richiesto'}), 400
        
        # Gestione posizione
        from models.consultant import Position
        posizione_id = data.get('posizione_id')
        if not posizione_id and data.get('posizione'):
            pos = Position.query.filter_by(nome=data.get('posizione')).first()
            if not pos:
                pos = Position(nome=data.get('posizione'))
                db.session.add(pos)
                db.session.commit()
            posizione_id = pos.id
        
        new_consultant = Consultant(
            nome=data.get('nome'),
            posizione_id=posizione_id,
            responsabile_id=data.get('responsabile_id'),
            residency=data.get('residency'),
            phone=data.get('phone'),
            email=data.get('email'),
            CF=data.get('CF')
        )
        
        db.session.add(new_consultant)
        db.session.commit()
        
        return jsonify({
            'message': 'Consulente creato con successo',
            'id': new_consultant.id
        }), 201

@bp.route('/clients', methods=['GET'])
@login_required
@limiter.limit("100 per minute")
def api_clients():
    """API per clienti"""
    
    clients = Client.query.all()
    result = [client.to_dict() for client in clients]
    
    return jsonify({'clients': result})

@bp.route('/stats/dashboard')
@login_required
@limiter.limit("50 per minute")
def api_dashboard_stats():
    """API per statistiche dashboard"""
    
    if current_user.is_admin():
        data = {
            'total_appointments': Appointment.query.count(),
            'total_consultants': Consultant.query.count(),
            'total_clients': Client.query.count(),
            'sold_appointments': Appointment.query.filter_by(venduto=True).count()
        }
    elif current_user.is_dealer() and current_user.consultant:
        appointments = current_user.consultant.appointments
        data = {
            'total_appointments': len(appointments),
            'sold_appointments': len([a for a in appointments if a.venduto]),
            'consultant_name': current_user.consultant.nome,
            'stats': current_user.consultant.get_appointments_stats()
        }
    else:
        return jsonify({'error': 'Accesso negato'}), 403
    
    return jsonify(data)

# Error handlers per API
@bp.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit superato. Riprova più tardi.'}), 429

@bp.errorhandler(404)
def not_found_api(e):
    return jsonify({'error': 'Risorsa non trovata'}), 404

@bp.errorhandler(500)
def internal_error_api(e):
    return jsonify({'error': 'Errore interno del server'}), 500
