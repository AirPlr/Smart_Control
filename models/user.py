from .database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='dealer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Settings e configurazioni
    settings = db.Column(db.JSON, default=lambda: {})
    integrations = db.Column(db.JSON, default=lambda: {})
    license_code = db.Column(db.String(64), nullable=False, default='')
    license_expiry = db.Column(db.DateTime, nullable=True)
    language = db.Column(db.String(8), nullable=False, default='it')
    theme = db.Column(db.String(20), nullable=False, default='default')
    
    # Relazione con consulente (per dealer)
    consultant_id = db.Column(db.Integer, db.ForeignKey('consultant.id'), nullable=True)
    consultant = db.relationship('Consultant', backref='user_account', foreign_keys=[consultant_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'
    
    def is_dealer(self):
        return self.role == 'dealer'
    
    def is_viewer(self):
        return self.role == 'viewer'
    
    def get_consultant(self):
        """Ogni utente ha un consulente associato"""
        return self.consultant
    
    def has_permission(self, permission):
        """Sistema di permessi granulare"""
        role_permissions = {
            'admin': [
                'manage_users', 'manage_consultants', 'manage_appointments',
                'view_reports', 'system_access', 'api_access', 'export_data'
            ],
            'dealer': [
                'view_own_stats', 'edit_own_profile', 'view_own_appointments',
                'mobile_dashboard'
            ],
            'viewer': [
                'view_reports', 'view_stats'
            ]
        }
        
        return permission in role_permissions.get(self.role, [])
    
    def get_accessible_appointments(self):
        """Appuntamenti accessibili all'utente"""
        from models.appointment import Appointment
        
        if self.is_admin():
            return Appointment.query.all()
        elif self.consultant:  # Ogni utente dovrebbe avere un consulente
            return self.consultant.appointments
        return []
    
    def get_dashboard_data(self):
        """Dati per la dashboard personalizzata per ruolo"""
        if self.is_admin():
            return self._get_admin_dashboard_data()
        elif self.consultant:  # Tutti gli utenti ora hanno un consulente
            return self._get_consultant_dashboard_data()
        else:
            return {}
    
    def _get_admin_dashboard_data(self):
        from models.appointment import Appointment
        from models.consultant import Consultant
        
        all_appointments = Appointment.query.all()
        sold_appointments = [a for a in all_appointments if a.venduto]
        
        return {
            'total_appointments': len(all_appointments),
            'total_consultants': Consultant.query.count(),
            'total_users': User.query.count(),
            'sold_appointments': len(sold_appointments),
            'recent_appointments': Appointment.query.order_by(Appointment.data_appuntamento.desc()).limit(8).all()
        }
    
    def _get_consultant_dashboard_data(self):  # Rinominato da _get_dealer_dashboard_data
        if not self.consultant:
            return {}
        
        appointments = self.consultant.appointments
        return {
            'total_appointments': len(appointments),
            'sold_appointments': len([a for a in appointments if a.venduto]),
            'monthly_stats': self._calculate_monthly_stats(appointments),
            'recent_appointments': sorted(appointments, key=lambda x: x.data_appuntamento, reverse=True)[:5]
        }
    
    def _calculate_monthly_stats(self, appointments):
        """Calcola statistiche mensili per dealer"""
        from datetime import datetime, timedelta
        from calendar import monthrange
        import calendar
        
        now = datetime.now()
        
        # Statistiche per questo mese
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        monthly_appointments = [a for a in appointments if a.data_appuntamento >= month_start]
        
        # Statistiche per gli ultimi 3 mesi
        months_data = []
        for i in range(3):
            if i == 0:
                # Mese corrente
                start_date = month_start
                end_date = now
                month_name = calendar.month_name[now.month]
            else:
                # Mesi precedenti
                year = now.year
                month = now.month - i
                if month <= 0:
                    month += 12
                    year -= 1
                
                start_date = datetime(year, month, 1)
                _, last_day = monthrange(year, month)
                end_date = datetime(year, month, last_day, 23, 59, 59)
                month_name = calendar.month_name[month]
            
            month_appointments = [a for a in appointments if start_date <= a.data_appuntamento <= end_date]
            
            months_data.append({
                'month': month_name,
                'total': len(month_appointments),
                'sold': len([a for a in month_appointments if a.venduto]),
                'assistenza': len([a for a in month_appointments if a.tipologia == 'Assistenza']),
                'dimostrazione': len([a for a in month_appointments if a.tipologia == 'Dimostrazione'])
            })
        
        # Target mensile (esempio: 20 appuntamenti al mese)
        monthly_target = 20
        current_progress = (len(monthly_appointments) / monthly_target * 100) if monthly_target > 0 else 0
        
        return {
            'total_this_month': len(monthly_appointments),
            'sold_this_month': len([a for a in monthly_appointments if a.venduto]),
            'assistenza_count': len([a for a in monthly_appointments if a.tipologia == 'Assistenza']),
            'dimostrazione_count': len([a for a in monthly_appointments if a.tipologia == 'Dimostrazione']),
            'monthly_target': monthly_target,
            'progress_percentage': min(100, current_progress),
            'months_comparison': months_data
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
