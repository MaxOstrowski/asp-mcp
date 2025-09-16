from typing import Any


class Summarizer:
    """A tool to compress a list of OpenAI chat messages in place by removing some messages."""

    @staticmethod
    def compress_messages(messages: list[dict[str, Any]]) -> int:
        """
        Compresses the list of OpenAI chat messages in place by removing tool_calls and tool role answers.
        Keeps first and last message. If the 3rd last message contains a test tool call, keeps it and its answer.
        """
        num = 0
        if len(messages) <= 2:
            return num
        
        # list of ids of all messages containing tool calls (except first and last)
        tool_call_message_ids = [i for i, msg in enumerate(messages[:-1]) if "tool_calls" in msg and msg["tool_calls"]]
        tool_answer_message_ids = [i for i, msg in enumerate(messages[:-1]) if msg["role"] == "tool"]


        # last message id and tool call index for the function name run_tests
        last_msg_id = None
        tool_call_id = None
        last_tool_call_msg_id = None
        tool_call_index = None
        for i in reversed(tool_call_message_ids):
            if any(tc.get("function", {}).get("name", "") == "run_tests" for tc in messages[i]["tool_calls"]):
                last_msg_id = i
                # get the index where the any hits
                tool_call_index = next(idx for idx, tc in enumerate(messages[i]["tool_calls"]) if tc.get("function", {}).get("name", "") == "run_tests")
                tool_call_id = messages[i]["tool_calls"][tool_call_index]["id"]
                for j in reversed(tool_answer_message_ids):
                    if messages[j].get("tool_call_id") == tool_call_id:
                        last_tool_call_msg_id = j
                        break

                break

        if last_msg_id is not None:
            # remove message from deletion list
            tool_call_message_ids.remove(last_msg_id)
            tool_answer_message_ids.remove(last_tool_call_msg_id)

            # remove all tool calls except the run_tests call from the last_msg_id message
            messages[last_msg_id]["tool_calls"] = [messages[last_msg_id]["tool_calls"][tool_call_index]]
            
        # delete all tool call messages and their answers
        to_delete_ids = sorted(tool_call_message_ids + tool_answer_message_ids, reverse=True)
        for i in to_delete_ids:
            if i in tool_answer_message_ids:
                del messages[i]
            elif i in tool_call_message_ids:
                del messages[i]["tool_calls"]
                if "content" not in messages[i] or not messages[i]["content"]:
                    del messages[i]
            num += 1
        
        return num

    @staticmethod
    def tool() -> dict:
        """Get the description of the summarizer."""
        return {
            "type": "function",
            "function": {
                "name": Summarizer.name(),
                "description": "Compresses history of the LLM to improve reasoning.",
            },
        }

    @staticmethod
    def name() -> str:
        """Return the name of the summarizer."""
        return "compress_messages"
