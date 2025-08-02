"""
Servizi business logic per l'applicazione AppointmentCRM
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from models.appointment import Appointment
from models.consultant import Consultant
from models.client import Client
from models.followup import FollowUp
from models.user import db
import logging

logger = logging.getLogger(__name__)

class AppointmentService:
    """Servizio per gestione appuntamenti"""
    
    @staticmethod
    def create_appointment(data: Dict) -> Appointment:
        """Crea nuovo appuntamento con validazione"""
        
        # Validazione dati richiesti
        required_fields = ['nome_cliente', 'numero_telefono', 'data_appuntamento']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Campo richiesto mancante: {field}")
        
        # Parsing date
        try:
            data_appuntamento = datetime.strptime(data['data_appuntamento'], '%Y-%m-%d')
            data_richiamo = None
            if data.get('data_richiamo'):
                data_richiamo = datetime.strptime(data['data_richiamo'], '%Y-%m-%d')
        except ValueError as e:
            raise ValueError(f"Formato data non valido: {e}")
        
        # Crea appuntamento
        appointment = Appointment(
            nome_cliente=data['nome_cliente'],
            indirizzo=data.get('indirizzo', ''),
            numero_telefono=data['numero_telefono'],
            note=data.get('note', ''),
            tipologia=data.get('tipologia', 'primo_appuntamento'),
            stato=data.get('stato', 'concluso'),
            nominativi_raccolti=data.get('nominativi_raccolti', 0),
            appuntamenti_personali=data.get('appuntamenti_personali', 0),
            venduto=bool(data.get('venduto', False)),
            data_appuntamento=data_appuntamento,
            data_richiamo=data_richiamo
        )
        
        # Associa consulenti
        consultant_ids = data.get('consultant_ids', [])
        for cid in consultant_ids:
            consultant = Consultant.query.get(cid)
            if consultant:
                appointment.consultants.append(consultant)
        
        db.session.add(appointment)
        db.session.commit()
        
        # Pianifica follow-up automatici se venduto
        if appointment.venduto:
            FollowUpService.schedule_automatic_followups(appointment)
        
        logger.info(f"Appuntamento creato: {appointment.id} per {appointment.nome_cliente}")
        return appointment
    
    @staticmethod
    def get_appointments_by_consultant(consultant_id: int, 
                                     date_from: Optional[datetime] = None,
                                     date_to: Optional[datetime] = None) -> List[Appointment]:
        """Ottieni appuntamenti per consulente con filtri opzionali"""
        
        query = Appointment.query.join(Appointment.consultants).filter(
            Consultant.id == consultant_id
        )
        
        if date_from:
            query = query.filter(Appointment.data_appuntamento >= date_from)
        if date_to:
            query = query.filter(Appointment.data_appuntamento <= date_to)
        
        return query.order_by(Appointment.data_appuntamento.desc()).all()
    
    @staticmethod
    def get_performance_stats(consultant_id: Optional[int] = None, 
                            days: int = 30) -> Dict:
        """Calcola statistiche performance"""
        
        date_from = datetime.now() - timedelta(days=days)
        
        query = Appointment.query.filter(Appointment.data_appuntamento >= date_from)
        
        if consultant_id:
            query = query.join(Appointment.consultants).filter(Consultant.id == consultant_id)
        
        appointments = query.all()
        
        total = len(appointments)
        sold = len([a for a in appointments if a.venduto])
        conversion_rate = (sold / total * 100) if total > 0 else 0
        
        return {
            'total_appointments': total,
            'sold_appointments': sold,
            'conversion_rate': round(conversion_rate, 2),
            'avg_nominativi': sum(a.nominativi_raccolti for a in appointments) / total if total > 0 else 0,
            'avg_appuntamenti_personali': sum(a.appuntamenti_personali for a in appointments) / total if total > 0 else 0
        }

class FollowUpService:
    """Servizio per gestione follow-up"""
    
    @staticmethod
    def schedule_automatic_followups(appointment: Appointment):
        """Pianifica follow-up automatici per appuntamento venduto"""
        
        if not appointment.venduto:
            return
        
        # Follow-up a 7, 30 e 90 giorni
        followup_schedules = [
            {'days': 7, 'type': 'first_check', 'priority': 'high'},
            {'days': 30, 'type': 'satisfaction_check', 'priority': 'medium'},
            {'days': 90, 'type': 'renewal_opportunity', 'priority': 'medium'}
        ]
        
        base_date = appointment.data_appuntamento
        
        for schedule in followup_schedules:
            due_date = base_date + timedelta(days=schedule['days'])
            
            followup = FollowUp(
                appointment_id=appointment.id,
                due_date=due_date,
                followup_type=schedule['type'],
                priority=schedule['priority'],
                status='pending',
                notes=f"Follow-up automatico per vendita del {appointment.data_appuntamento.strftime('%d/%m/%Y')}"
            )
            
            db.session.add(followup)
        
        db.session.commit()
        logger.info(f"Follow-up automatici pianificati per appuntamento {appointment.id}")
    
    @staticmethod
    def get_pending_followups(consultant_id: Optional[int] = None) -> List[FollowUp]:
        """Ottieni follow-up pendenti"""
        
        query = FollowUp.query.filter_by(completed=False)
        
        if consultant_id:
            query = query.join(FollowUp.appointment).join(Appointment.consultants).filter(
                Consultant.id == consultant_id
            )
        
        return query.filter(FollowUp.due_date <= datetime.now()).order_by(
            FollowUp.priority.desc(), FollowUp.due_date.asc()
        ).all()
    
    @staticmethod
    def complete_followup(followup_id: int, notes: str = None) -> FollowUp:
        """Completa follow-up"""
        
        followup = FollowUp.query.get(followup_id)
        if not followup:
            raise ValueError("Follow-up non trovato")
        
        followup.completed = True
        followup.completed_date = datetime.now()
        if notes:
            followup.notes += f"\n\nCompletato il {datetime.now().strftime('%d/%m/%Y %H:%M')}: {notes}"
        
        db.session.commit()
        logger.info(f"Follow-up {followup_id} completato")
        return followup

class ReportService:
    """Servizio per report e analisi"""
    
    @staticmethod
    def get_monthly_performance(consultant_id: Optional[int] = None, 
                              months: int = 6) -> Dict:
        """Report performance mensili"""
        
        result = []
        today = datetime.now()
        
        for i in range(months):
            month_start = today.replace(day=1) - timedelta(days=i*30)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            query = Appointment.query.filter(
                Appointment.data_appuntamento >= month_start,
                Appointment.data_appuntamento <= month_end
            )
            
            if consultant_id:
                query = query.join(Appointment.consultants).filter(Consultant.id == consultant_id)
            
            appointments = query.all()
            
            month_data = {
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'total_appointments': len(appointments),
                'sold_appointments': len([a for a in appointments if a.venduto]),
                'total_nominativi': sum(a.nominativi_raccolti for a in appointments),
                'total_personali': sum(a.appuntamenti_personali for a in appointments)
            }
            
            month_data['conversion_rate'] = (
                month_data['sold_appointments'] / month_data['total_appointments'] * 100
                if month_data['total_appointments'] > 0 else 0
            )
            
            result.append(month_data)
        
        return {'months': result[::-1]}  # Ordine cronologico
    
    @staticmethod
    def get_consultant_ranking(days: int = 30) -> List[Dict]:
        """Classifica consulenti per performance"""
        
        date_from = datetime.now() - timedelta(days=days)
        
        consultants = db.session.query(
            Consultant.id,
            Consultant.nome,
            db.func.count(Appointment.id).label('total_appointments'),
            db.func.sum(db.case([(Appointment.venduto == True, 1)], else_=0)).label('sold_appointments'),
            db.func.sum(Appointment.nominativi_raccolti).label('total_nominativi')
        ).join(
            Consultant.appointments
        ).filter(
            Appointment.data_appuntamento >= date_from
        ).group_by(
            Consultant.id
        ).order_by(
            db.text('sold_appointments DESC')
        ).all()
        
        result = []
        for i, consultant in enumerate(consultants):
            conversion_rate = (
                consultant.sold_appointments / consultant.total_appointments * 100
                if consultant.total_appointments > 0 else 0
            )
            
            result.append({
                'rank': i + 1,
                'id': consultant.id,
                'nome': consultant.nome,
                'total_appointments': consultant.total_appointments,
                'sold_appointments': consultant.sold_appointments,
                'total_nominativi': consultant.total_nominativi or 0,
                'conversion_rate': round(conversion_rate, 2)
            })
        
        return result

class ClientService:
    """Servizio per gestione clienti"""
    
    @staticmethod
    def create_client_from_appointment(appointment: Appointment) -> Client:
        """Crea cliente da appuntamento venduto"""
        
        if not appointment.venduto:
            raise ValueError("Cliente può essere creato solo da appuntamenti venduti")
        
        # Verifica se cliente esiste già
        existing_client = Client.query.filter_by(
            phone=appointment.numero_telefono
        ).first()
        
        if existing_client:
            return existing_client
        
        client = Client(
            name=appointment.nome_cliente,
            phone=appointment.numero_telefono,
            address=appointment.indirizzo,
            acquisition_date=appointment.data_appuntamento,
            source='appointment',
            notes=f"Cliente acquisito da appuntamento del {appointment.data_appuntamento.strftime('%d/%m/%Y')}"
        )
        
        db.session.add(client)
        db.session.commit()
        
        logger.info(f"Cliente creato: {client.id} - {client.name}")
        return client
    
    @staticmethod
    def get_client_history(client_id: int) -> Dict:
        """Storico completo cliente"""
        
        client = Client.query.get(client_id)
        if not client:
            raise ValueError("Cliente non trovato")
        
        # Trova tutti gli appuntamenti correlati
        appointments = Appointment.query.filter_by(
            numero_telefono=client.phone
        ).order_by(Appointment.data_appuntamento.desc()).all()
        
        # Follow-up correlati
        followups = []
        for appointment in appointments:
            appointment_followups = FollowUp.query.filter_by(
                appointment_id=appointment.id
            ).all()
            followups.extend(appointment_followups)
        
        return {
            'client': client.to_dict(),
            'appointments': [a.to_dict() for a in appointments],
            'followups': [f.to_dict() for f in followups],
            'total_appointments': len(appointments),
            'total_sales': len([a for a in appointments if a.venduto])
        }
