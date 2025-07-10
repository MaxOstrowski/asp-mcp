""" Agent class and loader """

import os
from core.llm import LLM
from utils.json_utils import load_json
from typing import Dict

AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "agents"))

OUTPUT_FORMAT = """
You are an agent in a multi agent system.
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
"""
class Agent:
    def __init__(self, agent_name: str, data: dict):
        self.agents: Dict[str, LazyAgent] = {}
        load_agent_descriptions(AGENTS_DIR, self.agents)

        description = OUTPUT_FORMAT
        description += """
RECIPIENT is the name of the agent to send the message to.
The following agents are available:"""
        for name, lazy_agent in self.agents.items():
            if name == agent_name:
                continue
            description += f"\n- {name}: {lazy_agent.get_short_description()}"
        description += "\n\nYou can also use the 'self' as an agent to send messages to yourself."
        description += "\nYou get called again with this additional messages."
        description += "\nThe order of messages is applied and agents answer to your messages in order."
        description += '\nYou should use "caller" as an agent to answer to the message you received. You will not get called again.'
        description += "\nYou can also use 'python' as an agent to execute your special functions with the message as parameter."
        description += f"\nYou can call any agent but yourself, you are agent {agent_name}"

        description += data['self_description']
        self.llm = LLM(description)  # Initialize LLM with description

        self.name = agent_name
        self.short_description = data['short_description']
        self.self_description = data['self_description']
        self.python_code = data.get('python', None)
        self.python_func = None
        if self.python_code:
            # Compile the function and store as self.python_func
            local_vars = {}
            exec(self.python_code, {}, local_vars)
            # Find the first function defined in local_vars
            self.python_func = next(
                v for v in local_vars.values() if callable(v)
            )
        a = 9

    def ask(self, message: str):
        self.ask(message)

   
    def ask(self, msg: str) -> str:
        # Default: echo if possible
        answer = self.llm.ask(msg)
        messages_to_self = []
        for key, value in answer.items():
            if key == "status":
                status = value
            elif key == "messages":
                for m in value:
                    recipient = m["recipient"] 
                    content = m["content"]
                    if recipient == "self":
                        messages_to_self.append(content)
                    elif recipient == "caller":
                        return content
                    elif recipient == "python":
                        assert self.python_func, "Python function is not defined for this agent."
                        # Call the compiled Python function with the content as input
                        response = self.python_func(content)
                        messages_to_self.append(response)
                    elif recipient in self.agents:
                        if recipient == self.name:
                            assert False, "You cannot send messages to yourself."
                        messages_to_self.append(self.agents[recipient].agent.ask(content))
                    else:
                        raise ValueError(f"Unknown recipient: {recipient}")
        return self.ask("\n".join(messages_to_self))

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
