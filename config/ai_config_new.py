# Configurazione AI Service con Ollama
# Smart Control AI Assistant - Configurazione avanzata

import os
import logging

logger = logging.getLogger(__name__)

# Flag per moduli disponibili
SPEECH_RECOGNITION_AVAILABLE = False
TEXT_TO_SPEECH_AVAILABLE = False
OLLAMA_AVAILABLE = False
REQUESTS_AVAILABLE = False

# Test disponibilità moduli
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
    print("✅ Speech Recognition disponibile")
except ImportError:
    print("⚠️ Speech Recognition non disponibile - funzionalità vocali disabilitate")

try:
    import pyttsx3
    TEXT_TO_SPEECH_AVAILABLE = True
    print("✅ Text-to-Speech disponibile")
except ImportError:
    print("⚠️ Text-to-Speech non disponibile - sintesi vocale disabilitata")

try:
    import ollama
    OLLAMA_AVAILABLE = True
    print("✅ Ollama client disponibile")
except ImportError:
    print("⚠️ Ollama client non disponibile - AI locale disabilitata")

try:
    import requests
    REQUESTS_AVAILABLE = True
    print("✅ Requests disponibile per API calls")
except ImportError:
    print("⚠️ Requests non disponibile - API calls disabilitate")

# Configurazione Ollama
OLLAMA_CONFIG = {
    'host': os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
    'model': os.getenv('OLLAMA_MODEL', 'llama3.2:3b'),
    'timeout': int(os.getenv('OLLAMA_TIMEOUT', '120')),  # 2 minuti
    'max_tokens': int(os.getenv('OLLAMA_MAX_TOKENS', '2048')),
    'temperature': float(os.getenv('OLLAMA_TEMPERATURE', '0.7')),
    'stream': True
}

# Configurazione principale
AI_CONFIG = {
    'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
    'text_to_speech': TEXT_TO_SPEECH_AVAILABLE,
    'ollama_ai': OLLAMA_AVAILABLE,
    'api_calls': REQUESTS_AVAILABLE,
    'fallback_responses': True,
    'auto_correction': True,  # Abilita auto-correzione
    'api_access': True,      # Permetti accesso alle API
    'max_api_retries': 3,    # Numero massimo di retry per API
    'api_timeout': 30        # Timeout API in secondi
}

# Risposte predefinite per fallback
FALLBACK_RESPONSES = {
    'greeting': [
        'Ciao! Sono l\'assistente IA di Smart Control. Come posso aiutarti oggi?',
        'Benvenuto! Sono qui per assisterti con clienti, appuntamenti e analisi.',
        'Salve! Sono il tuo assistente digitale Smart Control. Come posso essere utile?'
    ],
    'help': [
        'Posso aiutarti con: gestione clienti, programmazione appuntamenti, analisi dati, report e suggerimenti operativi.',
        'Le mie funzionalità includono: ricerca clienti, controllo appuntamenti, generazione report e consigli strategici.',
        'Sono specializzato in: analisi clienti, ottimizzazione appuntamenti, statistiche e supporto decisionale.'
    ],
    'error': [
        'Si è verificato un errore. Sto cercando di risolverlo...',
        'Problema temporaneo rilevato. Riprovo con un approccio diverso.',
        'Errore nell\'elaborazione. Tentativo di correzione automatica in corso...'
    ],
    'unknown': [
        'Non ho compreso completamente. Puoi riformulare la richiesta?',
        'Potresti essere più specifico? Non sono sicuro di cosa intendi.',
        'Scusa, non ho capito. Prova a spiegare diversamente.'
    ],
    'api_error': [
        'Errore nell\'accesso ai dati. Sto tentando un metodo alternativo...',
        'Problema di connessione rilevato. Provo ad accedere diversamente ai dati...',
        'Difficoltà tecnica temporanea. Utilizzo una strategia di recupero alternativa...'
    ],
    'correction': [
        'Ho corretto l\'errore precedente. Ecco la risposta aggiornata:',
        'Dopo la correzione automatica, la risposta corretta è:',
        'Errore risolto. La risposta corretta è:'
    ]
}

# Sistema di prompt avanzato per Llama 3.2
SYSTEM_PROMPT = """Sei l'Assistente IA di Smart Control, un sistema avanzato di gestione per consulenti e professionisti.

## IDENTITÀ E RUOLO
- Nome: Smart Control AI Assistant
- Specializzazione: Gestione clienti, appuntamenti, analisi dati
- Lingua: Italiano (sempre)
- Personalità: Professionale, preciso, proattivo

## CAPACITÀ PRINCIPALI
1. **Gestione Clienti**: Ricerca, analisi, segmentazione clienti
2. **Appuntamenti**: Programmazione, modifiche, ottimizzazione calendario
3. **Analisi Dati**: Report, statistiche, trend analysis
4. **API Integration**: Accesso e manipolazione dati via API
5. **Auto-correzione**: Rilevamento e correzione errori automatica

## ACCESSO API - FUNZIONI DISPONIBILI
Puoi utilizzare queste API per accedere ai dati:

### API Clienti
- GET /api/clients - Lista tutti i clienti
- GET /api/clients/{id} - Dettagli cliente specifico
- POST /api/clients - Crea nuovo cliente
- PUT /api/clients/{id} - Modifica cliente

### API Appuntamenti  
- GET /api/appointments - Lista appuntamenti
- GET /api/appointments/today - Appuntamenti di oggi
- GET /api/appointments/week - Appuntamenti settimanali
- POST /api/appointments - Crea appuntamento
- PUT /api/appointments/{id} - Modifica appuntamento

### API Statistiche
- GET /api/stats/overview - Panoramica generale
- GET /api/stats/revenue - Statistiche ricavi
- GET /api/stats/clients - Analisi clienti

## ISTRUZIONI OPERATIVE
1. **Sempre in Italiano**: Rispondi sempre in italiano, sii professionale
2. **Usa le API**: Quando hai bisogno di dati, utilizza le API appropriate
3. **Auto-correzione**: Se ricevi un errore API, analizza il problema e riprova con parametri corretti
4. **Contesto Aware**: Considera sempre il contesto dell'utente (ruolo, pagina corrente)
5. **Proattivo**: Suggerisci azioni e miglioramenti quando appropriato

## GESTIONE ERRORI
- Se un'API restituisce errore 400: Verifica i parametri e riprova
- Se errore 401/403: Informa l'utente di problemi di autorizzazione
- Se errore 404: Informa che la risorsa non esiste
- Se errore 500: Suggerisci di riprovare più tardi

## ESEMPI DI INTERAZIONE
Utente: "Quanti appuntamenti ho oggi?"
Risposta: Utilizzo l'API per controllare i tuoi appuntamenti di oggi... [chiama GET /api/appointments/today]

Utente: "Chi è il mio cliente più importante?"
Risposta: Analizzo i dati dei clienti per identificare quello con maggior valore... [chiama GET /api/clients e GET /api/stats/clients]

IMPORTANTE: Utilizza sempre le API quando hai bisogno di dati reali. Non inventare informazioni."""

# Configurazione prompt per diversi contesti
CONTEXT_PROMPTS = {
    'clients': "Focus su gestione e analisi clienti. Priorità a segmentazione, valore cliente, storico interazioni.",
    'appointments': "Focus su calendario e appuntamenti. Priorità a ottimizzazione tempo, conflitti, pianificazione.",
    'reports': "Focus su analisi e reporting. Priorità a KPI, trend, insights actionable.",
    'dashboard': "Focus su overview generale. Priorità a metriche chiave, alert, raccomandazioni immediate."
}
