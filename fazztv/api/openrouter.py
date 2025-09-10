"""OpenRouter API client for FazzTV."""

import requests
from typing import Optional, Dict, Any
from loguru import logger

from fazztv.config import get_settings, constants


class OpenRouterClient:
    """Client for OpenRouter AI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: Optional API key (uses settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
        
        if not self.api_key:
            logger.warning("OpenRouter API key not configured")
    
    def get_tax_info(self, artist: str) -> str:
        """
        Get tax information about an artist.
        
        Args:
            artist: Artist name
            
        Returns:
            Tax information text
        """
        prompt = (
            f"Provide a concise summary of {artist}'s tax problems, "
            "including key dates, fines, amounts, or relevant penalties."
        )
        
        response = self.query(prompt)
        return response if response else f"Tax information unavailable for {artist}"
    
    def query(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Send a query to OpenRouter.
        
        Args:
            prompt: The prompt to send
            model: Model to use (defaults to free model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response text or None if error
        """
        if not self.api_key:
            logger.error("OpenRouter API key not configured")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fazztv.com",
            "X-Title": "FazzTV"
        }
        
        data = {
            "model": model or self.default_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=constants.API_TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "choices" in result and result["choices"]:
                content = result["choices"][0].get("message", {}).get("content", "")
                if content:
                    logger.debug(f"OpenRouter response: {content[:100]}...")
                    return content
                else:
                    logger.error("No content in OpenRouter response")
                    return None
            else:
                logger.error(f"Unexpected OpenRouter response structure: {result}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"OpenRouter request timed out after {constants.API_TIMEOUT}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying OpenRouter: {e}")
            return None
    
    def generate_commentary(
        self,
        topic: str,
        style: str = "informative",
        length: int = 200
    ) -> Optional[str]:
        """
        Generate commentary on a topic.
        
        Args:
            topic: Topic to comment on
            style: Style of commentary (informative, humorous, serious)
            length: Approximate length in words
            
        Returns:
            Generated commentary or None
        """
        prompt = (
            f"Generate {style} commentary about {topic}. "
            f"Keep it approximately {length} words. "
            "Be engaging and suitable for a video overlay."
        )
        
        return self.query(prompt, max_tokens=length * 2)
    
    def summarize_content(
        self,
        content: str,
        max_length: int = 100
    ) -> Optional[str]:
        """
        Summarize content to a specific length.
        
        Args:
            content: Content to summarize
            max_length: Maximum length in words
            
        Returns:
            Summarized content or None
        """
        prompt = (
            f"Summarize the following content in {max_length} words or less:\n\n"
            f"{content}"
        )
        
        return self.query(prompt, temperature=0.3, max_tokens=max_length * 2)
    
    def translate_text(
        self,
        text: str,
        target_language: str = "Spanish"
    ) -> Optional[str]:
        """
        Translate text to another language.
        
        Args:
            text: Text to translate
            target_language: Target language
            
        Returns:
            Translated text or None
        """
        prompt = f"Translate the following to {target_language}:\n\n{text}"
        
        return self.query(prompt, temperature=0.3)
    
    def check_content_safety(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        Check if content is safe/appropriate.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with safety assessment
        """
        prompt = (
            "Analyze the following content for safety and appropriateness. "
            "Return a JSON response with fields: "
            "safe (boolean), concerns (list), rating (G/PG/PG-13/R).\n\n"
            f"{content}"
        )
        
        response = self.query(prompt, temperature=0.1)
        
        if response:
            try:
                import json
                # Try to extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"Failed to parse safety check response: {e}")
        
        return {
            "safe": True,
            "concerns": [],
            "rating": "Unknown"
        }