import asyncio
import logging
from asp_llm.chat_session import ChatSession
from asp_llm.configuration import Configuration
from asp_llm.server import Server

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
# Disable debug logging for external libraries
for lib in ("asyncio", "urllib3", "httpx", "httpcore", "requests", "openai"):
    logging.getLogger(lib).setLevel(logging.WARNING)



async def _main_async() -> None:
    """Initialize and run the chat session."""
    config = Configuration()
    server_config = config.load_config("servers_config.json")
    servers = [
        Server(name, srv_config)
        for name, srv_config in server_config["mcpServers"].items()
    ]
    chat_session = ChatSession(servers, config)
    await chat_session.start()

def main():
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()