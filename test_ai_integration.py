#!/usr/bin/env python3
"""
Test completo integrazione Smart Control AI con Ollama
Verifica tutte le funzionalità dell'assistente IA
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

def test_ollama_service():
    """Test servizio Ollama standalone"""
    print("🧪 Test 1: Servizio Ollama...")
    
    try:
        import ollama
        client = ollama.Client()
        
        # Test connessione
        models = client.list()
        print(f"✅ Connessione Ollama OK - {len(models['models'])} modelli disponibili")
        
        # Verifica modello Llama 3.2
        model_names = [m['name'] for m in models['models']]
        if 'llama3.2:3b' not in model_names:
            print("❌ Modello llama3.2:3b non trovato!")
            return False
            
        print("✅ Modello llama3.2:3b disponibile")
        
        # Test generazione
        response = client.chat(
            model='llama3.2:3b',
            messages=[{
                'role': 'user',
                'content': 'Rispondi in italiano: Ciao!'
            }],
            stream=False
        )
        
        print(f"✅ Test generazione OK: {response['message']['content'][:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Errore test Ollama: {e}")
        return False

def test_ai_config():
    """Test configurazione AI"""
    print("\n🧪 Test 2: Configurazione AI...")
    
    try:
        # Test import configurazione
        sys.path.append('/opt/smart_control')
        from config.ai_config_new import AI_CONFIG, OLLAMA_CONFIG
        
        print(f"✅ Configurazione caricata:")
        print(f"  - Ollama AI: {AI_CONFIG.get('ollama_ai', False)}")
        print(f"  - API Access: {AI_CONFIG.get('api_access', False)}")
        print(f"  - Auto Correction: {AI_CONFIG.get('auto_correction', False)}")
        print(f"  - Modello: {OLLAMA_CONFIG['model']}")
        print(f"  - Host: {OLLAMA_CONFIG['host']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore configurazione: {e}")
        return False

def test_ai_service():
    """Test servizio AI completo"""
    print("\n🧪 Test 3: Servizio AI...")
    
    try:
        sys.path.append('/opt/smart_control')
        from services.ai_service_new import OllamaAIService
        
        # Inizializza servizio
        service = OllamaAIService()
        
        if not service.client:
            print("❌ Client Ollama non inizializzato")
            return False
            
        print("✅ Servizio AI inizializzato")
        
        # Test contesto
        context = {
            'user_role': 'admin',
            'page_context': 'dashboard',
            'timestamp': datetime.now().isoformat()
        }
        
        # Test query semplice
        print("🔄 Test query semplice...")
        response_chunks = []
        for chunk in service.generate_response_stream(
            "Ciao, presentati come assistente Smart Control",
            context
        ):
            response_chunks.append(chunk)
            
        response = ''.join(response_chunks)
        print(f"✅ Risposta generata ({len(response)} caratteri)")
        print(f"Anteprima: {response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore servizio AI: {e}")
        return False

def test_api_integration():
    """Test integrazione API"""
    print("\n🧪 Test 4: Integrazione API...")
    
    try:
        sys.path.append('/opt/smart_control')
        from services.ai_service_new import APIClient
        
        # Inizializza client API
        api_client = APIClient(base_url="http://localhost:8000")
        
        # Test connessione (potrebbero fallire se app non è in esecuzione)
        print("🔄 Test connessioni API...")
        
        test_endpoints = [
            ('/api/clients', 'Clienti'),
            ('/api/appointments/today', 'Appuntamenti oggi'),
            ('/api/stats/overview', 'Statistiche')
        ]
        
        working_apis = 0
        for endpoint, name in test_endpoints:
            try:
                result = api_client._make_request('GET', endpoint)
                if result.get('success'):
                    print(f"✅ API {name} funzionante")
                    working_apis += 1
                else:
                    print(f"⚠️ API {name} non risponde (normale se app non è in esecuzione)")
            except Exception as e:
                print(f"⚠️ API {name} errore: {str(e)[:50]}...")
        
        print(f"📊 API funzionanti: {working_apis}/{len(test_endpoints)}")
        return True
        
    except Exception as e:
        print(f"❌ Errore test API: {e}")
        return False

def test_ai_with_api_simulation():
    """Test AI con simulazione API"""
    print("\n🧪 Test 5: AI con simulazione richieste dati...")
    
    try:
        sys.path.append('/opt/smart_control')
        from services.ai_service_new import OllamaAIService
        
        service = OllamaAIService()
        
        if not service.client:
            print("❌ Servizio AI non disponibile")
            return False
        
        context = {
            'user_role': 'dealer',
            'page_context': 'clients',
            'timestamp': datetime.now().isoformat()
        }
        
        # Test queries che dovrebbero attivare chiamate API
        test_queries = [
            "Quanti clienti ho in totale?",
            "Mostrami gli appuntamenti di oggi",
            "Quali sono le statistiche più importanti?",
            "Chi è il mio cliente più importante?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔄 Test Query {i}: {query}")
            
            try:
                response_chunks = []
                start_time = time.time()
                
                for chunk in service.generate_response_stream(query, context):
                    response_chunks.append(chunk)
                
                response = ''.join(response_chunks)
                elapsed = time.time() - start_time
                
                print(f"✅ Risposta generata in {elapsed:.2f}s")
                print(f"Lunghezza: {len(response)} caratteri")
                print(f"Anteprima: {response[:150]}...")
                
            except Exception as e:
                print(f"❌ Errore query {i}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test completo: {e}")
        return False

def main():
    """Esegue tutti i test"""
    print("🚀 SMART CONTROL AI - TEST COMPLETO INTEGRAZIONE")
    print("=" * 60)
    
    tests = [
        test_ollama_service,
        test_ai_config,
        test_ai_service,
        test_api_integration,
        test_ai_with_api_simulation
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} fallito: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("📊 RISULTATI FINALI:")
    print(f"✅ Test superati: {passed}")
    print(f"❌ Test falliti: {failed}")
    print(f"📈 Successo: {passed/(passed+failed)*100:.1f}%")
    
    if passed == len(tests):
        print("\n🎉 TUTTI I TEST SUPERATI! Smart Control AI è pronto!")
        return 0
    else:
        print(f"\n⚠️ {failed} test falliti. Controlla i log sopra per i dettagli.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
