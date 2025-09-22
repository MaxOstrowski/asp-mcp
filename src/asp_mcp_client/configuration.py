import json
import os
from typing import Any, IO
from dotenv import load_dotenv


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    REQUIRED_ENV_VARS = [
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_MODEL",
        "AZURE_OPENAI_API_VERSION",
    ]

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.load_env()
        
    def __getattr__(self, name: str) -> Any:
        if name in self.REQUIRED_ENV_VARS:
            raise AttributeError(f"Environment variable '{name}' not loaded. Please set it in your environment or .env file.")
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def load_env(self) -> None:
        """Load environment variables from .env file in several locations."""
        env_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.expanduser("~"), ".env"),
        ]

        for path in env_paths:
            if os.path.isfile(path):
                load_dotenv(dotenv_path=path)
                break
        
        # precache required env vars
        for var in self.REQUIRED_ENV_VARS:
            if var in os.environ:
                setattr(self, var, os.environ[var])

    @staticmethod
    def load_config(file: IO[str]) -> dict[str, Any]:
        """Load server configuration from JSON file.

        Args:
            file: File-like object containing the JSON configuration.

        Returns:
            Dict containing server configuration.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            JSONDecodeError: If configuration file is invalid JSON.
        """
        return json.load(file)
