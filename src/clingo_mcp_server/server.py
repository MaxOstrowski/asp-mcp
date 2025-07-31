"""
ASP ModelContextProtocol Server
Exposes an MCP server that executes ASP code using clingo.
"""

import pytest
import importlib
import logging
import os
import tempfile
import uuid

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
        self.files[name][str(index)] = content

    def delete_part_of_file(self, name: str, index: int) -> None:
        if name in self.files and str(index) in self.files[name]:
            del self.files[name][str(index)]

    def get_content(self, name: str) -> dict[str, str] | None:
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
    """Create a new virtual file (overwrites if exists).
    Use ending .lp for ASP encodings.
    Use ending .py for test files."""
    try:
        vfs.create_file(filename)
        return {"result": f"File '{filename}' created."}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def write_part_of_virtual_file(filename: str, content: str, part_index: Optional[int] = None) -> dict:
    """Write a part of a virtual file.
    Parts are usually increasing numbers starting from 0.
    Single parts can be overwritten  or deleted.
    If part_index is None, a new part with the next index is created."""
    try:
        vfs.write_to_file(filename, content, part_index)
        ret = {"result": f"Appended to '{filename}'."}
        # if filename ends in lp
        if filename.endswith(".lp"):
            msg = _check_syntax(content)
            if msg:
                ret["error"] = msg
            else:
                ret["hint"] = "Remember to write tests for this part of your encoding."
        content = vfs.get_content(filename)
        ret["content"] = content
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
### TODO: support for clingodl, clingcon
### TODO: debugging technique to add error in head of integrity and minimize amount of errors
### TODO: check examples in controlled natural language from https://github.com/dodaro/cnl2asp
### TODO: give more planning structure, create choices, write tests about expected solutions for example, etc...

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


@mcp.tool()
def run_tests() -> dict:
    """
    Run all test files with ending .py.
    Tests enumerate and check all models of a (part of) encoding.
    You can:

    def enumerate_at_most_n_models(num_models: int, constants: list[str], file_parts: list[tuple[str, list[int]]]) -> tuple[SolveResult, Model]:
    def enumerate_all_models(constants: list[str], file_parts: list[tuple[str, list[int]]]) -> tuple[SolveResult, list[Model]]:
    at most 10000 models are returned for performance reasons.

    Here is an example of a test1.py file that checks the n-queens problem:

    ```
    def test_solution_integrity():

        res, models = enumerate_all_models(["n=8"], [("encoding.lp", [0,1,2])])
        assert res.satisfiable
        assert len(models) == 92
        for model in models:
            queens: dict[int, int] = {}
            for atom in model.symbols:
                if atom.name == "queen":
                    queens[atom.arguments[0].number] = atom.arguments[1].number
            assert len(queens) == 8
            assert len(set(queens.values())) == 8  # all columns must be unique
            assert len(set(queens.keys())) == 8 # all rows must be unique
            assert len(set(queens[r] - r for r in queens)) == 8  # all diagonals must be unique
            assert len(set(queens[r] + r for r in queens)) == 8
    ```
    """
    result = {
        "tests": [],
    }
    for name in vfs.files.keys():
        if name.endswith(".py"):
            result["tests"].append(run_test(name))

    return result

def run_test(testfile: str) -> dict:
    """
    Run a single test file and check its output.
    """
    result = {"status": "error"}
    test_code = "__vfs = "
    test_code += repr(dict(vfs.files))  # Serialize the virtual file system state
    test_code += "\n\n"
    # load test code from resource file test_gen.py
    with importlib.resources.files("clingo_mcp_server.resources").joinpath("test_gen.py").open("r", encoding="utf-8") as f:
        test_code += f.read()

    test_code += "\n"
    test_code += "".join(vfs.get_content(testfile).values())

    import sys
    import io
    with tempfile.TemporaryDirectory() as tmpdirname:
        test_file = os.path.join(tmpdirname, f"test_file_{uuid.uuid4().hex}.py")
        with open(test_file, "w") as f:
            f.write(test_code)
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        try:
            sys.stdout = stdout_buffer
            sys.stderr = stderr_buffer
            sys.dont_write_bytecode = True
            exit_code = pytest.main([test_file])  # returns exit code (0 = success)
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr
            sys.dont_write_bytecode = False
        result = {
            "stdout": stdout_buffer.getvalue(),
            "stderr": stderr_buffer.getvalue(),
        }
        if exit_code == 0:
            result["status"] = "success"
            
    return result


def main():
    #run_tests()
    mcp.run()


if __name__ == "__main__":
    main()
