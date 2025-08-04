from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.user import db
from datetime import datetime, timedelta
import calendar

bp = Blueprint('dealer', __name__)

@bp.before_request
def require_dealer():
    """Middleware per verificare che l'utente sia un dealer o admin con consulente"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Ora tutti gli utenti dovrebbero avere un consulente associato
    if not current_user.consultant and not current_user.is_admin():
        flash('Nessun consulente associato. Contatta l\'amministratore.', 'warning')
        return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard mobile-optimized per dealer"""
    data = current_user.get_dashboard_data()
    
    # Aggiunge data formattata in italiano
    import locale
    try:
        locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'Italian')
        except:
            pass  # Usa locale di default se italiano non disponibile
    
    current_date = datetime.now().strftime('%A, %d %B %Y')
    
    # Assicura che tutti i dati necessari siano presenti
    if 'monthly_stats' not in data:
        data['monthly_stats'] = {
            'total_this_month': 0,
            'sold_this_month': 0,
            'assistenza_count': 0,
            'dimostrazione_count': 0,
            'consumabili_count': 0
        }
    
    # Aggiunge dati per grafici mobile
    if current_user.consultant:
        appointments = current_user.consultant.appointments
        
        # Statistiche settimanali per grafico mobile
        weekly_stats = _get_weekly_stats(appointments)
        
        # Performance mensile
        monthly_performance = _get_monthly_performance(appointments)
        
        data.update({
            'weekly_stats': weekly_stats,
            'monthly_performance': monthly_performance,
            'consultant_name': current_user.consultant.nome,
            'current_date': current_date
        })
    else:
        data.update({
            'consultant_name': 'Dealer Dashboard',
            'current_date': current_date,
            'total_appointments': 0,
            'sold_appointments': 0,
            'recent_appointments': [],
            'weekly_stats': {},
            'monthly_performance': []
        })
    
    return render_template('dealer/dashboard.html', data=data)

@bp.route('/stats')
@login_required 
def stats():
    """Statistiche dettagliate per dealer"""
    if not current_user.consultant:
        flash('Nessun consulente associato al tuo account.', 'warning')
        return redirect(url_for('dealer.dashboard'))
    
    appointments = current_user.consultant.appointments
    
    # Filtri per periodo
    period = request.args.get('period', 'month')  # month, quarter, year
    stats_data = _calculate_period_stats(appointments, period)
    
    return render_template('dealer/stats.html', 
                         stats=stats_data, 
                         period=period,
                         consultant=current_user.consultant)

@bp.route('/appointments')
@login_required
def appointments():
    """Lista appuntamenti del dealer"""
    if not current_user.consultant:
        return jsonify({'error': 'Nessun consulente associato'}), 400
    
    appointments = current_user.consultant.appointments
    
    # Filtri
    status_filter = request.args.get('status')
    if status_filter:
        appointments = [a for a in appointments if a.stato == status_filter]
    
    # Paginazione per mobile
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_appointments = appointments[start:end]
    
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'appointments': [{
                'id': a.id,
                'nome_cliente': a.nome_cliente,
                'data_appuntamento': a.data_appuntamento.strftime('%d/%m/%Y %H:%M'),
                'stato': a.stato,
                'tipologia': a.tipologia,
                'venduto': a.venduto
            } for a in paginated_appointments],
            'has_next': end < len(appointments),
            'page': page
        })
    
    return render_template('dealer/appointments.html', 
                         appointments=paginated_appointments,
                         has_next=end < len(appointments),
                         page=page)

@bp.route('/profile')
@login_required
def profile():
    """Profilo dealer - mobile friendly"""
    return render_template('dealer/profile.html', user=current_user)

@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Aggiorna profilo dealer"""
    try:
        current_user.email = request.form.get('email', current_user.email)
        
        # Aggiorna password se fornita
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
        
        # Aggiorna preferenze mobile
        mobile_settings = {
            'notifications': request.form.get('notifications') == 'on',
            'dark_mode': request.form.get('dark_mode') == 'on',
            'language': request.form.get('language', 'it')
        }
        
        current_user.settings.update(mobile_settings)
        db.session.commit()
        
        flash('Profilo aggiornato con successo!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'aggiornamento: {str(e)}', 'error')
    
    return redirect(url_for('dealer.profile'))

@bp.route('/quick-actions')
@login_required
def quick_actions():
    """Azioni rapide per mobile"""
    return render_template('dealer/quick_actions.html')

# API endpoints per mobile app
@bp.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    """Dati dashboard in formato JSON per app mobile"""
    data = current_user.get_dashboard_data()
    return jsonify(data)

@bp.route('/api/weekly-chart')
@login_required
def api_weekly_chart():
    """Dati per grafico settimanale mobile"""
    if not current_user.consultant:
        return jsonify({'error': 'No consultant'}), 400
    
    appointments = current_user.consultant.appointments
    weekly_data = _get_weekly_stats(appointments)
    
    return jsonify(weekly_data)

@bp.route('/reports')
@login_required
def reports():
    """Report personalizzati per dealer"""
    if not current_user.consultant:
        flash('Nessun consulente associato', 'warning')
        return redirect(url_for('dealer.dashboard'))
    
    # Dati di base per i report
    appointments = current_user.consultant.appointments
    now = datetime.now()
    
    # Statistiche generali
    total_appointments = len(appointments)
    sold_appointments = len([a for a in appointments if a.venduto])
    conversion_rate = (sold_appointments / total_appointments * 100) if total_appointments > 0 else 0
    
    # Statistiche per periodo
    current_month = now.replace(day=1)
    current_year = now.replace(month=1, day=1)
    
    monthly_appointments = [a for a in appointments if a.data_appuntamento >= current_month]
    yearly_appointments = [a for a in appointments if a.data_appuntamento >= current_year]
    
    stats = {
        'total_appointments': total_appointments,
        'sold_appointments': sold_appointments,
        'conversion_rate': round(conversion_rate, 2),
        'monthly': {
            'total': len(monthly_appointments),
            'sold': len([a for a in monthly_appointments if a.venduto]),
            'assistenza': len([a for a in monthly_appointments if a.tipologia == 'Assistenza']),
            'dimostrazione': len([a for a in monthly_appointments if a.tipologia == 'Dimostrazione']),
            'consumabili': len([a for a in monthly_appointments if a.tipologia == 'Consumabili'])
        },
        'yearly': {
            'total': len(yearly_appointments),
            'sold': len([a for a in yearly_appointments if a.venduto]),
            'assistenza': len([a for a in yearly_appointments if a.tipologia == 'Assistenza']),
            'dimostrazione': len([a for a in yearly_appointments if a.tipologia == 'Dimostrazione']),
            'consumabili': len([a for a in yearly_appointments if a.tipologia == 'Consumabili'])
        }
    }
    
    return render_template('dealer/reports.html', 
                         stats=stats, 
                         consultant=current_user.consultant,
                         current_date=now.strftime('%d/%m/%Y'))

@bp.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Genera report specifico per dealer"""
    if not current_user.consultant:
        return jsonify({'error': 'Nessun consulente associato'}), 400
    
    report_type = request.form.get('report_type')
    period = request.form.get('period', 'month')
    
    appointments = current_user.consultant.appointments
    now = datetime.now()
    
    # Determina il periodo
    if period == 'week':
        start_date = now - timedelta(days=7)
        period_name = "Ultima settimana"
    elif period == 'month':
        start_date = now.replace(day=1)
        period_name = f"Mese di {now.strftime('%B %Y')}"
    elif period == 'quarter':
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_month, day=1)
        period_name = f"Q{((now.month-1)//3)+1} {now.year}"
    else:  # year
        start_date = now.replace(month=1, day=1)
        period_name = f"Anno {now.year}"
    
    # Filtra appuntamenti per periodo
    period_appointments = [a for a in appointments if a.data_appuntamento >= start_date]
    
    if report_type == 'performance':
        # Report performance personale
        data = {
            'period': period_name,
            'consultant_name': current_user.consultant.nome,
            'total_appointments': len(period_appointments),
            'sold_appointments': len([a for a in period_appointments if a.venduto]),
            'conversion_rate': round((len([a for a in period_appointments if a.venduto]) / len(period_appointments) * 100) if period_appointments else 0, 2),
            'by_type': {
                'assistenza': {
                    'total': len([a for a in period_appointments if a.tipologia == 'Assistenza']),
                    'sold': len([a for a in period_appointments if a.tipologia == 'Assistenza' and a.venduto])
                },
                'dimostrazione': {
                    'total': len([a for a in period_appointments if a.tipologia == 'Dimostrazione']),
                    'sold': len([a for a in period_appointments if a.tipologia == 'Dimostrazione' and a.venduto])
                },
                'consumabili': {
                    'total': len([a for a in period_appointments if a.tipologia == 'Consumabili']),
                    'sold': len([a for a in period_appointments if a.tipologia == 'Consumabili' and a.venduto])
                }
            },
            'nominativi_raccolti': sum([a.nominativi_raccolti or 0 for a in period_appointments]),
            'appuntamenti_personali': sum([a.appuntamenti_personali or 0 for a in period_appointments])
        }
        
    elif report_type == 'activity':
        # Report attività dettagliato
        appointments_list = []
        for appointment in period_appointments:
            appointments_list.append({
                'id': appointment.id,
                'nome_cliente': appointment.nome_cliente,
                'data_appuntamento': appointment.data_appuntamento.strftime('%d/%m/%Y %H:%M'),
                'tipologia': appointment.tipologia,
                'stato': appointment.stato,
                'venduto': 'Sì' if appointment.venduto else 'No',
                'nominativi_raccolti': appointment.nominativi_raccolti or 0,
                'appuntamenti_personali': appointment.appuntamenti_personali or 0
            })
        
        data = {
            'period': period_name,
            'consultant_name': current_user.consultant.nome,
            'appointments': appointments_list
        }
    
    else:
        return jsonify({'error': 'Tipo di report non valido'}), 400
    
    return jsonify({'success': True, 'data': data})

# Utility functions
def _get_weekly_stats(appointments):
    """Calcola statistiche settimanali"""
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday())
    
    daily_stats = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_appointments = [a for a in appointments 
                          if a.data_appuntamento.date() == day.date()]
        
        daily_stats[day.strftime('%A')] = {
            'total': len(day_appointments),
            'sold': len([a for a in day_appointments if a.venduto]),
            'assistenza': len([a for a in day_appointments if a.tipologia == 'Assistenza']),
            'dimostrazione': len([a for a in day_appointments if a.tipologia == 'Dimostrazione']),
            'consumabili': len([a for a in day_appointments if a.tipologia == 'Consumabili'])
        }
    
    return daily_stats

def _get_monthly_performance(appointments):
    """Performance mensile per grafico"""
    now = datetime.now()
    months_data = []
    
    for i in range(6):  # Ultimi 6 mesi
        month_date = now.replace(day=1) - timedelta(days=i*30)
        month_start = month_date.replace(day=1)
        
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year+1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_date.replace(month=month_date.month+1, day=1) - timedelta(days=1)
        
        month_appointments = [a for a in appointments 
                            if month_start <= a.data_appuntamento <= month_end]
        
        months_data.append({
            'month': calendar.month_name[month_date.month],
            'year': month_date.year,
            'total': len(month_appointments),
            'sold': len([a for a in month_appointments if a.venduto]),
            'revenue': sum([1000 for a in month_appointments if a.venduto])  # Mock revenue
        })
    
    return list(reversed(months_data))

def _calculate_period_stats(appointments, period):
    """Calcola statistiche per periodo specificato"""
    now = datetime.now()
    
    if period == 'month':
        start_date = now.replace(day=1)
    elif period == 'quarter':
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_month, day=1)
    else:  # year
        start_date = now.replace(month=1, day=1)
    
    period_appointments = [a for a in appointments if a.data_appuntamento >= start_date]
    
    return {
        'total': len(period_appointments),
        'sold': len([a for a in period_appointments if a.venduto]),
        'assistenza': len([a for a in period_appointments if a.tipologia == 'Assistenza']),
        'dimostrazione': len([a for a in period_appointments if a.tipologia == 'Dimostrazione']),
        'consumabili': len([a for a in period_appointments if a.tipologia == 'Consumabili']),
        'conversion_rate': (len([a for a in period_appointments if a.venduto]) / len(period_appointments) * 100) if period_appointments else 0
    }
