# 🚀 App Ristrutturata - Sistema Gestione Appuntamenti Multiuser

Una versione completamente ristrutturata dell'applicazione originale con architettura modulare, sistema multiuser e dashboard mobile-ottimizzata.

## ✨ Nuove Caratteristiche

### 🔐 Sistema Multiuser
- **Admin**: Gestione completa sistema, utenti, console sicura, VPN management
- **Dealer**: Dashboard mobile-ottimizzata, statistiche personali, gestione appuntamenti
- **Viewer**: Solo visualizzazione statistiche e report

### 📱 Dashboard Mobile-First per Dealer
- Design responsive e mobile-ottimizzato
- Grafici interattivi con Chart.js
- Pull-to-refresh e PWA-like experience
- Azioni rapide per gestione veloce
- Statistiche in tempo reale

### 🛡️ Sicurezza Migliorata
- Console sistema con whitelist comandi sicuri
- Autenticazione Socket.IO
- Rate limiting su API
- Security headers automatici
- Validazione input robusta

### 🌐 VPN Management Integrato
- Interfaccia web per Tailscale
- Controllo stato e connessioni
- Comandi sicuri per diagnostica rete
- Supporto per WireGuard e OpenVPN

### 🏗️ Architettura Modulare
- Factory Pattern per app Flask
- Blueprint separati per funzionalità
- Modelli in moduli dedicati
- Servizi business logic separati
- Configurazione centralizzata

## 🚀 Avvio Rapido

### Installazione
```bash
cd app_restructured
pip install -r requirements.txt
```

### Primo Avvio con Dati Demo
```bash
python run.py --demo
```

### Avvio Standard
```bash
python run.py
```

### Avvio in Debug
```bash
python run.py --debug
```

## 🔗 URL Principali

| Funzionalità | URL | Descrizione |
|--------------|-----|-------------|
| **Dashboard Dealer** | `/dealer/dashboard` | Interface mobile-ottimizzata |
| **Admin Dashboard** | `/admin/dashboard` | Pannello amministrazione |
| **VPN Management** | `/admin/system/vpn` | Gestione Tailscale/VPN |
| **Console Sistema** | `/admin/system/console` | Terminal sicuro |
| **API REST** | `/api/*` | Endpoints API documentati |

## 👥 Utenti Default

### Amministratore
- **Username**: `admin`
- **Password**: `admin123`
- **Ruolo**: Accesso completo

### Dealer Demo (se --demo)
- **Username**: `mario.rossi` / `giulia.bianchi`
- **Password**: `demo123`
- **Ruolo**: Dashboard dealer personalizzata

## 📱 Caratteristiche Mobile Dashboard

### Performance
- ⚡ Caricamento < 2s su 3G
- 📊 Grafici optimizzati per touch
- 🔄 Auto-refresh dati
- 💾 Caching intelligente

### UX/UI
- 🎨 Design Material-inspired
- 🌓 Supporto dark mode automatico
- 👆 Gesture-friendly
- 📲 Install prompt PWA

### Funzionalità Dealer
- 📈 Statistiche personali in tempo reale
- 📅 Vista appuntamenti ottimizzata
- 🎯 KPI personalizzati
- 📤 Condivisione risultati

## 🔧 VPN Management

### Tailscale Integration
- ✅ Status monitoring in tempo reale
- 🔌 Start/stop da interfaccia web
- 🌐 Visualizzazione rete mesh
- 🔍 Diagnostica connessioni

### Comandi Sicuri Disponibili
```bash
tailscale status    # Stato connessioni
tailscale ip        # IP assegnati
tailscale netcheck  # Test connettività
tailscale ping      # Ping coordinator
```

### Altri VPN Supportati
- **WireGuard**: Controllo stato servizio
- **OpenVPN**: Gestione configurazioni
- **Network Info**: Diagnostica rete completa

## 🛡️ Sicurezza Implementata

### Console Sistema
- ✅ Whitelist comandi sicuri
- ❌ Blocco comandi pericolosi
- ⏱️ Timeout automatico (10s)
- 📝 Logging completo attività

### API Security
- 🚦 Rate limiting (100 req/min)
- 🔐 Autenticazione richiesta
- 📊 Monitoring abusi
- 🛡️ Input validation

### Headers di Sicurezza
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: [strict]
```

## 📊 Monitoring & Analytics

### Per Admin
- 👥 Gestione utenti completa
- 📈 Statistiche sistema globali
- 🔍 Log attività dettagliati
- ⚡ Health check automatici

### Per Dealer
- 📱 KPI personali mobile
- 📊 Conversioni e performance
- 📅 Calendario appuntamenti
- 🎯 Obiettivi e progress

## 🔄 Aggiornamenti dalla Versione Originale

### Problemi Risolti
- 🚫 Comando shell non sicuro → Console sicura con whitelist
- 🔑 Chiave hardcoded → Mantenuta per preview (come richiesto)
- 🏗️ Monolite 1500+ righe → Architettura modulare
- 📱 Non mobile-friendly → Dashboard mobile-first
- 👤 Single user → Sistema multiuser completo

### Nuove Funzionalità
- 🌐 VPN Management integrato
- 📊 Dashboard grafiche interattive
- 🔐 Sistema permessi granulare
- 📱 PWA-ready mobile experience
- 🔌 Real-time updates con SocketIO

## 🚀 Deployment Production

### Docker (Raccomandato)
```bash
# TODO: Creare Dockerfile
docker build -t app-restructured .
docker run -p 5000:5000 app-restructured
```

### Systemd Service
```bash
# TODO: Creare service file
sudo systemctl enable app-restructured
sudo systemctl start app-restructured
```

### Nginx Reverse Proxy
```nginx
# TODO: Configurazione nginx
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/nuova-funzionalita`)
3. Commit modifiche (`git commit -am 'Aggiunge nuova funzionalità'`)
4. Push branch (`git push origin feature/nuova-funzionalita`)
5. Crea Pull Request

## 📝 Changelog

### v2.0.0 (Ristrutturazione Completa)
- ✨ Sistema multiuser completo
- 📱 Dashboard mobile-ottimizzata
- 🌐 VPN Management integrato
- 🛡️ Sicurezza migliorata
- 🏗️ Architettura modulare
- 📊 Analytics avanzate

### v1.0.0 (Versione Originale)
- ⚠️ Monolite con problemi di sicurezza
- 👤 Single user
- 🖥️ Solo desktop
- 🔧 Console non sicura

## 📞 Support

Per supporto tecnico o domande:
- 📧 Email: [email protected]
- 💬 Chat: In-app support
- 📖 Wiki: [link to wiki]

---

**Nota**: Questa è una versione preview con chiave di crittografia hardcoded per scopi dimostrativi. In produzione, utilizzare variabili d'ambiente per le chiavi sensibili.
