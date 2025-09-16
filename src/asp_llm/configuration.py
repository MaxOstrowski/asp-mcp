import json
import os
from typing import Any, IO
from dotenv import load_dotenv


class Configuration:
    """Manages configuration and environment variables for the MCP client."""

    def __init__(self) -> None:
        """Initialize configuration with environment variables."""
        self.load_env()
        # get environment variables
        for key, value in os.environ.items():
            setattr(self, key, value)

    @staticmethod
    def load_env() -> None:
        """Load environment variables from .env file in several locations."""
        env_paths = [
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.expanduser("~"), ".env"),
        ]
        for path in env_paths:
            if os.path.isfile(path):
                load_dotenv(dotenv_path=path)
                break

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
