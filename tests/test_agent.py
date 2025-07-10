from core.agent import Agent, load_json


def test_agent():
    agent = Agent("general_reasoning_agent", load_json("agents/general_reasoning_agent.json"))
    print(agent.ask("What is the capital of France?"))
    print(agent.ask("list the files of my work directory"))
    print(agent.ask("Remove the mypy.ini file from the work directory"))