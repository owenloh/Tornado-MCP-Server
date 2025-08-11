"""
Abstract LLM Provider interface and implementations for Tornado MCP Seismic Navigation.

This module provides a unified interface for different LLM providers (HTTP LLM, Gemini)
with fallback mechanisms and configuration management.

Adapted from Segy Reformat project with Tornado-specific optimizations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import json
import os
import time
from pathlib import Path
import logging
import sys

# Add Windows venv to path FIRST if on Windows
try:
    import platform
    if platform.system() == 'Windows':
        win_venv_path = Path(__file__).resolve().parent.parent.parent / '.win-venv' / 'Lib' / 'site-packages'
        if win_venv_path.exists():
            sys.path.insert(0, str(win_venv_path))
except Exception:
    pass  # Continue anyway for development/testing

import requests

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    success: bool
    error_message: Optional[str] = None
    provider_name: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def invoke_prompt(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """
        Invoke a prompt with the LLM provider.
        
        Args:
            system_prompt: System/context prompt
            user_prompt: User query/prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with the result
        """
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the provider with new settings."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass


class HTTPLLMProvider(LLMProvider):
    """HTTP LLM provider for OpenAI-compatible API endpoints."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_url = config.get('server_url') or config.get('base_url', 'http://localhost:11434')
        self.model = config.get('model', 'meta-llama/Meta-Llama-3.3-70B-Instruct')
        self.temperature = config.get('temperature', 0.4)
        self.max_tokens = config.get('max_tokens', 120000)
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.name = "HTTPLLMProvider"
    
    def _build_payload(self, system_prompt: str, user_content: str) -> Dict:
        """Build OpenAI-compatible API payload."""
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
    
    def _post(self, payload: Dict) -> Dict:
        """Make HTTP POST request to LLM API with proper error handling."""
        try:
            resp = requests.post(
                self.server_url, 
                json=payload, 
                verify=False, 
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            raise Exception(f"HTTP LLM request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to HTTP LLM server at {self.server_url}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP LLM server error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"HTTP LLM request failed: {str(e)}")
    
    def invoke_prompt(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Invoke HTTP LLM via OpenAI-compatible API."""
        start_time = time.time()
        
        # Override temperature and max_tokens if provided in kwargs
        original_temp = self.temperature
        original_max_tokens = self.max_tokens
        
        if 'temperature' in kwargs:
            self.temperature = kwargs['temperature']
        if 'max_tokens' in kwargs:
            self.max_tokens = kwargs['max_tokens']
        
        try:
            # Build API payload
            payload = self._build_payload(system_prompt, user_prompt)
            
            for attempt in range(self.max_retries):
                try:
                    logger.debug(f"HTTP LLM attempt {attempt + 1}/{self.max_retries}")
                    
                    # Make API request
                    resp = self._post(payload)
                    
                    # Extract content from response
                    if "choices" not in resp or len(resp["choices"]) == 0:
                        raise Exception("Invalid response format: no choices")
                    
                    content = resp["choices"][0]["message"]["content"].strip()
                    
                    # Clean up response - remove markdown formatting if present
                    if content.startswith("```json"):
                        content = content.replace("```json", "").replace("```", "").strip()
                    elif content.startswith("```"):
                        content = content.replace("```", "").strip()
                    
                    response_time = time.time() - start_time
                    
                    logger.info(f"HTTP LLM success in {response_time:.2f}s")
                    return LLMResponse(
                        content=content,
                        success=True,
                        provider_name=self.name,
                        response_time=response_time
                    )
                    
                except Exception as e:
                    logger.warning(f"HTTP LLM attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.max_retries - 1:
                        return LLMResponse(
                            content="",
                            success=False,
                            error_message=f"HTTP LLM failed after {self.max_retries} attempts: {str(e)}",
                            provider_name=self.name
                        )
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            
            return LLMResponse(
                content="",
                success=False,
                error_message="HTTP LLM max retries exceeded",
                provider_name=self.name
            )
            
        finally:
            # Restore original values
            self.temperature = original_temp
            self.max_tokens = original_max_tokens
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Update configuration."""
        self.config.update(config)
        self.server_url = config.get('server_url', self.server_url)
        self.model = config.get('model', self.model)
        self.timeout = config.get('timeout', self.timeout)
        self.max_retries = config.get('max_retries', self.max_retries)
    
    def is_available(self) -> bool:
        """Check if HTTP LLM service is available."""
        try:
            # Quick health check with minimal payload
            test_payload = {
                "model": self.model,
                "temperature": 0.1,
                "max_tokens": 10,
                "messages": [
                    {"role": "system", "content": "You are a test."},
                    {"role": "user", "content": "Hi"}
                ]
            }
            
            response = requests.post(
                self.server_url, 
                json=test_payload, 
                timeout=5,
                verify=False
            )
            is_available = response.status_code == 200
            logger.debug(f"HTTP LLM availability check: {is_available}")
            return is_available
        except Exception as e:
            logger.debug(f"HTTP LLM not available: {str(e)}")
            return False


class GeminiProvider(LLMProvider):
    """Gemini provider using Google's Gemini API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key') or os.getenv('GEMINI_API_KEY')
        self.model = config.get('model', 'gemini-1.5-flash')
        self.base_url = config.get('base_url', 'https://generativelanguage.googleapis.com/v1beta')
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 1)
        self.name = "GeminiProvider"
    
    def invoke_prompt(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResponse:
        """Invoke Gemini model via REST API."""
        if not self.api_key:
            return LLMResponse(
                content="",
                success=False,
                error_message="Gemini API key not configured",
                provider_name=self.name
            )
        
        start_time = time.time()
        
        # Gemini API format
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"System: {system_prompt}\n\nUser: {user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": kwargs.get('temperature', 0.7),
                "topP": kwargs.get('top_p', 0.9),
                "maxOutputTokens": kwargs.get('max_tokens', 4000)
            }
        }
        
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Gemini attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_time = time.time() - start_time
                    
                    # Extract content from Gemini response format
                    content = ""
                    if 'candidates' in result and len(result['candidates']) > 0:
                        candidate = result['candidates'][0]
                        if 'content' in candidate and 'parts' in candidate['content']:
                            parts = candidate['content']['parts']
                            if len(parts) > 0 and 'text' in parts[0]:
                                content = parts[0]['text']
                    
                    if not content:
                        raise Exception("Empty response from Gemini API")
                    
                    logger.info(f"Gemini success in {response_time:.2f}s")
                    return LLMResponse(
                        content=content,
                        success=True,
                        provider_name=self.name,
                        response_time=response_time
                    )
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"Gemini attempt {attempt + 1} failed: {error_msg}")
                    if attempt == self.max_retries - 1:
                        return LLMResponse(
                            content="",
                            success=False,
                            error_message=error_msg,
                            provider_name=self.name
                        )
                    time.sleep(2 ** attempt)
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Gemini request failed: {str(e)}"
                logger.warning(f"Gemini attempt {attempt + 1} failed: {error_msg}")
                if attempt == self.max_retries - 1:
                    return LLMResponse(
                        content="",
                        success=False,
                        error_message=error_msg,
                        provider_name=self.name
                    )
                time.sleep(2 ** attempt)
        
        return LLMResponse(
            content="",
            success=False,
            error_message="Gemini max retries exceeded",
            provider_name=self.name
        )
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Update configuration."""
        self.config.update(config)
        self.api_key = config.get('api_key', self.api_key)
        self.model = config.get('model', self.model)
        self.base_url = config.get('base_url', self.base_url)
        self.timeout = config.get('timeout', self.timeout)
        self.max_retries = config.get('max_retries', self.max_retries)
    
    def is_available(self) -> bool:
        """Check if Gemini API is available and configured."""
        if not self.api_key:
            logger.debug("Gemini not available: no API key")
            return False
        
        try:
            # Test with a simple request
            test_payload = {
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            response = requests.post(
                url,
                json=test_payload,
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )
            is_available = response.status_code == 200
            logger.debug(f"Gemini availability check: {is_available}")
            return is_available
        except Exception as e:
            logger.debug(f"Gemini not available: {str(e)}")
            return False


class LLMFactory:
    """Factory for creating and managing LLM provider instances with fallback support."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.providers = {}
        self._initialize_providers()
        logger.info(f"LLM Factory initialized with providers: {list(self.providers.keys())}")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from .env file and environment variables."""
        config = {
            'default_provider': os.getenv('DEFAULT_LLM_PROVIDER', 'http_llm'),
            'fallback_providers': os.getenv('FALLBACK_LLM_PROVIDERS', 'gemini').split(','),
            'http_llm': {
                'server_url': os.getenv('HTTP_LLM_SERVER_URL', 'http://ai.cgg.com/api/llama-3-3-70b/v1/chat/completions'),
                'model': os.getenv('HTTP_LLM_MODEL', 'meta-llama/Meta-Llama-3.3-70B-Instruct'),
                'temperature': float(os.getenv('HTTP_LLM_TEMPERATURE', '0.4')),
                'max_tokens': int(os.getenv('HTTP_LLM_MAX_TOKENS', '120000')),
                'timeout': int(os.getenv('HTTP_LLM_TIMEOUT', '30')),
                'max_retries': int(os.getenv('HTTP_LLM_MAX_RETRIES', '3'))
            },
            'gemini': {
                'api_key': os.getenv('GEMINI_API_KEY'),
                'model': os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'),
                'timeout': int(os.getenv('GEMINI_TIMEOUT', '30')),
                'max_retries': int(os.getenv('GEMINI_MAX_RETRIES', '1'))
            }
        }
        
        # Clean up fallback providers list
        config['fallback_providers'] = [p.strip() for p in config['fallback_providers'] if p.strip()]
        
        # Load from config file if provided
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                logger.info(f"Loaded additional config from {config_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load config file {config_path}: {e}")
        
        return config
    
    def _initialize_providers(self):
        """Initialize all configured providers."""
        try:
            if 'http_llm' in self.config:
                self.providers['http_llm'] = HTTPLLMProvider(self.config['http_llm'])
                logger.debug("HTTP LLM provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize HTTP LLM provider: {e}")
        
        try:
            if 'gemini' in self.config:
                self.providers['gemini'] = GeminiProvider(self.config['gemini'])
                logger.debug("Gemini provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini provider: {e}")
    
    def create_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Create a specific provider instance."""
        if provider_name in self.providers:
            return self.providers[provider_name]
        logger.warning(f"Provider '{provider_name}' not found")
        return None
    
    def get_default_provider(self) -> Optional[LLMProvider]:
        """Get the configured default provider."""
        default_name = self.config.get('default_provider', 'http_llm')
        provider = self.create_provider(default_name)
        if provider and provider.is_available():
            logger.debug(f"Default provider '{default_name}' is available")
            return provider
        logger.debug(f"Default provider '{default_name}' is not available")
        return None
    
    def get_fallback_providers(self) -> List[LLMProvider]:
        """Get list of fallback providers in order."""
        fallback_names = self.config.get('fallback_providers', [])
        if isinstance(fallback_names, str):
            fallback_names = [name.strip() for name in fallback_names.split(',')]
        
        providers = []
        for name in fallback_names:
            provider = self.create_provider(name)
            if provider:
                providers.append(provider)
        
        return providers
    
    def get_available_provider(self) -> Optional[LLMProvider]:
        """
        Get the first available provider (default or fallback).
        
        This is the main method that implements the fallback logic.
        """
        # Try default provider first
        default = self.get_default_provider()
        if default:
            logger.info(f"Using default provider: {default.name}")
            return default
        
        # Try fallback providers in order
        fallback_providers = self.get_fallback_providers()
        for provider in fallback_providers:
            if provider.is_available():
                logger.info(f"Using fallback provider: {provider.name}")
                return provider
            else:
                logger.debug(f"Fallback provider {provider.name} not available")
        
        logger.error("No LLM providers available")
        return None
    
    def get_provider_status(self) -> Dict[str, bool]:
        """Get availability status of all providers."""
        status = {}
        for name, provider in self.providers.items():
            try:
                status[name] = provider.is_available()
            except Exception as e:
                logger.warning(f"Error checking {name} availability: {e}")
                status[name] = False
        return status