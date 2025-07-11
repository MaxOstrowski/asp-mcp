from core.agent import Agent, setup_logging

def main():
    setup_logging()
    agent = Agent("general_reasoning_agent")
    # ANSI escape code for light green
    LIGHT_GREEN = '\033[92m'
    RESET = '\033[0m'
    print(f"{LIGHT_GREEN}Type your command (type 'exit' to quit):{RESET}")
    while True:
        try:
            command = input('> ')
            if command.strip().lower() in {'exit', 'quit'}:
                print(f"{LIGHT_GREEN}Exiting.{RESET}")
                break
            response = agent.ask(command)
            print(f"{LIGHT_GREEN}{response}{RESET}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{LIGHT_GREEN}Exiting.{RESET}")
            break

if __name__ == "__main__":
    main()
