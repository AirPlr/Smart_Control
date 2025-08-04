"""
Smart Control AI Service con Ollama e Llama 3.2 3B
Servizio AI avanzato con accesso API e auto-correzione
"""

import json
import logging
import asyncio
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator, Any
from flask import current_app, request
from flask_login import current_user
import requests
from io import BytesIO
import base64
import threading
import queue

# Importa configurazione AI
try:
    from config.ai_config_new import (
        AI_CONFIG, OLLAMA_CONFIG, FALLBACK_RESPONSES, 
        SYSTEM_PROMPT, CONTEXT_PROMPTS
    )
except ImportError:
    # Fallback configuration
    AI_CONFIG = {'fallback_responses': True, 'ollama_ai': False, 'api_access': False}
    OLLAMA_CONFIG = {'host': 'http://localhost:11434', 'model': 'llama3.2:3b'}
    FALLBACK_RESPONSES = {'error': ['Si è verificato un errore.']}
    SYSTEM_PROMPT = "Sei un assistente IA."
    CONTEXT_PROMPTS = {}

# Importa moduli condizionalmente
if AI_CONFIG.get('ollama_ai', False):
    try:
        import ollama
    except ImportError:
        ollama = None

if AI_CONFIG.get('api_calls', False):
    try:
        import requests
    except ImportError:
        requests = None

logger = logging.getLogger(__name__)

class APIClient:
    """Client per interagire con le API del sistema"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or "http://localhost:5000"
        self.timeout = timeout
        self.session = requests.Session() if requests else None
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Esegue una richiesta HTTP con gestione errori"""
        if not self.session:
            raise Exception("Requests non disponibile")
            
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json() if response.content else None,
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            }
    
    def get_clients(self, limit: int = None) -> Dict[str, Any]:
        """Ottieni lista clienti"""
        params = {'limit': limit} if limit else {}
        return self._make_request('GET', '/api/clients', params=params)
    
    def get_client(self, client_id: int) -> Dict[str, Any]:
        """Ottieni dettagli cliente specifico"""
        return self._make_request('GET', f'/api/clients/{client_id}')
    
    def get_appointments(self, date: str = None, status: str = None) -> Dict[str, Any]:
        """Ottieni lista appuntamenti"""
        params = {}
        if date:
            params['date'] = date
        if status:
            params['status'] = status
        return self._make_request('GET', '/api/appointments', params=params)
    
    def get_appointments_today(self) -> Dict[str, Any]:
        """Ottieni appuntamenti di oggi"""
        return self._make_request('GET', '/api/appointments/today')
    
    def get_appointments_week(self) -> Dict[str, Any]:
        """Ottieni appuntamenti della settimana"""
        return self._make_request('GET', '/api/appointments/week')
    
    def get_stats_overview(self) -> Dict[str, Any]:
        """Ottieni panoramica statistiche"""
        return self._make_request('GET', '/api/stats/overview')
    
    def get_stats_revenue(self, period: str = 'month') -> Dict[str, Any]:
        """Ottieni statistiche ricavi"""
        return self._make_request('GET', '/api/stats/revenue', params={'period': period})

class OllamaAIService:
    """Servizio AI con Ollama e Llama 3.2 3B"""
    
    def __init__(self):
        self.client = None
        self.model = OLLAMA_CONFIG['model']
        self.host = OLLAMA_CONFIG['host']
        self.api_client = APIClient()
        self.conversation_history = {}
        
        # Inizializza client Ollama se disponibile
        if AI_CONFIG.get('ollama_ai', False) and ollama:
            try:
                self.client = ollama.Client(host=self.host)
                self._test_connection()
            except Exception as e:
                logger.error(f"Errore inizializzazione Ollama: {e}")
                self.client = None
    
    def _test_connection(self) -> bool:
        """Testa la connessione con Ollama"""
        try:
            if not self.client:
                return False
            models = self.client.list()
            available_models = [model['name'] for model in models.get('models', [])]
            if self.model not in available_models:
                logger.warning(f"Modello {self.model} non trovato. Disponibili: {available_models}")
                return False
            return True
        except Exception as e:
            logger.error(f"Test connessione Ollama fallito: {e}")
            return False
    
    def _call_api_with_retry(self, api_func, *args, **kwargs) -> Dict[str, Any]:
        """Chiama API con retry automatico"""
        max_retries = AI_CONFIG.get('max_api_retries', 3)
        
        for attempt in range(max_retries):
            try:
                result = api_func(*args, **kwargs)
                if result.get('success'):
                    return result
                else:
                    # Analizza l'errore e prova correzione
                    if attempt < max_retries - 1:
                        error_code = result.get('status_code', 500)
                        if error_code == 400:
                            # Bad Request - prova con parametri modificati
                            logger.info(f"Tentativo {attempt + 1}: Correzione parametri per errore 400")
                            if 'params' in kwargs:
                                # Rimuovi parametri problematici
                                kwargs['params'] = {k: v for k, v in kwargs['params'].items() if v is not None}
                        elif error_code == 404:
                            # Not Found - prova endpoint alternativi
                            logger.info(f"Tentativo {attempt + 1}: Risorsa non trovata")
                            break  # Non ritentare per 404
                        time.sleep(1)  # Attendi prima del retry
                    
            except Exception as e:
                logger.error(f"Errore chiamata API (tentativo {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                
        return {'success': False, 'error': 'Numero massimo di tentativi raggiunto'}
    
    def _format_api_data(self, data: Dict[str, Any], context: str) -> str:
        """Formatta i dati API per il prompt"""
        if not data.get('success'):
            return f"ERRORE API: {data.get('error', 'Errore sconosciuto')}"
        
        api_data = data.get('data', [])
        
        if context == 'clients':
            if isinstance(api_data, list):
                return f"CLIENTI TROVATI ({len(api_data)}):\n" + "\n".join([
                    f"- {client.get('name', 'N/A')} (ID: {client.get('id', 'N/A')})" 
                    for client in api_data[:10]  # Limita a 10 per il prompt
                ])
            else:
                return f"CLIENTE: {api_data.get('name', 'N/A')} - Dettagli: {json.dumps(api_data, indent=2)}"
                
        elif context == 'appointments':
            if isinstance(api_data, list):
                return f"APPUNTAMENTI TROVATI ({len(api_data)}):\n" + "\n".join([
                    f"- {apt.get('client_name', 'N/A')} il {apt.get('date', 'N/A')} alle {apt.get('time', 'N/A')}" 
                    for apt in api_data[:10]
                ])
            else:
                return f"APPUNTAMENTO: {json.dumps(api_data, indent=2)}"
                
        elif context == 'stats':
            return f"STATISTICHE: {json.dumps(api_data, indent=2)}"
            
        return f"DATI: {json.dumps(api_data, indent=2)}"
    
    def _build_enhanced_prompt(self, user_message: str, context: Dict[str, Any]) -> str:
        """Costruisce un prompt avanzato con contesto e accesso API"""
        
        # Prompt base del sistema
        prompt = SYSTEM_PROMPT + "\n\n"
        
        # Aggiungi contesto specifico della pagina
        page_context = context.get('page_context', 'dashboard')
        if page_context in CONTEXT_PROMPTS:
            prompt += f"CONTESTO PAGINA: {CONTEXT_PROMPTS[page_context]}\n\n"
        
        # Aggiungi informazioni utente
        user_role = context.get('user_role', 'viewer')
        timestamp = context.get('timestamp', datetime.now().isoformat())
        prompt += f"UTENTE: Ruolo {user_role} - Timestamp: {timestamp}\n\n"
        
        # Analizza la richiesta per determinare se servono dati API
        needs_api_data = self._analyze_request_for_api_needs(user_message)
        
        if needs_api_data and AI_CONFIG.get('api_access', False):
            prompt += "DATI DISPONIBILI:\n"
            
            # Carica dati pertinenti
            for api_need in needs_api_data:
                try:
                    if api_need == 'clients':
                        api_result = self._call_api_with_retry(self.api_client.get_clients, limit=20)
                        prompt += self._format_api_data(api_result, 'clients') + "\n\n"
                    
                    elif api_need == 'appointments_today':
                        api_result = self._call_api_with_retry(self.api_client.get_appointments_today)
                        prompt += self._format_api_data(api_result, 'appointments') + "\n\n"
                    
                    elif api_need == 'appointments':
                        api_result = self._call_api_with_retry(self.api_client.get_appointments)
                        prompt += self._format_api_data(api_result, 'appointments') + "\n\n"
                    
                    elif api_need == 'stats':
                        api_result = self._call_api_with_retry(self.api_client.get_stats_overview)
                        prompt += self._format_api_data(api_result, 'stats') + "\n\n"
                        
                except Exception as e:
                    prompt += f"ERRORE CARICAMENTO {api_need}: {str(e)}\n\n"
        
        # Messaggio dell'utente
        prompt += f"RICHIESTA UTENTE: {user_message}\n\n"
        prompt += "RISPOSTA (in italiano, professionale e basata sui dati reali forniti):"
        
        return prompt
    
    def _analyze_request_for_api_needs(self, message: str) -> List[str]:
        """Analizza il messaggio per determinare quali API chiamare"""
        message_lower = message.lower()
        api_needs = []
        
        # Pattern per clienti
        client_patterns = ['client', 'cliente', 'clienti', 'persona', 'persone']
        if any(pattern in message_lower for pattern in client_patterns):
            api_needs.append('clients')
        
        # Pattern per appuntamenti
        appointment_patterns = ['appuntamento', 'appuntamenti', 'incontro', 'incontri', 'oggi', 'domani', 'calendario']
        if any(pattern in message_lower for pattern in appointment_patterns):
            if 'oggi' in message_lower:
                api_needs.append('appointments_today')
            else:
                api_needs.append('appointments')
        
        # Pattern per statistiche
        stats_patterns = ['statistic', 'statistiche', 'report', 'analisi', 'ricavi', 'guadagni', 'performance']
        if any(pattern in message_lower for pattern in stats_patterns):
            api_needs.append('stats')
        
        return api_needs
    
    def generate_response_stream(self, message: str, context: Dict[str, Any]) -> Generator[str, None, None]:
        """Genera risposta in streaming con Ollama"""
        
        if not self.client:
            # Fallback response
            fallback = self._get_fallback_response('error')
            for char in fallback:
                yield char
                time.sleep(0.05)
            return
        
        try:
            # Costruisci prompt avanzato
            enhanced_prompt = self._build_enhanced_prompt(message, context)
            
            # Log per debugging
            logger.info(f"Prompt inviato a Ollama: {enhanced_prompt[:500]}...")
            
            # Chiamata streaming a Ollama
            response_stream = self.client.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'user',
                        'content': enhanced_prompt
                    }
                ],
                stream=True,
                options={
                    'temperature': OLLAMA_CONFIG.get('temperature', 0.7),
                    'max_tokens': OLLAMA_CONFIG.get('max_tokens', 2048)
                }
            )
            
            full_response = ""
            for chunk in response_stream:
                if chunk.get('message', {}).get('content'):
                    content = chunk['message']['content']
                    full_response += content
                    yield content
            
            # Salva nella cronologia conversazione
            user_id = getattr(current_user, 'id', 'anonymous')
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            self.conversation_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'user_message': message,
                'ai_response': full_response,
                'context': context.get('page_context', 'unknown')
            })
            
            # Mantieni solo gli ultimi 10 messaggi per utente
            if len(self.conversation_history[user_id]) > 10:
                self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
                
        except Exception as e:
            logger.error(f"Errore generazione risposta Ollama: {e}")
            
            # Auto-correzione: prova con prompt più semplice
            if AI_CONFIG.get('auto_correction', False):
                try:
                    logger.info("Tentativo auto-correzione con prompt semplificato...")
                    simple_response = self.client.chat(
                        model=self.model,
                        messages=[
                            {
                                'role': 'user', 
                                'content': f"Rispondi in italiano a questa domanda su Smart Control: {message}"
                            }
                        ],
                        stream=False
                    )
                    
                    correction_msg = FALLBACK_RESPONSES.get('correction', ['Risposta corretta:'])[0]
                    yield f"{correction_msg}\n\n"
                    
                    response_text = simple_response.get('message', {}).get('content', '')
                    for char in response_text:
                        yield char
                        time.sleep(0.02)
                    return
                        
                except Exception as e2:
                    logger.error(f"Auto-correzione fallita: {e2}")
            
            # Fallback finale
            fallback = self._get_fallback_response('error')
            for char in fallback:
                yield char
                time.sleep(0.05)
    
    def _get_fallback_response(self, response_type: str) -> str:
        """Ottieni risposta di fallback"""
        responses = FALLBACK_RESPONSES.get(response_type, ['Risposta non disponibile.'])
        import random
        return random.choice(responses)
    
    def get_context_data(self) -> Dict[str, Any]:
        """Ottieni dati di contesto per l'AI"""
        return {
            'timestamp': datetime.now().isoformat(),
            'user_role': getattr(current_user, 'role', 'viewer') if current_user.is_authenticated else 'anonymous',
            'user_id': getattr(current_user, 'id', 'anonymous') if current_user.is_authenticated else 'anonymous',
            'page_context': request.endpoint if request else 'unknown'
        }

# Istanza globale del servizio
ai_service = OllamaAIService()

# Compatibilità con il codice esistente
voice_processor = None  # Placeholder per compatibilità
