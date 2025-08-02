"""
Servizio AI Assistant Locale con elaborazione vocale e streaming
Utilizza modelli IA completamente offline (quando disponibili)
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator
from flask import current_app, request
from flask_login import current_user
from io import BytesIO
import base64
import threading
import queue
import time
import os
import re
import random

# Importa configurazione AI
try:
    from config.ai_config import AI_CONFIG, FALLBACK_RESPONSES
except ImportError:
    # Fallback se configurazione non disponibile
    AI_CONFIG = {
        'speech_recognition': False,
        'text_to_speech': False, 
        'local_ai': False,
        'embeddings': False,
        'fallback_responses': True
    }
    FALLBACK_RESPONSES = {
        'greeting': ['Ciao! Come posso aiutarti?'],
        'help': ['Puoi chiedermi informazioni su appuntamenti e clienti.'],
        'error': ['Si è verificato un errore.'],
        'unknown': ['Non ho capito la richiesta.']
    }

# Importa librerie per AI locale solo se disponibili
if AI_CONFIG.get('speech_recognition', False):
    try:
        import speech_recognition as sr
    except ImportError:
        sr = None

if AI_CONFIG.get('text_to_speech', False):
    try:
        import pyttsx3
    except ImportError:
        pyttsx3 = None

if AI_CONFIG.get('local_ai', False):
    try:
        from transformers import (
            AutoTokenizer, AutoModelForCausalLM, 
            pipeline, set_seed
        )
        import torch
    except ImportError:
        AutoTokenizer = AutoModelForCausalLM = pipeline = set_seed = torch = None

if AI_CONFIG.get('embeddings', False):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        SentenceTransformer = None

logger = logging.getLogger(__name__)

class LocalAIService:
    """Servizio IA completamente locale (con fallback)"""
    
    def __init__(self):
        self.model_name = "microsoft/DialoGPT-medium"  # Modello conversazionale leggero
        self.embedding_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
        # Inizializza componenti solo se disponibili
        self.tokenizer = None
        self.model = None
        self.embedding_model = None
        self.generator = None
        self.speech_engine = None
        self.speech_recognizer = None
        
        # Cache per risposte comuni
        self.response_cache = {}
        self.knowledge_base = self._load_knowledge_base()
        
        # Inizializza solo se i moduli sono disponibili
        if AI_CONFIG.get('local_ai', False):
            self._init_models()
        else:
            logger.info("AI locale non disponibile - usando risposte fallback")
            
        if AI_CONFIG.get('speech_recognition', False) or AI_CONFIG.get('text_to_speech', False):
            self._init_speech_engine()
        else:
            logger.info("Elaborazione vocale non disponibile")
            
        logger.info(f"LocalAI Service inizializzato con configurazione: {AI_CONFIG}")
    
    def _init_models(self):
        """Inizializza modelli IA locali"""
        if not AI_CONFIG.get('local_ai', False) or not torch:
            logger.warning("AI locale non disponibile, usando risposte predefinite")
            return
        
        try:
            # Imposta device (CPU/GPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Usando device: {self.device}")
            
            # Carica tokenizer e modello conversazionale
            logger.info(f"Caricando modello: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                padding_side='left'
            )
            
            # Aggiungi pad_token se non esiste
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            ).to(self.device)
            
            # Pipeline per generazione
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                max_length=512,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Carica modello embedding per similarity
            if AI_CONFIG.get('embeddings', False) and SentenceTransformer:
                logger.info(f"Caricando embedding model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
            
            logger.info("Modelli IA locali caricati con successo")
            
        except Exception as e:
            logger.error(f"Errore caricamento modelli IA: {e}")
            self.model = None
            self.tokenizer = None
            self.generator = None
    
    def _load_knowledge_base(self) -> Dict:
        """Carica knowledge base specifica per AppointmentCRM"""
        return {
            "greetings": [
                "Ciao! Sono il tuo assistente IA locale per AppointmentCRM.",
                "Benvenuto! Come posso aiutarti oggi?",
                "Salve! Sono qui per supportarti nella gestione degli appuntamenti."
            ],
            "analysis_prompts": {
                "performance": "Basandomi sui dati disponibili, ecco un'analisi delle performance:",
                "appointments": "Per ottimizzare la gestione appuntamenti:",
                "clients": "Riguardo alla gestione clienti:",
                "consultants": "Per l'analisi del team:"
            },
            "domain_knowledge": {
                "crm": "Il CRM (Customer Relationship Management) è fondamentale per tracciare interazioni clienti, gestire follow-up e ottimizzare le vendite.",
                "appointments": "Una gestione efficace degli appuntamenti include: pianificazione strategica, follow-up tempestivi, documentazione accurata.",
                "performance": "Le metriche chiave includono: tasso di conversione, numero appuntamenti/consulente, qualità follow-up, soddisfazione cliente.",
                "sales": "Tecniche vincenti: ascolto attivo, personalizzazione offerta, gestione obiezioni, closing tempestivo."
            },
            "tips": {
                "dealer": [
                    "Concentrati sui clienti ad alto potenziale per massimizzare il ROI",
                    "Usa i dati storici per identificare i migliori momenti per gli appuntamenti",
                    "Mantieni un follow-up costante ma non invasivo",
                    "Personalizza sempre l'approccio basandoti sulla cronologia cliente"
                ],
                "admin": [
                    "Monitora le performance del team con dashboard in tempo reale",
                    "Implementa processi standardizzati per consistenza qualitativa",
                    "Usa analytics per identificare trend e opportunità",
                    "Investi nella formazione continua del team"
                ]
            }
        }
    
    def _get_fallback_response(self, message: str) -> str:
        """Genera risposta fallback intelligente senza AI"""
        message_lower = message.lower()
        
        # Saluti
        if any(greeting in message_lower for greeting in ['ciao', 'salve', 'buongiorno', 'buonasera', 'hello', 'hi']):
            return random.choice(FALLBACK_RESPONSES['greeting'])
        
        # Richieste di aiuto
        if any(help_word in message_lower for help_word in ['aiuto', 'help', 'come', 'cosa posso']):
            return random.choice(FALLBACK_RESPONSES['help'])
        
        # Domande su appuntamenti
        if any(word in message_lower for word in ['appuntament', 'clienti', 'vendite', 'statistiche']):
            return "Posso aiutarti con informazioni su appuntamenti, clienti e statistiche. Accedi alle varie sezioni del sistema per visualizzare i dati dettagliati."
        
        # Domande generiche
        if '?' in message or any(word in message_lower for word in ['chi', 'cosa', 'come', 'quando', 'dove', 'perché']):
            return "Per informazioni dettagliate, consulta la documentazione o contatta il supporto tecnico."
        
        # Risposta generica
        return random.choice(FALLBACK_RESPONSES['unknown'])
    
    def _init_speech_engine(self):
        """Inizializza engine speech locale"""
        if not AI_CONFIG.get('speech_recognition', False) and not AI_CONFIG.get('text_to_speech', False):
            return
            
        try:
            if sr and AI_CONFIG.get('speech_recognition', False):
                self.speech_recognizer = sr.Recognizer()
                
            if pyttsx3 and AI_CONFIG.get('text_to_speech', False):
                self.speech_engine = pyttsx3.init()
                
                # Configurazione voce italiana
                voices = self.speech_engine.getProperty('voices')
                for voice in voices:
                    if 'italian' in voice.name.lower() or 'it' in voice.id.lower():
                        self.speech_engine.setProperty('voice', voice.id)
                        break
                
                self.speech_engine.setProperty('rate', 180)
                self.speech_engine.setProperty('volume', 0.8)
            
            logger.info("Speech engine locale inizializzato")
            
        except ImportError:
            logger.warning("Speech libraries non disponibili")
            self.speech_engine = None
            self.speech_recognizer = None
        except Exception as e:
            logger.error(f"Errore inizializzazione speech: {e}")
            self.speech_engine = None
            self.speech_recognizer = None
    
    def process_voice_input(self, audio_data: bytes) -> str:
        """Elabora input vocale con riconoscimento locale"""
        if not self.speech_recognizer:
            return "Servizio riconoscimento vocale non disponibile"
        
        try:
            # Converti bytes in AudioData
            audio_file = BytesIO(audio_data)
            
            with sr.AudioFile(audio_file) as source:
                audio = self.speech_recognizer.record(source)
            
            # Riconoscimento vocale offline (se disponibile) o Google
            try:
                # Prova prima con Sphinx (offline)
                text = self.speech_recognizer.recognize_sphinx(audio, language='it-IT')
                logger.info(f"Testo riconosciuto (offline): {text}")
                return text
            except (sr.UnknownValueError, sr.RequestError):
                # Fallback su Google (online)
                text = self.speech_recognizer.recognize_google(audio, language='it-IT')
                logger.info(f"Testo riconosciuto (online): {text}")
                return text
            
        except sr.UnknownValueError:
            return "Non ho capito cosa hai detto. Riprova parlando più chiaramente."
        except sr.RequestError as e:
            logger.error(f"Errore servizio riconoscimento vocale: {e}")
            return "Errore nel servizio di riconoscimento vocale."
        except Exception as e:
            logger.error(f"Errore elaborazione vocale: {e}")
            return "Errore nell'elaborazione dell'audio."
    
    def generate_response_stream(self, message: str, context: Dict = None) -> Generator[str, None, None]:
        """Genera risposta IA locale in streaming"""
        
        # Prepara il contesto
        system_prompt = self._build_system_prompt(context)
        
        # Ottieni risposta dal modello locale
        response_text = self._get_local_ai_response(message, system_prompt, context)
        
        # Simula streaming carattere per carattere
        for char in response_text:
            yield char
            time.sleep(0.02)  # Velocità di typing realistica
    
    def _get_local_ai_response(self, message: str, system_prompt: str, context: Dict = None) -> str:
        """Genera risposta usando IA locale o fallback intelligente"""
        
        # 1. Prova con modello locale se disponibile
        if AI_CONFIG.get('local_ai', False) and self.generator and self.model:
            try:
                return self._generate_with_local_model(message, system_prompt, context)
            except Exception as e:
                logger.error(f"Errore modello locale: {e}")
                # Continua con fallback
        
        # 2. Fallback con risposte predefinite intelligenti
        return self._get_intelligent_fallback_response(message, context)
    
    def _generate_with_local_model(self, message: str, system_prompt: str, context: Dict) -> str:
        """Genera risposta con modello locale Transformers"""
        
        # Costruisci prompt conversazionale
        conversation_prompt = f"""Sistema: {system_prompt}

Utente: {message}
Assistente:"""
        
        # Genera con il modello locale
        response = self.generator(
            conversation_prompt,
            max_new_tokens=200,
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        # Estrai solo la risposta dell'assistente
        full_text = response[0]['generated_text']
        assistant_response = full_text.split("Assistente:")[-1].strip()
        
        # Pulisci e valida la risposta
        assistant_response = self._clean_response(assistant_response)
        
        # Se la risposta è troppo corta o generica, usa fallback
        if len(assistant_response) < 20 or self._is_generic_response(assistant_response):
            return self._get_intelligent_fallback_response(message, context)
        
        return assistant_response
    
    def _clean_response(self, response: str) -> str:
        """Pulisce e formatta la risposta del modello"""
        
        # Rimuovi caratteri indesiderati
        response = re.sub(r'[^\w\s\.,!?\-:;()àèéìíîòóùú]', '', response)
        
        # Limita lunghezza
        if len(response) > 500:
            # Trova l'ultima frase completa
            sentences = response.split('.')
            response = '. '.join(sentences[:3]) + '.'
        
        # Capitalizza prima lettera
        if response:
            response = response[0].upper() + response[1:]
        
        return response.strip()
    
    def _is_generic_response(self, response: str) -> bool:
        """Verifica se la risposta è troppo generica"""
        generic_patterns = [
            r'^(si|no|ok|ciao)\.?$',
            r'non so',
            r'non capisco',
            r'^.{1,10}$'  # Troppo corta
        ]
        
        response_lower = response.lower()
        return any(re.match(pattern, response_lower) for pattern in generic_patterns)
    
    def _get_intelligent_fallback_response(self, message: str, context: Dict = None) -> str:
        """Risposta fallback intelligente basata su pattern e knowledge base"""
        
        message_lower = message.lower()
        
        # 1. Prima prova il pattern matching semplice
        simple_response = self._get_fallback_response(message)
        if simple_response != random.choice(FALLBACK_RESPONSES['unknown']):
            return simple_response
        
        # 2. Pattern matching avanzato per argomenti specifici del CRM
        
        # Saluti e convenevoli
        if any(word in message_lower for word in ['ciao', 'salve', 'buongiorno', 'buonasera']):
            return "Ciao! Sono il tuo assistente per il sistema di gestione appuntamenti. Come posso aiutarti oggi?"
        
        # Appuntamenti
        if any(word in message_lower for word in ['appuntamento', 'appuntamenti', 'prenotare', 'prenotazione']):
            return self._get_appointment_help(context)
        
        # Clienti
        if any(word in message_lower for word in ['cliente', 'clienti', 'paziente', 'pazienti']):
            return "Posso aiutarti con la gestione dei clienti. Puoi aggiungere nuovi clienti, modificare le informazioni esistenti, o visualizzare la lista completa nella sezione Clienti."
        
        # Consulenti
        if any(word in message_lower for word in ['consulente', 'consulenti', 'operatore', 'operatori']):
            return "Per la gestione dei consulenti, puoi accedere alla sezione dedicata dove puoi aggiungere nuovi consulenti, modificare le loro informazioni e gestire le loro specializzazioni."
        
        # Calendario
        if any(word in message_lower for word in ['calendario', 'orario', 'orari', 'disponibilità']):
            return "Il calendario ti mostra tutti gli appuntamenti programmati. Puoi visualizzare le diverse viste (giornaliera, settimanale, mensile) e gestire gli appuntamenti direttamente da lì."
        
        # Report e analytics
        if any(word in message_lower for word in ['report', 'statistiche', 'analytics', 'guadagni', 'incassi']):
            return "Nella sezione Report puoi visualizzare statistiche dettagliate sui tuoi appuntamenti, incassi, clienti più attivi e performance dei consulenti."
        
        # Pagamenti
        if any(word in message_lower for word in ['pagamento', 'pagamenti', 'fatturazione', 'prezzo']):
            return "Puoi gestire i pagamenti nella sezione dedicata, dove puoi registrare i pagamenti ricevuti, gestire le fatture e monitorare i crediti."
        
        # Sistema e impostazioni
        if any(word in message_lower for word in ['impostazioni', 'configurazione', 'sistema', 'setup']):
            return "Nelle impostazioni puoi configurare i parametri del sistema, gestire i temi, configurare le notifiche e personalizzare l'interfaccia."
        
        # VPN e sicurezza (per dealer)
        if any(word in message_lower for word in ['vpn', 'sicurezza', 'connessione', 'rete']):
            return "Per la gestione VPN e sicurezza, verifica lo stato delle connessioni nella dashboard dealer o contatta l'amministratore per supporto tecnico."
        
        # Aiuto generico
        if any(word in message_lower for word in ['aiuto', 'help', 'come', 'cosa', 'dove']):
            return "Sono qui per aiutarti! Puoi chiedermi informazioni su appuntamenti, clienti, consulenti, calendario, report, pagamenti e configurazioni. Cosa ti serve sapere?"
        
        # Domande su funzionalità
        if '?' in message:
            return "Ottima domanda! Il sistema di gestione appuntamenti offre molte funzionalità. Puoi essere più specifico su cosa ti interessa? Ad esempio: appuntamenti, clienti, calendario, report, o configurazioni?"
        
        # Risposta generica con suggerimenti
        return self._get_contextual_default_response(context)
    
    def _find_best_knowledge_match(self, message: str) -> str:
        """Trova la migliore corrispondenza nel knowledge base usando embeddings"""
        
        try:
            import numpy as np
            
            # Codifica il messaggio dell'utente
            user_embedding = self.embeddings_model.encode([message])
            
            best_score = -1
            best_response = None
            
            # Confronta con knowledge base
            for category, items in self.knowledge_base.items():
                for item in items:
                    if 'keywords' in item:
                        # Crea testo per l'embedding dal contenuto
                        content_text = f"{' '.join(item['keywords'])} {item.get('content', '')}"
                        content_embedding = self.embeddings_model.encode([content_text])
                        
                        # Calcola similarità coseno
                        similarity = np.dot(user_embedding[0], content_embedding[0]) / (
                            np.linalg.norm(user_embedding[0]) * np.linalg.norm(content_embedding[0])
                        )
                        
                        if similarity > best_score and similarity > 0.5:  # Soglia di similarità
                            best_score = similarity
                            best_response = item.get('response', item.get('content', ''))
            
            return best_response
            
        except Exception as e:
            logger.error(f"Errore in find_best_knowledge_match: {e}")
            return None
    
    def _get_appointment_help(self, context: Dict = None) -> str:
        """Risposta specifica per aiuto appuntamenti"""
        
        if context and context.get('user_role') == 'dealer':
            return "Come dealer, puoi visualizzare gli appuntamenti assegnati ai tuoi consulenti nella dashboard. Per gestire appuntamenti specifici, accedi alla sezione calendario."
        
        return "Per gli appuntamenti puoi: 1) Aggiungere nuovi appuntamenti con data, ora e consulente, 2) Modificare appuntamenti esistenti, 3) Visualizzare il calendario completo, 4) Ricevere notifiche per promemoria."
    
    def _get_contextual_default_response(self, context: Dict = None) -> str:
        """Risposta di default contestuale"""
        
        if context:
            user_role = context.get('user_role', 'user')
            current_page = context.get('current_page', '')
            
            if user_role == 'dealer':
                return f"Come dealer, hai accesso alle funzionalità di gestione VPN, dashboard clienti e monitoraggio. {current_page and f'Attualmente sei su {current_page}.' or ''} Come posso assisterti?"
            
            elif user_role == 'admin':
                return f"Come amministratore, hai accesso completo a tutte le funzionalità del sistema. {current_page and f'Attualmente sei su {current_page}.' or ''} Posso aiutarti con configurazioni, utenti, report o analisi."
        
        return "Sono il tuo assistente IA per il sistema di gestione appuntamenti. Posso aiutarti con appuntamenti, clienti, consulenti, calendario, report e configurazioni. Cosa ti serve?"
    
    def _build_system_prompt(self, context: Dict = None) -> str:
        """Costruisce prompt sistema con contesto applicazione"""
        
        base_prompt = """Sei un assistente IA specializzato nella gestione di appuntamenti e CRM.
        
Puoi aiutare con:
- Gestione appuntamenti e consulenti
- Analisi performance e statistiche
- Ricerca clienti e cronologia
- Pianificazione follow-up
- Report personalizzati
- Consigli strategici di vendita

Rispondi sempre in italiano, in modo professionale ma amichevole.
Usa i dati forniti nel contesto per dare risposte precise e utili."""

        if context:
            # Aggiungi informazioni utente
            if context.get('user_role'):
                base_prompt += f"\n\nRuolo utente: {context['user_role']}"
                if context['user_role'] == 'dealer':
                    base_prompt += "\nFocalizzati su metriche personali e consigli per migliorare le performance."
                elif context['user_role'] == 'admin':
                    base_prompt += "\nFornisci panoramiche generali e insights manageriali."
            
            # Aggiungi statistiche recenti
            if context.get('stats'):
                base_prompt += f"\n\nStatistiche recenti:\n{json.dumps(context['stats'], indent=2)}"
            
            # Aggiungi context specifico
            if context.get('page_context'):
                base_prompt += f"\n\nContesto pagina: {context['page_context']}"
        
        return base_prompt
    
    def _get_ai_response(self, message: str, system_prompt: str) -> str:
        """Ottiene risposta dall'AI (simulata per preview)"""
        
        # Risposte predefinite intelligenti basate su pattern
        responses = self._get_smart_responses(message)
        
        if responses:
            return responses[0]
        
        # Risposta generica se non trova pattern
        return f"""Ho capito la tua richiesta: "{message}".

Come assistente IA per AppointmentCRM, posso aiutarti con:

📊 **Analisi dati**: Statistiche appuntamenti, performance consulenti, trend vendite
📅 **Gestione appuntamenti**: Ricerca, modifica, pianificazione follow-up
👥 **Gestione clienti**: Cronologia, segmentazione, opportunità cross-sell
📈 **Report personalizzati**: Analisi periodo, comparazioni, previsioni
💡 **Consigli strategici**: Ottimizzazione processi, miglioramento conversioni

Cosa vorresti approfondire? Puoi anche utilizzare i comandi vocali per un'interazione più naturale."""
    
    def _get_smart_responses(self, message: str) -> List[str]:
        """Genera risposte intelligenti basate su pattern"""
        
        message_lower = message.lower()
        
        # Pattern per statistiche
        if any(word in message_lower for word in ['statistiche', 'performance', 'andamento', 'risultati']):
            return [self._generate_stats_response()]
        
        # Pattern per appuntamenti
        if any(word in message_lower for word in ['appuntamenti', 'appuntamento', 'calendario']):
            return [self._generate_appointments_response()]
        
        # Pattern per clienti
        if any(word in message_lower for word in ['clienti', 'cliente', 'vendite', 'vendita']):
            return [self._generate_clients_response()]
        
        # Pattern per consulenti
        if any(word in message_lower for word in ['consulenti', 'consulente', 'team']):
            return [self._generate_consultants_response()]
        
        # Pattern per consigli
        if any(word in message_lower for word in ['consigli', 'suggerimenti', 'migliorare', 'ottimizzare']):
            return [self._generate_advice_response()]
        
        return []
    
    def _generate_stats_response(self) -> str:
        """Genera risposta per statistiche"""
        return """📊 **Analisi Performance Recente**

Basandomi sui dati disponibili, ecco un'analisi delle tue performance:

**Metriche Chiave:**
• Tasso di conversione: Monitora il rapporto vendite/appuntamenti
• Tempo medio appuntamento: Ottimizza l'efficienza
• Follow-up completati: Mantieni il contatto post-vendita

**Suggerimenti:**
✅ Concentrati sui clienti con alto potenziale
✅ Pianifica follow-up strutturati
✅ Analizza i pattern di vendita per stagionalità

Vuoi che approfondisca una metrica specifica?"""
    
    def _generate_appointments_response(self) -> str:
        """Genera risposta per appuntamenti"""
        return """📅 **Gestione Appuntamenti Intelligente**

**Ottimizzazione Calendario:**
• Raggruppa appuntamenti per area geografica
• Lascia buffer time tra gli appuntamenti
• Pianifica i follow-up nei momenti ottimali

**Best Practices:**
✅ Conferma appuntamenti 24h prima
✅ Prepara materiali personalizzati
✅ Documenta outcome e prossimi step

**Automazioni Utili:**
• Follow-up automatici post-vendita
• Reminder per appuntamenti in scadenza
• Analisi pattern temporali di conversione

Posso aiutarti a ottimizzare una specifica parte del processo?"""
    
    def _generate_clients_response(self) -> str:
        """Genera risposta per clienti"""
        return """👥 **Strategia Clienti e Vendite**

**Segmentazione Intelligente:**
• Clienti ad alto valore: Focus su retention
• Prospect caldi: Accelera il closing
• Follow-up necessari: Riattiva relazioni

**Tecniche di Vendita:**
✅ Personalizza l'approccio per ogni segmento
✅ Utilizza la cronologia per identificare needs
✅ Cross-sell su clienti esistenti soddisfatti

**Analisi Opportunità:**
• Clienti inattivi da ricontattare
• Referral potenziali da clienti soddisfatti
• Upgrade e servizi aggiuntivi

Vuoi che analizzi un segmento specifico di clienti?"""
    
    def _generate_consultants_response(self) -> str:
        """Genera risposta per consulenti"""
        return """👨‍💼 **Analisi Team e Performance**

**Metriche Consulenti:**
• Conversion rate individuale
• Numero appuntamenti/settimana
• Qualità follow-up completati

**Sviluppo Team:**
✅ Identifica best practices dei top performer
✅ Programmi di coaching personalizzati
✅ Incentivi basati su obiettivi SMART

**Ottimizzazione Processi:**
• Standardizza approcci vincenti
• Condividi tecniche di successo
• Monitora carico lavoro e bilanciamento

Posso creare un'analisi dettagliata delle performance del team?"""
    
    def _generate_advice_response(self) -> str:
        """Genera consigli generali"""
        return """💡 **Consigli Strategici Personalizzati**

**Miglioramento Immediato:**
• Automatizza task ripetitivi
• Standardizza processi di qualità
• Monitora KPI in tempo reale

**Crescita a Medio Termine:**
✅ Investi in formazione consultenti
✅ Ottimizza customer journey
✅ Implementa strategie di retention

**Innovazione Continua:**
• Raccogli feedback sistematicamente
• Testa nuovi approcci di vendita
• Analizza competitor e best practices

**Tecnologia e Automazione:**
• Follow-up automatici
• Dashboard personalizzate
• Integrazione CRM avanzata

Su quale area vorresti che mi concentrassi maggiormente?"""
    
    def text_to_speech(self, text: str) -> bytes:
        """Converte testo in audio"""
        if not self.speech_engine:
            return b""
        
        try:
            # Salva in memoria
            audio_queue = queue.Queue()
            
            def save_to_queue():
                self.speech_engine.save_to_file(text, None)
                # Simula audio bytes (in produzione useresti un vero TTS)
                audio_queue.put(b"dummy_audio_data")
            
            thread = threading.Thread(target=save_to_queue)
            thread.start()
            thread.join(timeout=10)
            
            if not audio_queue.empty():
                return audio_queue.get()
            
        except Exception as e:
            logger.error(f"Errore TTS: {e}")
        
        return b""
    
    def get_context_data(self, user_id: int = None) -> Dict:
        """Ottiene dati di contesto per l'AI"""
        
        context = {
            'timestamp': datetime.now().isoformat(),
            'user_role': current_user.role if current_user.is_authenticated else 'guest'
        }
        
        try:
            # Importa qui per evitare circular imports
            from models.appointment import Appointment
            from models.consultant import Consultant
            from models.client import Client
            
            # Statistiche generali
            total_appointments = Appointment.query.count()
            sold_appointments = Appointment.query.filter_by(venduto=True).count()
            total_consultants = Consultant.query.count()
            total_clients = Client.query.count()
            
            # Appuntamenti recenti
            recent_appointments = Appointment.query.order_by(
                Appointment.data_appuntamento.desc()
            ).limit(5).all()
            
            context['stats'] = {
                'total_appointments': total_appointments,
                'sold_appointments': sold_appointments,
                'total_consultants': total_consultants,
                'total_clients': total_clients,
                'conversion_rate': (sold_appointments / total_appointments * 100) if total_appointments > 0 else 0,
                'recent_appointments': len(recent_appointments)
            }
            
            # Se utente dealer, filtra per suoi dati
            if current_user.is_authenticated and current_user.is_dealer() and current_user.consultant:
                consultant = current_user.consultant
                personal_appointments = consultant.appointments
                personal_stats = consultant.get_appointments_stats()
                
                context['personal_stats'] = {
                    'consultant_name': consultant.nome,
                    'total_appointments': len(personal_appointments),
                    'stats': personal_stats
                }
        
        except Exception as e:
            logger.error(f"Errore recupero context data: {e}")
        
        return context

class VoiceProcessor:
    """Processore per elaborazione vocale"""
    
    def __init__(self):
        self.is_recording = False
        self.audio_buffer = BytesIO()
    
    def start_recording(self):
        """Inizia registrazione vocale"""
        self.is_recording = True
        self.audio_buffer = BytesIO()
        return {"status": "recording_started"}
    
    def stop_recording(self):
        """Ferma registrazione vocale"""
        self.is_recording = False
        return {"status": "recording_stopped"}
    
    def process_audio_chunk(self, chunk: bytes):
        """Elabora chunk audio in streaming"""
        if self.is_recording and chunk:
            self.audio_buffer.write(chunk)
            return len(chunk)
        return 0
    
    def get_audio_data(self) -> bytes:
        """Ottiene dati audio registrati"""
        return self.audio_buffer.getvalue()

# Istanza globale del servizio
ai_service = LocalAIService()
voice_processor = VoiceProcessor()
