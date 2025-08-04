from datetime import datetime
from typing import List, Dict, Optional
from models.client import Client
from models.appointment import Appointment
from models.user import db
import logging
import re

logger = logging.getLogger(__name__)

class ClientService:
    """Servizio per gestione clienti"""
    
    @staticmethod
    def create_from_appointment(appointment: Appointment) -> Client:
        """Crea cliente da appuntamento venduto"""
        
        if not appointment.venduto:
            raise ValueError("Cliente può essere creato solo da appuntamenti venduti")
        
        # Normalizza numero di telefono
        phone = ClientService._normalize_phone(appointment.numero_telefono)
        
        # Verifica se cliente esiste già
        existing_client = Client.query.filter_by(phone=phone).first()
        if existing_client:
            # Aggiorna informazioni se necessario
            if not existing_client.name or len(appointment.nome_cliente) > len(existing_client.name):
                existing_client.name = appointment.nome_cliente
            if not existing_client.address and appointment.indirizzo:
                existing_client.address = appointment.indirizzo
            
            db.session.commit()
            logger.info(f"Cliente {existing_client.id} aggiornato da appuntamento {appointment.id}")
            return existing_client
        
        # Crea nuovo cliente
        client = Client(
            name=appointment.nome_cliente.strip(),
            phone=phone,
            address=appointment.indirizzo.strip() if appointment.indirizzo else '',
            acquisition_date=appointment.data_appuntamento,
            source='appointment',
            status='active',
            notes=f"Cliente acquisito da appuntamento del {appointment.data_appuntamento.strftime('%d/%m/%Y')}"
        )
        
        try:
            db.session.add(client)
            db.session.commit()
            logger.info(f"Cliente {client.id} creato da appuntamento {appointment.id}")
            return client
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione cliente da appuntamento {appointment.id}: {e}")
            raise
    
    @staticmethod
    def create_client(data: Dict, user_id: int) -> Client:
        """Crea cliente manualmente"""
        
        # Validazione dati richiesti
        required_fields = ['name', 'phone']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Campo richiesto: {field}")
        
        # Normalizza e valida telefono
        phone = ClientService._normalize_phone(data['phone'])
        if not ClientService._validate_phone(phone):
            raise ValueError("Numero di telefono non valido")
        
        # Verifica se cliente esiste già
        existing_client = Client.query.filter_by(phone=phone).first()
        if existing_client:
            raise ValueError(f"Cliente con telefono {phone} già esistente")
        
        client = Client(
            name=data['name'].strip(),
            phone=phone,
            email=data.get('email', '').strip(),
            address=data.get('address', '').strip(),
            acquisition_date=datetime.now(),
            source=data.get('source', 'manual'),
            status='active',
            notes=data.get('notes', '').strip(),
            created_by=user_id
        )
        
        try:
            db.session.add(client)
            db.session.commit()
            logger.info(f"Cliente {client.id} creato manualmente da utente {user_id}")
            return client
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione cliente manuale: {e}")
            raise
    
    @staticmethod
    def update_client(client_id: int, data: Dict, user_id: int) -> Client:
        """Aggiorna cliente esistente"""
        
        client = Client.query.get(client_id)
        if not client:
            raise ValueError("Cliente non trovato")
        
        # Campi aggiornabili
        updatable_fields = ['name', 'email', 'address', 'status', 'notes']
        
        for field in updatable_fields:
            if field in data and data[field] is not None:
                setattr(client, field, str(data[field]).strip())
        
        # Aggiorna telefono con validazione
        if 'phone' in data:
            new_phone = ClientService._normalize_phone(data['phone'])
            if not ClientService._validate_phone(new_phone):
                raise ValueError("Numero di telefono non valido")
            
            # Verifica se nuovo telefono è già in uso
            existing = Client.query.filter(
                Client.numero_telefono == new_phone,
                Client.id != client_id
            ).first()
            if existing:
                raise ValueError(f"Telefono {new_phone} già utilizzato da altro cliente")
            
            client.numero_telefono = new_phone
        
        client.updated_at = datetime.now()
        client.updated_by = user_id
        
        try:
            db.session.commit()
            logger.info(f"Cliente {client_id} aggiornato da utente {user_id}")
            return client
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore aggiornamento cliente {client_id}: {e}")
            raise
    
    @staticmethod
    def get_client_history(client_id: int) -> Dict:
        """Storico completo attività cliente"""
        
        client = Client.query.get(client_id)
        if not client:
            raise ValueError("Cliente non trovato")
        
        # Trova tutti gli appuntamenti correlati per telefono
        appointments = Appointment.query.filter_by(
            numero_telefono=client.numero_telefono
        ).order_by(Appointment.data_appuntamento.desc()).all()
        
        # Follow-up correlati
        from models.followup import FollowUp
        followups = []
        for appointment in appointments:
            appointment_followups = FollowUp.query.filter_by(
                appointment_id=appointment.id
            ).order_by(FollowUp.due_date.desc()).all()
            followups.extend(appointment_followups)
        
        # Statistiche
        stats = {
            'total_appointments': len(appointments),
            'sold_appointments': len([a for a in appointments if a.venduto]),
            'total_followups': len(followups),
            'completed_followups': len([f for f in followups if f.completed]),
            'first_appointment': appointments[-1].data_appuntamento if appointments else None,
            'last_appointment': appointments[0].data_appuntamento if appointments else None,
            'conversion_rate': (
                len([a for a in appointments if a.venduto]) / len(appointments) * 100
                if appointments else 0
            )
        }
        
        return {
            'client': client.to_dict(),
            'appointments': [a.to_dict() for a in appointments],
            'followups': [f.to_dict() if hasattr(f, 'to_dict') else {
                'id': f.id,
                'title': f.title,
                'due_date': f.due_date.isoformat(),
                'completed': f.completed,
                'priority': f.priority
            } for f in followups],
            'stats': stats
        }
    
    @staticmethod
    def search_clients(query: str, limit: int = 50) -> List[Client]:
        """Ricerca clienti per nome, telefono o email"""
        
        search_pattern = f"%{query.strip()}%"
        
        return Client.query.filter(
            db.or_(
                Client.name.ilike(search_pattern),
                Client.numero_telefono.ilike(search_pattern),
                Client.email.ilike(search_pattern)
            )
        ).order_by(Client.name.asc()).limit(limit).all()
    
    @staticmethod
    def get_clients_by_status(status: str = 'active') -> List[Client]:
        """Recupera clienti per status"""
        
        return Client.query.filter_by(status=status).order_by(
            Client.acquisition_date.desc()
        ).all()
    
    @staticmethod
    def get_client_statistics(days: int = 30) -> Dict:
        """Statistiche clienti"""
        
        from datetime import timedelta
        date_from = datetime.now() - timedelta(days=days)
        
        total_clients = Client.query.count()
        new_clients = Client.query.filter(Client.acquisition_date >= date_from).count()
        active_clients = Client.query.filter_by(status='active').count()
        
        # Clienti con appuntamenti recenti
        recent_appointments = Appointment.query.filter(
            Appointment.data_appuntamento >= date_from,
            Appointment.venduto == True
        ).all()
        
        clients_with_recent_sales = len(set(a.numero_telefono for a in recent_appointments))
        
        return {
            'total_clients': total_clients,
            'new_clients_period': new_clients,
            'active_clients': active_clients,
            'clients_with_recent_sales': clients_with_recent_sales,
            'retention_rate': (
                clients_with_recent_sales / total_clients * 100
                if total_clients > 0 else 0
            )
        }
    
    @staticmethod
    def delete_client(client_id: int, user_id: int) -> bool:
        """Elimina cliente (soft delete)"""
        
        client = Client.query.get(client_id)
        if not client:
            raise ValueError("Cliente non trovato")
        
        # Soft delete - marca come inattivo
        client.status = 'deleted'
        client.updated_at = datetime.now()
        client.updated_by = user_id
        client.notes = (client.notes or '') + f"\n\nEliminato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
        
        try:
            db.session.commit()
            logger.info(f"Cliente {client_id} eliminato (soft delete) da utente {user_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore eliminazione cliente {client_id}: {e}")
            raise
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalizza numero di telefono"""
        if not phone:
            return ''
        
        # Rimuovi spazi, trattini e altri caratteri
        normalized = re.sub(r'[^\d+]', '', phone.strip())
        
        # Gestisci prefisso italiano
        if normalized.startswith('00393'):
            normalized = '+39' + normalized[5:]
        elif normalized.startswith('0039'):
            normalized = '+39' + normalized[4:]
        elif normalized.startswith('393'):
            normalized = '+39' + normalized[3:]
        elif normalized.startswith('39') and len(normalized) > 5:
            normalized = '+39' + normalized[2:]
        elif normalized.startswith('3') and len(normalized) == 10:
            normalized = '+39' + normalized
        
        return normalized
    
    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """Valida formato numero di telefono"""
        if not phone:
            return False
        
        # Pattern per numeri italiani e internazionali
        patterns = [
            r'^\+39\d{9,10}$',  # Italiano
            r'^\+\d{10,15}$',   # Internazionale
            r'^\d{8,15}$'       # Senza prefisso
        ]
        
        return any(re.match(pattern, phone) for pattern in patterns)
