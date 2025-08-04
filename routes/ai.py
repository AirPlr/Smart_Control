from flask import Blueprint, request, jsonify, render_template, Response
from flask_login import login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import logging
import base64

# Prova prima il nuovo servizio, poi fallback al vecchio
try:
    from services.ai_service_new import ai_service, voice_processor
    logger = logging.getLogger(__name__)
    logger.info("✅ Caricato nuovo servizio AI con Ollama")
except ImportError:
    try:
        from services.ai_service import ai_service, voice_processor
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ Fallback al vecchio servizio AI")
    except ImportError:
        logger = logging.getLogger(__name__)
        logger.error("❌ Nessun servizio AI disponibile")
        ai_service = None
        voice_processor = None

bp = Blueprint('ai', __name__, url_prefix='/ai')

# Rate limiting per API AI
limiter = Limiter(key_func=get_remote_address)

@bp.route('/chat', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def chat():
    """Endpoint per chat con AI - Versione avanzata con Ollama"""
    
    if not ai_service:
        return jsonify({'error': 'Servizio AI non disponibile'}), 503
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Messaggio richiesto'}), 400
        
        # Ottieni contesto avanzato
        context = ai_service.get_context_data()
        context['page_context'] = data.get('page_context', 'dashboard')
        
        # Log interazione con più dettagli
        logger.info(f"AI Chat - User: {current_user.username} (ID: {current_user.id}), "
                   f"Page: {context['page_context']}, Message: {message[:100]}...")
        
        # Genera risposta in streaming
        response_chunks = []
        try:
            for chunk in ai_service.generate_response_stream(message, context):
                response_chunks.append(chunk)
        except Exception as e:
            logger.error(f"Errore durante streaming AI: {e}")
            # Tentativo di recovery
            response_chunks = ["Mi dispiace, si è verificato un errore. Riprova più tardi."]
        
        response_text = ''.join(response_chunks)
        
        # Log della risposta per analisi
        logger.info(f"AI Response length: {len(response_text)} chars")
        
        return jsonify({
            'response': response_text,
            'timestamp': context['timestamp'],
            'user_role': context['user_role'],
            'model_used': 'llama3.2:3b',
            'api_access': True,
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Errore AI chat: {e}")
        return jsonify({'error': 'Errore interno del servizio AI'}), 500

@bp.route('/stream-chat', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def stream_chat():
    """Endpoint per chat streaming"""
    
    def generate():
        try:
            data = request.get_json()
            message = data.get('message', '').strip()
            
            if not message:
                yield f"data: {json.dumps({'error': 'Messaggio richiesto'})}\n\n"
                return
            
            # Ottieni contesto
            context = ai_service.get_context_data()
            context['page_context'] = data.get('page_context', '')
            
            # Inizia streaming
            yield f"data: {json.dumps({'type': 'start', 'message': 'Sto pensando...'})}\n\n"
            
            # Stream risposta carattere per carattere
            for chunk in ai_service.generate_response_stream(message, context):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # Fine stream
            yield f"data: {json.dumps({'type': 'end', 'timestamp': context['timestamp']})}\n\n"
            
        except Exception as e:
            logger.error(f"Errore AI streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Errore servizio AI'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@bp.route('/voice-input', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def voice_input():
    """Elabora input vocale"""
    
    try:
        # Ottieni audio data
        if 'audio' not in request.files:
            return jsonify({'error': 'File audio richiesto'}), 400
        
        audio_file = request.files['audio']
        audio_data = audio_file.read()
        
        if len(audio_data) == 0:
            return jsonify({'error': 'File audio vuoto'}), 400
        
        # Processa audio
        transcribed_text = ai_service.process_voice_input(audio_data)
        
        if not transcribed_text or transcribed_text.startswith("Non ho capito") or transcribed_text.startswith("Errore"):
            return jsonify({
                'success': False,
                'error': transcribed_text,
                'transcription': ''
            })
        
        logger.info(f"Voice input - User: {current_user.username}, Transcription: {transcribed_text}")
        
        return jsonify({
            'success': True,
            'transcription': transcribed_text,
            'message': 'Audio elaborato con successo'
        })
    
    except Exception as e:
        logger.error(f"Errore voice input: {e}")
        return jsonify({'error': 'Errore elaborazione audio'}), 500

@bp.route('/text-to-speech', methods=['POST'])
@login_required
@limiter.limit("20 per minute") 
def text_to_speech():
    """Converte testo in audio"""
    
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Testo richiesto'}), 400
        
        if len(text) > 500:
            return jsonify({'error': 'Testo troppo lungo (max 500 caratteri)'}), 400
        
        # Genera audio
        audio_data = ai_service.text_to_speech(text)
        
        if not audio_data:
            return jsonify({'error': 'Errore generazione audio'}), 500
        
        # Converti in base64 per trasmissione
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'audio_data': audio_base64,
            'audio_format': 'wav'
        })
    
    except Exception as e:
        logger.error(f"Errore TTS: {e}")
        return jsonify({'error': 'Errore sintesi vocale'}), 500

@bp.route('/context-data')
@login_required
@limiter.limit("60 per minute")
def get_context_data():
    """Ottiene dati di contesto per AI"""
    
    try:
        context = ai_service.get_context_data()
        return jsonify(context)
    
    except Exception as e:
        logger.error(f"Errore context data: {e}")
        return jsonify({'error': 'Errore recupero contesto'}), 500

@bp.route('/suggestions')
@login_required
@limiter.limit("30 per minute")
def get_suggestions():
    """Ottiene suggerimenti contestuali"""
    
    try:
        page = request.args.get('page', 'dashboard')
        
        suggestions = {
            'dashboard': [
                "Mostrami le statistiche di questo mese",
                "Analizza le performance dei consulenti",
                "Quali sono i trend delle vendite?",
                "Consigli per migliorare la conversione"
            ],
            'appointments': [
                "Come posso ottimizzare il mio calendario?",
                "Analizza i miei appuntamenti recenti",
                "Suggerimenti per i follow-up",
                "Quali clienti dovrei ricontattare?"
            ],
            'consultants': [
                "Analizza le performance del team",
                "Chi sono i consulenti più performanti?",
                "Come migliorare la formazione?",
                "Strategie di motivazione del team"
            ],
            'clients': [
                "Identifica opportunità di cross-sell",
                "Analisi segmentazione clienti",
                "Clienti a rischio churn",
                "Strategie di retention"
            ]
        }
        
        return jsonify({
            'suggestions': suggestions.get(page, suggestions['dashboard']),
            'page': page
        })
    
    except Exception as e:
        logger.error(f"Errore suggestions: {e}")
        return jsonify({'error': 'Errore recupero suggerimenti'}), 500

@bp.route('/quick-analysis')
@login_required
@limiter.limit("15 per minute")
def quick_analysis():
    """Analisi rapida basata su parametri"""
    
    try:
        analysis_type = request.args.get('type', 'general')
        days = int(request.args.get('days', 30))
        
        context = ai_service.get_context_data()
        
        # Genera analisi specifica
        if analysis_type == 'performance':
            message = f"Analizza le performance degli ultimi {days} giorni"
        elif analysis_type == 'trends':
            message = f"Identifica i trend degli ultimi {days} giorni"
        elif analysis_type == 'opportunities':
            message = "Identifica le principali opportunità di business"
        else:
            message = "Fornisci un'analisi generale della situazione"
        
        # Genera risposta
        response_chunks = []
        for chunk in ai_service.generate_response_stream(message, context):
            response_chunks.append(chunk)
        
        response_text = ''.join(response_chunks)
        
        return jsonify({
            'analysis': response_text,
            'type': analysis_type,
            'period_days': days,
            'timestamp': context['timestamp']
        })
    
    except Exception as e:
        logger.error(f"Errore quick analysis: {e}")
        return jsonify({'error': 'Errore analisi rapida'}), 500

# Voice Recording endpoints
@bp.route('/voice/start-recording', methods=['POST'])
@login_required
def start_voice_recording():
    """Inizia registrazione vocale"""
    
    try:
        result = voice_processor.start_recording()
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Errore start recording: {e}")
        return jsonify({'error': 'Errore avvio registrazione'}), 500

@bp.route('/voice/stop-recording', methods=['POST'])
@login_required
def stop_voice_recording():
    """Ferma registrazione vocale"""
    
    try:
        result = voice_processor.stop_recording()
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Errore stop recording: {e}")
        return jsonify({'error': 'Errore stop registrazione'}), 500

@bp.route('/voice/process-recording', methods=['POST'])
@login_required
def process_voice_recording():
    """Elabora registrazione vocale completa"""
    
    try:
        audio_data = voice_processor.get_audio_data()
        
        if not audio_data:
            return jsonify({'error': 'Nessun audio registrato'}), 400
        
        # Processa audio
        transcribed_text = ai_service.process_voice_input(audio_data)
        
        # Genera risposta AI
        context = ai_service.get_context_data()
        response_chunks = []
        for chunk in ai_service.generate_response_stream(transcribed_text, context):
            response_chunks.append(chunk)
        
        response_text = ''.join(response_chunks)
        
        return jsonify({
            'transcription': transcribed_text,
            'ai_response': response_text,
            'success': True
        })
    
    except Exception as e:
        logger.error(f"Errore process recording: {e}")
        return jsonify({'error': 'Errore elaborazione registrazione'}), 500

# Error handlers
@bp.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'error': 'Troppi richieste AI. Riprova tra qualche minuto.',
        'retry_after': 60
    }), 429

@bp.errorhandler(500)
def internal_error_handler(e):
    return jsonify({
        'error': 'Errore interno del servizio AI'
    }), 500
