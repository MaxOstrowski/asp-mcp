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

    async def process_llm_response(self, llm_response: dict) -> list[dict]:
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
                if tool_name == self.io.input_io_tool_name():
                    # Handle the input tool call
                    user_input = self.io.get_input("".join(arguments["prompt"]) + ": ")
                    tool_result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": user_input,
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
            openai_tools = [self.io.input_tool()]
            for server in self.servers:
                tools = await server.list_tools()
                all_tools.extend(tools)
                openai_tools.extend(await server.openai_tools())

            system_message = (
                "Your task is to assist the user in developing an ASP (Answer Set programming) encoding.\n"
                "Use the tools to create an example and test instances for the problem,\n"
                "and develop an ASP encoding that captures the problem's requirements.\n"
                "Develop and test the output and syntax of this encoding step by step.\n"
                "Use a generate and test approach to develop the encoding.\n"
                "In the end, write the encoding to the disk.\n"
                "If you need additional information, ask the user using the input tool.\n\n"
                "## ASP Rule Syntax\n"
                "**Fact:**\n"
                "Facts are used to describe the instance of the problem. They are always true.\n"
                "Example: `parent(alice, bob).` means Alice is a parent of Bob.\n\n"
                "**Choice Rule:**\n"
                "A choice rule allows an atom to be true or false based on the body.\n"
                "Example: `{selected(X)} :- candidate(X).` means X can be selected if it is a candidate.\n"
                "Choice rules are used to generate all possible candidate solutions in generate and test.\n"
                "**Normal Rule:**\n"
                "A normal rule has a head and a body. The head is true if the body is true.\n"
                "Example: `grandparent(X, Y) :- parent(X, Z), parent(Z, Y).` means X is a grandparent of Y if X is a parent of Z and Z is a parent of Y.\n\n"
                "Example with negation: `half_brother(X, Y) :- parent(Z, X), parent(Z, Y), not parent(W, X), not parent(W, Y), person(W).`\n"
                "Example with condition: `orphan(X) :- person(X), dead(Y) : parent(Y, X).` X is an orphan, if all parents Y are dead.\n"
                "Syntax conditions: `head(X) :- body1(X), condition(X) : c(1), c(2); body2(X).`\n\n"
                "**Integrity Constraint:**\n"
                "An integrity constraint is a rule that forbids certain combinations.\n"
                "Example: `:- parent(X, Y), parent(Y, X).` means there cannot be a parent-child relationship where both are parents of each other.\n\n"
                "This is the so called Test part in Generate and Test. It is used to remove invalid solutions.\n"
                "**Aggregate:**\n"
                "An aggregate allows counting or summing over sets of atoms.\n"
                "Example: `head(X) :- #count{Y : body(Y, X)} > N.` means the head is true if the count of Y satisfying the body is greater than N.\n"
                "Other aggregates include `#sum`, `#min`, `#max`.\n\n"
                "Optimization statements:\n `#minimize{W,X : selected(X), weight(X,W)}.`\n"
                "This means we want to minimize the sum of weights W for selected X.\n\n"
                "All variables in the head must be bound by the body.\n\n"
                "Use choice rules to generate candidates, normal rules to define relationships, integrity constraints to filter out invalid solutions.\n"
                "Use several parts of a file for the generate and test approach. "
                "The first part consists of preprocessing the facts, "
                "the second part(s) generates the choices, "
                "the next part removes invalid solutions using rules and integrity constraints, "
                "the last parts adds optimization and show statements.\n"
                "Do not add the whole encoding in one write operation!\n"
                "Before starting with the encoding, depict a plan of the generate and the constraints in natural language.\n"
                "Test each step of the encoding with the provided tools.\n\n"
            )

            asp_llm = LLMClient(self.io, system_message, self.config, openai_tools)

            user_input = self.io.get_input("You: ")

            asp_llm.add_message({"role": "user", "content": user_input})

            while True:
                try:
                    llm_response = asp_llm.get_response()
                    tool_result_messages = await self.process_llm_response(llm_response)

                    for msg in tool_result_messages:
                        asp_llm.add_message(msg)
                    if not tool_result_messages:
                        user_input = self.io.get_input("You: ")
                        asp_llm.add_message({"role": "user", "content": user_input})

                except KeyboardInterrupt:
                    logging.info("\nExiting...")
                    break

        finally:
            await self.cleanup_servers()
