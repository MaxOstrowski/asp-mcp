"""A wrapper for handling output to stdin from different sources and input from stdin."""

from abc import ABC, abstractmethod
import json
from rich import print
from rich.prompt import Prompt
from rich.panel import Panel
from rich.align import Align


class AbstractIOHandler(ABC):
    """Abstract interface for IO handlers."""

    @abstractmethod
    def get_input(self, prompt: str) -> str:
        pass

    @abstractmethod
    def write_output(self, msg_dict: dict) -> None:
        pass


class StdIOHandler(AbstractIOHandler):
    """A class to handle messages with meta data"""

    ROLE_TO_COLOR = {
        "user": "blue",
        "assistant": "green",
        "tool": "yellow",
        "tool_call": "yellow",
        "system": "magenta",
        "unknown": "red",
    }

    def get_input(self, prompt: str) -> str:
        """Get input from stdin."""
        try:
            return Prompt.ask(f"[{self.ROLE_TO_COLOR['user']}] {prompt} [/{self.ROLE_TO_COLOR['user']}]").strip()
        except EOFError:
            return ""

    def write_output(self, msg_dict: dict) -> None:
        """Write output to stdout with role metadata."""
        content = msg_dict.get("content", "")
        role = msg_dict.get("role", "unknown")
        if role == "user":
            return
        color = self.ROLE_TO_COLOR.get(role, self.ROLE_TO_COLOR["unknown"])
        if content:
            if role == "tool":
                try:
                    if isinstance(content, str):
                        content = json.loads(content)
                except Exception:
                    pass  # leave content as is if not valid JSON
                if isinstance(content, dict):
                    StdIOHandler._print_dict(content, color)
                else:
                    print(Align.right(Panel(f"{role}: {content}", style=color)))
            else:
                print(Panel(f"{role}: {content}", style=color))

        # if its a tool call, print the call
        role = "tool_call"
        tool_calls = msg_dict.get("tool_calls", []) or []
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            name = function.get("name", "unknown")
            args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
            color = self.ROLE_TO_COLOR[role]
            print(Panel(f"{role}: {name}({args_str})", style=color))
        return

    @staticmethod
    def dict2string(data: dict) -> str:
        """Convert a dictionary to a formatted string."""
        lines = StdIOHandler._print_dict_aux(data)
        return "\n".join(lines)

    @staticmethod
    def _print_dict(data: dict, color: str) -> None:
        """Print a dictionary in a formatted way, wrapped in a Panel."""
        string = StdIOHandler.dict2string(data)
        print(Align.right(Panel(string, style=color)))

    @staticmethod
    def _print_dict_aux(data, indent: int = 0):
        """Helper method to collect lines for a dictionary in a formatted way."""
        lines = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    lines.append(f"{' ' * indent}{key}:")
                    lines.extend(StdIOHandler._print_dict_aux(value, indent + 2))
                else:
                    if isinstance(value, str):
                        value = value.replace("\\n", "\n")
                    lines.append(f"{' ' * indent}{key}: {value}")
        elif isinstance(data, list):
            for value in data:
                if isinstance(value, dict):
                    lines.extend(StdIOHandler._print_dict_aux(value, indent + 2))
                else:
                    if isinstance(value, str):
                        value = value.replace("\\n", "\n")
                    lines.append(f"{' ' * indent}{value}")
        else:
            lines.append(f"{' ' * indent}{data}")
        return lines

    def tool(self) -> dict:
        """ " get the description of the input io tool"""
        return {
            "type": "function",
            "function": {
                "name": self.name(),
                "description": "Ask the user for more information.",
                "parameters": {
                    "type": "object",
                    "properties": {"prompt": {"type": "string", "description": "The question to ask the user."}},
                    "required": ["prompt"],
                },
            },
        }

    def name(self) -> str:
        """Return the name of the input io tool."""
        return "get_user_input"
