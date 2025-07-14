""" Agent class and loader """

from dataclasses import dataclass
import hashlib
import io
import os
import logging
import sys

from core.llm import LLM
from typing import Optional

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "code"))

AGENT_DESCRIPTION = """
You are an agent in a multi agent system.
Your name is __AGENT_NAME__ and your parents are: __PARENTS__.
Your task is to execute tasks and answer questions.
You shall reason with logic and ensure that you have completed the given task.
You are encouraged to plan, subdivide any tasks and forward them to other agents.
These agents talk back to you, so you can reason with them, but they do not have your knowledge.
Ask precise questions or give precise instructions to other agents.
Do not repeat yourself too much, do not use stubs or placeholders.
ALWAYS CHECK the result of your work before you finish!

You output only in json format, sending a single message and status information.
{
    "sender": "AGENT",
    "recipient": RECIPIENT,
    "content": CONTENT,
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
- "python_exec": the message contains a python code snippet to execute, it will be executed in a separate process and the output will be captured, may also contain the available functions.
You can access the system using these functions but you do not have sudo rights.

The following python functions are available:
___PYTHON_FUNCTIONS___

"""


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

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    # Suppress logs from external libraries (e.g., openai)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    def __repr__(self):
        return f"<Agent {self.name}: {self.short_description}>"


@dataclass
class PythonFunction:
    """Represents a Python function with its metadata."""
    name: str
    signature: str
    docstring: str
    function: callable



class Agent:
    reset = '\033[0m'

    def __init__(self, agent_name: str, parent: Optional["Agent"] = None):
        # Set up logger for this class
        self.agent_name = agent_name  # Store agent name for coloring
        self.parent = parent
        self.color = agent_color(self.agent_name)

        self.logger = logging.getLogger(f"Agent.{self.long_name()}")
        python_functions: list[PythonFunction] = load_python_functions(CODE_DIR)

        description = AGENT_DESCRIPTION
        description = description.replace("__AGENT_NAME__", agent_name)
        parents = parent.long_name() if parent else ""
        description = description.replace("__PARENTS__", parents)
        # Add available python functions to the description
        description = description.replace("___PYTHON_FUNCTIONS___", "\n".join([f"{func.docstring}:\n {func.signature} END" for func in python_functions]))

        self.llm = LLM(description)  # Initialize LLM with description

        # create struct to be passed to eval to execute python functions
        self.python_func = {func.name: func.function for func in python_functions}

        self.agents: dict[str, Agent] = {}
        self.llm_finished = LLM("Given a task and an answer to the task, answer YES if question/task was accomplished, answer NO if not.")
        self.llm_new_task = LLM("Compare the two given tasks and answer YES is the task is semantically different.")


    def long_name(self) -> str:
        """Return a long name for the agent including all parents."""
        if self.parent:
            return f"{self.parent.long_name()}.{self.color}{self.agent_name}{self.reset}"
        return f"{self.color}{self.agent_name}{self.reset}"
    
    def task_completed(self, task: str, answers: list[str]) -> bool:
        """Check if the task is completed by asking the LLM."""
        m = [(task, "user")]
        m.extend([(msg, "assistant") for msg in answers])
        answer = self.llm_finished.ask(m)
          
        if "yes" in answer.lower():
            return True
        return False
    
    def task_differs(self, task: str, other_task: str) -> bool:
        """Check if the task is different from another task by asking the LLM."""
        m = [(task, "user"), (other_task, "assistant")]
        answer = self.llm_new_task.ask(m)
        
        if "yes" in answer.lower():
            return True
        return False
        
    
    def python_eval(self, content: str) -> tuple[str, str]:
        """Evaluate a Python expression and return the result."""
        self.logger.warning(f"{self.color}Calling python_eval with: {repr(content)}{self.reset}")
        try:
            response = str(eval(content, self.python_func))
            message_to_self = (response, "assistant")
        except Exception as e:
            message_to_self = (f"{self.color}[Error evaluating python function: {e} - {content}]{self.reset}", "assistant")
        return message_to_self
    
    def python_exec(self, content: str) -> tuple[str, str]:
        """Execute a Python code snippet and return the output."""
        self.logger.warning(f"{self.color}Calling python_exec with: {repr(content)}{self.reset}")
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
            message_to_self = (response, "assistant")
        except Exception as e:
            message_to_self = (f"{self.color}[Error executing python function: {e} - {content}]{self.reset}", "assistant")
        return message_to_self

    def ask(self, msg: str) -> str:
        # Default: echo if possible
        message_to_self = (msg, "user")
        messages_to_caller = []       
        while True:
            while message_to_self:
                answer_str = self.llm.ask([message_to_self])
                message_to_self = None
                while (True):
                    try:
                        answer = eval(answer_str)
                        break
                    except Exception as e:
                        answer_str = self.llm.ask([("Please return a dictionary with the messages, error: " + str(e), "user")])
                
                recipient = answer["recipient"]
                content = str(answer["content"])
                if recipient == "self":
                    message_to_self = (content, "assistant")
                elif recipient == "clear":
                    self.llm.clear_history()
                elif recipient == "caller":
                    self.logger.info(f"{self.color}Prepare message to caller: {content}{self.reset}")
                    messages_to_caller.append(content)
                elif recipient == "python_eval":
                    message_to_self = self.python_eval(content)
                elif recipient == "python_exec":
                    message_to_self = self.python_exec(content)
                else:
                    if self.agent_name == recipient:
                        message_to_self = (content, "assistant")
                    else:
                        if self.task_differs(msg, content):
                            agent = self.agents.setdefault(recipient, Agent(recipient, self))
                            self.logger.info(f"{self.color}Forwarding message to {recipient}: {content}{self.reset}")
                            response = agent.ask(content)
                            message_to_self = (response, "assistant")
                        else:
                            message_to_self = (f"{self.color}Skipping message to {recipient} as it is not a new task. Do it yourself.{self.reset}", "user")
                if message_to_self:
                    self.logger.info(f"{self.color}Message to self: {message_to_self}{self.reset}")
            if self.task_completed(msg, messages_to_caller):
                self.logger.info(f"{self.color}Task accomplished, returning to caller.{self.reset}")
                return str(messages_to_caller)
            
            msg = "The task is not complete. Try harder and find answers yourself. Make a plan, use the internet, delegate tasks."
            msg += " Dont go in circles."
            self.logger.info(f"{self.color}Adding message to self: {msg}{self.reset}")
            message_to_self = (msg, "user")

        #return str(messages_to_caller)
    




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