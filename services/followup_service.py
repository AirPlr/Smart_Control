from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models.followup import FollowUp
from models.appointment import Appointment
from models.user import db
import logging

logger = logging.getLogger(__name__)

class FollowUpService:
    """Servizio per gestione follow-up automatici e manuali"""
    
    # Configurazione follow-up automatici
    DEFAULT_FOLLOWUP_SCHEDULE = [
        {'days': 7, 'type': 'first_check', 'priority': 'high', 'title': 'Primo controllo post-vendita'},
        {'days': 30, 'type': 'satisfaction_check', 'priority': 'medium', 'title': 'Controllo soddisfazione'},
        {'days': 90, 'type': 'renewal_opportunity', 'priority': 'medium', 'title': 'Opportunità rinnovo'},
        {'days': 180, 'type': 'long_term_check', 'priority': 'low', 'title': 'Controllo lungo termine'}
    ]
    
    @staticmethod
    def schedule_automatic_followups(appointment: Appointment) -> List[FollowUp]:
        """Pianifica follow-up automatici per appuntamento venduto"""
        
        if not appointment.venduto:
            logger.warning(f"Tentativo di pianificare follow-up per appuntamento non venduto: {appointment.id}")
            return []
        
        created_followups = []
        base_date = appointment.data_appuntamento
        
        for schedule in FollowUpService.DEFAULT_FOLLOWUP_SCHEDULE:
            due_date = base_date + timedelta(days=schedule['days'])
            
            # Non creare follow-up per date già passate (oltre 1 settimana)
            if due_date < datetime.now() - timedelta(days=7):
                continue
            
            # Verifica se esiste già un follow-up simile
            existing = FollowUp.query.filter_by(
                appointment_id=appointment.id,
                followup_type=schedule['type']
            ).first()
            
            if existing:
                continue
            
            followup = FollowUp(
                appointment_id=appointment.id,
                title=schedule['title'],
                due_date=due_date,
                followup_type=schedule['type'],
                priority=schedule['priority'],
                status='pending',
                notes=f"Follow-up automatico per vendita del {appointment.data_appuntamento.strftime('%d/%m/%Y')}.\nCliente: {appointment.nome_cliente}\nTelefono: {appointment.numero_telefono}",
                created_at=datetime.now()
            )
            
            db.session.add(followup)
            created_followups.append(followup)
        
        try:
            db.session.commit()
            logger.info(f"Creati {len(created_followups)} follow-up automatici per appuntamento {appointment.id}")
            return created_followups
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione follow-up automatici: {e}")
            raise
    
    @staticmethod
    def create_manual_followup(appointment_id: int, data: Dict, user_id: int) -> FollowUp:
        """Crea follow-up manuale"""
        
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise ValueError("Appuntamento non trovato")
        
        # Validazione dati richiesti
        required_fields = ['title', 'due_date']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Campo richiesto: {field}")
        
        try:
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
            if due_date.date() < datetime.now().date():
                raise ValueError("Data scadenza non può essere nel passato")
        except ValueError as e:
            raise ValueError(f"Formato data non valido: {e}")
        
        followup = FollowUp(
            appointment_id=appointment_id,
            title=data['title'].strip(),
            due_date=due_date,
            followup_type=data.get('followup_type', 'manual'),
            priority=data.get('priority', 'medium'),
            status='pending',
            notes=data.get('notes', '').strip(),
            created_by=user_id,
            created_at=datetime.now()
        )
        
        try:
            db.session.add(followup)
            db.session.commit()
            logger.info(f"Follow-up manuale {followup.id} creato per appuntamento {appointment_id}")
            return followup
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione follow-up manuale: {e}")
            raise
    
    @staticmethod
    def get_pending_followups(consultant_id: Optional[int] = None, 
                            priority: Optional[str] = None,
                            overdue_only: bool = False) -> List[FollowUp]:
        """Recupera follow-up pendenti con filtri"""
        
        query = FollowUp.query.filter_by(completed=False)
        
        if consultant_id:
            query = (query.join(FollowUp.appointment)
                    .join(Appointment.consultants)
                    .filter(Consultant.id == consultant_id))
        
        if priority:
            query = query.filter(FollowUp.priority == priority)
        
        if overdue_only:
            query = query.filter(FollowUp.due_date < datetime.now())
        
        return query.order_by(
            FollowUp.priority == 'high',
            FollowUp.due_date.asc()
        ).all()
    
    @staticmethod
    def complete_followup(followup_id: int, completion_notes: str, user_id: int) -> FollowUp:
        """Completa follow-up con note"""
        
        followup = FollowUp.query.get(followup_id)
        if not followup:
            raise ValueError("Follow-up non trovato")
        
        if followup.completed:
            raise ValueError("Follow-up già completato")
        
        followup.completed = True
        followup.completed_date = datetime.now()
        followup.completed_by = user_id
        followup.completion_notes = completion_notes.strip() if completion_notes else ""
        
        # Aggiorna le note principali
        completion_info = f"\n\n--- COMPLETATO il {datetime.now().strftime('%d/%m/%Y alle %H:%M')} ---\n{completion_notes}"
        followup.notes = (followup.notes or "") + completion_info
        
        try:
            db.session.commit()
            logger.info(f"Follow-up {followup_id} completato da utente {user_id}")
            return followup
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore completamento follow-up {followup_id}: {e}")
            raise
    
    @staticmethod
    def postpone_followup(followup_id: int, new_due_date: datetime, reason: str, user_id: int) -> FollowUp:
        """Posticipa follow-up con motivo"""
        
        followup = FollowUp.query.get(followup_id)
        if not followup:
            raise ValueError("Follow-up non trovato")
        
        if followup.completed:
            raise ValueError("Non è possibile posticipare un follow-up completato")
        
        if new_due_date <= datetime.now():
            raise ValueError("La nuova data deve essere futura")
        
        old_date = followup.due_date
        followup.due_date = new_due_date
        
        # Aggiorna note con informazioni del posticipo
        postpone_info = f"\n\n--- POSTICIPATO il {datetime.now().strftime('%d/%m/%Y alle %H:%M')} ---\nDa: {old_date.strftime('%d/%m/%Y')}\nA: {new_due_date.strftime('%d/%m/%Y')}\nMotivo: {reason}"
        followup.notes = (followup.notes or "") + postpone_info
        
        try:
            db.session.commit()
            logger.info(f"Follow-up {followup_id} posticipato da {old_date} a {new_due_date}")
            return followup
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore posticipo follow-up {followup_id}: {e}")
            raise
    
    @staticmethod
    def delete_followup(followup_id: int, user_id: int) -> bool:
        """Elimina follow-up"""
        
        followup = FollowUp.query.get(followup_id)
        if not followup:
            raise ValueError("Follow-up non trovato")
        
        try:
            logger.info(f"Eliminazione follow-up {followup_id} ({followup.title}) da utente {user_id}")
            db.session.delete(followup)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore eliminazione follow-up {followup_id}: {e}")
            raise
    
    @staticmethod
    def get_followup_statistics(consultant_id: Optional[int] = None, days: int = 30) -> Dict:
        """Statistiche follow-up"""
        
        date_from = datetime.now() - timedelta(days=days)
        
        query = FollowUp.query.filter(FollowUp.created_at >= date_from)
        
        if consultant_id:
            query = (query.join(FollowUp.appointment)
                    .join(Appointment.consultants)
                    .filter(Consultant.id == consultant_id))
        
        all_followups = query.all()
        
        stats = {
            'total_followups': len(all_followups),
            'completed_followups': len([f for f in all_followups if f.completed]),
            'pending_followups': len([f for f in all_followups if not f.completed]),
            'overdue_followups': len([f for f in all_followups if not f.completed and f.due_date < datetime.now()]),
            'high_priority': len([f for f in all_followups if f.priority == 'high']),
            'medium_priority': len([f for f in all_followups if f.priority == 'medium']),
            'low_priority': len([f for f in all_followups if f.priority == 'low'])
        }
        
        # Calcola tasso completamento
        stats['completion_rate'] = (
            round(stats['completed_followups'] / stats['total_followups'] * 100, 2)
            if stats['total_followups'] > 0 else 0
        )
        
        return stats
    
    @staticmethod
    def get_upcoming_followups(days_ahead: int = 7, consultant_id: Optional[int] = None) -> List[FollowUp]:
        """Follow-up in scadenza nei prossimi giorni"""
        
        today = datetime.now()
        future_date = today + timedelta(days=days_ahead)
        
        query = FollowUp.query.filter(
            FollowUp.completed == False,
            FollowUp.due_date >= today,
            FollowUp.due_date <= future_date
        )
        
        if consultant_id:
            query = (query.join(FollowUp.appointment)
                    .join(Appointment.consultants)
                    .filter(Consultant.id == consultant_id))
        
        return query.order_by(FollowUp.due_date.asc()).all()
