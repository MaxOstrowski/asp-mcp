import logging
from asp_llm.configuration import Configuration
from asp_llm.server import Server
from asp_llm.llm_client import LLMClient
import json
import importlib.resources
from asp_llm.stdio import AbstractIOHandler, StdIOHandler
from asp_llm.summarizer import Summarizer


class ChatSession:
    """Orchestrates the interaction between user, LLM, and tools."""

    def __init__(self, servers: list[Server], config: Configuration) -> None:
        self.servers: list[Server] = servers
        self.config: Configuration = config
        self.io: AbstractIOHandler = StdIOHandler()
        self.summarizer = Summarizer()

    async def cleanup_servers(self) -> None:
        """Clean up all servers properly."""
        for server in reversed(self.servers):
            try:
                await server.cleanup()
            except Exception as e:
                logging.warning(f"Warning during final cleanup: {e}")

    async def process_llm_response(self, llm_response: dict, asp_llm: LLMClient) -> list[dict]:
        """
        Process the LLM response and execute OpenAI tool calls if present.

        Args:
            llm_response: The response object from the OpenAI API.

        Returns:
            A list of messages to append to the conversation history (tool results).
        """
        tool_result_messages = []

        # Check if the response contains tool calls (OpenAI Tool API)
        choice = llm_response.choices[0]
        tool_calls = getattr(choice.message, "tool_calls", []) or []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            tool_call_id = tool_call.id

            # Find the server that has this tool
            for server in self.servers:
                tools = await server.list_tools()
                if any(tool.name == tool_name for tool in tools):
                    try:
                        result = await server.execute_tool(tool_name, arguments)
                        # Prepare the tool result message for OpenAI API
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result,
                        })
                    except Exception as e:
                        logging.error(f"Error executing tool {tool_name}: {e}")
                        tool_result_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps({"error": str(e)}),
                        })
                    break
            else:
                if tool_name == self.io.name():
                    # Handle the input tool call
                    user_input = self.io.get_input("".join(arguments["prompt"]) + ": ")
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": user_input,
                    })
                elif tool_name == self.summarizer.name():
                    # Handle the input tool call
                    num = self.summarizer.compress_messages(asp_llm.history)
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"Messages compressed. {num} messages removed. Now list all files and their contents before proceeding with the next constraint.",
                    })
                else:
                    # No server found for this tool
                    logging.error(f"No server found with tool: {tool_name}")
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"error": f"No server found with tool: {tool_name}"}),
                    })
        return tool_result_messages

    async def start(self) -> None:
        """Main chat session handler."""
        try:
            for server in self.servers:
                try:
                    await server.initialize()
                except Exception as e:
                    logging.error(f"Failed to initialize server: {e}")
                    await self.cleanup_servers()
                    return

            all_tools = []
            openai_tools = [self.io.tool(), self.summarizer.tool()]
            for server in self.servers:
                tools = await server.list_tools()
                all_tools.extend(tools)
                openai_tools.extend(await server.openai_tools())

            with importlib.resources.files("asp_llm.resources").joinpath("agent_description.txt").open("r", encoding="utf-8") as f:
                system_message = f.read()

            asp_llm = LLMClient(self.io, system_message, self.config, openai_tools)

            user_input = self.io.get_input("You: ")

            asp_llm.add_message({"role": "user", "content": user_input})

            while True:
                try:
                    llm_response = asp_llm.get_response()
                    tool_result_messages = await self.process_llm_response(llm_response, asp_llm)

                    for msg in tool_result_messages:
                        asp_llm.add_message(msg)
                    msg = llm_response.choices[0].message.content
                    if msg and len(msg) >= 3 and '?' in msg[-3:]:
                        user_input = self.io.get_input("You: ")
                        asp_llm.add_message({"role": "user", "content": user_input})

                    # if not tool_result_messages:
                    #     user_input = self.io.get_input("You: ")
                    #     asp_llm.add_message({"role": "user", "content": user_input})

                except KeyboardInterrupt:
                    logging.info("\nExiting...")
                    break

        finally:
            await self.cleanup_servers()
