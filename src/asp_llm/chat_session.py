import logging
from asp_llm.configuration import Configuration
from asp_llm.server import Server
from asp_llm.llm_client import LLMClient
import json

from asp_llm.stdio import AbstractIOHandler, StdIOHandler


class ChatSession:
    """Orchestrates the interaction between user, LLM, and tools."""

    def __init__(self, servers: list[Server], config: Configuration) -> None:
        self.servers: list[Server] = servers
        self.config: Configuration = config
        self.io: AbstractIOHandler = StdIOHandler()

    async def cleanup_servers(self) -> None:
        """Clean up all servers properly."""
        for server in reversed(self.servers):
            try:
                await server.cleanup()
            except Exception as e:
                logging.warning(f"Warning during final cleanup: {e}")

    async def process_llm_response(self, llm_response: dict) -> dict:
        """
        Process the LLM response and execute OpenAI tool calls if present.

        Args:
            llm_response: The response object from the OpenAI API.

        Returns:
            A list of messages to append to the conversation history (tool results).
        """
        tool_result_message = {}

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
                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps(result),
                        }
                    except Exception as e:
                        logging.error(f"Error executing tool {tool_name}: {e}")
                        tool_result_message = {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    break
            else:
                # No server found for this tool
                logging.error(f"No server found with tool: {tool_name}")
                tool_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({"error": f"No server found with tool: {tool_name}"}),
                }
        return tool_result_message

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
            openai_tools = []
            for server in self.servers:
                tools = await server.list_tools()
                all_tools.extend(tools)
                openai_tools.extend(await server.openai_tools())

            system_message = (
                "If you need further user input, ask for it directly.\n"
                "Afterwards, respond with an empty string to indicate you are ready for the next user input.\n\n"
                "Your task is to assist the user in developing an ASP (Answer Set programming) encoding.\n"
                "Use the tools to create a example and test instances for the problem,\n"
                "and develop an ASP encoding that captures the problem's requirements.\n"
                "Develop and test the output and syntax of this encoding step by step.\n"
                "Use a generate and test approach to develop the encoding.\n"
                "In the end, write the encoding to the disk.\n"
                ## TODO give ASP syntax rules and examples
            )

            asp_llm = LLMClient(self.io, system_message, self.config, openai_tools)

            user_input = self.io.get_input("You: ")

            asp_llm.add_message({"role": "user", "content": user_input})

            while True:
                try:
                    llm_response = asp_llm.get_response()
                    tool_result_message = await self.process_llm_response(llm_response)

                    if tool_result_message:
                        asp_llm.add_message(tool_result_message)
                        # Continue the loop to let LLM process tool results
                        continue

                    # Get the LLM's reply content
                    choice = llm_response.choices[0]
                    content = getattr(choice.message, "content", "")
                    if content == "":
                        # LLM requests further user input
                        user_input = self.io.get_input("You: ")
                        asp_llm.add_message({"role": "user", "content": user_input})
                        continue

                except KeyboardInterrupt:
                    logging.info("\nExiting...")
                    break

        finally:
            await self.cleanup_servers()
