"""LLM provider abstraction layer."""
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from dotenv import load_dotenv, set_key
from pathlib import Path

load_dotenv()

class LLMProviderError(Exception):
    def __init__(self, message: str, provider: str = ""):
        super().__init__(message)
        self.provider = provider

@dataclass
class LLMConfig:
    provider: str = "mock"
    api_key: str = ""
    model: str = ""
    azure_endpoint: str = ""
    azure_deployment: str = ""
    azure_api_version: str = "2024-08-01-preview"

class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str: ...
    @abstractmethod
    def name(self) -> str: ...

class MockProvider(LLMProvider):
    def name(self): return "Mock (sem custo)"
    def complete(self, system, user, max_tokens=4096): return '{"error":"mock"}'

class AnthropicProvider(LLMProvider):
    DEFAULT_MODEL = "claude-haiku-4-5-20251001"
    def __init__(self, api_key, model=""):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
    def name(self): return f"Claude ({self._model})"
    def complete(self, system, user, max_tokens=4096):
        try:
            r = self._client.messages.create(model=self._model, max_tokens=max_tokens, system=system, messages=[{"role":"user","content":user}])
            return r.content[0].text
        except Exception as e:
            raise LLMProviderError(f"Erro API Anthropic: {e}", "anthropic")

class OpenAIProvider(LLMProvider):
    DEFAULT_MODEL = "gpt-4o-mini"
    def __init__(self, api_key, model=""):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
    def name(self): return f"ChatGPT ({self._model})"
    def complete(self, system, user, max_tokens=4096):
        try:
            r = self._client.chat.completions.create(model=self._model, max_tokens=max_tokens, messages=[{"role":"system","content":system},{"role":"user","content":user}])
            return r.choices[0].message.content
        except Exception as e:
            raise LLMProviderError(f"Erro API OpenAI: {e}", "openai")

class AzureOpenAIProvider(LLMProvider):
    def __init__(self, api_key, endpoint, deployment, api_version="2024-08-01-preview"):
        import openai
        self._client = openai.AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
        self._deployment = deployment
    def name(self): return f"Azure ({self._deployment})"
    def complete(self, system, user, max_tokens=4096):
        try:
            r = self._client.chat.completions.create(model=self._deployment, max_tokens=max_tokens, messages=[{"role":"system","content":system},{"role":"user","content":user}])
            return r.choices[0].message.content
        except Exception as e:
            raise LLMProviderError(f"Erro API Azure: {e}", "azure")

def build_provider(config: LLMConfig) -> LLMProvider:
    if not config.api_key or config.provider == "mock": return MockProvider()
    if config.provider == "anthropic": return AnthropicProvider(config.api_key, config.model)
    if config.provider == "openai": return OpenAIProvider(config.api_key, config.model)
    if config.provider == "azure": return AzureOpenAIProvider(config.api_key, config.azure_endpoint, config.azure_deployment, config.azure_api_version)
    return MockProvider()

def persist_to_env(updates: dict):
    p = Path(__file__).parent / ".env"
    for k, v in updates.items(): set_key(str(p), k, v)

def load_config_from_env() -> LLMConfig:
    prov = os.getenv("LLM_PROVIDER", "mock")
    keys = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "azure": "AZURE_OPENAI_API_KEY"}
    return LLMConfig(provider=prov, api_key=os.getenv(keys.get(prov,""), ""),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT",""), azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT",""),
        azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION","2024-08-01-preview"))
