from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models.appointment import Appointment
from models.consultant import Consultant
from models.user import db
import logging

logger = logging.getLogger(__name__)

class AppointmentService:
    """Servizio dedicato alla gestione degli appuntamenti"""
    
    @staticmethod
    def create_appointment(data: Dict, user_id: int) -> Appointment:
        """Crea nuovo appuntamento con validazione completa"""
        
        # Validazione dati obbligatori
        required_fields = ['nome_cliente', 'numero_telefono', 'data_appuntamento']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Campo obbligatorio mancante: {field}")
        
        # Validazione e parsing date
        try:
            data_appuntamento = datetime.strptime(data['data_appuntamento'], '%Y-%m-%d')
            if data_appuntamento.date() < datetime.now().date() - timedelta(days=365):
                raise ValueError("Data appuntamento troppo vecchia")
                
            data_richiamo = None
            if data.get('data_richiamo'):
                data_richiamo = datetime.strptime(data['data_richiamo'], '%Y-%m-%d')
                if data_richiamo <= data_appuntamento:
                    raise ValueError("Data richiamo deve essere successiva alla data appuntamento")
                    
        except ValueError as e:
            raise ValueError(f"Errore formato data: {e}")
        
        # Validazione numero telefono
        phone = data['numero_telefono'].strip()
        if len(phone) < 8 or not any(c.isdigit() for c in phone):
            raise ValueError("Numero di telefono non valido")
        
        # Crea l'appuntamento
        appointment = Appointment(
            nome_cliente=data['nome_cliente'].strip(),
            indirizzo=data.get('indirizzo', '').strip(),
            numero_telefono=phone,
            note=data.get('note', '').strip(),
            tipologia=data.get('tipologia', 'primo_appuntamento'),
            stato=data.get('stato', 'concluso'),
            nominativi_raccolti=max(0, int(data.get('nominativi_raccolti', 0))),
            appuntamenti_personali=max(0, int(data.get('appuntamenti_personali', 0))),
            venduto=bool(data.get('venduto', False)),
            data_appuntamento=data_appuntamento,
            data_richiamo=data_richiamo
        )
        
        # Associa consulenti se specificati
        consultant_ids = data.get('consultant_ids', [])
        if consultant_ids:
            consultants = Consultant.query.filter(Consultant.id.in_(consultant_ids)).all()
            appointment.consultants = consultants
        
        try:
            db.session.add(appointment)
            db.session.flush()  # Per ottenere l'ID prima del commit
            
            # Se venduto, crea cliente e pianifica follow-up
            if appointment.venduto:
                from services.client_service import ClientService
                from services.followup_service import FollowUpService
                
                ClientService.create_from_appointment(appointment)
                FollowUpService.schedule_automatic_followups(appointment)
            
            db.session.commit()
            logger.info(f"Appuntamento {appointment.id} creato per {appointment.nome_cliente}")
            return appointment
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione appuntamento: {e}")
            raise
    
    @staticmethod
    def update_appointment(appointment_id: int, data: Dict, user_id: int) -> Appointment:
        """Aggiorna appuntamento esistente"""
        
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise ValueError("Appuntamento non trovato")
        
        # Salva stato precedente per confronto
        was_sold = appointment.venduto
        
        # Aggiorna campi modificabili
        updatable_fields = {
            'nome_cliente', 'indirizzo', 'numero_telefono', 'note', 
            'tipologia', 'stato', 'nominativi_raccolti', 'appuntamenti_personali'
        }
        
        for field in updatable_fields:
            if field in data and data[field] is not None:
                if field in ['nominativi_raccolti', 'appuntamenti_personali']:
                    setattr(appointment, field, max(0, int(data[field])))
                else:
                    setattr(appointment, field, str(data[field]).strip())
        
        # Gestione flag venduto
        if 'venduto' in data:
            appointment.venduto = bool(data['venduto'])
        
        # Aggiorna date se fornite
        if 'data_appuntamento' in data:
            try:
                appointment.data_appuntamento = datetime.strptime(data['data_appuntamento'], '%Y-%m-%d')
            except ValueError:
                raise ValueError("Formato data_appuntamento non valido")
        
        if 'data_richiamo' in data:
            if data['data_richiamo']:
                try:
                    appointment.data_richiamo = datetime.strptime(data['data_richiamo'], '%Y-%m-%d')
                except ValueError:
                    raise ValueError("Formato data_richiamo non valido")
            else:
                appointment.data_richiamo = None
        
        # Aggiorna consulenti associati
        if 'consultant_ids' in data:
            consultant_ids = data['consultant_ids']
            if consultant_ids:
                consultants = Consultant.query.filter(Consultant.id.in_(consultant_ids)).all()
                appointment.consultants = consultants
            else:
                appointment.consultants = []
        
        # Metadati aggiornamento
        appointment.updated_by = user_id
        appointment.updated_at = datetime.now()
        
        try:
            # Se è diventato venduto, crea cliente e follow-up
            if not was_sold and appointment.venduto:
                from services.client_service import ClientService
                from services.followup_service import FollowUpService
                
                ClientService.create_from_appointment(appointment)
                FollowUpService.schedule_automatic_followups(appointment)
            
            db.session.commit()
            logger.info(f"Appuntamento {appointment.id} aggiornato")
            return appointment
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore aggiornamento appuntamento {appointment_id}: {e}")
            raise
    
    @staticmethod
    def delete_appointment(appointment_id: int, user_id: int) -> bool:
        """Elimina appuntamento con controlli di sicurezza"""
        
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise ValueError("Appuntamento non trovato")
        
        try:
            # Elimina follow-up associati
            from models.followup import FollowUp
            FollowUp.query.filter_by(appointment_id=appointment_id).delete()
            
            # Log dell'eliminazione
            logger.info(f"Eliminazione appuntamento {appointment_id} ({appointment.nome_cliente}) da utente {user_id}")
            
            db.session.delete(appointment)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore eliminazione appuntamento {appointment_id}: {e}")
            raise
    
    @staticmethod
    def get_appointments_by_consultant(consultant_id: int, 
                                     date_from: Optional[datetime] = None,
                                     date_to: Optional[datetime] = None,
                                     limit: int = 100) -> List[Appointment]:
        """Recupera appuntamenti per consulente con filtri"""
        
        query = (Appointment.query
                .join(Appointment.consultants)
                .filter(Consultant.id == consultant_id))
        
        if date_from:
            query = query.filter(Appointment.data_appuntamento >= date_from)
        if date_to:
            query = query.filter(Appointment.data_appuntamento <= date_to)
        
        return (query.order_by(Appointment.data_appuntamento.desc())
                .limit(limit).all())
    
    @staticmethod
    def get_appointments_by_date_range(date_from: datetime, 
                                     date_to: datetime,
                                     consultant_id: Optional[int] = None) -> List[Appointment]:
        """Recupera appuntamenti in range di date"""
        
        query = Appointment.query.filter(
            Appointment.data_appuntamento >= date_from,
            Appointment.data_appuntamento <= date_to
        )
        
        if consultant_id:
            query = query.join(Appointment.consultants).filter(Consultant.id == consultant_id)
        
        return query.order_by(Appointment.data_appuntamento.asc()).all()
    
    @staticmethod
    def get_performance_metrics(consultant_id: Optional[int] = None, 
                              days: int = 30) -> Dict:
        """Calcola metriche di performance"""
        
        date_from = datetime.now() - timedelta(days=days)
        
        query = Appointment.query.filter(Appointment.data_appuntamento >= date_from)
        
        if consultant_id:
            query = query.join(Appointment.consultants).filter(Consultant.id == consultant_id)
        
        appointments = query.all()
        
        if not appointments:
            return {
                'total_appointments': 0,
                'sold_appointments': 0,
                'conversion_rate': 0,
                'avg_nominativi': 0,
                'avg_appuntamenti_personali': 0,
                'total_nominativi': 0,
                'total_appuntamenti_personali': 0
            }
        
        total = len(appointments)
        sold = len([a for a in appointments if a.venduto])
        total_nominativi = sum(a.nominativi_raccolti for a in appointments)
        total_personali = sum(a.appuntamenti_personali for a in appointments)
        
        return {
            'total_appointments': total,
            'sold_appointments': sold,
            'conversion_rate': round((sold / total * 100) if total > 0 else 0, 2),
            'avg_nominativi': round(total_nominativi / total, 2) if total > 0 else 0,
            'avg_appuntamenti_personali': round(total_personali / total, 2) if total > 0 else 0,
            'total_nominativi': total_nominativi,
            'total_appuntamenti_personali': total_personali
        }
    
    @staticmethod
    def search_appointments(query: str, limit: int = 50) -> List[Appointment]:
        """Ricerca appuntamenti per nome cliente o telefono"""
        
        search_pattern = f"%{query.strip()}%"
        
        return (Appointment.query
                .filter(
                    db.or_(
                        Appointment.nome_cliente.ilike(search_pattern),
                        Appointment.numero_telefono.ilike(search_pattern)
                    )
                )
                .order_by(Appointment.data_appuntamento.desc())
                .limit(limit)
                .all())
