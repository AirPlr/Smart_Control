#!/bin/bash

# Smart Control - Setup Script per Ubuntu Server
# Installa tutte le dipendenze necessarie per l'assistente IA con Llama 3.2 3B

set -e

echo "🚀 Smart Control - Setup Ubuntu Server con AI Assistant"
echo "=============================================="

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Verifica che lo script sia eseguito come root o con sudo
if [[ $EUID -ne 0 ]]; then
   error "Questo script deve essere eseguito come root o con sudo"
fi

# Aggiorna il sistema
log "Aggiornamento del sistema..."
apt update && apt upgrade -y

# Installa dipendenze di sistema
log "Installazione dipendenze di sistema..."
apt install -y \
    software-properties-common \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    sqlite3 \
    libsqlite3-dev \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev

# Installa Python 3.11 se non presente
log "Verifica installazione Python 3.11..."
if ! command -v python3.11 &> /dev/null; then
    log "Installazione Python 3.11..."
    add-apt-repository ppa:deadsnakes/ppa -y
    apt update
    apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils
fi

# Installa pip per Python 3.11
log "Installazione pip per Python 3.11..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Verifica installazione Python
python3.11 --version
python3.11 -m pip --version

# Installa Node.js (per eventuali dipendenze frontend)
log "Installazione Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Crea utente per l'applicazione se non esiste
APP_USER="smartcontrol"
if ! id "$APP_USER" &>/dev/null; then
    log "Creazione utente applicazione: $APP_USER"
    useradd -m -s /bin/bash $APP_USER
    usermod -aG sudo $APP_USER
fi

# Crea directory applicazione
APP_DIR="/opt/smart_control"
log "Creazione directory applicazione: $APP_DIR"
mkdir -p $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

# Installa Ollama per gestione modelli IA
log "Installazione Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Configura Ollama come servizio
log "Configurazione servizio Ollama..."
cat > /etc/systemd/system/ollama.service << EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=$APP_USER
Group=$APP_USER
Restart=always
RestartSec=3
Environment="HOME=/home/$APP_USER"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=default.target
EOF

# Abilita e avvia Ollama
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Attendi che Ollama sia pronto
log "Attesa avvio Ollama..."
sleep 10

# Scarica il modello Llama 3.2 3B
log "Download modello Llama 3.2 3B (questo può richiedere diversi minuti)..."
su - $APP_USER -c "ollama pull llama3.2:3b"

# Verifica che il modello sia installato
log "Verifica installazione modello..."
su - $APP_USER -c "ollama list"

# Test di base del modello
log "Test di base del modello Llama 3.2..."
su - $APP_USER -c "echo 'Ciao, come stai?' | ollama run llama3.2:3b" || warn "Test modello fallito - continuando..."

# Installa Redis per caching (opzionale ma consigliato)
log "Installazione Redis..."
apt install -y redis-server
systemctl enable redis-server
systemctl start redis-server

# Installa dipendenze audio per speech recognition (opzionali)
log "Installazione dipendenze audio..."
apt install -y \
    portaudio19-dev \
    python3.11-dev \
    libasound2-dev \
    libsndfile1 \
    ffmpeg

# Configura firewall base
log "Configurazione firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22    # SSH
ufw allow 5000  # Flask dev server
ufw allow 8000  # Gunicorn
ufw allow 11434 # Ollama

log "Creazione script di setup ambiente Python..."
cat > $APP_DIR/setup_python_env.sh << 'EOF'
#!/bin/bash

# Script per setup ambiente Python per Smart Control
echo "🐍 Setup ambiente Python per Smart Control..."

# Vai alla directory dell'applicazione
cd /opt/smart_control

# Crea ambiente virtuale Python
echo "Creazione ambiente virtuale..."
python3.11 -m venv venv

# Attiva ambiente virtuale
source venv/bin/activate

# Aggiorna pip
pip install --upgrade pip setuptools wheel

# Installa dipendenze base
echo "Installazione dipendenze base..."
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==3.0.5
pip install Flask-Login==0.6.3
pip install Flask-Migrate==4.0.5
pip install Flask-SocketIO==5.3.6
pip install eventlet==0.33.3
pip install Flask-Limiter==3.5.0
pip install Flask-WTF==1.2.1
pip install cryptography==41.0.7
pip install SQLAlchemy==2.0.23
pip install XlsxWriter==3.1.9
pip install reportlab==4.0.6
pip install python-dateutil==2.8.2
pip install psutil==5.9.6
pip install requests==2.31.0
pip install python-dotenv==1.0.0
pip install gunicorn==21.2.0
pip install redis==5.0.1

# Installa client Ollama
echo "Installazione client Ollama..."
pip install ollama

# Installa dipendenze AI opzionali
echo "Installazione dipendenze AI opzionali..."
pip install numpy==1.24.3
pip install regex==2023.10.3

# Installa speech recognition (opzionale)
echo "Tentativo installazione Speech Recognition..."
pip install SpeechRecognition==3.10.0 || echo "Speech Recognition fallito - continuando..."
pip install pyttsx3==2.90 || echo "Text-to-Speech fallito - continuando..."

echo "✅ Ambiente Python configurato!"
echo "Per attivare l'ambiente: source /opt/smart_control/venv/bin/activate"
EOF

chmod +x $APP_DIR/setup_python_env.sh
chown $APP_USER:$APP_USER $APP_DIR/setup_python_env.sh

# Esegui setup ambiente Python
log "Esecuzione setup ambiente Python..."
su - $APP_USER -c "$APP_DIR/setup_python_env.sh"

# Crea script di avvio
log "Creazione script di avvio..."
cat > $APP_DIR/start_app.sh << 'EOF'
#!/bin/bash

# Script di avvio Smart Control
cd /opt/smart_control
source venv/bin/activate

# Verifica che Ollama sia in esecuzione
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    echo "⚠️ Ollama non è in esecuzione. Avviando..."
    sudo systemctl start ollama
    sleep 5
fi

# Avvia l'applicazione
export FLASK_ENV=production
export FLASK_APP=app.py

# Inizializza database se necessario
python setup_database.py

# Avvia con Gunicorn (produzione)
gunicorn --bind 0.0.0.0:8000 --workers 4 --worker-class eventlet -w 1 app:app
EOF

chmod +x $APP_DIR/start_app.sh
chown $APP_USER:$APP_USER $APP_DIR/start_app.sh

# Crea servizio systemd per l'applicazione
log "Creazione servizio systemd..."
cat > /etc/systemd/system/smart-control.service << EOF
[Unit]
Description=Smart Control Application
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/start_app.sh
Restart=always
RestartSec=3
Environment="PATH=/opt/smart_control/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

# Ricarica systemd
systemctl daemon-reload

# Crea script di test Ollama
log "Creazione script di test..."
cat > $APP_DIR/test_ollama.py << 'EOF'
#!/usr/bin/env python3

import ollama
import json

def test_ollama_connection():
    """Test connessione e modello Ollama"""
    try:
        print("🧪 Test connessione Ollama...")
        
        # Test connessione
        client = ollama.Client()
        models = client.list()
        print(f"✅ Connessione OK. Modelli disponibili: {len(models['models'])}")
        
        for model in models['models']:
            print(f"  - {model['name']}")
        
        # Test generazione testo
        if any('llama3.2:3b' in model['name'] for model in models['models']):
            print("\n🤖 Test generazione testo con Llama 3.2 3B...")
            
            response = client.chat(model='llama3.2:3b', messages=[
                {
                    'role': 'user',
                    'content': 'Ciao! Sei l\'assistente IA di Smart Control. Presentati brevemente in italiano e spiega cosa puoi fare.',
                }
            ])
            
            print("Risposta del modello:")
            print(response['message']['content'])
            
            # Test accesso API simulato
            print("\n🔗 Test funzionalità API...")
            api_test_response = client.chat(model='llama3.2:3b', messages=[
                {
                    'role': 'user',
                    'content': 'Come puoi aiutarmi con la gestione clienti in Smart Control? Elenca 3 funzionalità principali.',
                }
            ])
            
            print("Test API Response:")
            print(api_test_response['message']['content'])
            print("\n✅ Test completato con successo!")
        else:
            print("⚠️ Modello llama3.2:3b non trovato")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_ollama_connection()
EOF

chmod +x $APP_DIR/test_ollama.py
chown $APP_USER:$APP_USER $APP_DIR/test_ollama.py

# Crea script di test integrazione completa
log "Creazione script di test integrazione completa..."
cat > $APP_DIR/test_integration.py << 'EOF'
#!/usr/bin/env python3

import sys
import os
import subprocess

def run_test():
    """Esegue test completo integrazione"""
    print("🧪 Test integrazione Smart Control AI...")
    
    # Aggiungi path dell'applicazione
    sys.path.insert(0, '/opt/smart_control')
    
    try:
        # Test import nuovo servizio AI
        from services.ai_service_new import OllamaAIService, APIClient
        from config.ai_config_new import AI_CONFIG, OLLAMA_CONFIG
        
        print("✅ Import moduli AI riuscito")
        print(f"Configurazione: Ollama={AI_CONFIG.get('ollama_ai')}, API={AI_CONFIG.get('api_access')}")
        
        # Test inizializzazione
        service = OllamaAIService()
        if service.client:
            print("✅ Servizio Ollama inizializzato correttamente")
        else:
            print("⚠️ Servizio Ollama non disponibile")
            
        # Test API client
        api_client = APIClient()
        print("✅ Client API inizializzato")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
EOF

chmod +x $APP_DIR/test_integration.py
chown $APP_USER:$APP_USER $APP_DIR/test_integration.py

# Informazioni finali
log "✅ Setup completato!"
echo ""
echo "=============================================="
echo "📋 RIEPILOGO INSTALLAZIONE"
echo "=============================================="
echo ""
echo "🔧 Servizi installati:"
echo "  - Python 3.11 con ambiente virtuale"
echo "  - Ollama con Llama 3.2 3B"
echo "  - Redis per caching"
echo "  - Node.js 20.x"
echo ""
echo "📁 Directory applicazione: $APP_DIR"
echo "👤 Utente applicazione: $APP_USER"
echo ""
echo "🚀 Comandi utili:"
echo "  - Test Ollama base: sudo -u $APP_USER $APP_DIR/test_ollama.py"
echo "  - Test integrazione: sudo -u $APP_USER python3 $APP_DIR/test_integration.py"  
echo "  - Test completo: sudo -u $APP_USER python3 $APP_DIR/test_ai_integration.py"
echo "  - Avvio app: sudo systemctl start smart-control"
echo "  - Stato app: sudo systemctl status smart-control"
echo "  - Log app: sudo journalctl -f -u smart-control"
echo "  - Stato Ollama: sudo systemctl status ollama"
echo "  - Chat con modello: sudo -u $APP_USER ollama run llama3.2:3b"
echo ""
echo "🌐 Porte aperte:"
echo "  - 8000: Applicazione principale"
echo "  - 11434: Ollama API"
echo ""
echo "⚠️  PROSSIMI PASSI:"
echo "1. Copia i file dell'applicazione in $APP_DIR"
echo "2. Modifica le configurazioni AI per usare Ollama"
echo "3. Testa la connessione: sudo -u $APP_USER $APP_DIR/test_ollama.py"
echo "4. Avvia l'applicazione: sudo systemctl start smart-control"
echo ""
warn "IMPORTANTE: Assicurati di avere almeno 8GB di RAM per il modello Llama 3.2 3B"
echo ""
