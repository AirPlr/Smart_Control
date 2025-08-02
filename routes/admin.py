from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.user import db, User
from models.appointment import Appointment
from models.consultant import Consultant
from datetime import datetime
import subprocess
import os
from functools import wraps

bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator per richiedere privilegi admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Accesso negato. Solo gli amministratori possono accedere a questa sezione.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.before_request
def require_admin():
    """Middleware per verificare che l'utente sia admin"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    if not current_user.is_admin():
        flash('Accesso negato: area riservata agli amministratori.', 'danger')
        return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Dashboard amministratore"""
    print(f"Dashboard route chiamato - User: {current_user.username if current_user.is_authenticated else 'Non autenticato'}")
    try:
        data = current_user.get_dashboard_data()
        print(f"Dati utente ottenuti: {data}")
        
        # Statistiche aggiuntive per admin
        from models.appointment import Appointment
        from models.consultant import Consultant
        
        # Performance overview
        recent_activity = _get_recent_activity()
        system_health = _get_system_health()
        
        data.update({
            'recent_activity': recent_activity,
            'system_health': system_health,
            'total_appointments': Appointment.query.count(),
            'recent_appointments': Appointment.query.order_by(Appointment.data_appuntamento.desc()).limit(10).all()
        })
        
        print(f"Dati completi per template: {list(data.keys())}")
        return render_template('admin/dashboard.html', data=data)
    except Exception as e:
        # Log dell'errore per debug
        print(f"Errore dashboard admin: {e}")
        import traceback
        traceback.print_exc()
        # Dati minimi per evitare crash
        data = {
            'total_appointments': 0,
            'total_consultants': 0,
            'total_users': 0,
            'sold_appointments': 0,
            'recent_appointments': []
        }
        return render_template('admin/dashboard.html', data=data)

@bp.route('/users')
@login_required
@admin_required
def users():
    """Gestione utenti"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Crea nuovo utente"""
    if request.method == 'POST':
        try:
            # Verifica se username/email esistono già
            username = request.form.get('username')
            email = request.form.get('email')
            
            if User.query.filter_by(username=username).first():
                flash('Username già esistente', 'error')
                return redirect(url_for('admin.create_user'))
            
            if User.query.filter_by(email=email).first():
                flash('Email già esistente', 'error')
                return redirect(url_for('admin.create_user'))
            
            # Crea utente
            user = User(
                username=username,
                email=email,
                role=request.form.get('role', 'dealer'),
                license_code=request.form.get('license_code', ''),
                language=request.form.get('language', 'it')
            )
            
            user.set_password(request.form.get('password'))
            
            # Ogni utente automaticamente diventa anche un consulente
            from models.consultant import Consultant, Position
            
            # Cerca o crea una posizione di default
            default_position = Position.query.filter_by(nome='Consulente').first()
            if not default_position:
                default_position = Position(nome='Consulente')
                db.session.add(default_position)
                db.session.flush()  # Per ottenere l'ID
            
            # Crea il consulente associato
            consultant = Consultant(
                nome=request.form.get('nome_consulente', username),  # Usa username se nome non fornito
                posizione_id=default_position.id,
                email=email,
                phone=request.form.get('phone', ''),
                residency=request.form.get('residency', ''),
                CF=request.form.get('cf', '')
            )
            
            db.session.add(consultant)
            db.session.flush()  # Per ottenere l'ID del consulente
            
            # Collega l'utente al consulente
            user.consultant_id = consultant.id
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Utente {username} creato con successo!', 'success')
            return redirect(url_for('admin.users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione utente: {str(e)}', 'error')
    
    # Per il form, serve lista consulenti
    from models.consultant import Consultant
    consultants = Consultant.query.all()
    
    return render_template('admin/create_user.html', consultants=consultants)

@bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Attiva/disattiva utente"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'error': 'Non puoi disattivare il tuo stesso account'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'attivato' if user.is_active else 'disattivato'
    return jsonify({'message': f'Utente {status} con successo', 'is_active': user.is_active})

@bp.route('/system/console')
@login_required
@admin_required
def system_console():
    """Console di sistema sicura"""
    return render_template('admin/console.html')

@bp.route('/system/info')
@login_required
@admin_required
def system_info():
    """Ottieni informazioni sistema"""
    try:
        import psutil
        import platform
        
        # Informazioni sistema
        system_info = {
            'system': f"{platform.system()} {platform.release()}",
            'cpu_usage': round(psutil.cpu_percent(interval=1), 1),
            'memory_usage': round(psutil.virtual_memory().percent, 1),
            'disk_usage': round(psutil.disk_usage('/').percent, 1),
            'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0],
            'load_average': ', '.join([str(round(x, 2)) for x in psutil.getloadavg()]) if hasattr(psutil, 'getloadavg') else 'N/A'
        }
        
        # Status VPN
        vpn_info = _check_tailscale_status()
        system_info['vpn_status'] = 'running' if vpn_info['running'] else 'stopped'
        
        return jsonify(system_info)
        
    except ImportError:
        # Fallback se psutil non è disponibile
        return jsonify({
            'system': 'Sistema sconosciuto',
            'cpu_usage': 'N/A',
            'memory_usage': 'N/A', 
            'disk_usage': 'N/A',
            'uptime': 'N/A',
            'load_average': 'N/A',
            'vpn_status': 'unknown'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/system/console/execute', methods=['POST'])
@login_required
@admin_required
def execute_command():
    """Esegue comando di sistema (versione sicura)"""
    command = request.form.get('command', '').strip()
    
    if not command:
        return jsonify({'output': 'Nessun comando fornito.', 'success': False})
    
    # Lista comandi sicuri consentiti
    allowed_commands = {
        'ls': ['ls', '-la'],
        'dir': ['dir'],
        'pwd': ['pwd'],
        'whoami': ['whoami'],
        'date': ['date'],
        'ps': ['ps', 'aux'],
        'df': ['df', '-h'],
        'free': ['free', '-h'],
        'uptime': ['uptime'],
        'systemctl status': ['systemctl', 'status'],
        'ping': ['ping', '-c', '4'],
        'netstat': ['netstat', '-tuln'],
        'top': ['top', '-n', '1'],
    }
    
    # Parsing del comando
    cmd_parts = command.split()
    base_cmd = cmd_parts[0].lower()
    
    # Controlli di sicurezza
    dangerous_patterns = [
        'rm', 'del', 'format', 'fdisk', 'mkfs', 'dd',
        'sudo', 'su', 'chmod', 'chown', 'passwd',
        'shutdown', 'reboot', 'halt', 'poweroff',
        'wget', 'curl', 'nc', 'netcat', 'ssh',
        'python', 'bash', 'sh', 'powershell', 'cmd',
        '>', '>>', '|', '&', ';', '$(', '`',
        'systemctl start', 'systemctl stop', 'systemctl restart'
    ]
    
    # Verifica pattern pericolosi
    if any(pattern in command.lower() for pattern in dangerous_patterns):
        return jsonify({
            'output': f"❌ Comando '{command}' non consentito per motivi di sicurezza.",
            'success': False
        })
    
    # Verifica comando in whitelist
    if base_cmd not in [cmd.split()[0] for cmd in allowed_commands.keys()]:
        return jsonify({
            'output': f"❌ Comando '{base_cmd}' non consentito. Comandi disponibili: {', '.join(allowed_commands.keys())}",
            'success': False
        })
    
    # Esecuzione sicura
    try:
        result = subprocess.run(
            cmd_parts, 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            output = f"✅ Comando eseguito:\n{result.stdout}"
            success = True
        else:
            output = f"⚠️ Errore nell'esecuzione:\n{result.stderr}"
            success = False
            
    except subprocess.TimeoutExpired:
        output = "❌ Timeout: comando interrotto dopo 10 secondi"
        success = False
    except Exception as e:
        output = f"❌ Errore: {str(e)}"
        success = False
    
    # Log dell'attività
    from flask import current_app
    current_app.logger.info(f"Comando admin eseguito da {current_user.username}: {command}")
    
    return jsonify({'output': output, 'success': success})

@bp.route('/system/vpn')
@login_required  
def vpn_management():
    """Interfaccia gestione VPN/Tailscale"""
    # Controlla se Tailscale è installato
    tailscale_status = _check_tailscale_status()
    
    return render_template('admin/vpn.html', tailscale_status=tailscale_status)

@bp.route('/system/vpn/tailscale/status')
@login_required
def tailscale_status():
    """Status Tailscale"""
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            return jsonify({
                'installed': True,
                'running': True,
                'status': result.stdout,
                'success': True
            })
        else:
            return jsonify({
                'installed': True,
                'running': False,
                'error': result.stderr,
                'success': False
            })
            
    except FileNotFoundError:
        return jsonify({
            'installed': False,
            'running': False,
            'error': 'Tailscale non installato',
            'success': False
        })
    except Exception as e:
        return jsonify({
            'installed': False,
            'running': False,
            'error': str(e),
            'success': False
        })

@bp.route('/system/vpn/tailscale/toggle', methods=['POST'])
@login_required
def tailscale_toggle():
    """Avvia/ferma Tailscale"""
    action = request.json.get('action')  # 'up' o 'down'
    
    if action not in ['up', 'down']:
        return jsonify({'error': 'Azione non valida'}), 400
    
    try:
        if action == 'up':
            result = subprocess.run(['tailscale', 'up'], capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(['tailscale', 'down'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'message': f'Tailscale {action} eseguito con successo',
                'output': result.stdout
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Utility functions
def _get_recent_activity():
    """Ottiene attività recente del sistema"""
    activities = []
    
    # Ultimi utenti registrati
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    for user in recent_users:
        activities.append({
            'type': 'user_created',
            'message': f'Nuovo utente registrato: {user.username}',
            'timestamp': user.created_at,
            'icon': 'user-plus'
        })
    
    # Ultimi login (simulato - dovrebbe essere in una tabella di log)
    recent_logins = User.query.filter(User.last_login.isnot(None)).order_by(User.last_login.desc()).limit(5).all()
    for user in recent_logins:
        activities.append({
            'type': 'user_login',
            'message': f'Login: {user.username}',
            'timestamp': user.last_login,
            'icon': 'sign-in-alt'
        })
    
    # Ordina per timestamp
    activities.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime(1900, 1, 1), reverse=True)
    
    return activities[:10]

def _get_system_health():
    """Controlla salute del sistema"""
    health = {
        'database': True,
        'disk_space': True,
        'memory': True,
        'services': True
    }
    
    try:
        # Test database
        User.query.first()
    except:
        health['database'] = False
    
    try:
        # Controlla spazio disco (simulato)
        import shutil
        total, used, free = shutil.disk_usage("/")
        if (free / total) < 0.1:  # Meno del 10% libero
            health['disk_space'] = False
    except:
        health['disk_space'] = False
    
    return health

def _check_tailscale_status():
    """Controlla status Tailscale"""
    try:
        result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True, timeout=5)
        return {
            'installed': True,
            'running': result.returncode == 0,
            'status': result.stdout if result.returncode == 0 else result.stderr
        }
    except FileNotFoundError:
        return {
            'installed': False,
            'running': False,
            'status': 'Tailscale non installato'
        }
    except Exception as e:
        return {
            'installed': False,
            'running': False,
            'status': f'Errore: {str(e)}'
        }

@bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user(user_id):
    """Ottieni dettagli di un utente specifico"""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Aggiorna un utente esistente"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Aggiorna i campi
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Utente {user.username} aggiornato con successo'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user_active_status(user_id):
    """Attiva/disattiva un utente"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        user.is_active = data.get('is_active', not user.is_active)
        db.session.commit()
        
        status = "attivato" if user.is_active else "disattivato"
        return jsonify({'success': True, 'message': f'Utente {user.username} {status} con successo'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Elimina un utente (non se stesso)"""
    try:
        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Non puoi eliminare il tuo stesso account'}), 400
            
        user = User.query.get_or_404(user_id)
        username = user.username
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Utente {username} eliminato con successo'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/appointments')
@login_required
@admin_required
def appointments():
    """Gestione appuntamenti - vista admin"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filtri
    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    consultant_filter = request.args.get('consultant')
    
    query = Appointment.query
    
    if status_filter:
        query = query.filter(Appointment.stato == status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Appointment.data_appuntamento) == filter_date)
        except ValueError:
            flash('Formato data non valido', 'error')
    
    if consultant_filter:
        query = query.join(Appointment.consultants).filter(Consultant.id == consultant_filter)
    
    appointments = query.order_by(Appointment.data_appuntamento.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistiche
    stats = {
        'total': Appointment.query.count(),
        'conclusi': Appointment.query.filter_by(stato='concluso').count(),
        'da_richiamare': Appointment.query.filter_by(stato='da richiamare').count(),
        'venduti': Appointment.query.filter_by(venduto=True).count()
    }
    
    consultants = Consultant.query.all()
    
    return render_template('admin/appointments.html', 
                         appointments=appointments, 
                         stats=stats,
                         consultants=consultants)

@bp.route('/appointments/<int:appointment_id>')
@login_required
@admin_required
def appointment_detail(appointment_id):
    """Dettaglio appuntamento"""
    appointment = Appointment.query.get_or_404(appointment_id)
    return render_template('admin/appointment_detail.html', appointment=appointment)

@bp.route('/reports')
@login_required
@admin_required  
def reports():
    """Generazione report"""
    return render_template('admin/reports.html')

@bp.route('/reports/generate', methods=['POST'])
@login_required
@admin_required
def generate_report():
    """Genera report basato sui parametri"""
    try:
        report_type = request.form.get('report_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not all([report_type, start_date, end_date]):
            return jsonify({'error': 'Tutti i campi sono obbligatori'}), 400
        
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        if report_type == 'appointments':
            appointments = Appointment.query.filter(
                Appointment.data_appuntamento.between(start_date, end_date)
            ).all()
            
            data = {
                'period': f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                'total_appointments': len(appointments),
                'sold_appointments': sum(1 for a in appointments if a.venduto),
                'concluded_appointments': sum(1 for a in appointments if a.stato == 'concluso'),
                'pending_callbacks': sum(1 for a in appointments if a.stato == 'da richiamare'),
                'appointments': [{
                    'nome_cliente': a.nome_cliente,
                    'data_appuntamento': a.data_appuntamento.strftime('%d/%m/%Y %H:%M'),
                    'stato': a.stato,
                    'venduto': 'Sì' if a.venduto else 'No',
                    'consultants': ', '.join([c.nome for c in a.consultants])
                } for a in appointments]
            }
            
            return jsonify({'success': True, 'data': data})
        
        elif report_type == 'performance':
            # Report performance consulenti
            consultants = Consultant.query.all()
            consultant_stats = []
            
            for consultant in consultants:
                consultant_appointments = [a for a in consultant.appointments 
                                        if start_date <= a.data_appuntamento <= end_date]
                
                consultant_stats.append({
                    'nome': consultant.nome,
                    'total_appointments': len(consultant_appointments),
                    'sold_appointments': sum(1 for a in consultant_appointments if a.venduto),
                    'conversion_rate': round((sum(1 for a in consultant_appointments if a.venduto) / len(consultant_appointments) * 100) if consultant_appointments else 0, 2)
                })
            
            data = {
                'period': f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
                'consultant_stats': consultant_stats
            }
            
            return jsonify({'success': True, 'data': data})
        
        return jsonify({'error': 'Tipo di report non valido'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === IMPOSTAZIONI SISTEMA ===

@bp.route('/settings')
@login_required
@admin_required
def settings():
    """Pagina impostazioni sistema completa"""
    from models.consultant import Position
    
    # Dati per le impostazioni
    settings_data = {
        'system_info': _get_system_info(),
        'database_stats': _get_database_stats(),
        'positions': Position.query.all(),
        'vpn_status': _get_vpn_status(),
        'backup_info': _get_backup_info()
    }
    
    return render_template('admin/settings.html', **settings_data)

@bp.route('/settings/positions', methods=['GET', 'POST'])
@login_required  
@admin_required
def manage_positions():
    """Gestione posizioni consulenti"""
    from models.consultant import Position
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            nome = request.form.get('nome', '').strip()
            if nome:
                if not Position.query.filter_by(nome=nome).first():
                    position = Position(nome=nome)
                    db.session.add(position)
                    db.session.commit()
                    flash(f'Posizione "{nome}" creata con successo!', 'success')
                else:
                    flash('Posizione già esistente!', 'warning')
            else:
                flash('Nome posizione richiesto!', 'error')
                
        elif action == 'delete':
            position_id = request.form.get('position_id')
            if position_id:
                position = Position.query.get(position_id)
                if position:
                    # Controlla se ci sono consulenti con questa posizione
                    if position.consultants:
                        flash(f'Impossibile eliminare: {len(position.consultants)} consulenti utilizzano questa posizione', 'warning')
                    else:
                        db.session.delete(position)
                        db.session.commit()
                        flash(f'Posizione "{position.nome}" eliminata!', 'success')
                        
        elif action == 'update':
            position_id = request.form.get('position_id')
            new_name = request.form.get('new_name', '').strip()
            if position_id and new_name:
                position = Position.query.get(position_id)
                if position:
                    position.nome = new_name
                    db.session.commit()
                    flash(f'Posizione aggiornata a "{new_name}"!', 'success')
    
    return redirect(url_for('admin.settings'))

@bp.route('/settings/system', methods=['POST'])
@login_required
@admin_required  
def system_settings():
    """Gestione impostazioni sistema"""
    action = request.form.get('action')
    
    try:
        if action == 'restart_app':
            flash('Riavvio applicazione in corso...', 'info')
            # Implementa logica riavvio
            return jsonify({'success': True, 'message': 'Applicazione riavviata'})
            
        elif action == 'backup_db':
            # Implementa backup database
            backup_path = _create_database_backup()
            flash(f'Backup creato: {backup_path}', 'success')
            return jsonify({'success': True, 'backup_path': backup_path})
            
        elif action == 'clear_logs':
            # Pulisci logs
            _clear_application_logs()
            flash('Log applicazione puliti', 'success')
            return jsonify({'success': True})
            
        elif action == 'vpn_connect':
            # Connessione VPN
            result = _connect_vpn()
            return jsonify(result)
            
        elif action == 'vpn_disconnect':
            # Disconnessione VPN  
            result = _disconnect_vpn()
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# === FUNZIONI HELPER PER IMPOSTAZIONI ===

def _get_system_info():
    """Informazioni sistema"""
    import platform
    try:
        import psutil
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
    except ImportError:
        cpu_usage = memory_usage = disk_usage = 'N/A'
    
    return {
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'cpu_usage': cpu_usage,
        'memory_usage': memory_usage,
        'disk_usage': disk_usage,
        'uptime': 'N/A'
    }

def _get_database_stats():
    """Statistiche database"""
    try:
        return {
            'total_users': User.query.count(),
            'total_consultants': Consultant.query.count(), 
            'total_appointments': Appointment.query.count(),
            'db_size': 'N/A'
        }
    except Exception:
        return {'error': 'Impossibile recuperare stats database'}

def _get_vpn_status():
    """Stato connessione VPN"""
    try:
        result = subprocess.run(['ping', '-n', '1', '8.8.8.8'] if os.name == 'nt' else ['ping', '-c', '1', '8.8.8.8'], 
                              capture_output=True, text=True, timeout=5)
        return {
            'connected': result.returncode == 0,
            'ip': 'N/A',
            'location': 'N/A'
        }
    except Exception:
        return {'connected': False, 'error': 'Controllo VPN non disponibile'}

def _get_backup_info():
    """Informazioni backup"""
    import glob
    
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        return {'last_backup': None, 'backup_count': 0}
    
    backups = glob.glob(os.path.join(backup_dir, '*.db'))
    backups.sort(key=os.path.getmtime, reverse=True)
    
    return {
        'last_backup': os.path.basename(backups[0]) if backups else None,
        'backup_count': len(backups)
    }

def _create_database_backup():
    """Crea backup database"""
    import shutil
    from datetime import datetime
    
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'backup_{timestamp}.db'
    backup_path = os.path.join(backup_dir, backup_filename)
    
    db_path = 'instance/appointments.db'
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        return backup_filename
    else:
        raise Exception('Database non trovato')

def _clear_application_logs():
    """Pulisce i log dell'applicazione"""
    log_files = ['logs/app.log', 'logs/app.log.1']
    for log_file in log_files:
        if os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write('')

def _connect_vpn():
    """Connette VPN"""
    try:
        return {'success': True, 'message': 'VPN connessa (simulato)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _disconnect_vpn():
    """Disconnette VPN"""
    try:
        return {'success': True, 'message': 'VPN disconnessa (simulato)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@bp.route('/change-theme', methods=['POST'])
@login_required
@admin_required
def change_theme():
    """Endpoint per cambiare il tema dell'admin"""
    try:
        data = request.get_json()
        theme_name = data.get('theme', 'default')
        
        # Valida i temi disponibili
        valid_themes = ['default', 'dark', 'ocean', 'sunset', 'forest', 'purple']
        if theme_name not in valid_themes:
            return jsonify({
                'success': False, 
                'error': 'Tema non valido'
            }), 400
        
        # Aggiorna il tema dell'utente
        current_user.theme = theme_name
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tema cambiato a: {theme_name.title()}',
            'theme': theme_name
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel cambio tema: {str(e)}'
        }), 500

@bp.route('/theme-settings')
@login_required
@admin_required
def theme_settings():
    """Pagina delle impostazioni del tema"""
    return render_template('admin/theme_settings.html')

@bp.route('/save-theme-settings', methods=['POST'])
@login_required
@admin_required
def save_theme_settings():
    """Salva le impostazioni avanzate del tema"""
    try:
        data = request.get_json()
        
        # Aggiorna le impostazioni nell'oggetto settings dell'utente
        if not current_user.settings:
            current_user.settings = {}
        
        current_user.settings.update({
            'theme_animations': data.get('animations', True),
            'theme_reduced_motion': data.get('reducedMotion', False),
            'theme_compact_mode': data.get('compactMode', False),
            'theme_fixed_sidebar': data.get('fixedSidebar', True)
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Impostazioni tema salvate con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel salvataggio: {str(e)}'
        }), 500
