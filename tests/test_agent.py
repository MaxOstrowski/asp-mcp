from core.agent import Agent


def test_agent():
    agent = Agent("general_reasoning_agent")
    #print(agent.ask("What is the capital of France?"))
    #print(agent.ask("list the files of my work directory"))
    #print(agent.ask("Remove the mypy.ini file from the work directory"))
    #print(agent.ask("Read the content of all non-hidden files in the work directory recursively tu familiarize yourself with this project."\
    #                "Then create a new agent that can do google searches. This is a non interactive process, you have to solve all questions yourself."))
    #print(agent.ask("Repair your own search agent. Therefore read all python and json files recursively in the work directory. The search agent is a stub, make it actually search using a python function."))
    #print(agent.ask("read important files in directory recursively and tell me who you are"))
    print(agent.ask("install pip yfinance"))