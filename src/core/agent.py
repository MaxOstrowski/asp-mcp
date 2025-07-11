""" Agent class and loader """

from dataclasses import dataclass
import os
from core.llm import LLM
from utils.json_utils import load_json
from typing import Dict

AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agents"))
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "code"))

AGENT_DESCRIPTION = """
You are an agent in a multi agent system.
Your task is to execute tasks and answer questions.
You shall reason with logic and ensure that you have completed the given task.
You are encouraged to plan and structure your responses,
asking yourself intermediate questions that lead to the end result. You will get called again with your plan.
Do not repeat yourself too much, do not use stubs or placeholders.

You output only in json format, sending messages and status information.
{
    "messages": [
        {
            "recipient": RECIPIENT,
            "content": CONTENT,
        }
    ],   
}

CONTENT is the message to send to the recipient.
RECIPIENT is the target to send the message to.
The only valid targets are:
- "self": send the message to yourself, you will be called again with this message.
- "caller": send the message to the agent that called you
- "python": the message contains an evaluatable python expression, maybe containing the available functions.

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
    def __init__(self, agent_name: str):
        python_functions: list[PythonFunction] = load_python_functions(CODE_DIR)

        description = AGENT_DESCRIPTION
        for py_func in python_functions:
            description += f"\n{py_func.docstring}:\n {py_func.signature} END"
        self.llm = LLM(description)  # Initialize LLM with description

        # create struct to be passed to eval to execute python functions
        self.python_func = {func.name: func.function for func in python_functions}

   
    def ask(self, msg: str) -> str:
        # Default: echo if possible
        messages_to_self = [msg]
        num_old_messages = 0
        while (len(messages_to_self) > num_old_messages):
            num_old_messages = len(messages_to_self)
            answer = self.llm.ask(str(messages_to_self))
            messages_to_caller = []
            for key, value in answer.items():
                if key == "messages":
                    for m in value:
                        recipient = m["recipient"] 
                        content = str(m["content"])
                        if recipient == "self":
                            messages_to_self.append(content)
                        elif recipient == "caller":
                            messages_to_caller.append(content)
                        elif recipient == "python":
                            print(f"Calling python_func with: {repr(content)}")
                            try:
                                response = eval(content, self.python_func)
                                messages_to_self.append(response)
                            except Exception as e:
                                messages_to_self.append(f"[Error evaluating python function: {e} - {content}]")
                        else:
                            raise ValueError(f"Unknown recipient: {recipient}")
        return str(messages_to_caller)

    def __repr__(self):
        return f"<Agent {self.name}: {self.short_description}>"

class LazyAgent:
    def __init__(self, name: str, agents_dir: str, data: dict):
        self.name = name
        self.agents_dir = agents_dir
        self.data = data
        self._agent = None

    def _load_agent(self):
        if self._agent is None:
            self._agent = Agent(self.name, self.data)
        return self._agent
    
    def get_short_description(self):
        return self.data.get('short_description', '')
    
    def get_self_description(self):
        return self.data.get('self_description', '')
    
    def get_name(self):
        return self.name

    @property
    def agent(self):
        return self._load_agent()
    

def load_agent_descriptions(agents_dir: str, agents: Dict[str, LazyAgent]) -> None:
    """
    Update the given agents dict with any new agents found in agents_dir.
    Existing agents are not replaced.
    """
    for fname in os.listdir(agents_dir):
        if fname.endswith('.json'):
            agent_name = fname[:-5]  # Remove .json extension
            data = load_json(os.path.join(agents_dir, fname))
            agents[agent_name] = LazyAgent(agent_name, agents_dir, data)


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