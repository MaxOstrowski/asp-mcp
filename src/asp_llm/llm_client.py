
import logging
import httpx
from asp_llm.configuration import Configuration
from openai import AzureOpenAI
import os

class LLMClient:
    """A client to interact with OpenAI's LLM."""

    def __init__(self, initial_prompt: str, config: Configuration) -> None:
        """Initialize the LLM client with the provided API key."""
        
        self.initial_prompt = initial_prompt
        self.client = AzureOpenAI(api_version=config.AZURE_OPENAI_API_VERSION,
                                  azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                                  api_key=config.llm_api_key)
        self.clear_history()

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history = [{"role": "system", "content": self.initial_prompt}]

    def get_response(self, prompt: str, role: str) -> str:
        """Get a response from the LLM for a given prompt."""
        self.history.append({"role": role, "content": prompt})
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=self.history,
            max_tokens=1500,
            temperature=0.7
        )
        content = response.choices[0].message["content"]
        self.history.append({"role": "assistant", "content": content})
        return content