# Smart Control AI Assistant con Ollama e Llama 3.2 3B

## 🤖 Panoramica

L'assistente IA di Smart Control è un sistema avanzato basato su **Llama 3.2 3B** tramite **Ollama**, progettato specificamente per la gestione di clienti, appuntamenti e analisi dati.

## ✨ Funzionalità Principali

### 🎯 Capacità Core
- **Gestione Clienti**: Ricerca, analisi e segmentazione clienti
- **Appuntamenti**: Ottimizzazione calendario e gestione conflitti
- **Analisi Dati**: Report automatici, KPI e trend analysis
- **API Integration**: Accesso in tempo reale ai dati del sistema
- **Auto-correzione**: Sistema di correzione automatica degli errori

### 🔗 Integrazione API
L'assistente può accedere direttamente alle API del sistema per:

```
GET /api/clients          - Lista clienti
GET /api/clients/{id}     - Dettagli cliente
GET /api/appointments     - Lista appuntamenti  
GET /api/appointments/today - Appuntamenti giornalieri
GET /api/stats/overview   - Panoramica statistiche
GET /api/stats/revenue    - Analisi ricavi
```

### 🧠 Sistema di Prompt Avanzato

Il sistema utilizza un prompt specializzato che include:
- **Identità professionale** come assistente Smart Control
- **Accesso alle API** per dati in tempo reale
- **Contesto aware** (pagina corrente, ruolo utente)
- **Auto-correzione** per errori API
- **Risposte sempre in italiano**

## 🛠️ Architettura Tecnica

### Componenti Principali

1. **OllamaAIService** (`services/ai_service_new.py`)
   - Gestione comunicazione con Ollama
   - Streaming responses
   - Cache conversazioni
   - Sistema retry automatico

2. **APIClient** (integrato)
   - Client HTTP per API Smart Control
   - Gestione errori e retry
   - Formattazione dati per AI

3. **Configurazione** (`config/ai_config_new.py`)
   - Impostazioni Ollama
   - Prompt system avanzato
   - Configurazione contesti

### Flusso di Elaborazione

```
User Query → Context Analysis → API Calls → Prompt Building → Ollama → Streaming Response
```

## 🚀 Setup e Installazione

### Prerequisiti
- Ubuntu Server 20.04+
- Almeno 8GB RAM
- Python 3.11+
- Connessione internet (per download modello)

### Installazione Automatica

```bash
# Scarica e esegui script setup
curl -o setup_ubuntu_ai.sh https://raw.githubusercontent.com/AirPlr/Smart_Control/main/setup_ubuntu_ai.sh
chmod +x setup_ubuntu_ai.sh
sudo ./setup_ubuntu_ai.sh
```

### Installazione Manuale

1. **Installa Ollama**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. **Scarica modello Llama 3.2 3B**:
```bash
ollama pull llama3.2:3b
```

3. **Installa dipendenze Python**:
```bash
pip install ollama requests flask
```

## 🧪 Test e Verifica

### Test Base Ollama
```bash
python3 /opt/smart_control/test_ollama.py
```

### Test Integrazione Completa
```bash
python3 /opt/smart_control/test_ai_integration.py
```

### Test Manuale
```bash
# Chat diretta con modello
ollama run llama3.2:3b

# Test API Smart Control
curl http://localhost:8000/ai/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Ciao, quanti clienti ho?"}'
```

## 💬 Esempi di Utilizzo

### Query Supportate

```javascript
// Gestione clienti
"Quanti clienti ho in totale?"
"Mostrami i clienti più importanti"
"Analizza la segmentazione clienti"

// Appuntamenti
"Cosa ho in agenda oggi?"
"Ci sono conflitti nel calendario?"
"Ottimizza i miei appuntamenti"

// Analisi e Report
"Genera un report mensile"
"Quali sono i KPI principali?"
"Analizza il trend dei ricavi"

// Assistenza Generale
"Come posso migliorare le performance?"
"Suggerimenti per aumentare i ricavi"
"Analisi della soddisfazione clienti"
```

### Esempio Risposta AI

**Input**: "Quanti appuntamenti ho oggi?"

**Processo interno**:
1. Analisi query → rileva necessità "appointments_today"
2. Chiamata API → `GET /api/appointments/today`
3. Formattazione dati per prompt
4. Generazione risposta con Llama 3.2

**Output**: "Oggi hai 3 appuntamenti programmati: Mario Rossi alle 09:00, Laura Bianchi alle 14:30 e Giuseppe Verdi alle 16:00. Il tuo calendario è ben distribuito con pause adeguate tra gli incontri."

## ⚙️ Configurazione Avanzata

### Variabili Ambiente

```bash
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3.2:3b"
export OLLAMA_TIMEOUT="120"
export OLLAMA_TEMPERATURE="0.7"
export OLLAMA_MAX_TOKENS="2048"
```

### Personalizzazione Prompt

Modifica `SYSTEM_PROMPT` in `config/ai_config_new.py` per:
- Cambiare personalità AI
- Aggiungere nuove funzionalità
- Modificare comportamenti specifici

### Tuning Performance

```python
# In ai_config_new.py
OLLAMA_CONFIG = {
    'temperature': 0.7,    # Creatività (0.0-1.0)
    'max_tokens': 2048,    # Lunghezza risposta
    'timeout': 120,        # Timeout secondi
}
```

## 🔍 Troubleshooting

### Problemi Comuni

**Ollama non risponde**:
```bash
sudo systemctl status ollama
sudo systemctl restart ollama
```

**Modello non trovato**:
```bash
ollama list
ollama pull llama3.2:3b
```

**Errori API Smart Control**:
```bash
# Verifica servizio
sudo systemctl status smart-control

# Check logs
sudo journalctl -f -u smart-control
```

**Performance lente**:
- Verifica RAM disponibile (minimo 8GB)
- Controlla CPU usage
- Considera modello più piccolo (llama3.2:1b)

### Log e Debug

```bash
# Log Ollama
sudo journalctl -f -u ollama

# Log applicazione
tail -f /opt/smart_control/logs/ai.log

# Debug mode
export FLASK_DEBUG=1
export AI_DEBUG=1
```

## 🔒 Sicurezza

- **Rate Limiting**: 30 richieste/minuto per utente
- **Autenticazione**: Richiesto login per API chat
- **Sanitizzazione**: Input sanitizzati prima del processing
- **Timeout**: Protezione contro hanging requests
- **Local Processing**: Tutti i dati rimangono sul server locale

## 📈 Monitoraggio

### Metriche Disponibili
- Tempo risposta medio
- Numero query per utente
- Successo/errore ratio
- Usage modello AI
- Performance API calls

### Dashboard Monitoring
Accesso via `/admin/ai-monitoring` per utenti admin.

## 🛣️ Roadmap

### Versioni Future
- [ ] Supporto multilingue
- [ ] Integrazione speech-to-text
- [ ] Modelli specializzati per settore
- [ ] Plugin per CRM esterni
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard

---

## 📞 Supporto

Per problemi o domande:
- **Issues**: GitHub Issues
- **Documentazione**: `/docs/ai-assistant`
- **Log Debug**: `/admin/logs`

**Versione**: 2.0.0 con Ollama + Llama 3.2 3B
**Ultimo aggiornamento**: Agosto 2025
