import argparse
import asyncio
import logging
from asp_llm.chat_session import ChatSession
from asp_llm.configuration import Configuration
from asp_llm.server import Server

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")


async def _main_async(initial_file: str | None = None) -> None:
    """Initialize and run the chat session."""
    config = Configuration()
    server_config = config.load_config("servers_config.json")
    servers = [Server(name, srv_config) for name, srv_config in server_config["mcpServers"].items()]
    chat_session = ChatSession(servers, config)
    await chat_session.start(initial_file)


def main():
    parser = argparse.ArgumentParser(description="Run the ASP LLM chat session.")
    parser.add_argument("file", nargs="?", default=None, help="Optional file to use as initial prompt input")
    args = parser.parse_args()
    asyncio.run(_main_async(args.file))


if __name__ == "__main__":
    main()
