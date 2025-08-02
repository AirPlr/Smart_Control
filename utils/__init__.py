"""
Utilities e helper functions per l'applicazione
"""

import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

class SecurityUtils:
    """Utilities per sicurezza"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Genera token sicuro per sessioni o API"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """Hash sicuro della password con salt"""
        if not salt:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterazioni
        )
        
        return password_hash.hex(), salt
    
    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        """Verifica password contro hash"""
        computed_hash, _ = SecurityUtils.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, password_hash)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitizza input utente"""
        if not isinstance(text, str):
            return ""
        
        # Rimuovi caratteri pericolosi
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Tronca se troppo lungo
        return text.strip()[:max_length]

class ValidationUtils:
    """Utilities per validazione dati"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valida formato email"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Valida numero di telefono"""
        if not phone:
            return False
        
        # Rimuovi spazi e caratteri speciali
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Pattern per numeri italiani e internazionali
        patterns = [
            r'^\+39\d{9,10}$',  # Italiano con prefisso
            r'^\d{10}$',        # Italiano senza prefisso
            r'^\+\d{10,15}$'    # Internazionale
        ]
        
        return any(re.match(pattern, clean_phone) for pattern in patterns)
    
    @staticmethod
    def validate_date_string(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
        """Valida stringa data"""
        try:
            datetime.strptime(date_str, format_str)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> List[str]:
        """Valida campi richiesti, ritorna lista errori"""
        errors = []
        for field in required_fields:
            if not data.get(field) or (isinstance(data[field], str) and not data[field].strip()):
                errors.append(f"Campo richiesto: {field}")
        return errors

class DateUtils:
    """Utilities per gestione date"""
    
    @staticmethod
    def format_date(date: datetime, format_str: str = '%d/%m/%Y') -> str:
        """Formatta data per visualizzazione"""
        if not date:
            return ""
        return date.strftime(format_str)
    
    @staticmethod
    def format_datetime(dt: datetime, format_str: str = '%d/%m/%Y alle %H:%M') -> str:
        """Formatta datetime per visualizzazione"""
        if not dt:
            return ""
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_date(date_str: str, format_str: str = '%Y-%m-%d') -> Optional[datetime]:
        """Parse stringa data in datetime"""
        try:
            return datetime.strptime(date_str, format_str)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def get_month_range(year: int, month: int) -> tuple:
        """Ottieni primo e ultimo giorno del mese"""
        first_day = datetime(year, month, 1)
        
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        return first_day, last_day
    
    @staticmethod
    def get_week_range(date: datetime) -> tuple:
        """Ottieni primo e ultimo giorno della settimana"""
        days_since_monday = date.weekday()
        monday = date - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return monday, sunday

class StringUtils:
    """Utilities per manipolazione stringhe"""
    
    @staticmethod
    def slugify(text: str) -> str:
        """Converti testo in slug URL-friendly"""
        if not text:
            return ""
        
        # Converti in minuscolo e sostituisci spazi
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        
        return text.strip('-')
    
    @staticmethod
    def truncate(text: str, max_length: int = 50, suffix: str = '...') -> str:
        """Tronca testo con suffisso"""
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def capitalize_words(text: str) -> str:
        """Capitalizza ogni parola"""
        if not text:
            return ""
        
        return ' '.join(word.capitalize() for word in text.split())
    
    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """Pulisce e normalizza numero di telefono"""
        if not phone:
            return ""
        
        # Rimuovi tutti i caratteri non numerici eccetto +
        clean = re.sub(r'[^\d+]', '', phone.strip())
        
        # Aggiungi prefisso italiano se necessario
        if clean.startswith('3') and len(clean) == 10:
            clean = '+39' + clean
        elif clean.startswith('39') and len(clean) == 12:
            clean = '+' + clean
        
        return clean

class PaginationHelper:
    """Helper per paginazione"""
    
    def __init__(self, query, page: int = 1, per_page: int = 20):
        self.query = query
        self.page = max(1, page)
        self.per_page = min(100, max(1, per_page))  # Limita tra 1 e 100
        
        self.total = query.count()
        self.pages = (self.total - 1) // self.per_page + 1 if self.total > 0 else 1
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        
        offset = (self.page - 1) * self.per_page
        self.items = query.offset(offset).limit(self.per_page).all()
    
    def get_page_info(self) -> Dict:
        """Informazioni per template"""
        return {
            'page': self.page,
            'pages': self.pages,
            'per_page': self.per_page,
            'total': self.total,
            'has_prev': self.has_prev,
            'has_next': self.has_next,
            'prev_num': self.page - 1 if self.has_prev else None,
            'next_num': self.page + 1 if self.has_next else None
        }

class FlashMessageHelper:
    """Helper per messaggi flash categorizzati"""
    
    # Tipi di messaggio Bootstrap
    SUCCESS = 'success'
    ERROR = 'danger'
    WARNING = 'warning'
    INFO = 'info'
    
    @staticmethod
    def format_errors(errors: List[str]) -> str:
        """Formatta lista errori in messaggio"""
        if not errors:
            return ""
        
        if len(errors) == 1:
            return errors[0]
        
        return "Errori riscontrati:\n" + "\n".join(f"• {error}" for error in errors)

class LoggingHelper:
    """Helper per logging strutturato"""
    
    @staticmethod
    def log_user_action(user_id: int, action: str, details: Dict = None):
        """Log azione utente"""
        log_data = {
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        logger.info(f"User action: {action}", extra=log_data)
    
    @staticmethod
    def log_error(error: Exception, context: Dict = None):
        """Log errore con contesto"""
        log_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        logger.error(f"Error: {error}", extra=log_data, exc_info=True)

class ConfigHelper:
    """Helper per configurazione applicazione"""
    
    DEFAULT_CONFIG = {
        'COMPANY_NAME': 'AppointmentCRM',
        'DEFAULT_FOLLOWUP_DAYS': 7,
        'MAX_APPOINTMENTS_PER_DAY': 10,
        'EMAIL_NOTIFICATIONS': True,
        'SMS_NOTIFICATIONS': False,
        'THEME': 'blue',
        'ITEMS_PER_PAGE': 20,
        'SESSION_TIMEOUT': 3600,  # 1 ora
        'MAX_LOGIN_ATTEMPTS': 5,
        'BACKUP_RETENTION_DAYS': 30
    }
    
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """Ottieni valore configurazione"""
        return ConfigHelper.DEFAULT_CONFIG.get(key, default)
    
    @staticmethod
    def validate_config(config: Dict) -> List[str]:
        """Valida configurazione"""
        errors = []
        
        # Validazioni specifiche
        if 'DEFAULT_FOLLOWUP_DAYS' in config:
            try:
                days = int(config['DEFAULT_FOLLOWUP_DAYS'])
                if days < 1 or days > 365:
                    errors.append("DEFAULT_FOLLOWUP_DAYS deve essere tra 1 e 365")
            except (ValueError, TypeError):
                errors.append("DEFAULT_FOLLOWUP_DAYS deve essere un numero")
        
        if 'MAX_APPOINTMENTS_PER_DAY' in config:
            try:
                max_appts = int(config['MAX_APPOINTMENTS_PER_DAY'])
                if max_appts < 1 or max_appts > 100:
                    errors.append("MAX_APPOINTMENTS_PER_DAY deve essere tra 1 e 100")
            except (ValueError, TypeError):
                errors.append("MAX_APPOINTMENTS_PER_DAY deve essere un numero")
        
        return errors
