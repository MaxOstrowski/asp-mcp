""" LLM agent: receives messages and returns answers using an LLM (Azure OpenAI) """


# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import os
from openai import AzureOpenAI

class LLM():
    def __init__(self, initial_prompt: str):
        self.initial_prompt = initial_prompt
        # Initialize history with system message
        self.history = [{"role": "system", "content": self.initial_prompt}]
        # Azure OpenAI config
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        self.model_name = os.environ.get("AZURE_OPENAI_MODEL")
        self.api_version = os.environ.get("AZURE_OPENAI_API_VERSION")
        self.api_key = os.environ.get("AZURE_OPENAI_KEY")
        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
        )

    def ask(self, msg: str) -> dict:
        # Add user message to history
        self.history.append({"role": "user", "content": msg})
        answer = self.generate_response()
        try:
            return eval(answer)
        except Exception as e:
            return {
                "messages" : [
                    {
                        "recipient": "self",
                        "content": f"[Error evaluating response: {e} - {answer}]"
                    }
                ]
            }

    def generate_response(self) -> str:
        try:
            response = self.client.chat.completions.create(
                messages=self.history,
                max_completion_tokens=800,
                temperature=1.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                model=self.deployment
            )
            content = response.choices[0].message.content
            # Add assistant response to history
            self.history.append({"role": "assistant", "content": content})
            return str(content)
        except Exception as e:
            return f"[LLM error: {e}]"
