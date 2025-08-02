/**
 * AI Assistant con Voice Processing e Streaming
 * Componente JavaScript per interazione IA avanzata
 */

class AIAssistant {
    constructor(options = {}) {
        this.containerId = options.containerId || 'ai-assistant';
        this.position = options.position || 'bottom-right';
        this.theme = options.theme || 'blue';
        this.userRole = options.userRole || 'viewer';
        this.pageContext = options.pageContext || '';
        
        // Stato componente
        this.isOpen = false;
        this.isRecording = false;
        this.isProcessing = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.eventSource = null;
        
        // Configurazione
        this.config = {
            apiBase: '/ai',
            maxMessageLength: 1000,
            recordingTimeout: 30000, // 30 secondi max
            streamDelay: 30 // ms tra caratteri
        };
        
        this.init();
    }
    
    init() {
        this.createElements();
        this.attachEventListeners();
        this.loadSuggestions();
        
        // Auto-show per mobile se dealer
        if (this.userRole === 'dealer' && this.isMobile()) {
            setTimeout(() => this.show(), 2000);
        }
    }
    
    createElements() {
        // Container principale
        const container = document.createElement('div');
        container.id = this.containerId;
        container.className = `ai-assistant ai-assistant-${this.position} ai-theme-${this.theme}`;
        
        container.innerHTML = `
            <!-- Toggle Button -->
            <div class="ai-toggle-btn" id="ai-toggle">
                <i class="fas fa-robot"></i>
                <span class="ai-status-indicator" id="ai-status"></span>
            </div>
            
            <!-- Main Panel -->
            <div class="ai-panel" id="ai-panel">
                <!-- Header -->
                <div class="ai-header">
                    <div class="ai-title">
                        <i class="fas fa-robot"></i>
                        <span>AI Assistant</span>
                        <span class="ai-role-badge">${this.userRole}</span>
                    </div>
                    <div class="ai-actions">
                        <button class="ai-btn ai-btn-sm" id="ai-clear" title="Pulisci chat">
                            <i class="fas fa-broom"></i>
                        </button>
                        <button class="ai-btn ai-btn-sm" id="ai-minimize" title="Minimizza">
                            <i class="fas fa-minus"></i>
                        </button>
                    </div>
                </div>
                
                <!-- Chat Area -->
                <div class="ai-chat-area" id="ai-chat">
                    <div class="ai-welcome-message">
                        <div class="ai-avatar">
                            <i class="fas fa-robot"></i>
                        </div>
                        <div class="ai-message-content">
                            <p>👋 Ciao! Sono il tuo assistente IA per AppointmentCRM.</p>
                            <p>Posso aiutarti con analisi, statistiche, gestione appuntamenti e molto altro.</p>
                            <p><strong>💬 Scrivi</strong> o <strong>🎤 parla</strong> per iniziare!</p>
                        </div>
                    </div>
                    
                    <!-- Suggestions -->
                    <div class="ai-suggestions" id="ai-suggestions"></div>
                </div>
                
                <!-- Input Area -->
                <div class="ai-input-area">
                    <!-- Voice Controls -->
                    <div class="ai-voice-controls" id="ai-voice-controls">
                        <button class="ai-voice-btn" id="ai-record-btn" title="Registra messaggio vocale">
                            <i class="fas fa-microphone"></i>
                            <span class="ai-recording-indicator"></span>
                        </button>
                        <div class="ai-recording-timer" id="ai-recording-timer"></div>
                    </div>
                    
                    <!-- Text Input -->
                    <div class="ai-text-input">
                        <textarea 
                            id="ai-message-input" 
                            placeholder="Scrivi il tuo messaggio o usa il microfono..."
                            rows="2"
                            maxlength="${this.config.maxMessageLength}"></textarea>
                        <button class="ai-send-btn" id="ai-send-btn" title="Invia messaggio">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    
                    <!-- Audio Player (nascosto) -->
                    <audio id="ai-audio-player" style="display: none;"></audio>
                </div>
                
                <!-- Status Bar -->
                <div class="ai-status-bar" id="ai-status-bar">
                    <div class="ai-typing-indicator" id="ai-typing">
                        <span></span><span></span><span></span>
                    </div>
                    <div class="ai-connection-status" id="ai-connection">
                        <i class="fas fa-circle"></i> Connesso
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
        
        // Riferimenti elementi
        this.elements = {
            container: container,
            toggleBtn: document.getElementById('ai-toggle'),
            panel: document.getElementById('ai-panel'),
            chatArea: document.getElementById('ai-chat'),
            messageInput: document.getElementById('ai-message-input'),
            sendBtn: document.getElementById('ai-send-btn'),
            recordBtn: document.getElementById('ai-record-btn'),
            clearBtn: document.getElementById('ai-clear'),
            minimizeBtn: document.getElementById('ai-minimize'),
            suggestions: document.getElementById('ai-suggestions'),
            statusBar: document.getElementById('ai-status-bar'),
            typingIndicator: document.getElementById('ai-typing'),
            audioPlayer: document.getElementById('ai-audio-player'),
            recordingTimer: document.getElementById('ai-recording-timer')
        };
    }
    
    attachEventListeners() {
        // Toggle panel
        this.elements.toggleBtn.addEventListener('click', () => this.toggle());
        
        // Send message
        this.elements.sendBtn.addEventListener('click', () => this.sendMessage());
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Voice recording
        this.elements.recordBtn.addEventListener('click', () => this.toggleRecording());
        
        // Clear chat
        this.elements.clearBtn.addEventListener('click', () => this.clearChat());
        
        // Minimize
        this.elements.minimizeBtn.addEventListener('click', () => this.hide());
        
        // Auto-resize textarea
        this.elements.messageInput.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px';
        });
        
        // Click outside to close (mobile)
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.elements.container.contains(e.target)) {
                if (this.isMobile()) {
                    this.hide();
                }
            }
        });
    }
    
    async loadSuggestions() {
        try {
            const response = await fetch(`${this.config.apiBase}/suggestions?page=${this.pageContext}`);
            const data = await response.json();
            
            if (data.suggestions) {
                this.renderSuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('Errore caricamento suggerimenti:', error);
        }
    }
    
    renderSuggestions(suggestions) {
        const container = this.elements.suggestions;
        container.innerHTML = '';
        
        if (suggestions.length === 0) return;
        
        const suggestionsList = document.createElement('div');
        suggestionsList.className = 'ai-suggestions-list';
        
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'ai-suggestion-btn';
            btn.textContent = suggestion;
            btn.addEventListener('click', () => {
                this.elements.messageInput.value = suggestion;
                this.sendMessage();
            });
            suggestionsList.appendChild(btn);
        });
        
        container.appendChild(suggestionsList);
    }
    
    toggle() {
        if (this.isOpen) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    show() {
        this.isOpen = true;
        this.elements.container.classList.add('ai-open');
        this.elements.messageInput.focus();
        
        // Scroll to bottom
        setTimeout(() => {
            this.scrollToBottom();
        }, 300);
    }
    
    hide() {
        this.isOpen = false;
        this.elements.container.classList.remove('ai-open');
        
        // Stop recording se attiva
        if (this.isRecording) {
            this.stopRecording();
        }
    }
    
    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        
        if (!message || this.isProcessing) return;
        
        // Aggiungi messaggio utente
        this.addMessage(message, 'user');
        
        // Pulisci input
        this.elements.messageInput.value = '';
        this.elements.messageInput.style.height = 'auto';
        
        // Nascondi suggerimenti
        this.elements.suggestions.style.display = 'none';
        
        try {
            await this.processAIResponse(message);
        } catch (error) {
            this.addMessage('Errore di connessione. Riprova tra qualche momento.', 'ai', 'error');
        }
    }
    
    async processAIResponse(message) {
        this.isProcessing = true;
        this.showTypingIndicator();
        
        // Crea container per risposta
        const responseContainer = this.addMessage('', 'ai', 'streaming');
        const responseContent = responseContainer.querySelector('.ai-message-text');
        
        try {
            const response = await fetch(`${this.config.apiBase}/stream-chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    page_context: this.pageContext
                })
            });
            
            if (!response.ok) throw new Error('Errore API');
            
            // Setup EventSource per streaming
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            let buffer = '';
            let fullResponse = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Mantieni l'ultima linea incompleta
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'chunk') {
                                fullResponse += data.content;
                                responseContent.textContent = fullResponse;
                                this.scrollToBottom();
                            } else if (data.type === 'end') {
                                // Fine streaming
                                this.hideTypingIndicator();
                                this.addAudioButton(responseContainer, fullResponse);
                            } else if (data.type === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (e) {
                            // Ignora errori parsing JSON
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Errore AI response:', error);
            responseContent.textContent = 'Errore nella risposta. Riprova.';
            responseContainer.classList.add('ai-message-error');
        } finally {
            this.isProcessing = false;
            this.hideTypingIndicator();
        }
    }
    
    addMessage(content, sender, type = 'normal') {
        const chatArea = this.elements.chatArea;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ai-message-${sender} ai-message-${type}`;
        
        const timestamp = new Date().toLocaleTimeString('it-IT', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        messageDiv.innerHTML = `
            <div class="ai-message-header">
                <div class="ai-avatar">
                    <i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>
                </div>
                <div class="ai-message-meta">
                    <span class="ai-sender">${sender === 'user' ? 'Tu' : 'AI Assistant'}</span>
                    <span class="ai-timestamp">${timestamp}</span>
                </div>
            </div>
            <div class="ai-message-content">
                <div class="ai-message-text">${this.formatMessage(content)}</div>
            </div>
        `;
        
        chatArea.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    addAudioButton(messageContainer, text) {
        if (!text || text.length > 200) return; // Non aggiungere per testi troppo lunghi
        
        const audioBtn = document.createElement('button');
        audioBtn.className = 'ai-audio-btn';
        audioBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
        audioBtn.title = 'Ascolta risposta';
        
        audioBtn.addEventListener('click', async () => {
            await this.playTextAsAudio(text, audioBtn);
        });
        
        const messageContent = messageContainer.querySelector('.ai-message-content');
        messageContent.appendChild(audioBtn);
    }
    
    async playTextAsAudio(text, button) {
        try {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            button.disabled = true;
            
            const response = await fetch(`${this.config.apiBase}/text-to-speech`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: text })
            });
            
            const data = await response.json();
            
            if (data.success && data.audio_data) {
                // Converti base64 in blob
                const audioBlob = this.base64ToBlob(data.audio_data, 'audio/wav');
                const audioUrl = URL.createObjectURL(audioBlob);
                
                this.elements.audioPlayer.src = audioUrl;
                await this.elements.audioPlayer.play();
                
                // Cleanup URL quando finito
                this.elements.audioPlayer.onended = () => {
                    URL.revokeObjectURL(audioUrl);
                };
            }
            
        } catch (error) {
            console.error('Errore riproduzione audio:', error);
        } finally {
            button.innerHTML = '<i class="fas fa-volume-up"></i>';
            button.disabled = false;
        }
    }
    
    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };
            
            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                await this.processVoiceInput(audioBlob);
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            // UI Updates
            this.elements.recordBtn.classList.add('ai-recording');
            this.startRecordingTimer();
            
            // Auto-stop dopo timeout
            setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, this.config.recordingTimeout);
            
        } catch (error) {
            console.error('Errore avvio registrazione:', error);
            alert('Errore accesso microfono. Verifica i permessi.');
        }
    }
    
    async stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;
        
        this.isRecording = false;
        this.mediaRecorder.stop();
        
        // UI Updates
        this.elements.recordBtn.classList.remove('ai-recording');
        this.stopRecordingTimer();
    }
    
    startRecordingTimer() {
        let seconds = 0;
        this.recordingTimerInterval = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            this.elements.recordingTimer.textContent = 
                `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }, 1000);
    }
    
    stopRecordingTimer() {
        if (this.recordingTimerInterval) {
            clearInterval(this.recordingTimerInterval);
            this.recordingTimerInterval = null;
        }
        this.elements.recordingTimer.textContent = '';
    }
    
    async processVoiceInput(audioBlob) {
        this.showTypingIndicator();
        
        try {
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            const response = await fetch(`${this.config.apiBase}/voice-input`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success && data.transcription) {
                // Aggiungi messaggio trascritto
                this.addMessage(data.transcription, 'user');
                
                // Processa risposta AI
                await this.processAIResponse(data.transcription);
            } else {
                this.addMessage(data.error || 'Errore riconoscimento vocale', 'ai', 'error');
            }
            
        } catch (error) {
            console.error('Errore processamento voce:', error);
            this.addMessage('Errore elaborazione audio', 'ai', 'error');
        } finally {
            this.hideTypingIndicator();
        }
    }
    
    showTypingIndicator() {
        this.elements.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.elements.typingIndicator.style.display = 'none';
    }
    
    clearChat() {
        const messages = this.elements.chatArea.querySelectorAll('.ai-message');
        messages.forEach(msg => msg.remove());
        
        // Mostra nuovamente i suggerimenti
        this.elements.suggestions.style.display = 'block';
        this.loadSuggestions();
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.elements.chatArea.scrollTop = this.elements.chatArea.scrollHeight;
        }, 50);
    }
    
    formatMessage(text) {
        if (!text) return '';
        
        // Converti markdown semplice
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }
    
    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }
    
    isMobile() {
        return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    // API Helper Methods
    async quickAnalysis(type = 'general', days = 30) {
        try {
            const response = await fetch(`${this.config.apiBase}/quick-analysis?type=${type}&days=${days}`);
            const data = await response.json();
            
            if (data.analysis) {
                this.addMessage(data.analysis, 'ai');
            }
        } catch (error) {
            console.error('Errore quick analysis:', error);
        }
    }
    
    // Public methods per integrazione
    sendTextMessage(message) {
        this.elements.messageInput.value = message;
        this.sendMessage();
    }
    
    setPageContext(context) {
        this.pageContext = context;
        this.loadSuggestions();
    }
    
    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        if (this.recordingTimerInterval) {
            clearInterval(this.recordingTimerInterval);
        }
        
        if (this.elements.container) {
            this.elements.container.remove();
        }
    }
}

// Auto-inizializzazione globale
window.AIAssistant = AIAssistant;

// Inizializzazione automatica quando DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    // Rileva contesto pagina
    const pageContext = document.body.getAttribute('data-page') || 
                       window.location.pathname.split('/').pop() || 'dashboard';
    
    // Rileva ruolo utente
    const userRole = document.body.getAttribute('data-user-role') || 'viewer';
    
    // Inizializza assistente se non già presente
    if (!window.aiAssistant) {
        window.aiAssistant = new AIAssistant({
            pageContext: pageContext,
            userRole: userRole,
            theme: document.body.getAttribute('data-theme') || 'blue'
        });
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K per aprire AI Assistant
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (window.aiAssistant) {
            window.aiAssistant.show();
        }
    }
});
