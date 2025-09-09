from typing import Any

class Summarizer:
    """A tool to compress a list of OpenAI chat messages in place by removing some messages."""

    @staticmethod
    def compress_messages(messages: list[dict[str, Any]]) -> int:
        """
        Compresses the list of OpenAI chat messages in place by removing some messages.
        The removal logic should be implemented by the user.
        Args:
            messages: List of OpenAI chat message dicts (each with keys like 'role', 'content', etc.)
        Returns:
            None. The input list is modified in place.
        """
        num = 0
        last = 3 # ignore your own call + the last messages which are hopefully test calls
        # remove all tool call and response messages except the last one
        for i in range(len(messages) - 1 - last, -1, -1):
            if messages[i]["role"] in ["tool"]:
                del messages[i]
                num += 1
                continue
            if "content" in messages[i] and messages[i]["content"] is None:
                del messages[i]
                num += 1
                continue
            if "tool_calls" in messages[i]:
                del messages[i]["tool_calls"]
        return num

    @staticmethod
    def tool() -> dict:
        """Get the description of the summarizer."""
        return {
            "type": "function",
            "function": {
                "name": Summarizer.name(),
                "description": "Compresses history of the LLM to improve reasoning.",
            }
        }

    @staticmethod
    def name() -> str:
        """Return the name of the summarizer."""
        return "compress_messages"
