import logging
import httpx
from asp_llm.configuration import Configuration
from openai import AzureOpenAI
from openai.types.chat import ChatCompletion
import os

class LLMClient:
    """A client to interact with OpenAI's LLM."""

    def __init__(self, initial_prompt: str, config: Configuration,
                 tools: list[dict]) -> None:
        """Initialize the LLM client with the provided API key."""
        
        self.initial_prompt = initial_prompt
        self.client = AzureOpenAI(api_version=config.AZURE_OPENAI_API_VERSION,
                                  azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
                                  api_key=config.AZURE_OPENAI_KEY,
                                  azure_deployment=config.AZURE_OPENAI_DEPLOYMENT,
                                  )
        self.model = config.AZURE_OPENAI_MODEL
        self.clear_history()
        self.tools = tools

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history = [{"role": "system", "content": self.initial_prompt}]

    def add_message(self, message: dict) -> None:
        """Add a message to the conversation history."""
        # Ensure message is a dict for logging
        if hasattr(message, "model_dump"):
            msg_dict = message.model_dump()
        elif hasattr(message, "dict"):
            msg_dict = message.dict()
        elif isinstance(message, dict):
            msg_dict = message
        else:
            raise ValueError("Message must be a dict or have model_dump/dict method.")

        self.history.append(msg_dict)
        if msg_dict.get('role', 'unknown') == "unknown":
            a = 9
        logging.debug(f"Message added: {msg_dict.get('role', 'unknown')} - {msg_dict.get('content', '')}")

    def get_response(self) -> ChatCompletion:
        """Get a response from the LLM for a given prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            tools=self.tools,
            max_completion_tokens=1500,
            temperature=0.7
        )
        # add response to history, that looks weird
        choice = response.choices[0]
        message = choice.message
        self.history.append(message)
        # msg_dict = {"role": "assistant", "content": message.content}
        # if hasattr(message, "tool_calls") and message.tool_calls:
        #     msg_dict["tool_calls"] = [tc.model_dump() for tc in message.tool_calls]
        # self.history.append(msg_dict)
        return response