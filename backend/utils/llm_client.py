import os
import logging
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger("GeminiClient")

class GeminiClient:
    """
    Wrapper for Google Gemini API (via google-generativeai SDK).
    Replaces local Ollama instance.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            self.enabled = False
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
            self.enabled = True
            logger.info(f"✨ GeminiClient initialized with model: {model_name}")

    def generate_content(self, prompt: str) -> Optional[object]:
        """
        Generate content using Gemini.
        Returns response object with .text attribute.
        """
        if not self.enabled:
            logger.warning("Gemini is disabled (missing API key)")
            raise Exception("Gemini API key missing")

        try:
            # Set generation config for stability
            config = genai.types.GenerationConfig(
                candidate_count=1,
                temperature=0.7
            )
            
            response = self.model.generate_content(prompt, generation_config=config)
            return response
            
        except Exception as e:
            logger.error(f"❌ Gemini generation failed: {e}")
            raise

# For backward compatibility if needed, or we just update imports
def get_llm_client():
    return GeminiClient()
