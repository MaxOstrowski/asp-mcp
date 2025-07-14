""" Agent class and loader """

from dataclasses import dataclass
import hashlib
import io
import os
import logging
import sys
from core.llm import LLM
from utils.json_utils import load_json
from typing import Dict

AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agents"))
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "code"))

AGENT_DESCRIPTION = """
You are an agent in a multi agent system.
Your task is to execute tasks and answer questions.
You shall reason with logic and ensure that you have completed the given task.
You are encouraged to plan, subdivide any tasks and forward them to other agents.
These agents talk back to you, so you can reason with them, but they do not have your knowledge.
Ask precise questions or given precise instructions to other agents.
Do not repeat yourself too much, do not use stubs or placeholders.
ALWAYS CHECK the result of your work before you finish!

You output only in json format, sending messages and status information.
{
    "messages": [
        {
            "sender": "AGENT",
            "recipient": RECIPIENT,
            "content": CONTENT,
        }
    ],   
}

AGENT is your agent name
CONTENT is the message to send to the recipient.
RECIPIENT is the target to send the message to, the only valid targets are:
- "self": send the message to yourself, you will be called again with this message.
- "agent_XXX": where XXX is the name of another agent, you can send a message to another agent, it will be called with this message.
Use other agents to delegate tasks, subdivide your problem into smaller tasks. Do not end in a loop
- "caller": send the message to the agent that called you
- "clear": ignore content and clears your history, should be requested by the user
- "python_eval": the message contains an evaluatable python expression, maybe containing the available functions
- "python_exec": the message contains a python code snippet to execute, it will be executed in a separate process and the output will be captured, may also contain the available functions

The following python functions are available:

"""



@dataclass
class PythonFunction:
    """Represents a Python function with its metadata."""
    name: str
    signature: str
    docstring: str
    function: callable



class Agent:
    reset = '\033[0m'

    def __init__(self, agent_name: str):
        # Set up logger for this class
        self.agent_name = agent_name  # Store agent name for coloring
        self.color = agent_color(self.agent_name)

        self.logger = logging.getLogger(f"Agent.{agent_name}")
        python_functions: list[PythonFunction] = load_python_functions(CODE_DIR)

        description = AGENT_DESCRIPTION
        for py_func in python_functions:
            description += f"\n{py_func.docstring}:\n {py_func.signature} END"
        self.llm = LLM(description)  # Initialize LLM with description

        # create struct to be passed to eval to execute python functions
        self.python_func = {func.name: func.function for func in python_functions}

        self.agents: dict[str, Agent] = {}

   

    def ask(self, msg: str) -> str:
        # Default: echo if possible
        messages_to_self = [(msg, "user")]
        messages_to_caller = []
        llm_finished = LLM("Given a task and an answer to the task, answer YES if question/task was accomplished, answer NO if not.")
        llm_finished_messages = [(msg, "user")]
        while True:
            while messages_to_self:
                answer = self.llm.ask(messages_to_self)
                messages_to_self.clear()
                for key, value in answer.items():
                    if key == "messages":
                        for m in value:
                            recipient = m["recipient"]
                            content = str(m["content"])
                            if recipient == "self":
                                messages_to_self.append((content, "assistant"))
                            elif recipient == "clear":
                                self.llm.clear_history()
                            elif recipient == "caller":
                                messages_to_caller.append(content)
                            elif recipient == "python_eval":
                                self.logger.warning(f"Calling python_eval with: {repr(content)}")
                                try:
                                    response = eval(content, self.python_func)
                                    messages_to_self.append((response, "assistant"))
                                except Exception as e:
                                    messages_to_self.append((f"[Error evaluating python function: {e} - {content}]", "assistant"))
                            elif recipient == "python_exec":
                                self.logger.warning(f"Calling python_exec with: {repr(content)}")
                                try:
                                    stdout = io.StringIO()
                                    stderr = io.StringIO()
                                    old_stdout, old_stderr = sys.stdout, sys.stderr
                                    sys.stdout, sys.stderr = stdout, stderr
                                    try:
                                        exec(content, self.python_func)
                                    finally:
                                        sys.stdout, sys.stderr = old_stdout, old_stderr
                                    output = stdout.getvalue()
                                    error = stderr.getvalue()
                                    response = output if not error else f"{output}\n[stderr]: {error}"
                                    messages_to_self.append((response, "assistant"))
                                except Exception as e:
                                    messages_to_self.append((f"[Error evaluating python function: {e} - {content}]", "assistant"))
                            else:
                                if not recipient.startswith("agent_"):
                                    self.logger.warning(f"Unknown recipient: {recipient}")
                                if agent.agent_name == recipient:
                                    messages_to_self.append((content, "assistant"))
                                else:
                                    agent = self.agents.setdefault(recipient, Agent(recipient))
                                    self.logger.info(f"{self.color}Forwarding message to {recipient}: {content}{self.reset}")
                                    response = agent.ask(content)
                                    messages_to_self.append((response, "assistant"))
                # log new messages to self
                for msg in messages_to_self:
                    self.logger.info(f"{self.color}Message to self: {msg}{self.reset}")
            
            llm_finished_messages.extend(messages_to_caller)
            answer = llm_finished.ask(llm_finished_messages)
            for key, value in answer.items():
                    if key == "messages":
                        for m in value:
                            recipient = m["recipient"]
                            content = str(m["content"])
                            if content.lower() in ["yes", "y"]:
                                self.logger.info(f"{self.color}Task accomplished, returning to caller.{self.reset}")
                                return str(messages_to_caller)
            msg = "Try harder and find answers yourself. Make a plan, use the internet, delegate tasks."
            self.logger.info(f"{self.color}Adding message to self: {msg}{self.reset}")
            messages_to_self.append((msg, "user"))

        #return str(messages_to_caller)
    

def agent_color(agent_name):
    """List of ANSI color codes (foreground)"""
    COLORS = [
        '\033[32m', # Green
        '\033[34m', # Blue
        '\033[35m', # Magenta
        '\033[36m', # Cyan
        '\033[33m', # Yellow
        '\033[91m', # Light Red
        '\033[92m', # Light Green
        '\033[94m', # Light Blue
        '\033[95m', # Light Magenta
        '\033[96m', # Light Cyan
    ]
    # Hash agent name to pick a color
    idx = int(hashlib.md5(agent_name.encode()).hexdigest(), 16) % len(COLORS)
    return COLORS[idx]


def setup_logging():
    import sys

    class ColorFormatter(logging.Formatter):
        # ANSI escape codes
        DARK_GREEN = '\033[32m'
        RED = '\033[31m'
        RESET = '\033[0m'
        def format(self, record):
            msg = super().format(record)
            if record.levelno == logging.WARNING:
                return f"{self.RED}{msg}{self.RESET}"
            elif record.levelno == logging.INFO:
                return f"{self.DARK_GREEN}{msg}{self.RESET}"
            return msg

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    handler.setFormatter(ColorFormatter("[%(levelname)s] %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    # Suppress logs from external libraries (e.g., openai)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    def __repr__(self):
        return f"<Agent {self.name}: {self.short_description}>"


def load_python_functions(code_dir: str) -> list[PythonFunction]:
    """
    Load Python functions from all files in the code directory and return a list of PythonFunction instances.
    """
    import os
    import re
    functions = []
    
    for root, _, files in os.walk(code_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                functions.extend(load_python_function_from_file(path))
    
    return functions
            
def load_python_function_from_file(path_to_file: str) -> list[PythonFunction]:
    """
    Load Python functions from a file and return a list of PythonFunction instances.
    """
    import re
    local_vars = {}
    with open(path_to_file, 'r') as f:
        source = f.read()
        exec(source, {}, local_vars)
    # Find all function definitions and their first lines
    func_lines = {}
    func_def_pattern = re.compile(r'^(def .+):', re.MULTILINE)
    for match in func_def_pattern.finditer(source):
        line = match.group(1)
        func_name = line.split('(')[0][4:].strip()
        func_lines[func_name] = line
    functions = []
    for name, func in local_vars.items():
        if callable(func) and name in func_lines:
            signature = func_lines[name]
            docstring = func.__doc__ or ""
            functions.append(PythonFunction(
                name=name,
                signature=signature,
                docstring=docstring,
                function=func
            ))
    return functions