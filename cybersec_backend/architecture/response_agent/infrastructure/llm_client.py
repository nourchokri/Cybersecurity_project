"""LLM client for Response Agent."""

from __future__ import annotations
import logging
import json
from typing import Any, Dict, Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM API."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'LLM_API_KEY', '')
        self.base_url = getattr(settings, 'LLM_BASE_URL', '').rstrip('/')
        self.model = getattr(settings, 'LLM_MODEL', '')
        
        # Validate configuration
        if not self.base_url:
            logger.error("LLM_BASE_URL is not configured in settings")
        if not self.api_key:
            logger.error("LLM_API_KEY is not configured in settings")
        if not self.model:
            logger.error("LLM_MODEL is not configured in settings")
        
        logger.info(f"LLM Client initialized: base_url={self.base_url}, model={self.model}")
        
    def _call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Make API call to LLM."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a cybersecurity expert analyzing security events."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to extract JSON from LLM response: {e}")
            logger.debug(f"Response was: {response}")
            raise
