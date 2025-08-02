# Importa db da file separato per evitare import circolari
from .database import db, appointment_consultant

# Importa tutti i modelli
from .user import User
from .consultant import Consultant, Position
from .appointment import Appointment, OtherAppointment
from .client import Client
from .followup import FollowUp
from .note_event import note_event

# Esporta tutti i modelli
__all__ = [
    'db',
    'User', 
    'Consultant', 
    'Position',
    'Appointment', 
    'OtherAppointment', 
    'appointment_consultant',
    'Client',
    'FollowUp',
    'note_event'
]
