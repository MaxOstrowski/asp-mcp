"""
ASP ModelContextProtocol Server
Exposes an MCP server that executes ASP code using clingo.
"""

import logging

logging.getLogger("mcp").setLevel(logging.WARNING)

from collections import defaultdict
from mcp.server.fastmcp import FastMCP
import clingo
from typing import Dict, Optional, Any


# In-memory virtual file manager
class VirtualFileManager:
    def __init__(self):
        self.files: Dict[str, list[str]] = defaultdict(list)

    def create_file(self, name: str) -> None:
        self.files[name] = {}

    def write_to_file(self, name: str, content: str, index: Optional[int] = None) -> None:
        if name not in self.files:
            self.create_file(name)
        if index is None:
            index = len(self.files[name])
        self.files[name][index] = content

    def delete_part_of_file(self, name: str, index: int) -> None:
        if name in self.files and index in self.files[name]:
            del self.files[name][index]

    def get_content(self, name: str) -> dict[int, str] | None:
        if name not in self.files:
            return None
        return self.files.get(name, {})

    def list_files(self):
        return list(self.files.keys())

    def write_file_to_disk(self, name: str) -> None:
        """Write the content of a virtual file to disk."""
        with open(name, "w") as f:
            content = self.get_content(name)
            if content is None:
                raise ValueError(f"File '{name}' does not exist.")
            for part in content.values():
                f.write(part + "\n")


# Singleton file manager
vfs = VirtualFileManager()

mcp = FastMCP("clingo")


@mcp.tool()
def create_virtual_file(filename: str) -> dict:
    """Create a new virtual file (overwrites if exists)."""
    try:
        vfs.create_file(filename)
        return {"result": f"File '{filename}' created."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def write_part_of_virtual_file(filename: str, content: str, part_index: Optional[int] = None) -> dict:
    """Write a part of a virtual file.
    If part_index is None, appends to the file."""
    try:
        vfs.write_to_file(filename, content, part_index)
        msg = _check_syntax(content)
        content = vfs.get_content(filename)
        ret = {"result": f"Appended to '{filename}'.", "content": content}
        if msg:
            ret["error"] = msg
        return ret
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def delete_part_of_virtual_file(filename: str, part_index: int) -> dict:
    """Delete a part of a virtual file."""
    try:
        vfs.delete_part_of_file(filename, part_index)
        return {"result": f"Deleted part {part_index} of '{filename}'.", "content": vfs.get_content(filename)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_virtual_file_content(filename: str) -> dict:
    """Get the current content of a virtual file."""
    try:
        content = vfs.get_content(filename)
        if content is None:
            return {"error": f"File '{filename}' does not exist."}
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def list_virtual_files() -> dict:
    """List all virtual files."""
    try:
        files = vfs.list_files()
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def write_virtual_file_to_disk(filename: str) -> dict:
    """Write the content of a virtual file to disk."""
    try:
        vfs.write_file_to_disk(filename)
        return {"result": f"File '{filename}' written to disk."}
    except Exception as e:
        return {"error": str(e)}



### TODO: Also allow to inspect ground rules (maybe sample) of single parts of the file.
### TODO: use tree-sitter https://github.com/potassco/tree-sitter-clingo to check syntax with
### better messages and to parse the encoding while writing to a file.
### TODO: add clintest tool to test the encoding
### TODO: clingraph support to visualize the encoding
@mcp.tool()
def check_syntax(filenames: list[str]) -> dict:
    """Check syntax of a virtual file using clingo."""
    log_messages = []

    def logger(code, msg):
        log_messages.append(f"[{code.name}] {msg}")

    ctl = clingo.Control(logger=logger)
    for filename in filenames:
        content = vfs.get_content(filename)
        if content is None:
            return {"error": f"File '{filename}' does not exist."}
        content = "\n".join(content.values())
        msg = _check_syntax(content)
        if msg:
            return {"error": msg}
    return {"result": "Syntax OK"}

def _check_syntax(content: str) -> str:
    """Check syntax of a single content string using clingo."""
    log_messages = []

    def logger(code, msg):
        log_messages.append(f"[{code.name}] {msg}")

    ctl = clingo.Control(logger=logger)
    try:
        ctl.add("base", [], content)
        ctl.ground([("base", [])])
    except Exception as e:
        error_msg = f"Syntax error: {e}"
        if log_messages:
            error_msg += "\nClingo log:\n" + "\n".join(log_messages)
        return error_msg
    return ""


def select_statistics(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Select and format relevant statistics from clingo."""
    selected_stats = {}

    selected_stats["program"] = {}
    selected_stats["program"]["vars"] = stats["problem"]["generator"]["vars"]
    selected_stats["program"]["vars_eliminated"] = stats["problem"]["generator"]["vars_eliminated"]
    selected_stats["program"]["constraints"] = stats["problem"]["generator"]["constraints"]
    selected_stats["program"]["constraints_binary"] = stats["problem"]["generator"]["constraints_binary"]
    selected_stats["program"]["constraints_ternary"] = stats["problem"]["generator"]["constraints_ternary"]

    selected_stats["times"] = stats["accu"]["times"]
    selected_stats["enumeration"] = stats["accu"]["models"]

    selected_stats["solving"] = {}
    selected_stats["solving"]["choices"] = stats["accu"]["solving"]["solvers"]["choices"]
    selected_stats["solving"]["conflicts"] = stats["accu"]["solving"]["solvers"]["conflicts"]
    return selected_stats

@mcp.tool()
def run_clingo(
    filenames: list[str],
    max_models: int = 1,
    const_params: Optional[list[str]] = None,
) -> dict:
    """Run clingo on the virtual file(s) and return the output.
    max_models: Maximum number of models to return, 0 means all models.
    const_params: Additional constants of the form <constant>=<value> passed to the encoding."""
    if not filenames:
        return {"error": "No files provided."}
    log_messages = []
    if const_params is None:
        const_params = []

    def logger(code, msg):
        log_messages.append(f"[{code.name}] {msg}")

    try:
        ctl_args = ["--models", str(max_models)]
        for p in const_params:
            ctl_args.extend(["--const", str(p)])
        ctl_args.append("--stats")
        ctl = clingo.Control(ctl_args, logger=logger)
        for f in filenames:
            content = vfs.get_content(f)
            if content is None:
                return {"error": f"File '{f}' does not exist."}
            content = "\n".join(content.values())
            ctl.add("base", [], content)

        ctl.ground([("base", [])])
        models = {}
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                models[f"Answer {model.number}"] = [str(atom) for atom in model.symbols(shown=True)]
        if not models:
            result = {"result": "UNSATISFIABLE"}
        else:
            result = {"models": models}
        result["statistics"] = select_statistics(ctl.statistics)
        return result
    except Exception as e:
        error_msg = f"Error running clingo: {e}"
        if log_messages:
            error_msg += "\nClingo log:\n" + "\n".join(log_messages)
        return {"error": error_msg}
    



def main():
    mcp.run()


# Entry point for console_scripts
def main():
    mcp.run()


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
