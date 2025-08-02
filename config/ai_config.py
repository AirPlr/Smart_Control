# Configurazione AI Service
# Controllo disponibilità dei moduli AI

# Flag per moduli disponibili
SPEECH_RECOGNITION_AVAILABLE = False
TEXT_TO_SPEECH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
SENTENCE_TRANSFORMERS_AVAILABLE = False

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
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
    print("✅ Transformers disponibile")
except ImportError:
    print("⚠️ Transformers non disponibile - AI locale disabilitata")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    print("✅ Sentence Transformers disponibile")
except ImportError:
    print("⚠️ Sentence Transformers non disponibile - embeddings disabilitati")

# Configurazione fallback
AI_CONFIG = {
    'speech_recognition': SPEECH_RECOGNITION_AVAILABLE,
    'text_to_speech': TEXT_TO_SPEECH_AVAILABLE,
    'local_ai': TRANSFORMERS_AVAILABLE,
    'embeddings': SENTENCE_TRANSFORMERS_AVAILABLE,
    'fallback_responses': True,  # Abilita sempre risposte fallback
}

# Risposte predefinite per fallback
FALLBACK_RESPONSES = {
    'greeting': [
        'Ciao! Come posso aiutarti oggi?',
        'Benvenuto! Sono qui per assisterti.',
        'Salve! Come posso essere utile?'
    ],
    'help': [
        'Puoi chiedermi informazioni su appuntamenti, clienti e statistiche.',
        'Sono qui per aiutarti con le funzioni del sistema.',
        'Posso assisterti con domande sui dati e le operazioni.'
    ],
    'error': [
        'Mi dispiace, ho riscontrato un problema. Riprova più tardi.',
        'Non riesco a elaborare la richiesta al momento.',
        'Si è verificato un errore. Contatta il supporto se persiste.'
    ],
    'unknown': [
        'Non ho capito la tua richiesta. Puoi riformularla?',
        'Potresti essere più specifico nella tua domanda?',
        'Non sono sicuro di aver compreso. Puoi spiegare meglio?'
    ]
}

print(f"🤖 AI Service configurato: {AI_CONFIG}")
