"""
AI client for unified access to different AI providers.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
import logging

from janitor.config import Config, AIConfig


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def complete(self, prompt: str, max_tokens: int, 
                 temperature: float) -> str:
        """Generate a completion for the given prompt."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is available."""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize with API key and model."""
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def complete(self, prompt: str, max_tokens: int, 
                 temperature: float) -> str:
        """Generate completion using OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            split_prompt = prompt.split("## Refactored Code:")
            system_content = split_prompt[0] if split_prompt else prompt
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": "## Refactored Code:"}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content or ""
            
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            client.models.list()
            return True
        except Exception:
            return False


class AnthropicProvider(AIProvider):
    """Anthropic API provider."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """Initialize with API key and model."""
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def complete(self, prompt: str, max_tokens: int, 
                 temperature: float) -> str:
        """Generate completion using Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            split_prompt = prompt.split("## Refactored Code:")
            system_content = split_prompt[0] if split_prompt else prompt
            
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_content,
                messages=[{"role": "user", "content": "## Refactored Code:"}]
            )
            
            return response.content[0].text if response.content else ""
            
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            return True
        except Exception:
            return False


class OllamaProvider(AIProvider):
    """Local Ollama provider for open-source models."""
    
    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "llama3"):
        """Initialize with base URL and model."""
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def complete(self, prompt: str, max_tokens: int, 
                 temperature: float) -> str:
        """Generate completion using Ollama API."""
        import requests
        
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '')
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama API error: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if Ollama is running and model is available."""
        import requests
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                return any(self.model in m for m in models)
            return False
        except Exception:
            return False

class GroqProvider(AIProvider):
    """Groq API provider."""
    
    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        """Initialize with API key and model."""
        self.api_key = api_key
        # Default to a strong model on Groq if not specified via env
        self.model = model
        self.logger = logging.getLogger(__name__)
    
    def complete(self, prompt: str, max_tokens: int, 
                 temperature: float) -> str:
        """Generate completion using Groq API."""
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            
            # Groq implementation of system prompt
            split_prompt = prompt.split("## Refactored Code:")
            system_content = split_prompt[0] if split_prompt else prompt
            
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": "## Refactored Code:"}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False,
                stop=None,
            )
            
            return completion.choices[0].message.content or ""
            
        except ImportError:
            raise ImportError("Groq package not installed. Run: pip install groq")
        except Exception as e:
            self.logger.error(f"Groq API error: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if Groq API is accessible."""
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            client.models.list()
            return True
        except Exception:
            return False


class AIClient:
    """Unified client for AI providers."""
    
    def __init__(self, config: Config):
        """Initialize with configuration."""
        self.config = config
        self.ai_config = config.ai
        self.logger = logging.getLogger(__name__)
        self._provider: Optional[AIProvider] = None
    
    @property
    def provider(self) -> AIProvider:
        """Lazy initialization of provider."""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider
    
    def _create_provider(self) -> AIProvider:
        """Create the appropriate provider based on configuration."""
        provider_type = self.ai_config.provider.lower()
        
        if provider_type == "openai":
            api_key = self.ai_config.api_key or self._get_env_key("OPENAI_API_KEY")
            return OpenAIProvider(api_key, self.ai_config.model)
        
        if provider_type == "anthropic":
            api_key = self.ai_config.api_key or self._get_env_key("ANTHROPIC_API_KEY")
            return AnthropicProvider(api_key, self.ai_config.model)
            
        if provider_type == "groq":
            api_key = self.ai_config.api_key or self._get_env_key("GROQ_API_KEY")
            return GroqProvider(api_key, self.ai_config.model)
        
        if provider_type == "ollama":
            return OllamaProvider(model=self.ai_config.model)
        
        raise ValueError(f"Unknown AI provider: {provider_type}")
    
    def _get_env_key(self, env_name: str) -> str:
        """Get API key from environment."""
        import os
        key = os.getenv(env_name)
        if not key:
            raise ValueError(
                f"API key not found. Set {env_name} environment variable "
                "or provide in configuration."
            )
        return key
    
    def complete(self, prompt: str, max_tokens: int = 4000,
                 temperature: float = 0.2) -> str:
        """Generate completion using configured provider."""
        return self.provider.complete(prompt, max_tokens, temperature)
    
    def health_check(self) -> bool:
        """Check if the configured provider is available."""
        return self.provider.health_check()
