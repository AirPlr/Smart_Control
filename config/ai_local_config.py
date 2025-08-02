"""
Configurazione per IA locale
Gestisce le impostazioni per i modelli AI offline
"""

import os
from pathlib import Path
from typing import Dict, Any

class LocalAIConfig:
    """Configurazione per IA locale"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.models_dir = self.base_dir / 'models'
        self.models_dir.mkdir(exist_ok=True)
        
        # Configurazioni di default
        self.config = {
            # Modelli
            'dialogpt_model': 'microsoft/DialoGPT-medium',
            'embeddings_model': 'distiluse-base-multilingual-cased', 
            'models_cache_dir': str(self.models_dir),
            
            # Parametri generazione
            'max_new_tokens': 200,
            'temperature': 0.7,
            'do_sample': True,
            'similarity_threshold': 0.5,
            
            # Speech
            'speech_offline_enabled': True,
            'speech_language': 'it-IT',
            'speech_rate': 150,
            
            # Performance
            'use_gpu': True,  # Se disponibile
            'batch_size': 1,
            'cache_responses': True,
            'max_cache_size': 1000,
            
            # Debug
            'debug_mode': False,
            'log_responses': True
        }
        
        # Carica configurazione da file se esiste
        self._load_config()
    
    def _load_config(self):
        """Carica configurazione da file .env.ai"""
        config_file = self.base_dir / '.env.ai'
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip().lower()
                            value = value.strip()
                            
                            # Conversioni tipo
                            if value.lower() in ('true', 'false'):
                                value = value.lower() == 'true'
                            elif value.isdigit():
                                value = int(value)
                            elif value.replace('.', '').isdigit():
                                value = float(value)
                            
                            # Mapping variabili ambiente
                            env_mapping = {
                                'local_ai_enabled': 'enabled',
                                'model_cache_dir': 'models_cache_dir',
                                'dialogpt_model': 'dialogpt_model',
                                'embeddings_model': 'embeddings_model',
                                'speech_offline_enabled': 'speech_offline_enabled',
                                'ai_response_max_tokens': 'max_new_tokens',
                                'ai_response_temperature': 'temperature',
                                'similarity_threshold': 'similarity_threshold'
                            }
                            
                            config_key = env_mapping.get(key, key)
                            if config_key in self.config:
                                self.config[config_key] = value
                                
            except Exception as e:
                print(f"Errore caricamento configurazione: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Ottieni valore configurazione"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Imposta valore configurazione"""
        self.config[key] = value
    
    def is_enabled(self) -> bool:
        """Verifica se IA locale è abilitata"""
        return self.config.get('enabled', True)
    
    def get_model_path(self, model_type: str) -> str:
        """Ottieni percorso cache modello"""
        cache_dir = Path(self.config['models_cache_dir'])
        return str(cache_dir / model_type)
    
    def get_device(self) -> str:
        """Determina device per PyTorch"""
        try:
            import torch
            if self.config.get('use_gpu', True) and torch.cuda.is_available():
                return 'cuda'
            else:
                return 'cpu'
        except ImportError:
            return 'cpu'
    
    def save_config(self):
        """Salva configurazione su file"""
        config_file = self.base_dir / '.env.ai'
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write("# Configurazione IA Locale - AppointmentCRM\n\n")
                
                # Sezioni
                sections = {
                    'Generale': ['enabled', 'debug_mode', 'log_responses'],
                    'Modelli': ['dialogpt_model', 'embeddings_model', 'models_cache_dir'],
                    'Generazione': ['max_new_tokens', 'temperature', 'similarity_threshold'],
                    'Speech': ['speech_offline_enabled', 'speech_language', 'speech_rate'],
                    'Performance': ['use_gpu', 'batch_size', 'cache_responses', 'max_cache_size']
                }
                
                for section, keys in sections.items():
                    f.write(f"# {section}\n")
                    for key in keys:
                        if key in self.config:
                            value = self.config[key]
                            env_key = key.upper()
                            f.write(f"{env_key}={value}\n")
                    f.write("\n")
                    
        except Exception as e:
            print(f"Errore salvataggio configurazione: {e}")
    
    def get_generation_config(self) -> Dict[str, Any]:
        """Ottieni parametri per generazione testo"""
        return {
            'max_new_tokens': self.config['max_new_tokens'],
            'temperature': self.config['temperature'],
            'do_sample': self.config['do_sample'],
            'pad_token_id': None  # Verrà impostato dal tokenizer
        }
    
    def get_speech_config(self) -> Dict[str, Any]:
        """Ottieni parametri per speech processing"""
        return {
            'offline_enabled': self.config['speech_offline_enabled'],
            'language': self.config['speech_language'],
            'rate': self.config['speech_rate']
        }

# Istanza globale
local_ai_config = LocalAIConfig()
