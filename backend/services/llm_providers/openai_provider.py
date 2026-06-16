import os
import json
import logging
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

# Lazy import flag
OPENAI_AVAILABLE = False
try:
    from openai import OpenAI
    from openai import NotFoundError
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warn("OpenAI library not available. Install with: pip install openai")

def _get_openai_client() -> "OpenAI":
    if not OPENAI_AVAILABLE:
        raise ImportError("OpenAI library not available. Install with: pip install openai")
    
    # Allow overriding base URL for OpenAI compatible endpoints
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
        
    return OpenAI(base_url=base_url, api_key=api_key)

def openai_text_response(
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    top_p: float = 0.95,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate text using OpenAI or compatible API.
    """
    client = _get_openai_client()
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p
    )
    
    return response.choices[0].message.content

def openai_structured_json_response(
    prompt: str,
    schema: Dict[str, Any],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate structured JSON using OpenAI or compatible API.
    """
    client = _get_openai_client()
    
    # We use response_format={"type": "json_object"}
    # The prompt must instruct the model to output JSON.
    
    messages = []
    default_system = "You are a helpful assistant designed to output strictly valid JSON."
    if system_prompt:
        messages.append({"role": "system", "content": f"{default_system}\n{system_prompt}"})
    else:
        messages.append({"role": "system", "content": default_system})
        
    messages.append({"role": "user", "content": f"{prompt}\n\nPlease output JSON matching this schema:\n{json.dumps(schema)}"})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"}
    )
    
    return response.choices[0].message.content
